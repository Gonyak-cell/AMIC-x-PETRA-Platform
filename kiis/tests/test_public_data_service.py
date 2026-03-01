"""공공데이터포털 자산운용사 정보 서비스 테스트"""

from decimal import Decimal

import pytest

from app.services.public_data_service import PublicDataService
from app.utils.numeric import safe_decimal, safe_int

# --- 유틸리티 함수 테스트 ---


class TestSafeDecimal:
    def test_valid_number(self):
        assert safe_decimal("12345.67") == Decimal("12345.67")

    def test_comma_separated(self):
        assert safe_decimal("1,234,567") == Decimal("1234567")

    def test_none(self):
        assert safe_decimal(None) is None

    def test_empty(self):
        assert safe_decimal("") is None

    def test_dash(self):
        assert safe_decimal("-") is None

    def test_zero(self):
        assert safe_decimal("0") is None

    def test_invalid(self):
        assert safe_decimal("N/A") is None


class TestSafeInt:
    def test_valid(self):
        assert safe_int("42") == 42

    def test_comma(self):
        assert safe_int("1,234") == 1234

    def test_none(self):
        assert safe_int(None) is None

    def test_empty(self):
        assert safe_int("") is None

    def test_integer_input(self):
        assert safe_int(100) == 100


# --- 응답 파싱 테스트 ---


MOCK_GENERAL_RESPONSE = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "totalCount": 2,
            "items": {
                "item": [
                    {
                        "fncoNm": "에이티유파트너스자산운용",
                        "fncoNo": "FC001",
                        "empcnt": "15",
                        "oprtAssetAmt": "500000",
                        "fundCnt": "3",
                        "authorizDt": "20200101",
                        "baseYm": "202601",
                    },
                    {
                        "fncoNm": "삼성자산운용",
                        "fncoNo": "FC002",
                        "empcnt": "450",
                        "oprtAssetAmt": "350000000",
                        "fundCnt": "250",
                        "authorizDt": "19980301",
                        "baseYm": "202601",
                    },
                ]
            },
        },
    }
}

MOCK_FINANCIAL_RESPONSE = {
    "response": {
        "header": {"resultCode": "00"},
        "body": {
            "totalCount": 1,
            "items": {
                "item": [
                    {
                        "fncoNm": "삼성자산운용",
                        "cptlAmt": "50000",
                        "totalAsset": "120000",
                        "oprtRevnAmt": "80000",
                    },
                ]
            },
        },
    }
}

MOCK_FN_CO_RESPONSE = {
    "response": {
        "header": {"resultCode": "00"},
        "body": {
            "totalCount": 1,
            "items": {
                "item": [
                    {
                        "fncoNm": "에이티유파트너스자산운용",
                        "fncoEnNm": "ATU Partners Asset Management",
                        "brno": "123-45-67890",
                        "crno": "110111-0123456",
                        "estbDt": "20200101",
                        "bnAdrs": "서울특별시 강남구",
                        "rprsTelno": "02-1234-5678",
                    },
                ]
            },
        },
    }
}


class TestParseItems:
    def setup_method(self):
        self.service = PublicDataService()

    def test_parse_normal_items(self):
        items = self.service._parse_items(MOCK_GENERAL_RESPONSE)
        assert len(items) == 2
        assert items[0]["fncoNm"] == "에이티유파트너스자산운용"

    def test_parse_empty(self):
        items = self.service._parse_items({"response": {"body": {"items": {}}}})
        assert items == []

    def test_parse_single_item(self):
        data = {"response": {"body": {"items": {"item": {"fncoNm": "단일"}}}}}
        items = self.service._parse_items(data)
        assert len(items) == 1
        assert items[0]["fncoNm"] == "단일"

    def test_parse_total(self):
        total = self.service._parse_total(MOCK_GENERAL_RESPONSE)
        assert total == 2

    def test_parse_invalid(self):
        items = self.service._parse_items({})
        assert items == []

    def test_parse_total_invalid(self):
        total = self.service._parse_total({})
        assert total == 0


class TestSearchGPRegistry:
    """search_gp_registry의 데이터 조합 로직 테스트 (API 호출 모킹)."""

    @pytest.fixture
    def service(self, monkeypatch):
        svc = PublicDataService()
        # 캐시 데코레이터를 우회하여 직접 mock 반환
        monkeypatch.setattr(svc, "_get_gp_general_list", self._mock_general)
        monkeypatch.setattr(svc, "_get_gp_financial_list", self._mock_financial)
        monkeypatch.setattr(svc, "_get_fn_co_list", self._mock_fn_co)
        return svc

    @staticmethod
    async def _mock_general(page=1, size=500):
        return MOCK_GENERAL_RESPONSE

    @staticmethod
    async def _mock_financial(page=1, size=500):
        return MOCK_FINANCIAL_RESPONSE

    @staticmethod
    async def _mock_fn_co(page=1, size=500):
        return MOCK_FN_CO_RESPONSE

    @pytest.mark.asyncio
    async def test_all_gps_returned(self, service):
        items, total = await service.search_gp_registry()
        assert total == 2
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_search_filter(self, service):
        items, total = await service.search_gp_registry(company_name="에이티유")
        assert total == 1
        assert items[0].company_name == "에이티유파트너스자산운용"

    @pytest.mark.asyncio
    async def test_financial_join(self, service):
        items, _ = await service.search_gp_registry(company_name="삼성")
        samsung = items[0]
        assert samsung.capital == Decimal("50000")
        assert samsung.total_assets == Decimal("120000")

    @pytest.mark.asyncio
    async def test_fn_co_join(self, service):
        items, _ = await service.search_gp_registry(company_name="에이티유")
        atu = items[0]
        assert atu.company_name_en == "ATU Partners Asset Management"
        assert atu.address == "서울특별시 강남구"
        assert atu.established_date == "20200101"

    @pytest.mark.asyncio
    async def test_pagination(self, service):
        items, total = await service.search_gp_registry(page=1, size=1)
        assert total == 2
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_page_2(self, service):
        items, total = await service.search_gp_registry(page=2, size=1)
        assert total == 2
        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_sorted_by_aum_desc(self, service):
        items, _ = await service.search_gp_registry()
        # 삼성(350000000) > 에이티유(500000)
        assert items[0].company_name == "삼성자산운용"

    @pytest.mark.asyncio
    async def test_no_results(self, service):
        items, total = await service.search_gp_registry(company_name="존재하지않는운용사")
        assert total == 0
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_get_gp_by_name(self, service):
        result = await service.get_gp_by_name("에이티유파트너스자산운용")
        assert result is not None
        assert result.company_name == "에이티유파트너스자산운용"

    @pytest.mark.asyncio
    async def test_get_gp_by_name_not_found(self, service):
        result = await service.get_gp_by_name("없는운용사12345")
        assert result is None
