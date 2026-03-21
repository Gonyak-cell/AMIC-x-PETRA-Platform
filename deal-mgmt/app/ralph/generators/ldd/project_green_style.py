"""Project Green 스타일의 LDD 문체 유틸리티."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

_HANGUL_RE = re.compile(r"[가-힣]")
_LEGAL_MODE_ENDING_PATTERN = re.compile(r"것으로\s+(판단됩니다|보입니다|사료됩니다)")
_LEGAL_MODE_PATTERN = re.compile(r"(?<!것으로\s)(판단됩니다|보입니다|사료됩니다)")

_ENDING_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"것으로 판단됨\."), "것으로 판단됩니다."),
    (re.compile(r"것으로 판단됨"), "것으로 판단됩니다"),
    (re.compile(r"것으로 보임\."), "것으로 보입니다."),
    (re.compile(r"것으로 보임"), "것으로 보입니다"),
    (re.compile(r"판단됨\."), "판단됩니다."),
    (re.compile(r"판단됨"), "판단됩니다"),
    (re.compile(r"보임\."), "보입니다."),
    (re.compile(r"보임"), "보입니다"),
    (re.compile(r"사료됨\."), "사료됩니다."),
    (re.compile(r"사료됨"), "사료됩니다"),
    (re.compile(r"확인됨\."), "확인되었습니다."),
    (re.compile(r"확인됨"), "확인되었습니다"),
    (re.compile(r"제공되지 않았음\."), "제공되지 않았습니다."),
    (re.compile(r"제공되지 않았음"), "제공되지 않았습니다"),
    (re.compile(r"필요가 있음\."), "필요가 있습니다."),
    (re.compile(r"필요가 있음"), "필요가 있습니다"),
    (re.compile(r"필요함\."), "필요합니다."),
    (re.compile(r"필요함"), "필요합니다"),
    (re.compile(r"하여야 함\."), "하여야 합니다."),
    (re.compile(r"하여야 함"), "하여야 합니다"),
    (re.compile(r"해야 함\."), "해야 합니다."),
    (re.compile(r"해야 함"), "해야 합니다"),
    (re.compile(r"할 필요가 있음\."), "할 필요가 있습니다."),
    (re.compile(r"할 필요가 있음"), "할 필요가 있습니다"),
    (re.compile(r"반영할 필요가 있음\."), "반영할 필요가 있습니다."),
    (re.compile(r"반영할 필요가 있음"), "반영할 필요가 있습니다"),
    (re.compile(r"확보할 필요가 있음\."), "확보할 필요가 있습니다."),
    (re.compile(r"확보할 필요가 있음"), "확보할 필요가 있습니다"),
    (re.compile(r"명시할 필요가 있음\."), "명시할 필요가 있습니다."),
    (re.compile(r"명시할 필요가 있음"), "명시할 필요가 있습니다"),
    (re.compile(r"작성하였음\."), "작성하였습니다."),
    (re.compile(r"작성하였음"), "작성하였습니다"),
    (re.compile(r"검토하였음\."), "검토하였습니다."),
    (re.compile(r"검토하였음"), "검토하였습니다"),
    (re.compile(r"아니됨\."), "아닙니다."),
    (re.compile(r"아니됨"), "아닙니다"),
)


def is_korean_legal_text(text: str) -> bool:
    return bool(_HANGUL_RE.search(text or ""))


@dataclass(frozen=True)
class ProjectGreenToneContext:
    evidence_count: int = 0
    confidence: float = 0.0
    status: str = ""
    issue_level: str = ""
    rfi_required: bool = False
    evidence_refs: tuple[str, ...] = ()


_DIRECT_CONTRACT_KEYWORDS = (
    "agreement",
    "contract",
    "sha",
    "spa",
    "ssa",
    "bta",
    "mou",
    "정관",
    "주주간계약",
    "계약서",
)

_DIRECT_LEGAL_KEYWORDS = (
    "permit",
    "license",
    "registry",
    "certificate",
    "judgment",
    "lawsuit",
    "complaint",
    "ruling",
    "허가",
    "인허가",
    "등기",
    "등록",
    "판결",
    "소장",
    "고소",
)

_INDIRECT_EVIDENCE_KEYWORDS = (
    "memo",
    "email",
    "e-mail",
    "mail",
    "summary",
    "presentation",
    "ppt",
    "slide",
    "meeting",
    "interview",
    "note",
    "qna",
    "qa",
    "minutes summary",
    "메모",
    "요약",
    "발표",
    "인터뷰",
    "회의",
)


def choose_project_green_modality(context: ProjectGreenToneContext) -> str:
    """근거 강도에 따라 법률평가 종결 어미를 선택한다."""
    status = str(context.status or "").upper()
    profile = _profile_evidence_refs(context.evidence_refs)

    if status == "PENDING":
        return "사료됩니다"

    if context.rfi_required and context.evidence_count == 0:
        return "사료됩니다"

    if profile["has_contract_original"] and profile["has_legal_original"] and context.confidence >= 0.7:
        return "판단됩니다"

    if profile["direct_count"] >= 2 and context.confidence >= 0.8 and not context.rfi_required:
        return "판단됩니다"

    if context.evidence_count == 0 and (context.rfi_required or context.confidence < 0.45):
        return "사료됩니다"

    if profile["indirect_only"] and not profile["direct_count"]:
        return "보입니다"

    if context.evidence_count >= 1 or context.confidence >= 0.55:
        return "보입니다"

    return "사료됩니다"


def _profile_evidence_refs(evidence_refs: tuple[str, ...]) -> dict[str, int | bool]:
    has_contract_original = False
    has_legal_original = False
    direct_count = 0
    indirect_count = 0

    for ref in evidence_refs:
        ref_lower = str(ref or "").lower()
        if not ref_lower:
            continue

        is_contract = any(keyword in ref_lower for keyword in _DIRECT_CONTRACT_KEYWORDS)
        is_legal = any(keyword in ref_lower for keyword in _DIRECT_LEGAL_KEYWORDS)
        is_indirect = any(keyword in ref_lower for keyword in _INDIRECT_EVIDENCE_KEYWORDS)

        if is_contract:
            has_contract_original = True
        if is_legal:
            has_legal_original = True
        if is_contract or is_legal:
            direct_count += 1
        elif is_indirect:
            indirect_count += 1

    return {
        "has_contract_original": has_contract_original,
        "has_legal_original": has_legal_original,
        "direct_count": direct_count,
        "indirect_only": indirect_count > 0 and direct_count == 0,
    }


def normalize_project_green_text(text: str, *, modality: str | None = None) -> str:
    """Project Green 샘플과 유사한 법률실사 말투로 정규화한다."""
    if not text:
        return ""

    paragraphs = [re.sub(r"\s+", " ", paragraph).strip() for paragraph in str(text).split("\n\n")]
    normalized = [_normalize_paragraph(paragraph, modality=modality) for paragraph in paragraphs if paragraph.strip()]
    return "\n\n".join(part for part in normalized if part)


def _normalize_paragraph(text: str, *, modality: str | None = None) -> str:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean or not is_korean_legal_text(clean):
        return clean

    for pattern, replacement in _ENDING_REPLACEMENTS:
        clean = pattern.sub(replacement, clean)

    if modality:
        clean = _apply_selected_modality(clean, modality)

    clean = re.sub(r"\.\.", ".", clean)
    return clean


def _apply_selected_modality(text: str, modality: str) -> str:
    target = modality.rstrip(".")
    updated = _LEGAL_MODE_ENDING_PATTERN.sub(f"것으로 {target}", text)
    updated = _LEGAL_MODE_PATTERN.sub(target, updated)
    return updated


def format_project_green_date(value: datetime | date | str | None) -> str:
    if value is None:
        today = date.today()
        return f"{today.year}년 {today.month}월 {today.day}일"

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return f"{value.year}년 {value.month}월 {value.day}일"

    text = str(value).strip()
    if not text:
        return format_project_green_date(None)
    if "년" in text and "월" in text and "일" in text:
        return text
    date_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if date_match:
        year, month, day = (int(part) for part in date_match.groups())
        return f"{year}년 {month}월 {day}일"
    return text


def build_project_green_foreword(
    *,
    target_company: str,
    report_type_label: str,
    dd_period: str = "",
) -> list[str]:
    """Blank template의 서문 영역에 채울 Project Green 스타일 문단."""
    company = target_company or "대상회사"
    report_type = report_type_label or "법률실사"
    period_phrase = f"{dd_period} 기간 중 " if dd_period else ""

    return [
        (
            f"본 보고서는 {company} 및 관련 거래에 관하여 수행한 {report_type} 결과를 정리한 것으로서, "
            f"{period_phrase}제공된 서류·자료의 검토, 서면 및 구두 질의, 관계자 확인 절차를 통하여 파악된 주요 법률 이슈를 중심으로 작성하였습니다."
        ),
        (
            "본 실사의 목적은 거래 구조, 인허가, 주요 계약, 자산, 노무, 분쟁 기타 거래 종결 및 사후 통합 과정에 "
            "중요한 법률적 영향을 미칠 수 있는 사항을 파악, 확인 및 분석하는 데 있으며, 모든 문제를 망라하기보다는 "
            "거래 판단에 의미 있는 주요 이슈 위주로 제한된 범위 내에서 검토하였습니다. 또한 본 보고서는 현재 유효한 대한민국 법령을 기준으로 작성되었고, "
            "외국 법령이나 별도의 현장실사·독자조사 결과는 별도 명시가 없는 한 반영하지 않았으며, 구체적인 사안에 관한 정식 법률의견으로 해석되어서는 안 됩니다."
        ),
    ]
