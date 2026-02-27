import re
from datetime import date
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup

from app.services.reits_service import (
    REITsService,
    _classify_status,
    _extract_text,
    _parse_date,
    _parse_decimal,
    _parse_int,
)

# --- Mock HTML 응답 ---

MOCK_REITS_LIST_HTML = """
<html><body>
<table class="tbl_list">
<thead><tr><th>코드</th><th>리츠명</th><th>유형</th><th>자산관리회사</th><th>총자산</th><th>부동산비율</th><th>상태</th><th>상장</th></tr></thead>
<tbody>
<tr>
  <td>REITS001</td>
  <td>롯데리츠</td>
  <td>위탁관리</td>
  <td>롯데AMC</td>
  <td>2,500,000</td>
  <td>85.50</td>
  <td>영업중</td>
  <td>상장</td>
</tr>
<tr>
  <td>REITS002</td>
  <td>신한알파리츠</td>
  <td>위탁관리</td>
  <td>신한리츠운용</td>
  <td>1,800,000</td>
  <td>92.30</td>
  <td>영업중</td>
  <td>상장</td>
</tr>
<tr>
  <td>REITS003</td>
  <td>한국토지신탁리츠</td>
  <td>자기관리</td>
  <td></td>
  <td>500,000</td>
  <td>65.00</td>
  <td>인가</td>
  <td>비상장</td>
</tr>
<tr>
  <td>REITS004</td>
  <td>청산중리츠</td>
  <td>위탁관리</td>
  <td>테스트AMC</td>
  <td>100,000</td>
  <td>45.00</td>
  <td>해산</td>
  <td>비상장</td>
</tr>
</tbody>
</table>
</body></html>
"""

MOCK_REITS_DETAIL_HTML = """
<html><body>
<table class="tbl_view">
<tr><th>리츠코드</th><td>REITS001</td></tr>
<tr><th>리츠명</th><td>롯데리츠</td></tr>
<tr><th>리츠유형</th><td>위탁관리 리츠</td></tr>
<tr><th>자산관리회사</th><td>롯데AMC</td></tr>
<tr><th>설립인가일</th><td>2019.07.15</td></tr>
<tr><th>상장일</th><td>2019-10-30</td></tr>
<tr><th>총자산</th><td>2,500,000백만원</td></tr>
<tr><th>부동산자산</th><td>2,137,500백만원</td></tr>
<tr><th>부동산비율</th><td>85.50%</td></tr>
<tr><th>배당수익률</th><td>5.20%</td></tr>
<tr><th>당기순이익</th><td>150,000백만원</td></tr>
<tr><th>배당금</th><td>140,000백만원</td></tr>
<tr><th>임직원수</th><td>0명</td></tr>
<tr><th>상태</th><td>영업중</td></tr>
<tr><th>상장여부</th><td>상장</td></tr>
</table>

<table class="tbl_asset">
<thead><tr><th>자산명</th><th>가액(백만원)</th><th>비율(%)</th><th>소재지</th><th>취득일</th></tr></thead>
<tbody>
<tr>
  <td>롯데월드타워 오피스</td>
  <td>1,200,000</td>
  <td>48.00</td>
  <td>서울 송파구</td>
  <td>2019-10-30</td>
</tr>
<tr>
  <td>롯데백화점 강남점 리테일</td>
  <td>600,000</td>
  <td>24.00</td>
  <td>서울 강남구</td>
  <td>2019-10-30</td>
</tr>
<tr>
  <td>롯데마트 물류센터</td>
  <td>337,500</td>
  <td>13.50</td>
  <td>경기 이천시</td>
  <td>2020-03-15</td>
</tr>
</tbody>
</table>
</body></html>
"""

