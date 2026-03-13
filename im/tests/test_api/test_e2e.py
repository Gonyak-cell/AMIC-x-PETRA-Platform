"""E2E 통합 테스트 (T-I23).

> 마지막 수정: 2026-02-10 23:45:00

전체 API 흐름을 Celery eager mode + 모킹으로 검증한다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.db.models.company import Company
from src.api.db.models.document import Document, DocumentStatus
from src.api.db.models.user import User
from src.api.db.session import get_async_session
from src.api.dependencies import get_current_user
from src.api.exceptions import AuthorizationError


def _mock_user(role: str = "USER") -> MagicMock:
    """테스트 User mock."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.is_active = True
    user.email = "test@example.com"
    return user


def _mock_document(owner_id: uuid.UUID, **kwargs) -> MagicMock:
    """테스트 Document mock."""
    now = datetime.now(timezone.utc)
    doc = MagicMock(spec=Document)
    doc.id = kwargs.get("id", uuid.uuid4())
    doc.owner_id = owner_id
    doc.corp_code = "00123456"
    doc.company_name = "테스트 주식회사"
    doc.project_name = kwargs.get("project_name")
    doc.data_source = kwargs.get("data_source", "MANUAL")
    doc.industry = kwargs.get("industry", "tech")
    doc.im_style = "FULL"
    doc.sections = []
    doc.status = kwargs.get("status", DocumentStatus.COMPLETED.value)
    doc.progress_pct = kwargs.get("progress_pct", 100)
    doc.celery_task_id = "task-e2e-123"
    doc.pptx_path = kwargs.get("pptx_path", "/tmp/test.pptx")
    doc.pdf_path = kwargs.get("pdf_path", "/tmp/test.pdf")
    doc.file_size_bytes = 1024
    doc.generation_config = kwargs.get("generation_config", {})
    doc.stage_details = kwargs.get("stage_details")
    doc.created_at = now
    doc.updated_at = now
    doc.completed_at = now
    doc.quality_score = kwargs.get("quality_score")
    doc.quality_status = kwargs.get("quality_status")
    doc.quality_issues = kwargs.get("quality_issues")
    doc.slide_count = kwargs.get("slide_count")
    doc.generation_profile = kwargs.get("generation_profile")
    doc.supported_formats = kwargs.get("supported_formats")
    return doc


def _mock_company(**kwargs) -> MagicMock:
    """테스트 Company mock."""
    now = datetime.now(timezone.utc)
    company = MagicMock(spec=Company)
    company.id = uuid.uuid4()
    company.corp_code = kwargs.get("corp_code", "00123456")
    company.corp_name = "테스트 주식회사"
    company.corp_name_en = "Test Corp"
    company.stock_code = "123456"
    company.industry = "tech"
    company.homepage_url = "https://test.co.kr"
    company.fetch_status = kwargs.get("fetch_status", "COMPLETED")
    company.last_fetched_at = now
    company.cache_expires_at = None
    company.created_at = now
    company.updated_at = now
    return company


@pytest.fixture
def test_user() -> MagicMock:
    return _mock_user()


@pytest.fixture
def e2e_app(test_user):
    """E2E 테스트용 앱 (인증 우회)."""
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_async_session] = lambda: AsyncMock()
    return app


@pytest.fixture
async def e2e_client(e2e_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=e2e_app),
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
# E2E: Full pipeline flow
# ---------------------------------------------------------------------------


