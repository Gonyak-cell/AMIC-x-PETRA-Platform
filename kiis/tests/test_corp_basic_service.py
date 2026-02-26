"""금융위원회 기업기본정보 서비스 (CorpBasicService) 테스트.

테스트 대상: app.services.corp_basic_service.CorpBasicService
- _parse_items(): data.go.kr 응답 파싱 (dict/list 변형 대응)
- _check_result_code(): 응답 코드 검증
- get_outline(): 기업 개요 필드 매핑 (camelCase → snake_case)
- get_affiliates(): 계열회사 필드 매핑
- get_subsidiaries(): 종속기업 필드 매핑 (이중 키 대응)
- get_full_info(): 에러 격리 (부분 실패 시 graceful degradation)
"""

import pytest

from app.core.exceptions import ExternalAPIError
from app.schemas.corp_basic import (
    AffiliateItem,
    CorpBasicInfoResponse,
    CorpOutlineItem,
    SubsidiaryItem,
)
from app.services.corp_basic_service import CorpBasicService


# ── Mock 응답 데이터 ──

MOCK_OUTLINE_RESPONSE = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "totalCount": 1,
            "items": {
                "item": {
                    "crno": "1301110006246",
                    "corpNm": "삼성전자",
                    "corpEnsnNm": "SAMSUNG ELECTRONICS",
                    "enpPbanCmpyNm": "삼성전자",
                    "enpRprFnm": "한종희",
                    "corpRegMrktDcd": "P",
                    "corpRegMrktDcdNm": "유가증권시장",
                    "bzno": "1248100998",
                    "enpOzpno": "16677",
                    "enpBsadr": "경기도 수원시 영통구 삼성로 129",
                    "enpDtadr": "",
                    "enpHmpgUrl": "www.samsung.com",
                    "enpTlno": "031-200-1114",
                    "enpFxno": "031-200-7538",
                    "sicNm": "반도체",
                    "enpEstbDt": "19690113",
                    "enpStacMm": "12",
                    "enpXchgLstgDt": "19750611",
                    "enpKosdaqLstgDt": "",
                    "enpKrxLstgDt": "",
                    "smenpYn": "N",
                    "enpMntrBnkNm": "우리은행",
                    "enpEmpeCnt": "113485",
                    "empeAvgCnwkTermCtt": "12.5",
                    "enpPn1AvgSlryAmt": "130000000",
                    "actnAudpnNm": "삼일회계법인",
                    "audtRptOpnnCtt": "적정",
                    "enpMainBizNm": "반도체 제조",
                    "fssCorpUnqNo": "00126380",
                }
            },
        },
    }
}

MOCK_AFFILIATES_RESPONSE = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "totalCount": 2,
            "items": {
                "item": [
                    {
                        "basDt": "20240101",
                        "crno": "1301110006246",
                        "afilCmpyNm": "삼성SDI",
                        "afilCmpyCrno": "1301110010414",
                        "lstgYn": "상장",
                    },
                    {
                        "basDt": "20240101",
                        "crno": "1301110006246",
                        "afilCmpyNm": "삼성물산",
                        "afilCmpyCrno": "1101110015456",
                        "lstgYn": "상장",
                    },
                ]
            },
        },
    }
}

MOCK_SUBSIDIARIES_RESPONSE = {
    "response": {
        "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
        "body": {
            "totalCount": 1,
            "items": {
                "item": [
                    {
                        "basDt": "20240101",
                        "crno": "1301110006246",
                        "sbrdEnpNm": "Samsung Semiconductor Inc.",
                        "sbrdEnpEstbDt": "20190101",
                        "sbrdEnpAdr": "San Jose, CA",
                        "sbrdEnpMainBizCtt": "반도체 판매",
                        "sbrdEnpLtstEbzyrTastAmt": "5000000000",
                        "dntRltBsisCtt": "의결권 과반수",
                        "mainSbrdEnpYnCtt": "Y",
                    },
                ]
            },
        },
    }
}

MOCK_ERROR_RESPONSE = {
    "response": {
        "header": {"resultCode": "99", "resultMsg": "SERVICE ERROR"},
        "body": {},
    }
}


