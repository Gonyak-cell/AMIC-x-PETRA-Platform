import re
from datetime import date
from decimal import Decimal

import pytest

from app.services.kofia_service import KOFIAService, _parse_date, _parse_decimal, _parse_int

# --- Mock KOFIA DIS 응답 ---

MOCK_FUND_LIST_RESPONSE = {
    "totalCount": 3,
    "result": [
        {
            "fundCd": "KR5200001234",
            "fundNm": "한국투자파트너스 블라인드 벤처투자조합 1호",
            "companyNm": "한국투자파트너스",
            "totalAmt": "50000000000",
            "establishedDt": "20200315",
            "maturityDt": "20300315",
        },
        {
            "fundCd": "KR5200005678",
            "fundNm": "ABC기업 인수 목적 프로젝트 펀드",
            "companyNm": "디지털캐피탈",
            "totalAmt": "100,000,000,000",
            "establishedDt": "20180601",
            "maturityDt": "20280601",
        },
        {
            "fundCd": "KR5200009999",
            "fundNm": "미래성장 기술금융 투자조합",
            "companyNm": "미래에셋벤처투자",
            "totalAmt": "30000000000",
            "establishedDt": "20190101",
            "maturityDt": "20290101",
        },
    ],
}

MOCK_FUND_DETAIL_RESPONSE = {
    "result": {
        "fundCd": "KR5200001234",
        "fundNm": "한국투자파트너스 블라인드 벤처투자조합 1호",
        "fundCategory": "VC",
        "companyNm": "한국투자파트너스",
        "companyCd": "COM001",
        "totalAmt": "50000000000",
        "mgmtFeeRate": "2.0",
        "perfFeeRate": "20.0",
        "establishedDt": "2020-03-15",
        "maturityDt": "2030-03-15",
        "fundDesc": "국내외 벤처기업 투자 목적",
        "sourceUrl": "https://dis.kofia.or.kr/fund/KR5200001234",
    }
}

MOCK_MANAGERS_RESPONSE = {
    "totalCount": 2,
    "result": [
        {
            "managerNm": "김철수",
            "position": "심사역",
            "role": "펀드매니저",
            "careerYears": "10",
            "education": "서울대학교 경영학과",
            "certifications": "CFA, 투자자산운용사",
            "appointedDt": "20200315",
            "resignedDt": "",
            "isActive": True,
        },
        {
            "managerNm": "박영희",
            "position": "수석심사역",
            "role": "리드매니저",
            "careerYears": "15",
            "education": "KAIST 경영대학원",
            "certifications": "CFA",
            "appointedDt": "20200315",
            "resignedDt": "",
            "isActive": True,
        },
    ],
}


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


# --- 회수 집중 구간 테스트 ---


def test_calculate_maturity_alert_in_range():
    """7~10년차 펀드는 회수 집중 구간"""
    # 2019년 설정 → 현재 기준 약 7년차
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
    # 최근 설정이지만 만기가 1년 후
    vintage, is_alert = KOFIAService.calculate_maturity_alert(
        established_date=date(2023, 1, 1),
        maturity_date=date(2027, 1, 1),
    )
    assert vintage == 2023
    assert is_alert is True  # 만기 2년 이내


def test_calculate_maturity_alert_none():
    """설정일 없으면 None, False"""
    vintage, is_alert = KOFIAService.calculate_maturity_alert(None)
    assert vintage is None
    assert is_alert is False


# --- 서비스 파싱 메서드 테스트 ---


@pytest.mark.asyncio
async def test_parse_fund_list():
    """펀드 목록 파싱 테스트"""
    service = KOFIAService()

    items, total = service._parse_fund_list(MOCK_FUND_LIST_RESPONSE)
    await service.close()

    assert total == 3
    assert len(items) == 3

    # 첫 번째: 블라인드 펀드
    assert items[0].fund_code == "KR5200001234"
    assert items[0].fund_name == "한국투자파트너스 블라인드 벤처투자조합 1호"
    assert items[0].fund_type == "blind"
    assert items[0].company_name == "한국투자파트너스"
    assert items[0].total_amount == Decimal("50000000000")

    # 두 번째: 프로젝트 펀드 (쉼표 구분 숫자)
    assert items[1].fund_code == "KR5200005678"
    assert items[1].fund_type == "project"
    assert items[1].total_amount == Decimal("100000000000")

    # 세 번째: 블라인드 펀드 (기술 키워드)
    assert items[2].fund_type == "blind"


