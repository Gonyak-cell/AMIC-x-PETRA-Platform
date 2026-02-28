"""DART 임원·주요주주 소유보고 딜 신호 서비스 테스트."""

import re
from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import select

from app.core.exceptions import DARTAPIError
from app.models.company import Company
from app.models.deal import Deal
from app.models.elestock import DartExecutiveHolding
from app.schemas.dart import ElestockItem
from app.services.dart_service import DARTService
from app.services.elestock_signal_service import ElestockSignalService
from app.utils.dart_helpers import is_acquisition, parse_date, parse_float, parse_year

# ── Mock 데이터 ──

ELESTOCK_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "rcept_no": "20240601000001",
            "rcept_dt": "20240601",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "repror": "홍길동",
            "isu_exctv_rgist_at": "Y",
            "isu_exctv_ofcps": "대표이사",
            "isu_main_shrholdr": "N",
            "sp_stock_lmp_cnt": "50000",
            "sp_stock_lmp_irds_cnt": "10000",
            "sp_stock_lmp_rate": "2.5",
            "sp_stock_lmp_irds_rate": "0.5",
            "ctr_stkqy": "0",
            "ctr_stkrt": "0",
            "report_resn": "장내취득",
        },
        {
            "rcept_no": "20240602000001",
            "rcept_dt": "20240602",
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "repror": "김철수",
            "isu_exctv_rgist_at": "N",
            "isu_exctv_ofcps": "",
            "isu_main_shrholdr": "Y",
            "sp_stock_lmp_cnt": "100000",
            "sp_stock_lmp_irds_cnt": "-5000",
            "sp_stock_lmp_rate": "5.0",
            "sp_stock_lmp_irds_rate": "-0.2",
            "ctr_stkqy": "0",
            "ctr_stkrt": "0",
            "report_resn": "장내매도",
        },
    ],
}


# ── DARTService.get_executive_holdings() 테스트 ──


@pytest.mark.asyncio
async def test_get_executive_holdings(httpx_mock):
    """임원소유보고 API 파싱 테스트."""
    httpx_mock.add_response(
        url=re.compile(r".*/elestock\.json.*"),
        json=ELESTOCK_RESPONSE,
    )

    service = DARTService()
    items = await service.get_executive_holdings("00126380")
    await service.close()

    assert len(items) == 2
    assert items[0].rcept_no == "20240601000001"
    assert items[0].repror == "홍길동"
    assert items[0].isu_exctv_rgist_at == "Y"
    assert items[1].isu_main_shrholdr == "Y"
    assert items[1].report_resn == "장내매도"


# ── ElestockSignalService.sync_executive_holdings() 테스트 ──


@pytest.mark.asyncio
async def test_sync_executive_holdings_upsert(async_session):
    """sync_executive_holdings가 임원소유보고 레코드를 DB에 저장하는지 확인한다."""
    mock_items = [
        ElestockItem(
            rcept_no="20240601000001",
            rcept_dt="20240601",
            corp_code="00126380",
            corp_name="삼성전자",
            repror="홍길동",
            isu_exctv_rgist_at="Y",
            isu_exctv_ofcps="대표이사",
            isu_main_shrholdr="N",
            sp_stock_lmp_cnt="50000",
            sp_stock_lmp_rate="2.5",
            report_resn="장내취득",
        ),
    ]

    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_executive_holdings = AsyncMock(return_value=mock_items)

    service = ElestockSignalService(mock_dart)
    result = await service.sync_executive_holdings(async_session, "00126380")

    assert result.total_fetched == 1
    assert result.new_records == 1
    assert result.errors == []

    # DB 확인
    db_result = await async_session.execute(select(DartExecutiveHolding))
    holdings = list(db_result.scalars().all())
    assert len(holdings) == 1
    assert holdings[0].rcept_no == "20240601000001"
    assert holdings[0].repror == "홍길동"
    assert holdings[0].isu_exctv_rgist_at == "Y"