MOCK_SELF_MANAGED_DETAIL_HTML = """
<html><body>
<table class="tbl_view">
<tr><th>리츠코드</th><td>REITS005</td></tr>
<tr><th>리츠명</th><td>한국자기관리리츠</td></tr>
<tr><th>리츠유형</th><td>자기관리 리츠</td></tr>
<tr><th>자산관리회사</th><td></td></tr>
<tr><th>설립인가일</th><td>20180315</td></tr>
<tr><th>총자산</th><td>800,000</td></tr>
<tr><th>부동산자산</th><td>520,000</td></tr>
<tr><th>당기순이익</th><td>50,000</td></tr>
<tr><th>배당금</th><td>30,000</td></tr>
<tr><th>임직원수</th><td>25명</td></tr>
<tr><th>상태</th><td>영업중</td></tr>
<tr><th>상장여부</th><td>비상장</td></tr>
</table>
<table class="tbl_asset"><tbody></tbody></table>
</body></html>
"""


# --- 유틸리티 함수 테스트 ---


def test_extract_text():
    """HTML 엘리먼트 텍스트 추출"""
    soup = BeautifulSoup("<td> 테스트 값 </td>", "html.parser")
    assert _extract_text(soup.find("td")) == "테스트 값"


def test_extract_text_none():
    """None 엘리먼트는 빈 문자열"""
    assert _extract_text(None) == ""


def test_parse_date_yyyymmdd():
    """YYYYMMDD 형식 날짜 파싱"""
    assert _parse_date("20190715") == date(2019, 7, 15)


def test_parse_date_with_dashes():
    """YYYY-MM-DD 형식 날짜 파싱"""
    assert _parse_date("2019-10-30") == date(2019, 10, 30)


def test_parse_date_with_dots():
    """YYYY.MM.DD 형식 날짜 파싱"""
    assert _parse_date("2019.07.15") == date(2019, 7, 15)


def test_parse_date_empty():
    """빈 문자열은 None 반환"""
    assert _parse_date("") is None
    assert _parse_date("  ") is None
    assert _parse_date(None) is None  # type: ignore[arg-type]


def test_parse_date_invalid():
    """잘못된 형식은 None 반환"""
    assert _parse_date("not-a-date") is None
    assert _parse_date("2019") is None


def test_parse_decimal():
    """숫자 문자열 Decimal 변환"""
    assert _parse_decimal("2,500,000") == Decimal("2500000")
    assert _parse_decimal("85.50") == Decimal("85.50")
    assert _parse_decimal("85.50%") == Decimal("85.50")
    assert _parse_decimal("2,500,000백만원") == Decimal("2500000")
    assert _parse_decimal(100) == Decimal("100")


def test_parse_decimal_empty():
    """빈 값은 None 반환"""
    assert _parse_decimal(None) is None
    assert _parse_decimal("") is None


def test_parse_int():
    """정수 파싱"""
    assert _parse_int("25") == 25
    assert _parse_int("25명") == 25
    assert _parse_int("1,200") == 1200
    assert _parse_int(10) == 10
    assert _parse_int(None) is None
    assert _parse_int("") is None


def test_classify_status():
    """상태 코드 변환"""
    assert _classify_status("영업중") == "operating"
    assert _classify_status("운영중") == "operating"
    assert _classify_status("해산") == "dissolved"
    assert _classify_status("청산") == "dissolved"
    assert _classify_status("인가") == "authorized"
    assert _classify_status("") == "authorized"


# --- 리츠 유형 분류 테스트 ---


def test_classify_reits_type_entrusted():
    """위탁관리 리츠 분류"""
    assert REITsService.classify_reits_type("위탁관리 리츠") == "entrusted"
    assert REITsService.classify_reits_type("위탁관리") == "entrusted"
    assert REITsService.classify_reits_type("기업구조조정 리츠") == "entrusted"


def test_classify_reits_type_self_managed():
    """자기관리 리츠 분류"""
    assert REITsService.classify_reits_type("자기관리 리츠") == "self_managed"
    assert REITsService.classify_reits_type("자기관리") == "self_managed"


def test_classify_reits_type_by_employees():
    """임직원 수 기반 유형 추정"""
    # 유형 텍스트 불명확하지만 임직원 있으면 자기관리
    assert REITsService.classify_reits_type("리츠", employee_count=25) == "self_managed"
    # 임직원 0이면 위탁관리
    assert REITsService.classify_reits_type("리츠", employee_count=0) == "entrusted"
    # 텍스트가 명확하면 텍스트 우선
    assert REITsService.classify_reits_type("위탁관리 리츠", employee_count=25) == "entrusted"


