"""서비스 레이어 테스트 (T-I18).

> 마지막 수정: 2026-02-10 23:30:00

DocumentService, CompanyService, WebhookService 단위 테스트.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.db.models.company import Company
from src.api.db.models.document import Document, DocumentStatus
from src.api.db.models.user import User
from src.api.exceptions import AuthorizationError, NotFoundError
from src.api.schemas.documents import DocumentCreate
from src.api.services.company_service import CompanyService
from src.api.services.document_service import DocumentService
from src.api.services.webhook_service import WebhookService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(role: str = "USER") -> MagicMock:
    """테스트 User mock을 생성한다."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    return user


def _make_document(owner_id: uuid.UUID, **kwargs) -> MagicMock:
    """테스트 Document mock을 생성한다."""
    doc = MagicMock(spec=Document)
    doc.id = kwargs.get("id", uuid.uuid4())
    doc.owner_id = owner_id
    doc.corp_code = kwargs.get("corp_code", "00123456")
    doc.company_name = kwargs.get("company_name", "테스트 주식회사")
    doc.status = kwargs.get("status", DocumentStatus.PENDING.value)
    doc.progress_pct = kwargs.get("progress_pct", 0)
    doc.pptx_path = kwargs.get("pptx_path")
    doc.pdf_path = kwargs.get("pdf_path")
    doc.celery_task_id = kwargs.get("celery_task_id")
    doc.generation_config = kwargs.get("generation_config", {})
    return doc


# ---------------------------------------------------------------------------
# DocumentService
# ---------------------------------------------------------------------------


class TestDocumentServiceCreate:
    """DocumentService.create_document 테스트."""

    @pytest.mark.asyncio
    async def test_create_document_db_and_task(self) -> None:
        """DB 레코드 생성 및 Celery task_id 저장."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        # 중복 체크 쿼리: 진행 중인 문서 없음
        dup_check_result = MagicMock()
        dup_check_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=dup_check_result)

        with patch(
            "src.api.services.document_service.DocumentService.__init__",
            return_value=None,
        ):
            service = DocumentService.__new__(DocumentService)
            service.db = db

        create_data = DocumentCreate(
            company_name="테스트 주식회사",
            project_name="프로젝트 A",
            corp_code="00123456",
            im_style="FULL",
            industry="tech",
        )

        with patch("src.api.tasks.generate_im.generate_im_task.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="task-123")
            await service.create_document(uuid.uuid4(), create_data)

        db.add.assert_called_once()
        assert db.commit.call_count >= 2  # 생성 + task_id 저장
        mock_delay.assert_called_once()


class TestDocumentServiceGet:
    """DocumentService.get_document 테스트."""

    @pytest.mark.asyncio
    async def test_get_document_owner_access(self) -> None:
        """소유자 접근 성공."""
        user = _make_user()
        doc = _make_document(owner_id=user.id)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service.get_document(doc.id, user)
        assert result == doc

    @pytest.mark.asyncio
    async def test_get_document_admin_access(self) -> None:
        """ADMIN 접근 성공."""
        admin = _make_user(role="ADMIN")
        other_user_id = uuid.uuid4()
        doc = _make_document(owner_id=other_user_id)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        result = await service.get_document(doc.id, admin)
        assert result == doc

    @pytest.mark.asyncio
    async def test_get_document_forbidden(self) -> None:
        """타 사용자 문서 접근 시 403."""
        user = _make_user()
        other_user_id = uuid.uuid4()
        doc = _make_document(owner_id=other_user_id)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        with pytest.raises(AuthorizationError):
            await service.get_document(doc.id, user)

    @pytest.mark.asyncio
    async def test_get_document_not_found(self) -> None:
        """존재하지 않는 문서 조회 시 404."""
        user = _make_user()

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        with pytest.raises(NotFoundError):
            await service.get_document(uuid.uuid4(), user)


class TestDocumentServiceList:
    """DocumentService.list_documents 테스트."""

    @pytest.mark.asyncio
    async def test_list_documents_user_filter(self) -> None:
        """USER는 본인 문서만 조회."""
        user = _make_user()

        db = AsyncMock()
        count_mock = MagicMock()
        count_mock.scalar_one.return_value = 0
        items_mock = MagicMock()
        items_mock.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(side_effect=[count_mock, items_mock])

        service = DocumentService(db)
        items, total = await service.list_documents(user, offset=0, limit=20)
        assert total == 0
        assert items == []


class TestDocumentServiceDownload:
    """DocumentService.get_download_path 테스트."""

    @pytest.mark.asyncio
    async def test_get_download_path_not_completed(self) -> None:
        """PENDING 상태 문서 다운로드 시 404."""
        user = _make_user()
        doc = _make_document(owner_id=user.id, status=DocumentStatus.PENDING.value)

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = doc
        db.execute = AsyncMock(return_value=result_mock)

        service = DocumentService(db)
        with pytest.raises(NotFoundError, match="생성 완료되지"):
            await service.get_download_path(doc.id, "pptx", user)


# ---------------------------------------------------------------------------
# CompanyService
# ---------------------------------------------------------------------------


class TestCompanyServiceFetch:
    """CompanyService.fetch_company 테스트."""

    @pytest.mark.asyncio
    async def test_company_fetch_upsert_new(self) -> None:
        """신규 company 생성 + Celery 디스패치."""
        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        service = CompanyService(db)
        with patch(
            "src.api.tasks.fetch_company.fetch_company_task.delay"
        ) as mock_delay:
            mock_delay.return_value = MagicMock(id="task-456")
            await service.fetch_company("00123456")

        db.add.assert_called_once()
        mock_delay.assert_called_once_with("00123456")


class TestCompanyServiceGet:
    """CompanyService.get_company 테스트."""

    @pytest.mark.asyncio
    async def test_company_cache_expiry_refresh(self) -> None:
        """캐시 만료 시 자동 재수집 트리거."""
        company = MagicMock(spec=Company)
        company.corp_code = "00123456"
        company.cache_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        company.fetch_status = "COMPLETED"

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = company
        db.execute = AsyncMock(return_value=result_mock)
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        service = CompanyService(db)
        with patch(
            "src.api.tasks.fetch_company.fetch_company_task.delay"
        ) as mock_delay:
            mock_delay.return_value = MagicMock(id="task-789")
            await service.get_company("00123456")

        assert company.fetch_status == "REFRESHING"
        mock_delay.assert_called_once_with("00123456")


# ---------------------------------------------------------------------------
# WebhookService
# ---------------------------------------------------------------------------


class TestWebhookService:
    """WebhookService 테스트."""

    @pytest.mark.asyncio
    async def test_webhook_success(self) -> None:
        """웹훅 전송 성공."""
        with patch(
            "src.api.services.webhook_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await WebhookService.trigger(
                url="https://example.com/hook",
                payload={"status": "COMPLETED"},
            )
        assert result is True

    @pytest.mark.asyncio
    async def test_webhook_retry_on_failure(self) -> None:
        """웹훅 실패 시 3회 재시도."""
        with patch(
            "src.api.services.webhook_service.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("connection error"))
            mock_client_cls.return_value.__aenter__ = AsyncMock(
                return_value=mock_client
            )
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await WebhookService.trigger(
                url="https://example.com/hook",
                payload={"status": "COMPLETED"},
                retries=3,
            )
        assert result is False
        assert mock_client.post.call_count == 3