# ── _parse_items 테스트 ──


class TestParseItems:
    def setup_method(self):
        self.service = CorpBasicService()

    def test_parse_normal_list(self):
        items = self.service._parse_items(MOCK_AFFILIATES_RESPONSE)
        assert len(items) == 2
        assert items[0]["afilCmpyNm"] == "삼성SDI"

    def test_parse_single_item_dict(self):
        """단건 응답 시 item이 dict로 올 때 list[dict]로 변환."""
        items = self.service._parse_items(MOCK_OUTLINE_RESPONSE)
        assert len(items) == 1
        assert items[0]["corpNm"] == "삼성전자"

    def test_parse_empty_items(self):
        data = {"response": {"body": {"items": {}}}}
        items = self.service._parse_items(data)
        assert items == []

    def test_parse_missing_body(self):
        items = self.service._parse_items({})
        assert items == []

    def test_parse_items_as_list(self):
        """items가 list로 바로 오는 경우."""
        data = {
            "response": {
                "body": {
                    "items": [{"key": "val"}]
                }
            }
        }
        items = self.service._parse_items(data)
        assert len(items) == 1

    def test_parse_invalid_type(self):
        data = {"response": {"body": {"items": "invalid"}}}
        items = self.service._parse_items(data)
        assert items == []


# ── _check_result_code 테스트 ──


class TestCheckResultCode:
    def setup_method(self):
        self.service = CorpBasicService()

    def test_success_code(self):
        data = {"response": {"header": {"resultCode": "00"}}}
        self.service._check_result_code(data)  # 예외 없음

    def test_error_code_raises(self):
        with pytest.raises(ExternalAPIError):
            self.service._check_result_code(MOCK_ERROR_RESPONSE)

    def test_missing_result_code_raises(self):
        """resultCode 누락 시 기본값 '99'로 에러 발생."""
        data = {"response": {"header": {}}}
        with pytest.raises(ExternalAPIError):
            self.service._check_result_code(data)

    def test_empty_header_raises(self):
        """header 자체가 없으면 기본값 '99'로 에러 발생."""
        data = {"response": {}}
        with pytest.raises(ExternalAPIError):
            self.service._check_result_code(data)


# ── 필드 매핑 테스트 ──


class TestOutlineMapping:
    def setup_method(self):
        self.service = CorpBasicService()

    def test_outline_fields(self):
        raw_items = self.service._parse_items(MOCK_OUTLINE_RESPONSE)
        item = raw_items[0]
        outline = CorpOutlineItem(
            crno=item.get("crno", ""),
            corp_nm=item.get("corpNm", ""),
            corp_nm_en=item.get("corpEnsnNm", ""),
            pban_cmp_nm=item.get("enpPbanCmpyNm", ""),
            rep_nm=item.get("enpRprFnm", ""),
            mkt_dcd=item.get("corpRegMrktDcd", ""),
            mkt_dcd_nm=item.get("corpRegMrktDcdNm", ""),
            bzno=item.get("bzno", ""),
            ozpno=item.get("enpOzpno", ""),
            bsadr=item.get("enpBsadr", ""),
            dtadr=item.get("enpDtadr", ""),
            hmpg_url=item.get("enpHmpgUrl", ""),
            tlno=item.get("enpTlno", ""),
            fxno=item.get("enpFxno", ""),
            sic_nm=item.get("sicNm", ""),
            est_dt=item.get("enpEstbDt", ""),
            stac_mm=item.get("enpStacMm", ""),
            xchg_lstg_dt=item.get("enpXchgLstgDt", ""),
            kosdaq_lstg_dt=item.get("enpKosdaqLstgDt", ""),
            krx_lstg_dt=item.get("enpKrxLstgDt", ""),
            smenp_yn=item.get("smenpYn", ""),
            mntr_bnk_nm=item.get("enpMntrBnkNm", ""),
            emp_cnt=item.get("enpEmpeCnt", ""),
            avg_cnwk_term=item.get("empeAvgCnwkTermCtt", ""),
            avg_slry_amt=item.get("enpPn1AvgSlryAmt", ""),
            audpn_nm=item.get("actnAudpnNm", ""),
            audt_opnn=item.get("audtRptOpnnCtt", ""),
            main_biz_nm=item.get("enpMainBizNm", ""),
            fss_corp_unq_no=item.get("fssCorpUnqNo", ""),
        )

        assert outline.crno == "1301110006246"
        assert outline.corp_nm == "삼성전자"
        assert outline.corp_nm_en == "SAMSUNG ELECTRONICS"
        assert outline.rep_nm == "한종희"
        assert outline.mkt_dcd == "P"
        assert outline.mkt_dcd_nm == "유가증권시장"
        assert outline.sic_nm == "반도체"
        assert outline.est_dt == "19690113"
        assert outline.emp_cnt == "113485"
        assert outline.audpn_nm == "삼일회계법인"
        assert outline.audt_opnn == "적정"

    def test_outline_missing_fields(self):
        """API 응답에 일부 필드 누락 시 기본값 빈 문자열."""
        outline = CorpOutlineItem(crno="123", corp_nm="테스트")
        assert outline.rep_nm == ""
        assert outline.sic_nm == ""
        assert outline.emp_cnt == ""