@pytest.mark.asyncio
async def test_sync_executive_holdings_update_existing(async_session):
    """이미 존재하는 rcept_no는 업데이트한다."""
    existing = DartExecutiveHolding(
        rcept_no="20240601000001",
        rcept_dt="20240601",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="홍길동",
        sp_stock_lmp_rate="1.5",
    )
    async_session.add(existing)
    await async_session.flush()

    mock_items = [
        ElestockItem(
            rcept_no="20240601000001",
            rcept_dt="20240601",
            corp_code="00126380",
            corp_name="삼성전자",
            repror="홍길동",
            sp_stock_lmp_cnt="50000",
            sp_stock_lmp_rate="2.5",
            report_resn="장내취득",
        ),
    ]

    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_executive_holdings = AsyncMock(return_value=mock_items)

    service = ElestockSignalService(mock_dart)
    result = await service.sync_executive_holdings(async_session, "00126380")

    assert result.new_records == 0
    assert result.updated_records == 1

    db_result = await async_session.execute(
        select(DartExecutiveHolding).where(DartExecutiveHolding.rcept_no == "20240601000001")
    )
    holding = db_result.scalar_one()
    assert holding.sp_stock_lmp_rate == "2.5"


# ── generate_deal_signals() 테스트 ──


@pytest.mark.asyncio
async def test_generate_deal_signals_executive(async_session):
    """임원의 취득 보고 시 딜 신호가 생성되는지 확인한다."""
    company = Company(corp_name="삼성전자", corp_code="00126380")
    async_session.add(company)
    await async_session.flush()

    holding = DartExecutiveHolding(
        rcept_no="20240601000001",
        rcept_dt="20240601",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="홍길동",
        isu_exctv_rgist_at="Y",
        isu_main_shrholdr="N",
        sp_stock_lmp_rate="2.5",
        report_resn="장내취득",
        company_id=company.id,
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 1

    db_result = await async_session.execute(select(Deal))
    deals = list(db_result.scalars().all())
    assert len(deals) == 1
    assert deals[0].deal_type == "executive_change"
    assert deals[0].source_type == "disclosure"
    assert deals[0].target_company == "삼성전자"
    assert deals[0].deal_date == date(2024, 6, 1)

    await async_session.refresh(holding)
    assert holding.deal_id == deals[0].id


@pytest.mark.asyncio
async def test_generate_deal_signals_major_shareholder(async_session):
    """주요주주의 취득 보고 시 딜 신호가 생성되는지 확인한다."""
    holding = DartExecutiveHolding(
        rcept_no="20240701000001",
        rcept_dt="20240701",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="김대주주",
        isu_exctv_rgist_at="N",
        isu_main_shrholdr="Y",
        sp_stock_lmp_rate="8.0",
        report_resn="매수",
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 1


@pytest.mark.asyncio
async def test_generate_deal_signals_skip_low_rate(async_session):
    """최소 비율(1%) 미만이면 딜 신호를 생성하지 않는다."""
    holding = DartExecutiveHolding(
        rcept_no="20240801000001",
        rcept_dt="20240801",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="김소액",
        isu_exctv_rgist_at="Y",
        sp_stock_lmp_rate="0.3",
        report_resn="취득",
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0


@pytest.mark.asyncio
async def test_generate_deal_signals_skip_disposal(async_session):
    """처분/매도 사유는 딜 신호를 생성하지 않는다."""
    holding = DartExecutiveHolding(
        rcept_no="20240901000001",
        rcept_dt="20240901",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="홍매도",
        isu_exctv_rgist_at="Y",
        sp_stock_lmp_rate="5.0",
        report_resn="장내매도",
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0


@pytest.mark.asyncio
async def test_generate_deal_signals_skip_non_significant(async_session):
    """임원도 아니고 주요주주도 아니면 딜 신호를 생성하지 않는다."""
    holding = DartExecutiveHolding(
        rcept_no="20241001000001",
        rcept_dt="20241001",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="일반인",
        isu_exctv_rgist_at="N",
        isu_main_shrholdr="N",
        sp_stock_lmp_rate="3.0",
        report_resn="취득",
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0


# ── 유틸리티 메서드 테스트 ──


class TestElestockHelpers:
    """DART 공유 헬퍼 메서드 테스트 (임원소유보고 키워드)."""

    _KEYWORDS = ("취득", "매수", "증여받음", "상속")

    def test_is_acquisition_true(self):
        assert is_acquisition("장내취득", self._KEYWORDS) is True
        assert is_acquisition("매수 보고", self._KEYWORDS) is True
        assert is_acquisition("증여받음", self._KEYWORDS) is True
        assert is_acquisition("상속에 의한 취득", self._KEYWORDS) is True

    def test_is_acquisition_false(self):
        assert is_acquisition("장내매도", self._KEYWORDS) is False
        assert is_acquisition(None, self._KEYWORDS) is False
        assert is_acquisition("", self._KEYWORDS) is False

    def test_parse_float(self):
        assert parse_float("2.5") == 2.5
        assert parse_float("1,000") == 1000.0
        assert parse_float("-") is None
        assert parse_float(None) is None

    def test_parse_date(self):
        assert parse_date("20240601") == date(2024, 6, 1)
        assert parse_date("2024") is None
        assert parse_date(None) is None

    def test_parse_year(self):
        assert parse_year("20240601") == 2024
        assert parse_year("abc") is None
        assert parse_year(None) is None

    def test_is_significant_person(self):
        def _mock_holding(exec_at: str | None, main_sh: str | None) -> Mock:
            return Mock(
                spec=DartExecutiveHolding,
                isu_exctv_rgist_at=exec_at,
                isu_main_shrholdr=main_sh,
            )

        assert ElestockSignalService._is_significant_person(_mock_holding("Y", "N")) is True
        assert ElestockSignalService._is_significant_person(_mock_holding("N", "Y")) is True
        assert ElestockSignalService._is_significant_person(_mock_holding("Y", "Y")) is True
        assert ElestockSignalService._is_significant_person(_mock_holding("N", "N")) is False
        assert ElestockSignalService._is_significant_person(_mock_holding(None, None)) is False


# ── 경계값 테스트 ──


@pytest.mark.asyncio
async def test_generate_deal_signals_exact_threshold(async_session):
    """정확히 최소 비율(1.0%)이면 딜 신호를 생성한다."""
    holding = DartExecutiveHolding(
        rcept_no="20241101000099",
        rcept_dt="20241101",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="경계임원",
        isu_exctv_rgist_at="Y",
        sp_stock_lmp_rate="1.0",
        report_resn="취득",
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 1


# ── 중복 Deal 방지 테스트 ──


@pytest.mark.asyncio
async def test_generate_deal_signals_dedup_existing_deal(async_session):
    """동일 rcept_no의 Deal이 이미 존재하면 새 Deal을 생성하지 않고 연결만 한다."""
    # 기존 Deal 생성
    existing_deal = Deal(
        target_company="삼성전자",
        deal_type="executive_change",
        source_type="disclosure",
        rcept_no="20241201000088",
    )
    async_session.add(existing_deal)
    await async_session.flush()

    # 동일 rcept_no를 가진 holding
    holding = DartExecutiveHolding(
        rcept_no="20241201000088",
        rcept_dt="20241201",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="중복임원",
        isu_exctv_rgist_at="Y",
        sp_stock_lmp_rate="5.0",
        report_resn="취득",
    )
    async_session.add(holding)
    await async_session.flush()

    mock_dart = AsyncMock(spec=DARTService)
    service = ElestockSignalService(mock_dart)

    deals_created = await service.generate_deal_signals(async_session)
    assert deals_created == 0

    # holding.deal_id가 기존 Deal에 연결되었는지 확인 (dirty 상태를 DB에 반영 후 검증)
    await async_session.flush()
    await async_session.refresh(holding)
    assert holding.deal_id == existing_deal.id


# ── DART API 에러 처리 테스트 ──


@pytest.mark.asyncio
async def test_sync_elestock_dart_api_no_data(async_session):
    """DART API가 status_code='013' (데이터 없음) 반환 시 정상 종료한다."""
    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_executive_holdings = AsyncMock(
        side_effect=DARTAPIError(status_code="013", message="조회된 데이터가 없습니다.")
    )

    service = ElestockSignalService(mock_dart)
    result = await service.sync_executive_holdings(async_session, "00126380")

    assert result.total_fetched == 0
    assert result.errors == []


@pytest.mark.asyncio
async def test_sync_elestock_dart_api_error(async_session):
    """DART API가 기타 에러 반환 시 에러를 기록한다."""
    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_executive_holdings = AsyncMock(
        side_effect=DARTAPIError(status_code="020", message="잘못된 요청입니다.")
    )

    service = ElestockSignalService(mock_dart)
    result = await service.sync_executive_holdings(async_session, "00126380")

    assert result.total_fetched == 0
    assert len(result.errors) == 1
    assert "020" in result.errors[0]


@pytest.mark.asyncio
async def test_sync_elestock_unexpected_exception(async_session):
    """DART API 호출 중 예외 발생 시 에러를 기록한다."""
    mock_dart = AsyncMock(spec=DARTService)
    mock_dart.get_executive_holdings = AsyncMock(side_effect=ConnectionError("timeout"))

    service = ElestockSignalService(mock_dart)
    result = await service.sync_executive_holdings(async_session, "00126380")

    assert result.total_fetched == 0
    assert len(result.errors) == 1
    assert "조회 실패" in result.errors[0]
