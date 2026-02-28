"""DART 대량보유 딜 신호 서비스 테스트."""

import re
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.core.exceptions import DARTAPIError
from app.models.company import Company
from app.models.deal import Deal
from app.models.holding import DartMajorHolding
from app.schemas.dart import MajorHoldingItem
from app.services.dart_service import DARTService
from app.services.holding_signal_service import HoldingSignalService
from app.utils.dart_helpers import is_acquisition, parse_date, parse_float, parse_year

# ── Mock 데이터 ──

MAJOR_HOLDING_RESPONSE = {
    "status": "000",
    "message": "정상",
    "page_no": 1,
    "page_count": 100,
    "total_count": 2,
    "total_page": 1,
    "list": [
        {
            "rcept_no": "20240301000001",
            "rcept_dt": "20240301",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "report_tp": "신규",
            "repror": "한국투자파트너스",
            "stkqy": "1000000",
            "stkrt": "7.5",
            "stkqy_irds": "1000000",
            "stkrt_irds": "7.5",
            "ctr_stkqy": "500000",
            "ctr_stkrt": "3.75",
            "report_resn": "주식취득",
        },
        {
            "rcept_no": "20240302000001",
            "rcept_dt": "20240302",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "report_tp": "변경",
            "repror": "IMM인베스트먼트",
            "stkqy": "200000",
            "stkrt": "1.5",
            "stkqy_irds": "-50000",
            "stkrt_irds": "-0.3",
            "ctr_stkqy": "0",
            "ctr_stkrt": "0",
            "report_resn": "주식처분",
        },
    ],
}


# ── DARTService.get_major_holdings() 테스트 ──


@pytest.mark.asyncio
async def test_get_major_holdings(httpx_mock):
    """대량보유상황보고서 API 파싱 테스트."""
    httpx_mock.add_response(
        url=re.compile(r".*/majorstock\.json.*"),
        json=MAJOR_HOLDING_RESPONSE,
    )

    service = DARTService()
    items, total_count, total_page = await service.get_major_holdings("00126380")
    await service.close()

    assert len(items) == 2
    assert total_count == 2
    assert total_page == 1
    assert items[0].rcept_no == "20240301000001"
    assert items[0].repror == "한국투자파트너스"
    assert items[0].stkrt == "7.5"
    assert items[1].report_resn == "주식처분"


# ── HoldingSignalService.sync_holdings() 테스트 ──


@pytest.mark.asyncio
async def test_sync_holdings_upsert(async_session):
    """sync_holdings가 대량보유 레코드를 DB에 저장하는지 확인한다."""
    mock_items = [
        MajorHoldingItem(
            rcept_no="20240301000001",
            rcept_dt="20240301",
            corp_code="00126380",
            corp_name="삼성전자",
            report_tp="신규",
            repror="한국투자파트너스",
            stkqy="1000000",
            stkrt="7.5",
            stkqy_irds="1000000",
            stkrt_irds="7.5",
            ctr_stkqy="500000",
            ctr_stkrt="3.75",
            report_resn="주식취득",
        ),
    ]

    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_major_holdings = AsyncMock(return_value=(mock_items, 1, 1))

    service = HoldingSignalService(mock_dart)

    with patch.object(service, "_resolve_reporter", return_value=None):
        result = await service.sync_holdings(async_session, "00126380")

    assert result.total_fetched == 1
    assert result.new_records == 1
    assert result.errors == []

    # DB 확인
    db_result = await async_session.execute(select(DartMajorHolding))
    holdings = list(db_result.scalars().all())
    assert len(holdings) == 1
    assert holdings[0].rcept_no == "20240301000001"
    assert holdings[0].corp_name == "삼성전자"