class TestAffiliateMapping:
    def setup_method(self):
        self.service = CorpBasicService()

    def test_affiliate_fields(self):
        raw_items = self.service._parse_items(MOCK_AFFILIATES_RESPONSE)
        affiliates = [
            AffiliateItem(
                bas_dt=item.get("basDt", ""),
                crno=item.get("crno", ""),
                afil_cmpy_nm=item.get("afilCmpyNm", ""),
                afil_cmpy_crno=item.get("afilCmpyCrno", ""),
                lstg_yn=item.get("lstgYn", ""),
            )
            for item in raw_items
        ]
        assert len(affiliates) == 2
        assert affiliates[0].afil_cmpy_nm == "삼성SDI"
        assert affiliates[0].afil_cmpy_crno == "1301110010414"
        assert affiliates[0].lstg_yn == "상장"
        assert affiliates[1].afil_cmpy_nm == "삼성물산"


class TestSubsidiaryMapping:
    def setup_method(self):
        self.service = CorpBasicService()

    def test_subsidiary_fields(self):
        raw_items = self.service._parse_items(MOCK_SUBSIDIARIES_RESPONSE)
        subsidiaries = [
            SubsidiaryItem(
                bas_dt=item.get("basDt", ""),
                crno=item.get("crno", ""),
                sbrd_enp_nm=item.get("sbrdEnpNm", ""),
                sbrd_enp_estb_dt=item.get("sbrdEnpEstbDt", ""),
                sbrd_enp_adr=item.get("sbrdEnpAdr", item.get("sbrdEnpadr", "")),
                sbrd_enp_main_biz=item.get("sbrdEnpMainBizCtt", ""),
                sbrd_enp_tast_amt=item.get("sbrdEnpLtstEbzyrTastAmt", ""),
                dnt_rlt_bsis=item.get("dntRltBsisCtt", ""),
                main_sbrd_enp_yn=item.get("mainSbrdEnpYnCtt", ""),
            )
            for item in raw_items
        ]
        assert len(subsidiaries) == 1
        sub = subsidiaries[0]
        assert sub.sbrd_enp_nm == "Samsung Semiconductor Inc."
        assert sub.sbrd_enp_adr == "San Jose, CA"
        assert sub.sbrd_enp_main_biz == "반도체 판매"
        assert sub.sbrd_enp_tast_amt == "5000000000"
        assert sub.dnt_rlt_bsis == "의결권 과반수"
        assert sub.main_sbrd_enp_yn == "Y"

    def test_subsidiary_adr_fallback(self):
        """sbrdEnpAdr 대신 sbrdEnpadr (소문자 a) 케이스 대응."""
        item = {
            "sbrdEnpadr": "Tokyo, Japan",
            "sbrdEnpNm": "Samsung Japan",
        }
        adr = item.get("sbrdEnpAdr", item.get("sbrdEnpadr", ""))
        assert adr == "Tokyo, Japan"

    def test_subsidiary_adr_primary(self):
        """sbrdEnpAdr가 있으면 우선 사용."""
        item = {
            "sbrdEnpAdr": "San Jose, CA",
            "sbrdEnpadr": "should not use",
        }
        adr = item.get("sbrdEnpAdr", item.get("sbrdEnpadr", ""))
        assert adr == "San Jose, CA"


