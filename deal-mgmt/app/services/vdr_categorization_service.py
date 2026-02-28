"""VDR 파일명 기반 폴더 카테고리 자동 분류 서비스."""

from __future__ import annotations

from app.models.enums import VdrFolderCategory

# 카테고리별 한글/영문 키워드 (우선순위 순서대로 검사)
_CATEGORY_KEYWORDS: list[tuple[VdrFolderCategory, list[str]]] = [
    (
        VdrFolderCategory.FINANCIAL,
        [
            "재무",
            "감사보고서",
            "손익",
            "재무상태표",
            "시산표",
            "세무조정",
            "현금흐름",
            "BS",
            "IS",
            "PL",
            "CF",
            "financial",
            "audit",
        ],
    ),
    (
        VdrFolderCategory.LEGAL,
        [
            "계약",
            "소송",
            "법률",
            "MOU",
            "NDA",
            "SPA",
            "SHA",
            "BTA",
            "SSA",
            "약정",
            "합의",
            "contract",
            "agreement",
            "legal",
        ],
    ),
    (
        VdrFolderCategory.TAX,
        [
            "세금",
            "세무",
            "법인세",
            "부가세",
            "원천세",
            "이전가격",
            "tax",
            "transfer pricing",
        ],
    ),
    (
        VdrFolderCategory.CORPORATE,
        [
            "정관",
            "등기부",
            "사업자등록",
            "주주명부",
            "이사회",
            "의사록",
            "정기주총",
            "법인등기",
            "corporate",
            "articles",
        ],
    ),
    (
        VdrFolderCategory.HR,
        [
            "인사",
            "노무",
            "급여",
            "취업규칙",
            "근로계약",
            "퇴직",
            "인원현황",
            "조직도",
            "HR",
            "employment",
            "payroll",
        ],
    ),
    (
        VdrFolderCategory.IP,
        [
            "특허",
            "상표",
            "저작권",
            "지식재산",
            "라이선스",
            "디자인권",
            "patent",
            "trademark",
            "IP",
        ],
    ),
    (
        VdrFolderCategory.TECHNICAL,
        [
            "기술",
            "시스템",
            "소프트웨어",
            "IT",
            "서버",
            "technical",
            "software",
        ],
    ),
    (
        VdrFolderCategory.COMMERCIAL,
        [
            "영업",
            "매출",
            "고객",
            "마케팅",
            "수주",
            "파이프라인",
            "commercial",
            "sales",
            "customer",
        ],
    ),
    (
        VdrFolderCategory.REAL_ESTATE,
        [
            "부동산",
            "임대",
            "토지",
            "건물",
            "등기",
            "감정평가",
            "real estate",
            "property",
            "lease",
        ],
    ),
    (
        VdrFolderCategory.ENVIRONMENT,
        [
            "환경",
            "폐기물",
            "오염",
            "환경영향",
            "토양",
            "environment",
            "pollution",
        ],
    ),
    (
        VdrFolderCategory.INSURANCE,
        [
            "보험",
            "보상",
            "보험증권",
            "insurance",
            "policy",
        ],
    ),
    (
        VdrFolderCategory.MARKET_RESEARCH,
        [
            "시장",
            "산업",
            "경쟁사",
            "동향",
            "리서치",
            "트렌드",
            "벤치마크",
            "시장조사",
            "market",
            "industry",
            "research",
            "benchmark",
        ],
    ),
]


def suggest_category(filename: str) -> VdrFolderCategory | None:
    """파일명 기반 VDR 폴더 카테고리를 추천한다.

    Returns:
        매칭된 카테고리, 또는 매칭 실패 시 None
    """
    name_lower = filename.lower()
    for category, keywords in _CATEGORY_KEYWORDS:
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    return None
