"""LDD 별첨(Appendix) 생성기.

체크리스트 분석 결과에서 섹션별 데이터를 추출하여
별첨 테이블을 자동 구성한다.

두 가지 모드:
1. 규칙 기반(rule-based): 체크리스트 항목의 structured 필드에서 직접 추출
2. LLM 보조(llm-assisted): 서술 블록에서 LLM이 구조화 데이터 추출 (선택적)
"""

from __future__ import annotations

import logging
from typing import Any

from app.ralph.generators.ldd.appendix_types import (
    APPENDIX_SECTION_MAP,
    APPENDIX_TITLES,
    AppendixResult,
    AppendixRow,
    AppendixTable,
    AppendixType,
)

logger = logging.getLogger(__name__)


class AppendixGenerator:
    """별첨 테이블을 생성한다.

    규칙 기반으로 체크리스트 분석 결과에서 데이터를 추출한다.
    """

    def __init__(self, llm_call=None) -> None:
        self._llm_call = llm_call

    def generate(
        self,
        section_results: dict[str, list[dict[str, Any]]],
        *,
        include_ok: bool = False,
    ) -> AppendixResult:
        """체크리스트 분석 결과에서 별첨 테이블을 생성한다.

        Args:
            section_results: 섹션별 분석 항목 dict
            include_ok: OK 항목도 별첨에 포함할지 여부

        Returns:
            AppendixResult
        """
        tables: list[AppendixTable] = []

        for appendix_type in AppendixType:
            table = self._build_table(
                appendix_type, section_results, include_ok=include_ok,
            )
            tables.append(table)

        return AppendixResult(tables=tables)

    def _build_table(
        self,
        appendix_type: AppendixType,
        section_results: dict[str, list[dict]],
        *,
        include_ok: bool = False,
    ) -> AppendixTable:
        """단일 별첨 타입의 테이블을 구축한다."""
        title = APPENDIX_TITLES.get(appendix_type, f"별지. {appendix_type.value}")
        table = AppendixTable(appendix_type=appendix_type, title=title)
        related_sections = APPENDIX_SECTION_MAP.get(appendix_type, [])

        row_num = 1
        for section_type, items in section_results.items():
            if section_type not in related_sections:
                continue

            for item in items:
                status = item.get("status", "PENDING")
                if status == "NA" or status == "PENDING":
                    continue
                if not include_ok and status == "OK":
                    continue

                row = self._extract_row(appendix_type, item, row_num)
                if row:
                    table.rows.append(row)
                    row_num += 1

        return table

    def _extract_row(
        self,
        appendix_type: AppendixType,
        item: dict[str, Any],
        row_num: int,
    ) -> AppendixRow | None:
        """항목에서 별첨 행을 추출한다."""
        extractor = _EXTRACTORS.get(appendix_type)
        if extractor:
            return extractor(item, row_num)
        return _extract_generic(item, row_num)


# ── 별첨별 데이터 추출 함수 ─────────────────────────────────────────────────

def _extract_litigation(item: dict, row_num: int) -> AppendixRow:
    """소송/분쟁 별첨 행 추출."""
    return AppendixRow(values={
        "연번": str(row_num),
        "사건번호": item.get("case_number", "-"),
        "관할법원": item.get("court", "-"),
        "소송유형": item.get("litigation_type", item.get("name", "-")),
        "당사자": item.get("parties", "-"),
        "소송물가액": item.get("claim_amount", "-"),
        "현재상태": item.get("status_detail", item.get("status", "-")),
        "예상결과": item.get("expected_outcome", "-"),
        "리스크등급": item.get("issue_level", "-"),
        "비고": _truncate(item.get("description", ""), 100),
    })