def test_classify_reits_type_default():
    """분류 불가 시 기본값 entrusted"""
    assert REITsService.classify_reits_type("알 수 없는 유형") == "entrusted"
    assert REITsService.classify_reits_type("") == "entrusted"


# --- 부동산 비율 경고 테스트 ---


def test_check_asset_ratio_warning_normal():
    """70% 이상이면 경고 없음"""
    assert REITsService.check_asset_ratio_warning(Decimal("85.50")) is False
    assert REITsService.check_asset_ratio_warning(Decimal("70.00")) is False
    assert REITsService.check_asset_ratio_warning(Decimal("100.00")) is False


def test_check_asset_ratio_warning_below():
    """70% 미달이면 경고"""
    assert REITsService.check_asset_ratio_warning(Decimal("69.99")) is True
    assert REITsService.check_asset_ratio_warning(Decimal("45.00")) is True
    assert REITsService.check_asset_ratio_warning(Decimal("0.00")) is True


def test_check_asset_ratio_warning_none():
    """비율 없으면 경고 없음"""
    assert REITsService.check_asset_ratio_warning(None) is False


# --- 배당성향 계산 테스트 ---


def test_calculate_dividend_payout_ratio():
    """배당성향 = 배당금 / 당기순이익 × 100"""
    ratio = REITsService.calculate_dividend_payout_ratio(
        total_dividend=Decimal("140000"),
        net_income=Decimal("150000"),
    )
    assert ratio == Decimal("93.33")


def test_calculate_dividend_payout_ratio_full():
    """배당성향 100%"""
    ratio = REITsService.calculate_dividend_payout_ratio(
        total_dividend=Decimal("100"),
        net_income=Decimal("100"),
    )
    assert ratio == Decimal("100.00")


def test_calculate_dividend_payout_ratio_none():
    """데이터 없으면 None"""
    assert REITsService.calculate_dividend_payout_ratio(None, Decimal("100")) is None
    assert REITsService.calculate_dividend_payout_ratio(Decimal("100"), None) is None
    assert REITsService.calculate_dividend_payout_ratio(None, None) is None


def test_calculate_dividend_payout_ratio_negative_income():
    """적자(당기순이익 ≤ 0)이면 None"""
    assert REITsService.calculate_dividend_payout_ratio(Decimal("100"), Decimal("-50")) is None
    assert REITsService.calculate_dividend_payout_ratio(Decimal("100"), Decimal("0")) is None


# --- 자산 유형 분류 테스트 ---


def test_classify_asset_type_office():
    """오피스 자산 분류"""
    assert REITsService.classify_asset_type("롯데월드타워 오피스") == "office"
    assert REITsService.classify_asset_type("강남 사무실 빌딩") == "office"
    assert REITsService.classify_asset_type("업무시설 A동") == "office"


def test_classify_asset_type_logistics():
    """물류 자산 분류"""
    assert REITsService.classify_asset_type("롯데마트 물류센터") == "logistics"
    assert REITsService.classify_asset_type("이천 창고") == "logistics"


def test_classify_asset_type_retail():
    """리테일 자산 분류"""
    assert REITsService.classify_asset_type("롯데백화점 강남점 리테일") == "retail"
    assert REITsService.classify_asset_type("역삼동 상가") == "retail"


def test_classify_asset_type_residential():
    """주거 자산 분류"""
    assert REITsService.classify_asset_type("판교 아파트") == "residential"
    assert REITsService.classify_asset_type("임대 주택") == "residential"


def test_classify_asset_type_hotel():
    """호텔 자산 분류"""
    assert REITsService.classify_asset_type("제주 호텔") == "hotel"
    assert REITsService.classify_asset_type("숙박시설") == "hotel"
    assert REITsService.classify_asset_type("강원 리조트") == "hotel"


def test_classify_asset_type_other():
    """분류 불가 시 기본값 other"""
    assert REITsService.classify_asset_type("기타 자산") == "other"
    assert REITsService.classify_asset_type("토지") == "other"


# --- HTML 파싱 테스트 ---