@pytest.mark.asyncio
async def test_sync_holdings_update_existing(async_session):
    """이미 존재하는 rcept_no는 업데이트한다."""
    # 기존 레코드 생성
    existing = DartMajorHolding(
        rcept_no="20240301000001",
        rcept_dt="20240301",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="한국투자파트너스",
        stkqy="500000",
        stkrt="3.5",
    )
    async_session.add(existing)
    await async_session.flush()

    # 업데이트할 데이터
    mock_items = [
        MajorHoldingItem(
            rcept_no="20240301000001",
            rcept_dt="20240301",
            corp_code="00126380",
            corp_name="삼성전자",
            repror="한국투자파트너스",
            stkqy="1000000",
            stkrt="7.5",
            report_resn="주식취득",
        ),
    ]

    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_major_holdings = AsyncMock(return_value=(mock_items, 1, 1))

    service = HoldingSignalService(mock_dart)

    with patch.object(service, "_resolve_reporter", return_value=None):
        result = await service.sync_holdings(async_session, "00126380")

    assert result.new_records == 0
    assert result.updated_records == 1

    # 업데이트 확인
    db_result = await async_session.execute(
        select(DartMajorHolding).where(DartMajorHolding.rcept_no == "20240301000001")
    )
    holding = db_result.scalar_one()
    assert holding.stkrt == "7.5"
    assert holding.stkqy == "1000000"


# ── generate_deal_signals() 테스트 ──


@pytest.mark.asyncio
async def test_generate_deal_signals(async_session):
    """GP의 취득 보고 시 딜 신호가 생성되는지 확인한다."""
    # GP Company 생성
    gp = Company(
        corp_name="한국투자파트너스",
        is_gp=True,
        corp_code="00164779",
    )
    async_session.add(gp)
    await async_session.flush()

    # 대량보유 레코드 (취득, 7.5% → 딜 생성 대상)
    holding = DartMajorHolding(
        rcept_no="20240301000001",
        rcept_dt="20240301",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="한국투자파트너스",
        stkqy="1000000",
        stkrt="7.5",
        report_resn="주식취득",
        reporter_company_id=gp.id,
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = HoldingSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)

    assert deals_created == 1

    # Deal 확인
    db_result = await async_session.execute(select(Deal))
    deals = list(db_result.scalars().all())
    assert len(deals) == 1
    assert deals[0].deal_type == "holding_change"
    assert deals[0].source_type == "disclosure"
    assert deals[0].target_company == "삼성전자"
    assert deals[0].rcept_no == "20240301000001"
    assert deals[0].deal_date == date(2024, 3, 1)

    # holding.deal_id 업데이트 확인
    await async_session.refresh(holding)
    assert holding.deal_id == deals[0].id


