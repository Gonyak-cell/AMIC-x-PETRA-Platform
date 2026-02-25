"""평판 테마 매핑

IB 실무 관점에서 감성 사전 용어를 정성적 테마 그룹으로 매핑한다.
"""

# 긍정 용어 → 테마 매핑
POSITIVE_THEME_MAP: dict[str, str] = {
    # 엑시트/상장
    "엑시트": "exit_ipo",
    "EXIT": "exit_ipo",
    "상장": "exit_ipo",
    "IPO": "exit_ipo",
    "코스닥": "exit_ipo",
    "코스피": "exit_ipo",
    "스팩합병": "exit_ipo",
    "상장 성공": "exit_ipo",
    "기업공개": "exit_ipo",
    # 펀드레이징/LP
    "펀드 결성": "fundraising",
    "펀드레이징": "fundraising",
    "출자": "fundraising",
    "LP": "fundraising",
    "운용자산": "fundraising",
    "AUM": "fundraising",
    "자금 모집": "fundraising",
    "블라인드펀드": "fundraising",
    # M&A
    "인수": "mna",
    "M&A": "mna",
    "합병": "mna",
    "매각": "mna",
    "바이아웃": "mna",
    # 실적/성과
    "수익률": "performance",
    "성과 보수": "performance",
    "배당": "performance",
    "성장": "performance",
    "호실적": "performance",
    "실적 개선": "performance",
    "최대 실적": "performance",
    "흑자": "performance",
    # 투자 확대
    "투자 확대": "investment_expansion",
    "신규 투자": "investment_expansion",
    "추가 투자": "investment_expansion",
    "후속 투자": "investment_expansion",
    "시리즈": "investment_expansion",
    "대규모 투자": "investment_expansion",
}

# 부정 용어 → 테마 매핑
NEGATIVE_THEME_MAP: dict[str, str] = {
    # 재무/수익성 악화
    "적자": "financial_risk",
    "손실": "financial_risk",
    "수익률 하락": "financial_risk",
    "부실": "financial_risk",
    "채무": "financial_risk",
    "유동성 위기": "financial_risk",
    "자금난": "financial_risk",
    "실적 악화": "financial_risk",
    # 경영/인력 리스크
    "대표 교체": "management_risk",
    "경영권 분쟁": "management_risk",
    "내부 갈등": "management_risk",
    "퇴사": "management_risk",
    "구조조정": "management_risk",
    "인력 유출": "management_risk",
    # 법적/규제 리스크
    "소송": "legal_risk",
    "제재": "legal_risk",
    "과징금": "legal_risk",
    "검찰": "legal_risk",
    "조사": "legal_risk",
    "위반": "legal_risk",
    "불공정": "legal_risk",
    "횡령": "legal_risk",
    # 시장 리스크
    "하락": "market_risk",
    "침체": "market_risk",
    "불황": "market_risk",
    "위축": "market_risk",
    "둔화": "market_risk",
}

# 테마 코드 → 표시명 매핑
THEME_DISPLAY_NAMES: dict[str, str] = {
    "exit_ipo": "포트폴리오 엑시트/상장",
    "fundraising": "펀드레이징/LP 관계",
    "mna": "M&A/매각",
    "performance": "실적/수익성",
    "investment_expansion": "투자 확대",
    "financial_risk": "재무/수익성 악화",
    "management_risk": "경영/인력 리스크",
    "legal_risk": "법적/규제 리스크",
    "market_risk": "시장 리스크",
}

# 테마별 기본 sentiment 방향 (positive / negative)
THEME_SENTIMENT: dict[str, str] = {
    "exit_ipo": "positive",
    "fundraising": "positive",
    "mna": "positive",
    "performance": "positive",
    "investment_expansion": "positive",
    "financial_risk": "negative",
    "management_risk": "negative",
    "legal_risk": "negative",
    "market_risk": "negative",
}

# 리스크 없음 표시 대상 테마 (부정 보도 0건일 때 "✓ ~ 보도 없음" 표시)
RISK_ABSENCE_THEMES = ["legal_risk", "management_risk"]


def get_theme_for_term(term: str) -> str | None:
    """감성 사전 용어에 대응하는 테마 코드를 반환한다."""
    if term in POSITIVE_THEME_MAP:
        return POSITIVE_THEME_MAP[term]
    if term in NEGATIVE_THEME_MAP:
        return NEGATIVE_THEME_MAP[term]
    return None
