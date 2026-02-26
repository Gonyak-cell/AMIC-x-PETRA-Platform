"""LDD 별첨(Appendix) 데이터 타입.

본문과 분리된 상세 데이터 테이블을 자동 생성하기 위한 타입 정의.

별첨 유형 (거래유형 공통 6종):
- 별지1: 소송/분쟁 목록
- 별지2: 지식재산권 목록
- 별지3: 부동산 현황
- 별지4: 주요 계약 목록
- 별지5: 보험 현황
- 별지6: 인허가 목록
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AppendixType(str, Enum):
    """별첨 유형."""

    LITIGATION = "LITIGATION"  # 별지1: 소송/분쟁 목록
    IP = "IP"  # 별지2: 지식재산권 목록
    REAL_ESTATE = "REAL_ESTATE"  # 별지3: 부동산 현황
    CONTRACTS = "CONTRACTS"  # 별지4: 주요 계약 목록
    INSURANCE = "INSURANCE"  # 별지5: 보험 현황
    PERMITS = "PERMITS"  # 별지6: 인허가 목록


# ── 별첨별 테이블 컬럼 정의 ─────────────────────────────────────────────

APPENDIX_COLUMNS: dict[str, list[str]] = {
    AppendixType.LITIGATION: [
        "연번",
        "사건번호",
        "관할법원",
        "소송유형",
        "당사자",
        "소송물가액",
        "현재상태",
        "예상결과",
        "리스크등급",
        "비고",
    ],
    AppendixType.IP: [
        "연번",
        "권리유형",
        "등록번호",
        "명칭",
        "출원일",
        "등록일",
        "권리자",
        "존속기간",
        "실시계약",
        "비고",
    ],
    AppendixType.REAL_ESTATE: [
        "연번",
        "소재지",
        "면적(㎡)",
        "용도지역",
        "소유형태",
        "등기사항",
        "담보설정",
        "임차현황",
        "감정가(원)",
        "비고",
    ],
    AppendixType.CONTRACTS: [
        "연번",
        "계약명",
        "계약상대방",
        "계약유형",
        "계약금액",
        "계약기간",
        "해지조건",
        "COC조항",
        "리스크등급",
        "비고",
    ],
    AppendixType.INSURANCE: [
        "연번",
        "보험유형",
        "보험회사",
        "보험기간",
        "보험가입금액",
        "보험료",
        "주요면책사항",
        "갱신여부",
        "비고",
    ],
    AppendixType.PERMITS: [
        "연번",
        "인허가명",
        "관할기관",
        "허가번호",
        "허가일",
        "유효기간",
        "갱신여부",
        "양도가능성",
        "리스크등급",
        "비고",
    ],
}

# ── 별첨 유형 → 관련 섹션 매핑 ──────────────────────────────────────────

APPENDIX_SECTION_MAP: dict[str, list[str]] = {
    AppendixType.LITIGATION: ["LITIGATION"],
    AppendixType.IP: ["IP"],
    AppendixType.REAL_ESTATE: ["REAL_ESTATE", "PROPERTY_STATUS", "LEASE"],
    AppendixType.CONTRACTS: ["CONTRACTS", "CONTRACT_SUCCESSION"],
    AppendixType.INSURANCE: ["INSURANCE"],
    AppendixType.PERMITS: ["PERMITS", "ANTITRUST"],
}


@dataclass
class AppendixRow:
    """별첨 테이블의 단일 행."""

    values: dict[str, str] = field(default_factory=dict)

    def to_list(self, columns: list[str]) -> list[str]:
        """컬럼 순서에 맞춰 값 리스트를 반환한다."""
        return [self.values.get(col, "-") for col in columns]


@dataclass
class AppendixTable:
    """별첨 테이블 (별지 1개)."""

    appendix_type: AppendixType
    title: str  # 예: "별지 1. 소송 및 분쟁 현황"
    columns: list[str] = field(default_factory=list)
    rows: list[AppendixRow] = field(default_factory=list)

    def __post_init__(self):
        if not self.columns:
            self.columns = APPENDIX_COLUMNS.get(self.appendix_type, [])

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def is_empty(self) -> bool:
        return len(self.rows) == 0

    def to_dict(self) -> dict:
        return {
            "appendix_type": self.appendix_type.value,
            "title": self.title,
            "columns": self.columns,
            "rows": [r.to_list(self.columns) for r in self.rows],
            "row_count": self.row_count,
        }


@dataclass
class AppendixResult:
    """전체 별첨 결과."""

    tables: list[AppendixTable] = field(default_factory=list)
    cost_usd: float = 0.0

    @property
    def total_tables(self) -> int:
        return len(self.tables)

    @property
    def non_empty_tables(self) -> int:
        return sum(1 for t in self.tables if not t.is_empty)

    @property
    def total_rows(self) -> int:
        return sum(t.row_count for t in self.tables)

    def to_dict(self) -> dict:
        return {
            "total_tables": self.total_tables,
            "non_empty_tables": self.non_empty_tables,
            "total_rows": self.total_rows,
            "cost_usd": self.cost_usd,
            "tables": [t.to_dict() for t in self.tables],
        }


# ── 별첨 제목 매핑 ─────────────────────────────────────────────────────

APPENDIX_TITLES: dict[str, str] = {
    AppendixType.LITIGATION: "별지 1. 소송 및 분쟁 현황",
    AppendixType.IP: "별지 2. 지식재산권 현황",
    AppendixType.REAL_ESTATE: "별지 3. 부동산 현황",
    AppendixType.CONTRACTS: "별지 4. 주요 계약 현황",
    AppendixType.INSURANCE: "별지 5. 보험 현황",
    AppendixType.PERMITS: "별지 6. 인허가 현황",
}
