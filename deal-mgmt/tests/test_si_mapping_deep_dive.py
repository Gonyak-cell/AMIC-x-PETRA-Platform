"""SI 기업 딥다이브 엔드포인트 + 파서 단위 테스트 (TQ-01, TQ-04)."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.si_company import SICompany
from app.services.si_mapping_service import (
    _extract_amount,
    _match_corp_code,
    _parse_financials,
    _parse_sanctions,
)

pytestmark = pytest.mark.anyio


# ── 헬퍼 ──────────────────────────────────────────────────


async def _create_si_company(
    session: AsyncSession,
    *,
    company_name: str = "테스트기업",
    corp_basic_synced_at: datetime.datetime | None = None,
    corp_code: str | None = None,
) -> SICompany:
    """테스트용 SI 기업을 DB에 삽입하고 반환."""
    company = SICompany(
        id=uuid.uuid4(),
        company_name=company_name,
        ksic_codes=["C10"],
        revenue=10_000_000_000,
        corp_basic_synced_at=corp_basic_synced_at,
        corp_code=corp_code,
    )
    session.add(company)
    await session.commit()
    return company


# ── GET /si-mapping/companies/{id}/deep-dive ──────────────


async def test_deep_dive_company_not_found(client: AsyncClient):
    """존재하지 않는 company_id → 404."""
    unknown_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/si-mapping/companies/{unknown_id}/deep-dive")
    assert resp.status_code == 404


async def test_deep_dive_dart_unavailable(client: AsyncClient, async_session: AsyncSession):
    """KIIS DART API 접근 불가(RuntimeError) → 200, dart_available=False."""
    company = await _create_si_company(async_session)
    with patch(
        "app.services.si_mapping_service.make_service_token",
        new=AsyncMock(side_effect=RuntimeError("JWT config error")),
    ):
        resp = await client.get(f"/api/v1/si-mapping/companies/{company.id}/deep-dive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dart_available"] is False
    assert body["company"]["id"] == str(company.id)
    assert body["overview"] is None


async def test_deep_dive_db_overview_used(client: AsyncClient, async_session: AsyncSession):
    """corp_basic_synced_at 설정 시 DB 기반 overview 포함 + dart_available=False."""
    company = await _create_si_company(
        async_session,
        company_name="DB개황기업",
        corp_basic_synced_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        corp_code="D000001",
    )
    with patch(
        "app.services.si_mapping_service.make_service_token",
        new=AsyncMock(side_effect=RuntimeError("JWT config error")),
    ):
        resp = await client.get(f"/api/v1/si-mapping/companies/{company.id}/deep-dive")
    assert resp.status_code == 200
    body = resp.json()
    assert body["dart_available"] is False
    assert body["overview"] is not None
    assert body["overview"]["corp_name"] == "DB개황기업"
    assert body["overview"]["corp_code"] == "D000001"


# ── _parse_financials 단위 테스트 ──────────────────────────


def _make_financial_response(bsns_year: str, revenue_raw: str) -> httpx.Response:
    """재무제표 응답 mock 생성."""
    data = {
        "items": [
            {"bsns_year": bsns_year, "account_nm": "매출액", "thstrm_amount": revenue_raw},
            {"bsns_year": bsns_year, "account_nm": "영업이익", "thstrm_amount": "5,000,000"},
        ]
    }
    return httpx.Response(200, json=data)


def test_parse_financials_success():
    """정상 재무제표 파싱 — 매출액, 영업이익 추출."""
    resp = _make_financial_response("2023", "100,000,000")
    result = _parse_financials([resp])
    assert len(result) == 1
    assert result[0].bsns_year == "2023"
    assert result[0].revenue == Decimal("100000000")
    assert result[0].operating_income == Decimal("5000000")


def test_parse_financials_invalid_json():
    """JSON 파싱 실패 응답 → 해당 항목 스킵, 다음 항목 계속 처리."""
    bad_resp = httpx.Response(200, content=b"not-valid-json", headers={"content-type": "text/plain"})
    good_resp = _make_financial_response("2022", "50,000,000")
    result = _parse_financials([bad_resp, good_resp])
    assert len(result) == 1
    assert result[0].bsns_year == "2022"


def test_parse_financials_non_200():
    """비200 응답 → 스킵."""
    resp = httpx.Response(404)
    result = _parse_financials([resp])
    assert result == []


def test_parse_financials_exception_in_list():
    """asyncio.gather return_exceptions=True 예외 → 스킵."""
    exc = RuntimeError("network error")
    resp = _make_financial_response("2021", "30,000,000")
    result = _parse_financials([exc, resp])
    assert len(result) == 1
    assert result[0].bsns_year == "2021"


# ── _parse_sanctions 단위 테스트 ──────────────────────────


def test_parse_sanctions_success():
    """정상 제재 내역 파싱."""
    data = {
        "items": [
            {"sanctions_date": "20240101", "sanctions_type": "과태료", "sanctions_detail": "위반행위"},
        ]
    }
    resp = httpx.Response(200, json=data)
    result = _parse_sanctions(resp)
    assert len(result) == 1
    assert result[0].date == "20240101"
    assert result[0].type == "과태료"
    assert result[0].content == "위반행위"


def test_parse_sanctions_empty():
    """제재 내역 없음 → 빈 리스트."""
    resp = httpx.Response(200, json={"items": []})
    result = _parse_sanctions(resp)
    assert result == []


def test_parse_sanctions_non_200():
    """비200 응답 → 빈 리스트."""
    resp = httpx.Response(503)
    result = _parse_sanctions(resp)
    assert result == []


def test_parse_sanctions_fallback_fields():
    """DART 원본 필드명 fallback — sanction_date, sanction_type."""
    data = {
        "items": [
            {"sanction_date": "20230601", "sanction_type": "경고", "sanction_content": "내용"},
        ]
    }
    resp = httpx.Response(200, json=data)
    result = _parse_sanctions(resp)
    assert len(result) == 1
    assert result[0].date == "20230601"


# ── _match_corp_code 단위 테스트 ──────────────────────────


def _make_si_company_stub(company_name: str) -> object:
    """테스트용 SICompany 스텁 (DB 미저장).

    SQLAlchemy 모델을 object.__new__로 생성하면 _sa_instance_state 부재로
    AttributeError가 발생하므로 SimpleNamespace를 사용한다.
    """
    from types import SimpleNamespace

    return SimpleNamespace(company_name=company_name, jurir_no=None)


def test_match_corp_code_exact_name():
    """기업명 정확 매칭."""
    items = [
        {"corp_name": "다른기업", "corp_code": "X111"},
        {"corp_name": "정확기업", "corp_code": "A123"},
    ]
    company = _make_si_company_stub("정확기업")
    result = _match_corp_code(items, company)
    assert result == "A123"


def test_match_corp_code_no_match():
    """매칭 없음 → None."""
    items = [{"corp_name": "다른기업", "corp_code": "X111"}]
    company = _make_si_company_stub("매칭없음기업")
    result = _match_corp_code(items, company)
    assert result is None


def test_match_corp_code_empty_items():
    """빈 items → None."""
    company = _make_si_company_stub("기업")
    result = _match_corp_code([], company)
    assert result is None


def test_match_corp_code_first_exact_wins():
    """중복 정확 매칭 시 첫 번째 반환."""
    items = [
        {"corp_name": "정확기업", "corp_code": "A001"},
        {"corp_name": "정확기업", "corp_code": "A002"},
    ]
    company = _make_si_company_stub("정확기업")
    result = _match_corp_code(items, company)
    assert result == "A001"


# ── _extract_amount 단위 테스트 ───────────────────────────


def test_extract_amount_success():
    """계정과목 금액 추출."""
    items = [
        {"account_nm": "매출액", "thstrm_amount": "100,000"},
        {"account_nm": "영업이익", "thstrm_amount": "10,000"},
    ]
    result = _extract_amount(items, "매출액")
    assert result == Decimal("100000")


def test_extract_amount_missing():
    """해당 계정 없음 → None."""
    items = [{"account_nm": "영업이익", "thstrm_amount": "10,000"}]
    result = _extract_amount(items, "매출액")
    assert result is None


def test_extract_amount_dash():
    """금액이 '-'인 경우 → None."""
    items = [{"account_nm": "매출액", "thstrm_amount": "-"}]
    result = _extract_amount(items, "매출액")
    assert result is None


def test_extract_amount_empty_string():
    """금액이 빈 문자열인 경우 → None."""
    items = [{"account_nm": "매출액", "thstrm_amount": ""}]
    result = _extract_amount(items, "매출액")
    assert result is None