@pytest.mark.asyncio
async def test_generate_deal_signals_skip_low_stkrt(async_session):
    """최소 지분율(5%) 미만이면 딜 신호를 생성하지 않는다."""
    gp = Company(corp_name="테스트GP", is_gp=True, corp_code="00000001")
    async_session.add(gp)
    await async_session.flush()

    holding = DartMajorHolding(
        rcept_no="20240401000001",
        rcept_dt="20240401",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="테스트GP",
        stkrt="3.0",
        report_resn="주식취득",
        reporter_company_id=gp.id,
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = HoldingSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0


@pytest.mark.asyncio
async def test_generate_deal_signals_skip_disposal(async_session):
    """처분 사유는 딜 신호를 생성하지 않는다."""
    gp = Company(corp_name="테스트GP", is_gp=True, corp_code="00000002")
    async_session.add(gp)
    await async_session.flush()

    holding = DartMajorHolding(
        rcept_no="20240501000001",
        rcept_dt="20240501",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="테스트GP",
        stkrt="10.0",
        report_resn="주식처분",
        reporter_company_id=gp.id,
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = HoldingSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0


# ── 유틸리티 메서드 테스트 ──


class TestHelpers:
    """DART 공유 헬퍼 메서드 테스트 (대량보유 키워드)."""

    _KEYWORDS = ("주식취득", "취득", "매수", "인수")

    def test_is_acquisition_true(self):
        assert is_acquisition("주식취득", self._KEYWORDS) is True
        assert is_acquisition("대량 매수 보고", self._KEYWORDS) is True
        assert is_acquisition("지분 인수", self._KEYWORDS) is True

    def test_is_acquisition_false(self):
        assert is_acquisition("주식처분", self._KEYWORDS) is False
        assert is_acquisition(None, self._KEYWORDS) is False
        assert is_acquisition("", self._KEYWORDS) is False

    def test_parse_float(self):
        assert parse_float("7.5") == 7.5
        assert parse_float("1,000,000") == 1000000.0
        assert parse_float("-") is None
        assert parse_float("") is None
        assert parse_float(None) is None
        assert parse_float("abc") is None

    def test_parse_date(self):
        assert parse_date("20240301") == date(2024, 3, 1)
        assert parse_date("2024") is None
        assert parse_date("") is None
        assert parse_date(None) is None

    def test_parse_year(self):
        assert parse_year("20240301") == 2024
        assert parse_year("abc") is None
        assert parse_year(None) is None


# ── 경계값 테스트 ──


@pytest.mark.asyncio
async def test_generate_deal_signals_exact_threshold(async_session):
    """정확히 최소 지분율(5.0%)이면 딜 신호를 생성한다."""
    gp = Company(corp_name="경계GP", is_gp=True, corp_code="00000099")
    async_session.add(gp)
    await async_session.flush()

    holding = DartMajorHolding(
        rcept_no="20240601000099",
        rcept_dt="20240601",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="경계GP",
        stkrt="5.0",
        report_resn="주식취득",
        reporter_company_id=gp.id,
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = HoldingSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 1


# ── 중복 Deal 방지 테스트 ──


@pytest.mark.asyncio
async def test_generate_deal_signals_dedup_existing_deal(async_session):
    """동일 rcept_no의 Deal이 이미 존재하면 새 Deal을 생성하지 않고 연결만 한다."""
    gp = Company(corp_name="중복GP", is_gp=True, corp_code="00000088")
    async_session.add(gp)
    await async_session.flush()

    # 기존 Deal 생성
    existing_deal = Deal(
        target_company="삼성전자",
        deal_type="holding_change",
        source_type="disclosure",
        rcept_no="20240701000088",
    )
    async_session.add(existing_deal)
    await async_session.flush()

    # 동일 rcept_no를 가진 holding
    holding = DartMajorHolding(
        rcept_no="20240701000088",
        rcept_dt="20240701",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="중복GP",
        stkrt="10.0",
        report_resn="주식취득",
        reporter_company_id=gp.id,
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = HoldingSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0

    # holding.deal_id가 기존 Deal에 연결되었는지 확인 (dirty 상태를 DB에 반영 후 검증)
    await async_session.flush()
    await async_session.refresh(holding)
    assert holding.deal_id == existing_deal.id


# ── DART API 에러 처리 테스트 ──


@pytest.mark.asyncio
async def test_sync_holdings_dart_api_no_data(async_session):
    """DART API가 status_code='013' (데이터 없음) 반환 시 정상 종료한다."""
    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_major_holdings = AsyncMock(
        side_effect=DARTAPIError(status_code="013", message="조회된 데이터가 없습니다.")
    )

    service = HoldingSignalService(mock_dart)
    result = await service.sync_holdings(async_session, "00126380")

    assert result.total_fetched == 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_sync_holdings_dart_api_error(async_session):
    """DART API가 기타 에러 반환 시 에러를 기록한다."""
    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_major_holdings = AsyncMock(side_effect=DARTAPIError(status_code="020", message="잘못된 요청입니다."))

    service = HoldingSignalService(mock_dart)
    result = await service.sync_holdings(async_session, "00126380")

    assert result.total_fetched == 0
    assert len(result.errors) == 1
    assert "020" in result.errors[0]


@pytest.mark.asyncio
async def test_sync_holdings_unexpected_exception(async_session):
    """DART API 호출 중 예외 발생 시 에러를 기록한다."""
    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_major_holdings = AsyncMock(side_effect=ConnectionError("timeout"))

    service = HoldingSignalService(mock_dart)
    result = await service.sync_holdings(async_session, "00126380")

    assert result.total_fetched == 0
    assert len(result.errors) == 1
    assert "조회 실패" in result.errors[0]
