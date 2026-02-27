import io
import re
import xml.etree.ElementTree as ET
import zipfile

import pytest

from app.core.exceptions import DARTAPIError
from app.schemas.dart import CompanyInfo
from app.services.dart_service import DARTService


def _make_corp_code_zip() -> bytes:
    """테스트용 기업 고유번호 ZIP 파일 생성"""
    root = ET.Element("result")
    for code, name, stock in [
        ("00126380", "삼성전자", "005930"),
        ("00164779", "한국투자파트너스", " "),
        ("00100210", "SK하이닉스", "000660"),
    ]:
        corp = ET.SubElement(root, "list")
        ET.SubElement(corp, "corp_code").text = code
        ET.SubElement(corp, "corp_name").text = name
        ET.SubElement(corp, "stock_code").text = stock
        ET.SubElement(corp, "modify_date").text = "20240101"

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("CORPCODE.xml", xml_bytes)
    return buf.getvalue()


COMPANY_INFO_RESPONSE = {
    "status": "000",
    "message": "정상",
    "corp_code": "00126380",
    "corp_name": "삼성전자",
    "corp_name_eng": "SAMSUNG ELECTRONICS CO.,LTD",
    "stock_name": "삼성전자",
    "stock_code": "005930",
    "ceo_nm": "한종희",
    "corp_cls": "Y",
    "jurir_no": "1301110006246",
    "bizr_no": "1248100998",
    "adres": "경기도 수원시 영통구 삼성로 129",
    "hm_url": "www.samsung.com",
    "ir_url": "",
    "phn_no": "031-200-1114",
    "fax_no": "031-200-7538",
    "induty_code": "264",
    "est_dt": "19690113",
    "acc_mt": "12",
}

DISCLOSURE_RESPONSE = {
    "status": "000",
    "message": "정상",
    "page_no": 1,
    "page_count": 10,
    "total_count": 2,
    "total_page": 1,
    "list": [
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "corp_cls": "Y",
            "report_nm": "사업보고서 (2023.12)",
            "rcept_no": "20240315000001",
            "flr_nm": "삼성전자",
            "rcept_dt": "20240315",
            "rm": "",
        },
        {
            "corp_code": "00126380",
            "corp_name": "삼성전자",
            "corp_cls": "Y",
            "report_nm": "분기보고서 (2024.03)",
            "rcept_no": "20240515000001",
            "flr_nm": "삼성전자",
            "rcept_dt": "20240515",
            "rm": "",
        },
    ],
}

FINANCIAL_RESPONSE = {
    "status": "000",
    "message": "정상",
    "list": [
        {
            "rcept_no": "20240315000001",
            "reprt_code": "11011",
            "bsns_year": "2023",
            "corp_code": "00126380",
            "sj_div": "BS",
            "sj_nm": "재무상태표",
            "account_id": "ifrs-full_Assets",
            "account_nm": "자산총계",
            "account_detail": "-",
            "thstrm_nm": "제 55 기",
            "thstrm_amount": "455905812000000",
            "frmtrm_nm": "제 54 기",
            "frmtrm_amount": "426612010000000",
            "bfefrmtrm_nm": "제 53 기",
            "bfefrmtrm_amount": "426630191000000",
            "ord": "1",
        }
    ],
}


@pytest.mark.asyncio
async def test_get_corp_codes(httpx_mock):
    """기업 고유번호 ZIP 파싱 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*/corpCode\.xml.*"),
        content=_make_corp_code_zip(),
    )

    service = DARTService()
    items = await service.get_corp_codes()
    await service.close()

    assert len(items) == 3
    assert items[0].corp_code == "00126380"
    assert items[0].corp_name == "삼성전자"
    assert items[0].stock_code == "005930"


@pytest.mark.asyncio
async def test_get_company_info(httpx_mock):
    """기업 개황 조회 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*/company\.json.*"),
        json=COMPANY_INFO_RESPONSE,
    )

    service = DARTService()
    result = await service.get_company_info("00126380")
    await service.close()

    assert isinstance(result, CompanyInfo)
    assert result.corp_name == "삼성전자"
    assert result.ceo_nm == "한종희"
    assert result.jurir_no == "1301110006246"


@pytest.mark.asyncio
async def test_search_disclosures(httpx_mock):
    """공시 검색 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*/list\.json.*"),
        json=DISCLOSURE_RESPONSE,
    )

    service = DARTService()
    items, total_count, _total_page = await service.search_disclosures(
        corp_code="00126380",
        bgn_de="20240101",
        end_de="20241231",
    )
    await service.close()

    assert len(items) == 2
    assert total_count == 2
    assert items[0].report_nm == "사업보고서 (2023.12)"


@pytest.mark.asyncio
async def test_get_financial_statements(httpx_mock):
    """재무제표 조회 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*/fnlttSinglAcntAll\.json.*"),
        json=FINANCIAL_RESPONSE,
    )

    service = DARTService()
    items = await service.get_financial_statements(
        corp_code="00126380",
        bsns_year="2023",
    )
    await service.close()

    assert len(items) == 1
    assert items[0].account_nm == "자산총계"
    assert items[0].sj_div == "BS"


@pytest.mark.asyncio
async def test_dart_api_error(httpx_mock):
    """DART API 에러 처리 테스트"""
    httpx_mock.add_response(
        url=re.compile(r".*/company\.json.*"),
        json={"status": "013", "message": "조회된 데이터가 없습니다"},
    )

    service = DARTService()

    with pytest.raises(DARTAPIError) as exc_info:
        await service.get_company_info("99999999")
    await service.close()

    assert exc_info.value.status_code == "013"