@pytest.mark.asyncio
async def test_parse_fund_detail():
    """펀드 상세 파싱 테스트"""
    service = KOFIAService()

    fund = service._parse_fund_detail(MOCK_FUND_DETAIL_RESPONSE)
    await service.close()

    assert fund.fund_code == "KR5200001234"
    assert fund.fund_name == "한국투자파트너스 블라인드 벤처투자조합 1호"
    assert fund.fund_type == "blind"
    assert fund.fund_category == "VC"
    assert fund.company_name == "한국투자파트너스"
    assert fund.total_amount == Decimal("50000000000")
    assert fund.management_fee_rate == Decimal("2.0")
    assert fund.performance_fee_rate == Decimal("20.0")
    assert fund.established_date == date(2020, 3, 15)
    assert fund.maturity_date == date(2030, 3, 15)
    assert fund.vintage_year == 2020


@pytest.mark.asyncio
async def test_parse_managers():
    """운용 전문인력 파싱 테스트"""
    managers = KOFIAService._parse_managers(MOCK_MANAGERS_RESPONSE)

    assert len(managers) == 2

    assert managers[0].manager_name == "김철수"
    assert managers[0].position == "심사역"
    assert managers[0].role == "펀드매니저"
    assert managers[0].career_years == 10
    assert managers[0].education == "서울대학교 경영학과"
    assert managers[0].appointed_date == date(2020, 3, 15)
    assert managers[0].is_active is True

    assert managers[1].manager_name == "박영희"
    assert managers[1].career_years == 15


# --- HTTP 통합 테스트 (httpx_mock) ---


@pytest.mark.asyncio
async def test_search_funds(httpx_mock):
    """펀드 검색 API 호출 + 파싱 통합 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*dis\.kofia\.or\.kr.*callServletService.*"),
        json=MOCK_FUND_LIST_RESPONSE,
    )

    service = KOFIAService()
    items, total = await service.search_funds(company_name="한국투자")
    await service.close()

    assert total == 3
    assert len(items) == 3
    assert items[0].fund_code == "KR5200001234"


@pytest.mark.asyncio
async def test_search_funds_filter_type(httpx_mock):
    """펀드 검색 + 유형 필터 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*dis\.kofia\.or\.kr.*callServletService.*"),
        json=MOCK_FUND_LIST_RESPONSE,
    )

    service = KOFIAService()
    items, total = await service.search_funds(fund_type="project")
    await service.close()

    # 3개 중 프로젝트 펀드는 1개
    assert len(items) == 1
    assert items[0].fund_type == "project"
    assert items[0].fund_code == "KR5200005678"


@pytest.mark.asyncio
async def test_get_fund_detail(httpx_mock):
    """펀드 상세 조회 통합 테스트"""
    # 펀드 기본 정보 + 매니저 목록 (2회 요청)
    httpx_mock.add_response(
        url=re.compile(r".*dis\.kofia\.or\.kr.*callServletService.*"),
        json=MOCK_FUND_DETAIL_RESPONSE,
    )
    httpx_mock.add_response(
        url=re.compile(r".*dis\.kofia\.or\.kr.*callServletService.*"),
        json=MOCK_MANAGERS_RESPONSE,
    )

    service = KOFIAService()
    result = await service.get_fund_detail("KR5200001234")
    await service.close()

    assert result.fund.fund_code == "KR5200001234"
    assert result.fund.management_fee_rate == Decimal("2.0")
    assert len(result.managers) == 2
    assert result.managers[0].manager_name == "김철수"


@pytest.mark.asyncio
async def test_get_fund_managers(httpx_mock):
    """운용 전문인력 목록 통합 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*dis\.kofia\.or\.kr.*callServletService.*"),
        json=MOCK_MANAGERS_RESPONSE,
    )

    service = KOFIAService()
    managers, total = await service.get_fund_managers(company_name="한국투자")
    await service.close()

    assert total == 2
    assert len(managers) == 2
    assert managers[0].manager_name == "김철수"


@pytest.mark.asyncio
async def test_kofia_api_error(httpx_mock):
    """KOFIA API 에러 처리 테스트"""
    from app.core.exceptions import ExternalAPIError

    # AsyncHTTPClient는 500 에러 시 3회 재시도하므로 3개 응답 필요
    for _ in range(3):
        httpx_mock.add_response(
            url=re.compile(r".*dis\.kofia\.or\.kr.*callServletService.*"),
            status_code=500,
        )

    service = KOFIAService()
    with pytest.raises(ExternalAPIError) as exc_info:
        await service.search_funds()
    await service.close()

    assert exc_info.value.source == "KOFIA"
