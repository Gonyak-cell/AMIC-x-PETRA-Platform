"""KOFIA 펀드 서비스 테스트

ProFrame XML 프로토콜 기반 (proframeWeb/XMLSERVICES/) 서비스 테스트.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.services.kofia_service import (
    KOFIAService,
    _build_proframe_xml,
    _parse_date,
    _parse_decimal,
    _parse_int,
    _parse_proframe_response,
)

# --- Mock ProFrame XML 응답 ---

MOCK_STD_DATE_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmResponseCode>0000</pfmResponseCode>
  </proframeHeader>
  <systemHeader></systemHeader>
  <DISComStdYMDDTO>
    <standardDt>20260213</standardDt>
  </DISComStdYMDDTO>
</message>"""

MOCK_FUND_PRICE_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmResponseCode>0000</pfmResponseCode>
  </proframeHeader>
  <systemHeader></systemHeader>
  <DISCondFuncListDTO>
    <dbio_total_count_>3</dbio_total_count_>
    <selectMeta>
      <tmpV1>한국투자파트너스</tmpV1>
      <tmpV2>한투파 블라인드 벤처투자조합 1호</tmpV2>
      <tmpV3>혼합주식형</tmpV3>
      <tmpV4>20200315</tmpV4>
      <tmpV5>50000</tmpV5>
      <tmpV6>1100.50</tmpV6>
      <tmpV12>KR5200001234</tmpV12>
      <tmpV13>COM001</tmpV13>
      <tmpV14>20260213</tmpV14>
    </selectMeta>
    <selectMeta>
      <tmpV1>디지털캐피탈</tmpV1>
      <tmpV2>ABC기업 인수 목적 프로젝트 펀드</tmpV2>
      <tmpV3>주식형</tmpV3>
      <tmpV4>20180601</tmpV4>
      <tmpV5>100000</tmpV5>
      <tmpV6>980.20</tmpV6>
      <tmpV12>KR5200005678</tmpV12>
      <tmpV13>COM002</tmpV13>
      <tmpV14>20260213</tmpV14>
    </selectMeta>
    <selectMeta>
      <tmpV1>미래에셋벤처투자</tmpV1>
      <tmpV2>미래성장 기술금융 투자조합</tmpV2>
      <tmpV3>혼합채권형</tmpV3>
      <tmpV4>20190101</tmpV4>
      <tmpV5>30000</tmpV5>
      <tmpV6>1050.00</tmpV6>
      <tmpV12>KR5200009999</tmpV12>
      <tmpV13>COM003</tmpV13>
      <tmpV14>20260213</tmpV14>
    </selectMeta>
  </DISCondFuncListDTO>
</message>"""

MOCK_FEE_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmResponseCode>0000</pfmResponseCode>
  </proframeHeader>
  <systemHeader></systemHeader>
  <DISCondFuncListDTO>
    <dbio_total_count_>2</dbio_total_count_>
    <selectMeta>
      <tmpV1>한국투자파트너스</tmpV1>
      <tmpV2>한투파 블라인드 벤처투자조합 1호</tmpV2>
      <tmpV5>2.0</tmpV5>
      <tmpV11>20.0</tmpV11>
      <tmpV15>KR5200001234</tmpV15>
    </selectMeta>
    <selectMeta>
      <tmpV1>디지털캐피탈</tmpV1>
      <tmpV2>ABC기업 인수 목적 프로젝트 펀드</tmpV2>
      <tmpV5>1.5</tmpV5>
      <tmpV11>15.0</tmpV11>
      <tmpV15>KR5200005678</tmpV15>
    </selectMeta>
  </DISCondFuncListDTO>
</message>"""

MOCK_EMPTY_FEE_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmResponseCode>0000</pfmResponseCode>
  </proframeHeader>
  <systemHeader></systemHeader>
  <DISCondFuncListDTO>
    <dbio_total_count_>0</dbio_total_count_>
  </DISCondFuncListDTO>
</message>"""

MOCK_PROFRAME_ERROR = """<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmResponseCode>COMS00001</pfmResponseCode>
    <pfmResponseBasc>Unexpected element</pfmResponseBasc>
  </proframeHeader>
  <systemHeader></systemHeader>