@pytest.mark.asyncio
async def test_parse_reits_list():
    """리츠 목록 HTML 파싱 테스트"""
    service = REITsService()
    soup = BeautifulSoup(MOCK_REITS_LIST_HTML, "html.parser")

    items, total = service._parse_reits_list(soup)
    await service.close()

    assert total == 4
    assert len(items) == 4

    # 첫 번째: 위탁관리, 상장, 경고 없음
    assert items[0].reits_code == "REITS001"
    assert items[0].reits_name == "롯데리츠"
    assert items[0].reits_type == "entrusted"
    assert items[0].management_company == "롯데AMC"
    assert items[0].total_assets == Decimal("2500000")
    assert items[0].real_estate_ratio == Decimal("85.50")
    assert items[0].has_asset_ratio_warning is False
    assert items[0].status == "operating"
    assert items[0].is_listed is True

    # 세 번째: 자기관리, 70% 미달 경고
    assert items[2].reits_code == "REITS003"
    assert items[2].reits_type == "self_managed"
    assert items[2].real_estate_ratio == Decimal("65.00")
    assert items[2].has_asset_ratio_warning is True
    assert items[2].status == "authorized"
    assert items[2].is_listed is False

    # 네 번째: 해산, 45% 경고
    assert items[3].reits_code == "REITS004"
    assert items[3].status == "dissolved"
    assert items[3].has_asset_ratio_warning is True


@pytest.mark.asyncio
async def test_parse_reits_detail():
    """리츠 상세 HTML 파싱 테스트 (위탁관리)"""
    service = REITsService()
    soup = BeautifulSoup(MOCK_REITS_DETAIL_HTML, "html.parser")

    reits = service._parse_reits_detail(soup)
    await service.close()

    assert reits.reits_code == "REITS001"
    assert reits.reits_name == "롯데리츠"
    assert reits.reits_type == "entrusted"
    assert reits.management_company == "롯데AMC"
    assert reits.establishment_date == date(2019, 7, 15)
    assert reits.listing_date == date(2019, 10, 30)
    assert reits.total_assets == Decimal("2500000")
    assert reits.real_estate_amount == Decimal("2137500")
    assert reits.real_estate_ratio == Decimal("85.50")
    assert reits.has_asset_ratio_warning is False
    assert reits.dividend_rate == Decimal("5.20")
    assert reits.net_income == Decimal("150000")
    assert reits.total_dividend == Decimal("140000")
    assert reits.dividend_payout_ratio == Decimal("93.33")
    assert reits.employee_count == 0
    assert reits.status == "operating"
    assert reits.is_listed is True


@pytest.mark.asyncio
async def test_parse_reits_detail_self_managed():
    """자기관리 리츠 상세 파싱 + 부동산 비율 자동 계산"""
    service = REITsService()
    soup = BeautifulSoup(MOCK_SELF_MANAGED_DETAIL_HTML, "html.parser")

    reits = service._parse_reits_detail(soup)
    await service.close()

    assert reits.reits_code == "REITS005"
    assert reits.reits_type == "self_managed"
    assert reits.employee_count == 25
    assert reits.establishment_date == date(2018, 3, 15)

    # 부동산 비율 자동 계산: 520,000 / 800,000 * 100 = 65.00%
    assert reits.real_estate_ratio == Decimal("65.00")
    assert reits.has_asset_ratio_warning is True  # 70% 미달

    # 배당성향: 30,000 / 50,000 * 100 = 60.00%
    assert reits.dividend_payout_ratio == Decimal("60.00")
    assert reits.is_listed is False


@pytest.mark.asyncio
async def test_parse_assets():
    """자산 목록 HTML 파싱 테스트"""
    soup = BeautifulSoup(MOCK_REITS_DETAIL_HTML, "html.parser")

    assets = REITsService._parse_assets(soup)

    assert len(assets) == 3

    # 오피스
    assert assets[0].asset_name == "롯데월드타워 오피스"
    assert assets[0].asset_type == "office"
    assert assets[0].asset_value == Decimal("1200000")
    assert assets[0].asset_ratio == Decimal("48.00")
    assert assets[0].location == "서울 송파구"
    assert assets[0].acquisition_date == date(2019, 10, 30)

    # 리테일
    assert assets[1].asset_name == "롯데백화점 강남점 리테일"
    assert assets[1].asset_type == "retail"
    assert assets[1].asset_value == Decimal("600000")

    # 물류
    assert assets[2].asset_name == "롯데마트 물류센터"
    assert assets[2].asset_type == "logistics"
    assert assets[2].location == "경기 이천시"
    assert assets[2].acquisition_date == date(2020, 3, 15)