# ── get_full_info 에러 격리 테스트 ──


class TestGetFullInfoIsolation:
    """get_full_info에서 affiliate/subsidiary 실패 시 outline만 반환되는지 검증."""

    @pytest.fixture
    def service(self, monkeypatch):
        svc = CorpBasicService()
        monkeypatch.setattr(svc, "get_outline", self._mock_outline)
        return svc

    @staticmethod
    async def _mock_outline(crno: str):
        return CorpOutlineItem(crno=crno, corp_nm="테스트기업")

    @staticmethod
    async def _mock_affiliates_ok(crno: str):
        return [AffiliateItem(afil_cmpy_nm="자회사A")]

    @staticmethod
    async def _mock_subsidiaries_ok(crno: str):
        return [SubsidiaryItem(sbrd_enp_nm="종속기업B")]

    @staticmethod
    async def _mock_affiliates_fail(crno: str):
        raise ExternalAPIError(source="test", message="affiliate error")

    @staticmethod
    async def _mock_subsidiaries_fail(crno: str):
        raise ExternalAPIError(source="test", message="subsidiary error")

    @pytest.mark.asyncio
    async def test_all_success(self, service, monkeypatch):
        monkeypatch.setattr(service, "get_affiliates", self._mock_affiliates_ok)
        monkeypatch.setattr(service, "get_subsidiaries", self._mock_subsidiaries_ok)

        result = await service.get_full_info("1301110006246")
        assert result.outline is not None
        assert result.outline.corp_nm == "테스트기업"
        assert len(result.affiliates) == 1
        assert len(result.subsidiaries) == 1

    @pytest.mark.asyncio
    async def test_affiliates_fail_graceful(self, service, monkeypatch):
        monkeypatch.setattr(service, "get_affiliates", self._mock_affiliates_fail)
        monkeypatch.setattr(service, "get_subsidiaries", self._mock_subsidiaries_ok)

        result = await service.get_full_info("1301110006246")
        assert result.outline is not None
        assert result.affiliates == []
        assert len(result.subsidiaries) == 1

    @pytest.mark.asyncio
    async def test_subsidiaries_fail_graceful(self, service, monkeypatch):
        monkeypatch.setattr(service, "get_affiliates", self._mock_affiliates_ok)
        monkeypatch.setattr(service, "get_subsidiaries", self._mock_subsidiaries_fail)

        result = await service.get_full_info("1301110006246")
        assert result.outline is not None
        assert len(result.affiliates) == 1
        assert result.subsidiaries == []

    @pytest.mark.asyncio
    async def test_both_fail_graceful(self, service, monkeypatch):
        monkeypatch.setattr(service, "get_affiliates", self._mock_affiliates_fail)
        monkeypatch.setattr(service, "get_subsidiaries", self._mock_subsidiaries_fail)

        result = await service.get_full_info("1301110006246")
        assert result.outline is not None
        assert result.outline.corp_nm == "테스트기업"
        assert result.affiliates == []
        assert result.subsidiaries == []


# ── CorpBasicInfoResponse 스키마 테스트 ──


class TestCorpBasicInfoResponse:
    def test_default_values(self):
        response = CorpBasicInfoResponse()
        assert response.outline is None
        assert response.affiliates == []
        assert response.subsidiaries == []

    def test_with_data(self):
        response = CorpBasicInfoResponse(
            outline=CorpOutlineItem(crno="123", corp_nm="테스트"),
            affiliates=[AffiliateItem(afil_cmpy_nm="계열A")],
            subsidiaries=[SubsidiaryItem(sbrd_enp_nm="종속B")],
        )
        assert response.outline.corp_nm == "테스트"
        assert len(response.affiliates) == 1
        assert len(response.subsidiaries) == 1