def _extract_ip(item: dict, row_num: int) -> AppendixRow:
    """지식재산권 별첨 행 추출."""
    return AppendixRow(values={
        "연번": str(row_num),
        "권리유형": item.get("ip_type", item.get("name", "-")),
        "등록번호": item.get("registration_number", "-"),
        "명칭": item.get("ip_name", item.get("name", "-")),
        "출원일": item.get("application_date", "-"),
        "등록일": item.get("registration_date", "-"),
        "권리자": item.get("holder", "-"),
        "존속기간": item.get("expiry_date", "-"),
        "실시계약": item.get("license_info", "-"),
        "비고": _truncate(item.get("description", ""), 100),
    })


def _extract_real_estate(item: dict, row_num: int) -> AppendixRow:
    """부동산 별첨 행 추출."""
    return AppendixRow(values={
        "연번": str(row_num),
        "소재지": item.get("location", "-"),
        "면적(㎡)": item.get("area", "-"),
        "용도지역": item.get("zoning", "-"),
        "소유형태": item.get("ownership_type", "-"),
        "등기사항": item.get("registry_info", "-"),
        "담보설정": item.get("collateral", "-"),
        "임차현황": item.get("lease_info", "-"),
        "감정가(원)": item.get("appraised_value", "-"),
        "비고": _truncate(item.get("description", ""), 100),
    })


def _extract_contracts(item: dict, row_num: int) -> AppendixRow:
    """주요 계약 별첨 행 추출."""
    return AppendixRow(values={
        "연번": str(row_num),
        "계약명": item.get("contract_name", item.get("name", "-")),
        "계약상대방": item.get("counterparty", "-"),
        "계약유형": item.get("contract_type", "-"),
        "계약금액": item.get("contract_amount", "-"),
        "계약기간": item.get("contract_period", "-"),
        "해지조건": item.get("termination_clause", "-"),
        "COC조항": item.get("coc_clause", "-"),
        "리스크등급": item.get("issue_level", "-"),
        "비고": _truncate(item.get("description", ""), 100),
    })


def _extract_insurance(item: dict, row_num: int) -> AppendixRow:
    """보험 별첨 행 추출."""
    return AppendixRow(values={
        "연번": str(row_num),
        "보험유형": item.get("insurance_type", item.get("name", "-")),
        "보험회사": item.get("insurer", "-"),
        "보험기간": item.get("coverage_period", "-"),
        "보험가입금액": item.get("coverage_amount", "-"),
        "보험료": item.get("premium", "-"),
        "주요면책사항": item.get("exclusions", "-"),
        "갱신여부": item.get("renewable", "-"),
        "비고": _truncate(item.get("description", ""), 100),
    })


def _extract_permits(item: dict, row_num: int) -> AppendixRow:
    """인허가 별첨 행 추출."""
    return AppendixRow(values={
        "연번": str(row_num),
        "인허가명": item.get("permit_name", item.get("name", "-")),
        "관할기관": item.get("authority", "-"),
        "허가번호": item.get("permit_number", "-"),
        "허가일": item.get("issue_date", "-"),
        "유효기간": item.get("expiry_date", "-"),
        "갱신여부": item.get("renewable", "-"),
        "양도가능성": item.get("transferable", "-"),
        "리스크등급": item.get("issue_level", "-"),
        "비고": _truncate(item.get("description", ""), 100),
    })


def _extract_generic(item: dict, row_num: int) -> AppendixRow:
    """범용 별첨 행 추출 (특정 추출기가 없을 때)."""
    return AppendixRow(values={
        "연번": str(row_num),
        "항목": item.get("name", "-"),
        "상태": item.get("status", "-"),
        "리스크등급": item.get("issue_level", "-"),
        "설명": _truncate(item.get("description", ""), 200),
    })


def _truncate(text: str, max_len: int) -> str:
    """텍스트를 최대 길이로 자른다."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


# ── 추출기 매핑 ─────────────────────────────────────────────────────────────

_EXTRACTORS = {
    AppendixType.LITIGATION: _extract_litigation,
    AppendixType.IP: _extract_ip,
    AppendixType.REAL_ESTATE: _extract_real_estate,
    AppendixType.CONTRACTS: _extract_contracts,
    AppendixType.INSURANCE: _extract_insurance,
    AppendixType.PERMITS: _extract_permits,
}
