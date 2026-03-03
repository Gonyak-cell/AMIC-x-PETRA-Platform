"""API 스키마 단위 테스트 (T-I15).

> 마지막 수정: 2026-02-10 23:30:00

Pydantic v2 스키마 검증 로직을 테스트한다.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.api.schemas.common import ErrorResponse, PaginationParams
from src.api.schemas.companies import CompanyRequest, CompanyResponse
from src.api.schemas.documents import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
)


# ---------------------------------------------------------------------------
# DocumentCreate
# ---------------------------------------------------------------------------


class TestDocumentCreate:
    """DocumentCreate 스키마 검증."""

    def test_valid_defaults(self) -> None:
        """기본값으로 유효한 생성 요청."""
        doc = DocumentCreate(
            company_name="테스트 주식회사",
            project_name="프로젝트 A",
            corp_code="00123456",
        )
        assert doc.corp_code == "00123456"
        assert doc.im_style == "FULL"
        assert doc.sections == []

    def test_valid_full(self) -> None:
        """모든 필드가 채워진 유효한 요청."""
        doc = DocumentCreate(
            company_name="테스트 주식회사",
            corp_code="00123456",
            project_name="Project TITAN",
            im_style="TITAN",
            sections=["executive_summary", "financial_analysis"],
            industry="tech",
            webhook_url="https://example.com/hook",
            pdf_password="secure123",
        )
        assert doc.project_name == "Project TITAN"
        assert doc.im_style == "TITAN"
        assert len(doc.sections) == 2

    def test_invalid_corp_code_non_digit(self) -> None:
        """비숫자 corp_code 거부."""
        with pytest.raises(ValidationError, match="corp_code는 8자리 숫자"):
            DocumentCreate(
                company_name="테스트",
                project_name="프로젝트",
                corp_code="ABCD1234",
            )

    def test_invalid_corp_code_short(self) -> None:
        """짧은 corp_code 거부."""
        with pytest.raises(ValidationError):
            DocumentCreate(
                company_name="테스트",
                project_name="프로젝트",
                corp_code="1234",
            )

    def test_invalid_im_style(self) -> None:
        """잘못된 im_style 거부."""
        with pytest.raises(ValidationError, match="im_style"):
            DocumentCreate(
                company_name="테스트",
                project_name="프로젝트",
                corp_code="00123456",
                im_style="INVALID",
            )

    def test_short_pdf_password(self) -> None:
        """4자 미만 pdf_password 거부."""
        with pytest.raises(ValidationError):
            DocumentCreate(
                company_name="테스트",
                project_name="프로젝트",
                corp_code="00123456",
                pdf_password="ab",
            )


# ---------------------------------------------------------------------------
# DocumentResponse
# ---------------------------------------------------------------------------


class TestDocumentResponse:
    """DocumentResponse 스키마 검증."""

    def test_from_attributes(self) -> None:
        """from_attributes 모드로 ORM-like 객체에서 변환."""
        now = datetime.now(timezone.utc)
        _doc_id = uuid.uuid4()
        _owner_id = uuid.uuid4()

        fake = type(
            "FakeDocument",
            (),
            {
                "id": _doc_id,
                "owner_id": _owner_id,
                "corp_code": "00123456",
                "company_name": "테스트 주식회사",
                "project_name": "Project TITAN",
                "data_source": "MANUAL",
                "im_style": "FULL",
                "sections": ["executive_summary"],
                "status": "PENDING",
                "progress_pct": 0,
                "celery_task_id": None,
                "pptx_path": None,
                "pdf_path": None,
                "file_size_bytes": None,
                "created_at": now,
                "updated_at": now,
                "completed_at": None,
            },
        )()

        resp = DocumentResponse.model_validate(fake)
        assert resp.id == _doc_id
        assert resp.status == "PENDING"
        assert resp.corp_code == "00123456"


# ---------------------------------------------------------------------------
# DocumentListResponse
# ---------------------------------------------------------------------------


class TestDocumentListResponse:
    """DocumentListResponse 스키마 검증."""

    def test_list_response(self) -> None:
        """items + pagination 필드 구성."""
        resp = DocumentListResponse(items=[], total=0, offset=0, limit=20)
        assert resp.items == []
        assert resp.total == 0
        assert resp.offset == 0
        assert resp.limit == 20


# ---------------------------------------------------------------------------
# PaginationParams
# ---------------------------------------------------------------------------


class TestPaginationParams:
    """PaginationParams 스키마 검증."""

    def test_defaults(self) -> None:
        """기본값 offset=0, limit=20."""
        params = PaginationParams()
        assert params.offset == 0
        assert params.limit == 20

    def test_limit_bounds(self) -> None:
        """limit 범위 검증 (1~100)."""
        with pytest.raises(ValidationError):
            PaginationParams(limit=0)
        with pytest.raises(ValidationError):
            PaginationParams(limit=101)
        params = PaginationParams(limit=100)
        assert params.limit == 100

    def test_offset_non_negative(self) -> None:
        """offset은 음수 불가."""
        with pytest.raises(ValidationError):
            PaginationParams(offset=-1)


# ---------------------------------------------------------------------------
# CompanyRequest / CompanyResponse
# ---------------------------------------------------------------------------


class TestCompanyRequest:
    """CompanyRequest 스키마 검증."""

    def test_valid(self) -> None:
        """유효한 corp_code."""
        req = CompanyRequest(corp_code="00123456")
        assert req.corp_code == "00123456"

    def test_invalid_corp_code(self) -> None:
        """비숫자 corp_code 거부."""
        with pytest.raises(ValidationError, match="corp_code는 8자리 숫자"):
            CompanyRequest(corp_code="ABCDEFGH")


class TestCompanyResponse:
    """CompanyResponse 스키마 검증."""

    def test_from_attributes(self) -> None:
        """ORM-like 객체에서 변환."""
        now = datetime.now(timezone.utc)
        company_id = uuid.uuid4()

        class FakeCompany:
            id = company_id
            corp_code = "00123456"
            corp_name = "테스트 주식회사"
            corp_name_en = "Test Corp"
            stock_code = "123456"
            industry = "tech"
            homepage_url = "https://test.co.kr"
            fetch_status = "COMPLETED"
            last_fetched_at = now
            cache_expires_at = now
            created_at = now
            updated_at = now

        resp = CompanyResponse.model_validate(FakeCompany())
        assert resp.corp_code == "00123456"
        assert resp.fetch_status == "COMPLETED"


# ---------------------------------------------------------------------------
# ErrorResponse
# ---------------------------------------------------------------------------


class TestErrorResponse:
    """ErrorResponse 스키마 검증."""

    def test_error_response(self) -> None:
        """error + details 구성."""
        resp = ErrorResponse(
            error="문서를 찾을 수 없습니다.",
            details={"document_id": "abc-123"},
        )
        assert resp.error == "문서를 찾을 수 없습니다."
        assert resp.details["document_id"] == "abc-123"

    def test_error_response_defaults(self) -> None:
        """details 기본값은 빈 dict."""
        resp = ErrorResponse(error="에러 발생")
        assert resp.details == {}