</message>"""


# --- 유틸리티 함수 테스트 ---


def test_parse_date_yyyymmdd():
    """YYYYMMDD 형식 날짜 파싱"""
    assert _parse_date("20200315") == date(2020, 3, 15)


def test_parse_date_with_dashes():
    """YYYY-MM-DD 형식 날짜 파싱"""
    assert _parse_date("2020-03-15") == date(2020, 3, 15)


def test_parse_date_empty():
    """빈 문자열은 None 반환"""
    assert _parse_date("") is None
    assert _parse_date("  ") is None
    assert _parse_date(None) is None  # type: ignore[arg-type]


def test_parse_date_invalid():
    """잘못된 형식은 None 반환"""
    assert _parse_date("not-a-date") is None
    assert _parse_date("2020") is None


def test_parse_decimal():
    """숫자 문자열 Decimal 변환"""
    assert _parse_decimal("50000000000") == Decimal("50000000000")
    assert _parse_decimal("100,000,000,000") == Decimal("100000000000")
    assert _parse_decimal("2.5") == Decimal("2.5")
    assert _parse_decimal(100) == Decimal("100")


def test_parse_decimal_empty():
    """빈 값은 None 반환"""
    assert _parse_decimal(None) is None
    assert _parse_decimal("") is None


def test_parse_int():
    """정수 파싱"""
    assert _parse_int("10") == 10
    assert _parse_int(15) == 15
    assert _parse_int(None) is None
    assert _parse_int("") is None


# --- ProFrame XML 빌더/파서 테스트 ---


def test_build_proframe_xml():
    """ProFrame XML 요청 빌드 테스트"""
    xml = _build_proframe_xml(
        "FS-DIS2",
        "DISFundStdPriceSO",
        "select",
        "DISCondFuncDTO",
        {"tmpV30": "20260213", "tmpV11": ""},
    )
    assert "<pfmAppName>FS-DIS2</pfmAppName>" in xml
    assert "<pfmSvcName>DISFundStdPriceSO</pfmSvcName>" in xml
    assert "<pfmFnName>select</pfmFnName>" in xml
    assert "<DISCondFuncDTO>" in xml
    assert "<tmpV30>20260213</tmpV30>" in xml
    assert '<?xml version="1.0" encoding="utf-8"?>' in xml


def test_parse_proframe_response_selectmeta():
    """selectMeta 형식 ProFrame 응답 파싱"""
    items, total = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    assert total == 3
    assert len(items) == 3
    assert items[0]["tmpV12"] == "KR5200001234"
    assert items[0]["tmpV1"] == "한국투자파트너스"
    assert items[0]["tmpV2"] == "한투파 블라인드 벤처투자조합 1호"
    assert items[1]["tmpV12"] == "KR5200005678"


def test_parse_proframe_response_error():
    """ProFrame 에러 응답 처리"""
    items, total = _parse_proframe_response(MOCK_PROFRAME_ERROR)
    assert total == 0
    assert items == []


def test_parse_proframe_response_invalid_xml():
    """유효하지 않은 XML 응답 처리"""
    items, total = _parse_proframe_response("not valid xml <")
    assert total == 0
    assert items == []


# --- 펀드 유형 분류 테스트 ---


def test_classify_fund_type_blind():
    """블라인드 펀드 분류"""
    assert KOFIAService.classify_fund_type("한투파 블라인드 벤처투자조합 1호") == "blind"
    assert KOFIAService.classify_fund_type("미래성장 기술금융 투자조합") == "blind"
    assert KOFIAService.classify_fund_type("일반 성장기업 펀드") == "blind"
    assert KOFIAService.classify_fund_type("신기술사업투자조합") == "blind"


def test_classify_fund_type_project():
    """프로젝트 펀드 분류"""
    assert KOFIAService.classify_fund_type("ABC기업 인수 목적 프로젝트 펀드") == "project"
    assert KOFIAService.classify_fund_type("특정자산 투자 PF 사모펀드") == "project"
    assert KOFIAService.classify_fund_type("XX빌딩 인수 목적 펀드") == "project"


def test_classify_fund_type_default():
    """분류 불가 시 기본값 blind"""
    assert KOFIAService.classify_fund_type("알 수 없는 이름의 펀드") == "blind"
    assert KOFIAService.classify_fund_type("") == "blind"


def test_classify_legal_type():
    """법률 유형 분류"""
    assert KOFIAService.classify_legal_type("전문투자형 사모펀드") == "professional_private"
    assert KOFIAService.classify_legal_type("공모 주식형 펀드") == "public"
    assert KOFIAService.classify_legal_type("일반 사모펀드") == "general_private"


def test_classify_asset_class():
    """자산 클래스 분류"""
    assert KOFIAService.classify_asset_class("부동산 사모펀드", "") == "real_estate"
    assert KOFIAService.classify_asset_class("인프라 투자조합", "") == "infra"
    assert KOFIAService.classify_asset_class("메자닌 CB펀드", "") == "mezzanine"
    assert KOFIAService.classify_asset_class("재간접 FoF", "") == "fund_of_funds"
    assert KOFIAService.classify_asset_class("벤처투자조합", "VC") == "vc"
    assert KOFIAService.classify_asset_class("경영참여형", "PEF") == "pef"
    assert KOFIAService.classify_asset_class("알 수 없는 펀드", "") == "pef"  # default


# --- 회수 집중 구간 테스트 ---


def test_calculate_maturity_alert_in_range():
    """7~10년차 펀드는 회수 집중 구간"""
    vintage, is_alert = KOFIAService.calculate_maturity_alert(date(2019, 1, 1))
    assert vintage == 2019
    assert is_alert is True


def test_calculate_maturity_alert_too_young():
    """6년 미만 펀드는 비알림"""
    vintage, is_alert = KOFIAService.calculate_maturity_alert(date(2022, 1, 1))
    assert vintage == 2022
    assert is_alert is False


def test_calculate_maturity_alert_too_old():
    """11년 이상 펀드는 비알림 (회수 구간 지남)"""
    vintage, is_alert = KOFIAService.calculate_maturity_alert(date(2014, 1, 1))
    assert vintage == 2014
    assert is_alert is False


def test_calculate_maturity_alert_with_maturity_date():
    """만기 2년 이내이면 알림 (연차 무관)"""
    vintage, is_alert = KOFIAService.calculate_maturity_alert(
        established_date=date(2023, 1, 1),
        maturity_date=date(2027, 1, 1),
    )
    assert vintage == 2023
    assert is_alert is True


def test_calculate_maturity_alert_none():
    """설정일 없으면 None, False"""
    vintage, is_alert = KOFIAService.calculate_maturity_alert(None)
    assert vintage is None
    assert is_alert is False


# --- 서비스 파싱 메서드 테스트 ---


def test_parse_fund_list_from_proframe():
    """ProFrame 펀드 목록 파싱 테스트"""
    service = KOFIAService()
    items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fund_list = service._parse_fund_list_from_proframe(items)

    assert len(fund_list) == 3

    # 첫 번째: 블라인드 펀드 (벤처 키워드)
    assert fund_list[0].fund_code == "KR5200001234"
    assert fund_list[0].fund_name == "한투파 블라인드 벤처투자조합 1호"
    assert fund_list[0].fund_type == "blind"
    assert fund_list[0].company_name == "한국투자파트너스"
    # 설정액: 50000 (백만원) → 50,000,000,000 원
    assert fund_list[0].total_amount == Decimal("50000000000")
    assert fund_list[0].asset_class == "vc"

    # 두 번째: 프로젝트 펀드 (인수 목적 키워드)
    assert fund_list[1].fund_code == "KR5200005678"
    assert fund_list[1].fund_type == "project"
    assert fund_list[1].total_amount == Decimal("100000000000")

    # 세 번째: 블라인드 펀드 (기술 키워드)
    assert fund_list[2].fund_type == "blind"
    assert fund_list[2].fund_code == "KR5200009999"


def test_parse_fund_detail_from_proframe():
    """ProFrame 펀드 상세 파싱 테스트"""
    service = KOFIAService()
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fee_items, _ = _parse_proframe_response(MOCK_FEE_RESPONSE)

    price_row = price_items[0]
    fee_row = next(r for r in fee_items if r.get("tmpV15") == "KR5200001234")

    fund = service._parse_fund_detail_from_proframe(price_row, fee_row)

    assert fund.fund_code == "KR5200001234"
    assert fund.fund_name == "한투파 블라인드 벤처투자조합 1호"
    assert fund.fund_type == "blind"
    assert fund.company_name == "한국투자파트너스"
    assert fund.company_code == "COM001"
    assert fund.total_amount == Decimal("50000000000")
    assert fund.management_fee_rate == Decimal("2.0")
    assert fund.performance_fee_rate == Decimal("20.0")
    assert fund.established_date == date(2020, 3, 15)
    assert fund.vintage_year == 2020


def test_parse_fund_detail_without_fee():
    """수수료 데이터 없는 펀드 상세 파싱"""
    service = KOFIAService()
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fund = service._parse_fund_detail_from_proframe(price_items[2], None)

    assert fund.fund_code == "KR5200009999"
    assert fund.management_fee_rate is None
    assert fund.performance_fee_rate is None


# --- 필터 / 정렬 테스트 ---


def test_apply_filters_fund_type():
    """fund_types 필터 테스트"""
    service = KOFIAService()
    items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fund_list = service._parse_fund_list_from_proframe(items)

    filtered = KOFIAService._apply_filters(fund_list, fund_types=["project"])
    assert len(filtered) == 1
    assert filtered[0].fund_type == "project"


def test_apply_filters_fund_name():
    """fund_name 키워드 필터 테스트"""
    service = KOFIAService()
    items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fund_list = service._parse_fund_list_from_proframe(items)

    filtered = KOFIAService._apply_filters(fund_list, fund_name="한투파")
    assert len(filtered) == 1
    assert "한투파" in filtered[0].fund_name


def test_apply_sort_by_total_amount():
    """설정액 정렬 테스트"""
    service = KOFIAService()
    items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fund_list = service._parse_fund_list_from_proframe(items)

    sorted_list = KOFIAService._apply_sort(fund_list, sort_by="total_amount", sort_order="desc")
    assert sorted_list[0].total_amount >= sorted_list[1].total_amount


# --- 서비스 통합 테스트 (mock _request_proframe) ---


def _make_service_with_mock(responses: list[tuple[list[dict], int]]):
    """_request_proframe을 모킹한 KOFIAService를 생성한다."""
    from unittest.mock import AsyncMock

    service = KOFIAService()
    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        if call_count < len(responses):
            result = responses[call_count]
            call_count += 1
            return result
        return [], 0

    service._request_proframe = AsyncMock(side_effect=mock_request)
    return service


@pytest.mark.asyncio
async def test_search_funds():
    """펀드 검색 통합 테스트"""
    std_date_items = [{"standardDt": "20260213"}]
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)

    service = _make_service_with_mock(
        [
            (std_date_items, 1),  # _get_latest_standard_date
            (price_items, 3),  # _get_all_fund_prices
        ]
    )

    items, total = await service.search_funds(page=1, size=20)
    await service.close()

    assert total == 3
    assert len(items) == 3
    assert items[0].fund_code == "KR5200001234"


@pytest.mark.asyncio
async def test_search_funds_filter_types():
    """펀드 검색 + 유형 필터 테스트"""
    std_date_items = [{"standardDt": "20260213"}]
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)

    service = _make_service_with_mock(
        [
            (std_date_items, 1),
            (price_items, 3),
        ]
    )

    items, _total = await service.search_funds(fund_types=["project"])
    await service.close()

    assert len(items) == 1
    assert items[0].fund_type == "project"
    assert items[0].fund_code == "KR5200005678"


@pytest.mark.asyncio
async def test_search_funds_company_name():
    """펀드 검색 + 운용사명 필터 테스트"""
    std_date_items = [{"standardDt": "20260213"}]
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)

    service = _make_service_with_mock(
        [
            (std_date_items, 1),
            (price_items, 3),
        ]
    )

    items, _total = await service.search_funds(company_name="미래에셋")
    await service.close()

    assert len(items) == 1
    assert "미래에셋" in items[0].company_name


@pytest.mark.asyncio
async def test_get_fund_detail():
    """펀드 상세 조회 통합 테스트"""
    std_date_items = [{"standardDt": "20260213"}]
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)
    fee_items, _ = _parse_proframe_response(MOCK_FEE_RESPONSE)

    service = _make_service_with_mock(
        [
            (std_date_items, 1),  # _get_latest_standard_date
            (price_items, 3),  # _get_all_fund_prices
            (fee_items, 2),  # _get_latest_fee_date → 수수료 데이터 있음 (탐색)
            (fee_items, 2),  # _get_all_fund_fees → 실제 수수료 조회
        ]
    )

    result = await service.get_fund_detail("KR5200001234")
    await service.close()

    assert result.fund.fund_code == "KR5200001234"
    assert result.fund.management_fee_rate == Decimal("2.0")
    assert result.fund.performance_fee_rate == Decimal("20.0")
    assert result.managers == []


@pytest.mark.asyncio
async def test_get_fund_detail_no_fee():
    """수수료 없는 펀드 상세 조회"""
    std_date_items = [{"standardDt": "20260213"}]
    price_items, _ = _parse_proframe_response(MOCK_FUND_PRICE_RESPONSE)

    service = _make_service_with_mock(
        [
            (std_date_items, 1),  # _get_latest_standard_date
            (price_items, 3),  # _get_all_fund_prices
            ([], 0),  # _get_latest_fee_date 시도 1 (빈 응답)
            ([], 0),  # _get_latest_fee_date 시도 2 (빈 응답)
            ([], 0),  # _get_latest_fee_date 시도 3 (빈 응답)
            # 폴백: std_dt 캐시 사용 → 추가 요청 없음
            ([], 0),  # _get_all_fund_fees (폴백 기준일)
        ]
    )

    result = await service.get_fund_detail("KR5200009999")
    await service.close()

    assert result.fund.fund_code == "KR5200009999"
    assert result.fund.management_fee_rate is None


@pytest.mark.asyncio
async def test_get_fund_managers():
    """운용 전문인력 조회 (현재 미지원)"""
    service = KOFIAService()
    managers, total = await service.get_fund_managers(company_name="한국투자")
    await service.close()

    assert total == 0
    assert managers == []


@pytest.mark.asyncio
async def test_kofia_api_error():
    """KOFIA API 에러 처리 테스트"""
    from unittest.mock import AsyncMock

    from app.core.exceptions import ExternalAPIError

    service = KOFIAService()

    # rate_limiter와 client를 모킹하여 에러 발생 시뮬레이션
    service.rate_limiter.acquire = AsyncMock()

    import httpx

    mock_response = httpx.Response(500, request=httpx.Request("POST", "http://test"))
    service.client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=mock_response.request,
            response=mock_response,
        )
    )

    with pytest.raises(ExternalAPIError) as exc_info:
        await service._request_proframe(
            "FS-DIS2",
            "DISFundStdPriceSO",
            "select",
            "DISCondFuncDTO",
            {"tmpV30": "20260213"},
        )
    await service.close()

    assert exc_info.value.source == "KOFIA"


# --- GP(운용사) 그룹화 테스트 ---

# 5개 펀드 (한투파 2, 디지털캐피탈 1, 미래에셋 2)
MOCK_GP_FUND_RESPONSE = """<?xml version="1.0" encoding="utf-8"?>
<message>
  <proframeHeader>
    <pfmResponseCode>0000</pfmResponseCode>
  </proframeHeader>
  <systemHeader></systemHeader>
  <DISCondFuncListDTO>
    <dbio_total_count_>5</dbio_total_count_>
    <selectMeta>
      <tmpV1>한국투자파트너스</tmpV1>
      <tmpV2>한투파 블라인드 벤처투자조합 1호</tmpV2>
      <tmpV3>혼합주식형</tmpV3>
      <tmpV4>20200315</tmpV4>
      <tmpV5>50000</tmpV5>
      <tmpV12>KR5200001234</tmpV12>
      <tmpV13>COM001</tmpV13>
    </selectMeta>
    <selectMeta>
      <tmpV1>한국투자파트너스</tmpV1>
      <tmpV2>한투파 부동산 사모펀드 2호</tmpV2>
      <tmpV3>부동산형</tmpV3>
      <tmpV4>20220601</tmpV4>
      <tmpV5>80000</tmpV5>
      <tmpV12>KR5200001235</tmpV12>
      <tmpV13>COM001</tmpV13>
    </selectMeta>
    <selectMeta>
      <tmpV1>디지털캐피탈</tmpV1>
      <tmpV2>ABC기업 인수 목적 프로젝트 펀드</tmpV2>
      <tmpV3>주식형</tmpV3>
      <tmpV4>20180601</tmpV4>
      <tmpV5>100000</tmpV5>
      <tmpV12>KR5200005678</tmpV12>
      <tmpV13>COM002</tmpV13>
    </selectMeta>
    <selectMeta>
      <tmpV1>미래에셋벤처투자</tmpV1>
      <tmpV2>미래성장 기술금융 투자조합</tmpV2>
      <tmpV3>혼합채권형</tmpV3>
      <tmpV4>20190101</tmpV4>
      <tmpV5>30000</tmpV5>
      <tmpV12>KR5200009999</tmpV12>
      <tmpV13>COM003</tmpV13>
    </selectMeta>
    <selectMeta>
      <tmpV1>미래에셋벤처투자</tmpV1>
      <tmpV2>미래 인프라 투자조합 1호</tmpV2>
      <tmpV3>인프라형</tmpV3>
      <tmpV4>20240301</tmpV4>
      <tmpV5>20000</tmpV5>
      <tmpV12>KR5200009998</tmpV12>
      <tmpV13>COM003</tmpV13>
    </selectMeta>
  </DISCondFuncListDTO>