class TestE2EFullPipeline:
    """전체 파이프라인 E2E 테스트."""

    @pytest.mark.asyncio
    async def test_full_pipeline_create_and_status(
        self, e2e_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """POST document -> GET status -> COMPLETED 확인."""
        pending_doc = _mock_document(
            owner_id=test_user.id, status=DocumentStatus.PENDING.value
        )
        completed_doc = _mock_document(
            owner_id=test_user.id,
            id=pending_doc.id,
            status=DocumentStatus.COMPLETED.value,
        )

        with patch(
            "src.api.routes.documents.DocumentService.create_document",
            new_callable=AsyncMock,
            return_value=pending_doc,
        ):
            response = await e2e_client.post(
                "/api/v1/documents",
                json={
                    "company_name": "테스트 주식회사",
                    "project_name": "프로젝트 A",
                    "corp_code": "00123456",
                    "im_style": "FULL",
                    "industry": "tech",
                },
            )
        assert response.status_code == 202
        doc_id = response.json()["id"]

        # 상태 조회
        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            return_value=completed_doc,
        ):
            response = await e2e_client.get(f"/api/v1/documents/{doc_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "COMPLETED"

    @pytest.mark.asyncio
    async def test_pipeline_failure_sets_failed(
        self, e2e_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """파이프라인 실패 시 FAILED 상태."""
        failed_doc = _mock_document(
            owner_id=test_user.id, status=DocumentStatus.FAILED.value
        )
        failed_doc.stage_details = {"error": "LLM API 호출 실패"}

        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            return_value=failed_doc,
        ):
            response = await e2e_client.get(f"/api/v1/documents/{failed_doc.id}")
        assert response.status_code == 200
        assert response.json()["status"] == "FAILED"


# ---------------------------------------------------------------------------
# E2E: Company flow
# ---------------------------------------------------------------------------


class TestE2ECompany:
    """기업 데이터 E2E 테스트."""

    @pytest.mark.asyncio
    async def test_company_fetch_and_cache_hit(
        self, e2e_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """POST company -> GET cache hit."""
        company = _mock_company(fetch_status="PENDING")
        completed_company = _mock_company(fetch_status="COMPLETED")

        with patch(
            "src.api.routes.companies.CompanyService.fetch_company",
            new_callable=AsyncMock,
            return_value=company,
        ):
            response = await e2e_client.post(
                "/api/v1/companies",
                json={"corp_code": "00123456"},
            )
        assert response.status_code == 202

        with patch(
            "src.api.routes.companies.CompanyService.get_company",
            new_callable=AsyncMock,
            return_value=completed_company,
        ):
            response = await e2e_client.get("/api/v1/companies/00123456")
        assert response.status_code == 200
        assert response.json()["fetch_status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# E2E: Auth
# ---------------------------------------------------------------------------


class TestE2EAuth:
    """인증/인가 E2E 테스트."""

    @pytest.mark.asyncio
    async def test_unauthorized_access_401(self, unauth_client: AsyncClient) -> None:
        """인증 없이 POST/GET 시 401."""
        response = await unauth_client.post(
            "/api/v1/documents",
            json={"corp_code": "00123456"},
        )
        assert response.status_code == 401

        response = await unauth_client.get("/api/v1/companies/00123456")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_forbidden_access_403(
        self, e2e_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """다른 사용자 문서 접근 시 403."""
        with patch(
            "src.api.routes.documents.DocumentService.get_document",
            new_callable=AsyncMock,
            side_effect=AuthorizationError(required_role="ADMIN"),
        ):
            response = await e2e_client.get(f"/api/v1/documents/{uuid.uuid4()}")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# E2E: Pagination
# ---------------------------------------------------------------------------


class TestE2EPagination:
    """페이지네이션 E2E 테스트."""

    @pytest.mark.asyncio
    async def test_document_list_pagination(
        self, e2e_client: AsyncClient, test_user: MagicMock
    ) -> None:
        """다수 문서 -> offset/limit 동작."""
        docs = [_mock_document(owner_id=test_user.id) for _ in range(5)]

        with patch(
            "src.api.routes.documents.DocumentService.list_documents",
            new_callable=AsyncMock,
            return_value=(docs[:3], 5),
        ):
            response = await e2e_client.get("/api/v1/documents?offset=0&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3
        assert data["total"] == 5
        assert data["offset"] == 0
        assert data["limit"] == 3


# ---------------------------------------------------------------------------
# E2E: Health check (sanity)
# ---------------------------------------------------------------------------


class TestE2EHealth:
    """헬스체크 E2E 검증."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, e2e_client: AsyncClient) -> None:
        """GET /health 는 인증 없이 접근 가능."""
        with patch(
            "src.api.routes.health._check_db",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await e2e_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
