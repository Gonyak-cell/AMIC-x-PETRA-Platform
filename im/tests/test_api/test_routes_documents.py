"""Documents 라우트 테스트 (T-I16).

> 마지막 수정: 2026-03-13 22:38:00

POST/GET /api/v1/documents 엔드포인트 검증.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.db.models.document import Document, DocumentStatus
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.exceptions import AuthorizationError, NotFoundError


def _make_user(role: str = "USER") -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    user.email = "test@example.com"
    return user


def _make_document(owner_id: uuid.UUID, **kwargs) -> MagicMock:
    """테스트 Document mock."""
    now = datetime.now(timezone.utc)
    doc = MagicMock(spec=Document)
    doc.id = kwargs.get("id", uuid.uuid4())
    doc.owner_id = owner_id
    doc.corp_code = "00123456"
    doc.company_name = "테스트 주식회사"
    doc.project_name = None
    doc.data_source = "MANUAL"
    doc.industry = None
    doc.im_style = "FULL"
    doc.sections = []
    doc.status = kwargs.get("status", DocumentStatus.PENDING.value)
    doc.progress_pct = kwargs.get("progress_pct", 0)
    doc.celery_task_id = kwargs.get("celery_task_id", "task-123")
    doc.pptx_path = kwargs.get("pptx_path")
    doc.pdf_path = kwargs.get("pdf_path")
    doc.file_size_bytes = kwargs.get("file_size_bytes")
    doc.generation_config = {}
    doc.created_at = now
    doc.updated_at = now
    doc.completed_at = kwargs.get("completed_at")
    doc.stage_details = kwargs.get("stage_details")
    doc.quality_score = kwargs.get("quality_score")
    doc.quality_status = kwargs.get("quality_status")
    doc.quality_issues = kwargs.get("quality_issues")
    doc.slide_count = kwargs.get("slide_count")
    doc.generation_profile = kwargs.get("generation_profile")
    doc.supported_formats = kwargs.get("supported_formats")
    return doc


@pytest.fixture
def test_user() -> MagicMock:
    return _make_user()


@pytest.fixture
def route_app(test_user):
    """라우트 테스트용 앱 (인증 우회)."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    return app


@pytest.fixture
async def route_client(route_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=route_app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def unauth_app():
    """인증 우회 없는 앱."""
    return create_app()


@pytest.fixture
async def unauth_client(unauth_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=unauth_app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# POST /api/v1/documents
# ---------------------------------------------------------------------------


class TestCreateDocument:
    """POST /api/v1/documents 테스트."""

    @pytest.mark.asyncio
    async def test_create_document_returns_202(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """정상 생성 시 202."""
        doc = _make_document(owner_id=test_user.id)
        with patch(
            "src.api.routes.documents.DocumentService.create_document",
            new_callable=AsyncMock,
            return_value=doc,
        ):
            response = await route_client.post(
                "/api/v1/documents",
                json={
                    "company_name": "테스트 주식회사",
                    "project_name": "프로젝트 A",
                    "corp_code": "00123456",
                    "im_style": "FULL",
                },
            )
        assert response.status_code == 202
        data = response.json()
        assert data["corp_code"] == "00123456"
        assert data["status"] == "PENDING"

    @pytest.mark.asyncio
    async def test_create_document_invalid_corp_code(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """잘못된 corp_code 시 422."""
        response = await route_client.post(
            "/api/v1/documents",
            json={"corp_code": "ABCD1234"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_document_unauthorized(
        self, unauth_client: AsyncClient
    ) -> None:
        """인증 없이 요청 시 401."""
        response = await unauth_client.post(
            "/api/v1/documents",
            json={"corp_code": "00123456"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{id}
# ---------------------------------------------------------------------------


class TestGetDocument:
    """GET /api/v1/documents/{id} 테스트."""

    @pytest.mark.asyncio
    async def test_get_document_success(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """정상 조회 시 200."""
        doc = _make_document(owner_id=test_user.id)
        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            return_value=doc,
        ):
            response = await route_client.get(f"/api/v1/documents/{doc.id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """존재하지 않는 문서 404."""
        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            side_effect=NotFoundError("Document", "abc"),
        ):
            response = await route_client.get(f"/api/v1/documents/{uuid.uuid4()}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_document_forbidden(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """타 사용자 문서 접근 시 403."""
        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            side_effect=AuthorizationError(required_role="ADMIN"),
        ):
            response = await route_client.get(f"/api/v1/documents/{uuid.uuid4()}")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/v1/documents/{id}/download
# ---------------------------------------------------------------------------


class TestDownloadDocument:
    """GET /api/v1/documents/{id}/download 테스트."""

    @pytest.mark.asyncio
    async def test_download_before_complete(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """미완성 문서 다운로드 시 404."""
        mock_doc = _make_document(owner_id=test_user.id, status="PENDING")
        with (
            patch(
                "src.api.routes.documents.DocumentService.get_document",
                new_callable=AsyncMock,
                return_value=mock_doc,
            ),
            patch(
                "src.api.routes.documents.DocumentService.get_download_path",
                new_callable=AsyncMock,
                side_effect=NotFoundError(
                    "File", "문서가 아직 생성 완료되지 않았습니다"
                ),
            ),
        ):
            response = await route_client.get(
                f"/api/v1/documents/{uuid.uuid4()}/download?format=pptx"
            )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_quality_failed_blocked(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """QUALITY_FAILED 문서 다운로드 차단 (422)."""
        mock_doc = _make_document(owner_id=test_user.id, status="QUALITY_FAILED")
        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            return_value=mock_doc,
        ):
            response = await route_client.get(
                f"/api/v1/documents/{uuid.uuid4()}/download?format=pptx"
            )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/documents
# ---------------------------------------------------------------------------


class TestListDocuments:
    """GET /api/v1/documents 테스트."""

    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self, route_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """페이지네이션 동작 검증."""
        doc = _make_document(owner_id=test_user.id)
        with patch(
            "src.api.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
            return_value=([doc], 1),
        ):
            response = await route_client.get("/api/v1/documents?offset=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["offset"] == 0
        assert data["limit"] == 10

    @pytest.mark.asyncio
    async def test_list_documents_admin_sees_all(
        self, route_app, route_client: AsyncClient
    ) -> None:
        """ADMIN 전체 조회."""
        admin = _make_user(role="ADMIN")
        route_app.dependency_overrides[get_current_user] = lambda: admin
        doc = _make_document(owner_id=uuid.uuid4())
        with patch(
            "src.api.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
            return_value=([doc], 1),
        ):
            response = await route_client.get("/api/v1/documents")
        assert response.status_code == 200
        assert response.json()["total"] == 1