@pytest.mark.asyncio
async def test_parse_empty_assets():
    """빈 자산 테이블 파싱"""
    html = "<html><body><table class='tbl_asset'><tbody></tbody></table></body></html>"
    soup = BeautifulSoup(html, "html.parser")

    assets = REITsService._parse_assets(soup)
    assert len(assets) == 0


# --- HTTP 통합 테스트 (httpx_mock) ---


@pytest.mark.asyncio
async def test_search_reits(httpx_mock):
    """리츠 검색 API 호출 + 파싱 통합 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*reits\.molit\.go\.kr.*reitsList.*"),
        text=MOCK_REITS_LIST_HTML,
    )

    service = REITsService()
    items, total = await service.search_reits()
    await service.close()

    assert total == 4
    assert len(items) == 4
    assert items[0].reits_code == "REITS001"


@pytest.mark.asyncio
async def test_search_reits_filter_type(httpx_mock):
    """리츠 검색 + 유형 필터 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*reits\.molit\.go\.kr.*reitsList.*"),
        text=MOCK_REITS_LIST_HTML,
    )

    service = REITsService()
    items, _total = await service.search_reits(reits_type="self_managed")
    await service.close()

    # 4개 중 자기관리 리츠는 1개
    assert len(items) == 1
    assert items[0].reits_type == "self_managed"
    assert items[0].reits_code == "REITS003"


@pytest.mark.asyncio
async def test_search_reits_filter_status(httpx_mock):
    """리츠 검색 + 상태 필터 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*reits\.molit\.go\.kr.*reitsList.*"),
        text=MOCK_REITS_LIST_HTML,
    )

    service = REITsService()
    items, _total = await service.search_reits(status="dissolved")
    await service.close()

    assert len(items) == 1
    assert items[0].status == "dissolved"
    assert items[0].reits_code == "REITS004"


@pytest.mark.asyncio
async def test_get_reits_detail(httpx_mock):
    """리츠 상세 조회 통합 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*reits\.molit\.go\.kr.*reitsDetail.*"),
        text=MOCK_REITS_DETAIL_HTML,
    )

    service = REITsService()
    result = await service.get_reits_detail("REITS001")
    await service.close()

    assert result.reits.reits_code == "REITS001"
    assert result.reits.reits_type == "entrusted"
    assert result.reits.dividend_payout_ratio == Decimal("93.33")
    assert len(result.assets) == 3
    assert result.assets[0].asset_type == "office"


@pytest.mark.asyncio
async def test_get_reits_assets(httpx_mock):
    """리츠 자산 목록 조회 통합 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*reits\.molit\.go\.kr.*reitsDetail.*"),
        text=MOCK_REITS_DETAIL_HTML,
    )

    service = REITsService()
    assets = await service.get_reits_assets("REITS001")
    await service.close()

    assert len(assets) == 3
    assert assets[0].asset_name == "롯데월드타워 오피스"
    assert assets[2].asset_type == "logistics"


@pytest.mark.asyncio
async def test_reits_api_error(httpx_mock):
    """REITs API 에러 처리 테스트"""
    from app.core.exceptions import ExternalAPIError

    # AsyncHTTPClient는 500 에러 시 3회 재시도하므로 3개 응답 필요
    for _ in range(3):
        httpx_mock.add_response(
            url=re.compile(r".*reits\.molit\.go\.kr.*reitsList.*"),
            status_code=500,
        )

    service = REITsService()
    with pytest.raises(ExternalAPIError) as exc_info:
        await service.search_reits()
    await service.close()

    assert exc_info.value.source == "REITs"