</message>"""


def _make_gp_service():
    """GP 테스트용 모킹된 서비스를 생성한다."""
    from unittest.mock import AsyncMock

    service = KOFIAService()
    std_date_items = [{"standardDt": "20260213"}]
    price_items, _ = _parse_proframe_response(MOCK_GP_FUND_RESPONSE)

    call_count = 0

    async def mock_request(*args, **kwargs):
        nonlocal call_count
        responses = [
            (std_date_items, 1),
            (price_items, 5),
        ]
        if call_count < len(responses):
            result = responses[call_count]
            call_count += 1
            return result
        return [], 0

    service._request_proframe = AsyncMock(side_effect=mock_request)
    return service


@pytest.mark.asyncio
async def test_get_gp_list_basic():
    """GP 목록 기본 조회 — AUM desc 정렬"""
    service = _make_gp_service()
    items, total = await service.get_gp_list()
    await service.close()

    assert total == 3
    assert len(items) == 3
    # AUM desc 정렬: 한투파(130B) > 디지털(100B) > 미래에셋(50B)
    assert items[0].company_name == "한국투자파트너스"
    assert items[1].company_name == "디지털캐피탈"
    assert items[2].company_name == "미래에셋벤처투자"


@pytest.mark.asyncio
async def test_get_gp_list_company_name_filter():
    """GP 목록 운용사명 검색 필터"""
    service = _make_gp_service()
    items, total = await service.get_gp_list(company_name="미래")
    await service.close()

    assert total == 1
    assert items[0].company_name == "미래에셋벤처투자"


@pytest.mark.asyncio
async def test_get_gp_list_aum_and_vintage():
    """GP AUM 합산 및 빈티지 범위 검증"""
    service = _make_gp_service()
    items, _total = await service.get_gp_list()
    await service.close()

    # 한투파: 50000 + 80000 = 130000 (백만원) → 130,000,000,000원
    hantupa = next(g for g in items if g.company_name == "한국투자파트너스")
    assert hantupa.fund_count == 2
    assert hantupa.total_aum == Decimal("130000000000")
    assert hantupa.vintage_range == "2020~2022"

    # 디지털: 1개 펀드 → 단일 빈티지
    digital = next(g for g in items if g.company_name == "디지털캐피탈")
    assert digital.fund_count == 1
    assert digital.vintage_range == "2018"

    # 미래에셋: 2019~2024
    mirae = next(g for g in items if g.company_name == "미래에셋벤처투자")
    assert mirae.fund_count == 2
    assert mirae.vintage_range == "2019~2024"


@pytest.mark.asyncio
async def test_get_gp_list_asset_class_filter():
    """GP 목록 자산 클래스 필터 (real_estate)"""
    service = _make_gp_service()
    items, total = await service.get_gp_list(asset_class="real_estate")
    await service.close()

    # 한투파에만 부동산 펀드가 있음
    assert total == 1
    assert items[0].company_name == "한국투자파트너스"


@pytest.mark.asyncio
async def test_get_gp_list_pagination():
    """GP 목록 페이지네이션 (size=2)"""
    service = _make_gp_service()
    items, total = await service.get_gp_list(size=2, page=1)
    await service.close()

    assert total == 3
    assert len(items) == 2

    service2 = _make_gp_service()
    items2, total2 = await service2.get_gp_list(size=2, page=2)
    await service2.close()

    assert total2 == 3
    assert len(items2) == 1


@pytest.mark.asyncio
async def test_get_gp_list_sort_by_fund_count():
    """GP 목록 펀드 수 내림차순 정렬"""
    service = _make_gp_service()
    items, total = await service.get_gp_list(sort_by="fund_count", sort_order="desc")
    await service.close()

    assert total == 3
    # 한투파(2), 미래에셋(2), 디지털(1) — 동일 수는 삽입 순
    assert items[0].fund_count >= items[1].fund_count
    assert items[1].fund_count >= items[2].fund_count
    assert items[2].fund_count == 1
