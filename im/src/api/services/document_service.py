"""Document 서비스 레이어 (T-I18).

> 마지막 수정: 2026-02-17 22:55:00

DB CRUD + Celery 태스크 디스패치 + 권한 검증.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.db.models.document import Document, DocumentStatus
from src.api.db.models.user import User
from src.api.exceptions import AuthorizationError, ConflictError, NotFoundError
from src.api.schemas.documents import DocumentCreate


class DocumentService:
    """Document 관련 비즈니스 로직."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_document(
        self,
        owner_id: UUID,
        create_data: DocumentCreate,
    ) -> Document:
        """새 문서를 생성하고 Celery 태스크를 디스패치한다.

        Args:
            owner_id: 소유자 사용자 ID.
            create_data: 생성 요청 데이터.

        Returns:
            생성된 Document 인스턴스.

        Raises:
            ConflictError: 동일 corp_code로 진행 중인 문서가 있을 때.
        """
        from src.api.tasks.generate_im import generate_im_task

        # corp_code가 있는 경우에만 진행 중 문서 중복 체크
        in_progress_statuses = [
            DocumentStatus.PENDING.value,
            DocumentStatus.COLLECTING.value,
            DocumentStatus.ANALYZING.value,
            DocumentStatus.GENERATING.value,
            DocumentStatus.RENDERING.value,
        ]
        if create_data.corp_code:
            existing = await self.db.execute(
                select(Document).where(
                    Document.corp_code == create_data.corp_code,
                    Document.status.in_(in_progress_statuses),
                )
            )
            if existing.scalar_one_or_none():
                raise ConflictError(
                    "Document",
                    f"corp_code={create_data.corp_code} (이미 진행 중인 문서가 있습니다)",
                )

        document = Document(
            owner_id=owner_id,
            corp_code=create_data.corp_code,
            company_name=create_data.company_name,
            project_name=create_data.project_name,
            data_source=create_data.data_source,
            im_style=create_data.im_style,
            sections=create_data.sections,
            generation_config={
                "industry": create_data.industry,
                "webhook_url": create_data.webhook_url,
                "pdf_password": create_data.pdf_password,
                "ppt_design_style": create_data.ppt_design_style,
                "collab_partner_name": create_data.collab_partner_name,
            },
            status=DocumentStatus.PENDING.value,
            progress_pct=0,
        )
        self.db.add(document)
        # Fix #6: flush로 ID 확보 후, Celery dispatch 성공 시에만 commit
        # Fix #7: partial unique index로 TOCTOU race condition 방어
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            if "uq_documents_corp_code_active" in str(exc.orig):
                raise ConflictError(
                    "Document",
                    f"corp_code={create_data.corp_code} (이미 진행 중인 문서가 있습니다)",
                ) from exc
            raise

        try:
            task = generate_im_task.delay(
                str(document.id),
                create_data.corp_code,
                document.generation_config,
                create_data.data_source,
            )
            document.celery_task_id = task.id
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise

        await self.db.refresh(document)
        return document

    async def get_document(
        self,
        document_id: UUID,
        current_user: User,
    ) -> Document:
        """문서를 조회한다 (권한 검증 포함).

        Args:
            document_id: 문서 ID.
            current_user: 현재 사용자.

        Returns:
            Document 인스턴스.

        Raises:
            NotFoundError: 문서가 없을 때.
            AuthorizationError: 권한 없을 때.
        """
        result = await self.db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if document is None:
            raise NotFoundError("Document", str(document_id))

        if current_user.role != "ADMIN" and document.owner_id != current_user.id:
            raise AuthorizationError(required_role="ADMIN")

        return document

    async def list_documents(
        self,
        current_user: User,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[Document], int]:
        """문서 목록을 조회한다 (페이지네이션).

        ADMIN은 전체 조회, 일반 사용자는 본인 것만.

        Args:
            current_user: 현재 사용자.
            offset: 시작 오프셋.
            limit: 페이지 크기.
            search: 검색어 (company_name, project_name, corp_code ILIKE).

        Returns:
            (문서 리스트, 전체 개수) 튜플.
        """
        base_query = select(Document)
        if current_user.role != "ADMIN":
            base_query = base_query.where(Document.owner_id == current_user.id)

        if search:
            pattern = f"%{search}%"
            filters = [
                Document.company_name.ilike(pattern),
                Document.project_name.ilike(pattern),
            ]
            # corp_code는 nullable이므로 IS NOT NULL 조건 포함
            filters.append(
                Document.corp_code.isnot(None) & Document.corp_code.ilike(pattern)
            )
            base_query = base_query.where(or_(*filters))

        count_result = await self.db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total = count_result.scalar_one()

        query = (
            base_query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def delete_document(
        self,
        document_id: UUID,
        current_user: User,
    ) -> None:
        """문서를 삭제한다 (소유자 또는 ADMIN만).

        진행 중인 문서는 삭제할 수 없다.

        Args:
            document_id: 문서 ID.
            current_user: 현재 사용자.

        Raises:
            NotFoundError: 문서가 없을 때.
            AuthorizationError: 권한 없을 때.
            ConflictError: 진행 중인 문서를 삭제하려 할 때.
        """
        document = await self.get_document(document_id, current_user)

        in_progress_statuses = [
            DocumentStatus.PENDING.value,
            DocumentStatus.COLLECTING.value,
            DocumentStatus.ANALYZING.value,
            DocumentStatus.GENERATING.value,
            DocumentStatus.RENDERING.value,
        ]
        if document.status in in_progress_statuses:
            raise ConflictError(
                "Document",
                f"진행 중인 문서는 삭제할 수 없습니다 (status={document.status})",
            )

        await self.db.delete(document)
        await self.db.commit()

    async def get_download_path(
        self,
        document_id: UUID,
        format: str,
        current_user: User,
    ) -> Path:
        """다운로드 파일 경로를 반환한다.

        Args:
            document_id: 문서 ID.
            format: "pptx" 또는 "pdf".
            current_user: 현재 사용자.

        Returns:
            파일 절대 경로.

        Raises:
            NotFoundError: 문서/파일이 없을 때.
        """
        document = await self.get_document(document_id, current_user)

        if document.status != DocumentStatus.COMPLETED.value:
            raise NotFoundError(
                "File",
                f"문서가 아직 생성 완료되지 않았습니다 (status={document.status})",
            )

        file_path_str = document.pptx_path if format == "pptx" else document.pdf_path
        if not file_path_str:
            raise NotFoundError("File", f"{format.upper()} 파일이 생성되지 않았습니다")

        file_path = Path(file_path_str)
        if not file_path.exists():
            raise NotFoundError("File", f"파일을 찾을 수 없습니다: {file_path_str}")

        return file_path
