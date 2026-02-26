"""한국어 M&A 재무/법률 용어 사전 — 동의어 매핑 및 정규화."""

from __future__ import annotations

import re

# ── 재무 용어 동의어 그룹 ─────────────────────────────────────────────────────

FINANCE_SYNONYMS: dict[str, list[str]] = {
    "revenue": ["매출액", "매출", "수익", "revenue", "sales", "turnover", "연 매출", "매출실적"],
    "operating_income": ["영업이익", "영업손익", "operating income", "operating profit", "OP"],
    "ebitda": ["EBITDA", "상각전영업이익", "ebitda", "감가상각전영업이익"],
    "net_income": ["순이익", "당기순이익", "net income", "NI", "당기순손익"],
    "total_assets": ["총자산", "자산총계", "total assets"],
    "total_liabilities": ["총부채", "부채총계", "total liabilities"],
    "equity": ["자본총계", "자기자본", "equity", "shareholders equity"],
    "debt": ["차입금", "부채", "debt", "borrowings", "금융부채"],
    "working_capital": ["운전자본", "순운전자본", "working capital", "NWC"],
    "capex": ["설비투자", "자본적 지출", "capex", "capital expenditure", "CAPEX"],
    "depreciation": ["감가상각비", "depreciation", "상각비"],
    "gross_profit": ["매출총이익", "gross profit", "GP"],
    "gross_margin": ["매출총이익률", "gross margin"],
    "operating_margin": ["영업이익률", "operating margin", "OP margin"],
    "net_margin": ["순이익률", "net margin"],
    "debt_ratio": ["부채비율", "debt ratio", "D/E ratio"],
    "current_ratio": ["유동비율", "current ratio"],
}

# ── 법률 용어 동의어 그룹 ─────────────────────────────────────────────────────

LEGAL_SYNONYMS: dict[str, list[str]] = {
    "change_of_control": ["경영권 변동", "지배구조 변경", "CoC", "Change of Control", "지배권 이전"],
    "representations_warranties": ["진술보장", "진술 및 보장", "R&W", "reps and warranties"],
    "condition_precedent": ["선행조건", "CP", "condition precedent", "전제조건"],
    "indemnification": ["면책", "손해배상", "indemnification", "indemnity"],
    "escrow": ["에스크로", "escrow", "예치"],
    "earnout": ["조건부 대가", "earnout", "earn-out", "성과보상"],
    "material_adverse_change": ["중대한 악영향", "MAC", "material adverse change", "MAE"],
    "non_compete": ["경업금지", "non-compete", "경쟁제한"],
    "disclosure_schedule": ["공시목록", "disclosure schedule", "DS"],
    "definitive_agreement": ["본계약", "최종계약", "definitive agreement", "DA"],
    "letter_of_intent": ["투자의향서", "LOI", "letter of intent", "의향서"],
    "due_diligence": ["실사", "DD", "due diligence", "기업실사"],
    "shareholder_agreement": ["주주간계약", "SHA", "shareholder agreement", "주주계약"],
    "articles_of_incorporation": ["정관", "articles of incorporation", "AOI"],
}

# ── DDRL 섹션 ↔ 실사자료 매핑 키워드 ──────────────────────────────────────────

DDRL_FILE_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "GOVERNANCE": {
        "keywords": [
            "정관",
            "등기사항",
            "등기부",
            "이사회",
            "주주명부",
            "사업자등록증",
            "법인등기",
            "설립",
            "임원",
            "대표이사",
            "이사",
            "감사",
        ],
        "ddrl_prefixes": ["L1", "L2", "L3"],
    },
    "CAPITAL": {
        "keywords": [
            "주식",
            "자본금",
            "전환사채",
            "CB",
            "BW",
            "스톡옵션",
            "주주협약",
            "우선주",
            "신주인수",
            "유상증자",
            "ESOP",
        ],
        "ddrl_prefixes": ["L4", "L5"],
    },
    "CONTRACTS": {
        "keywords": [
            "계약서",
            "거래처",
            "고객계약",
            "공급계약",
            "금융계약",
            "라이선스",
            "리스",
            "임대차",
            "프랜차이즈",
            "대리점",
        ],
        "ddrl_prefixes": ["L12"],
    },
    "LITIGATION": {
        "keywords": [
            "소송",
            "분쟁",
            "행정처분",
            "제재",
            "과태료",
            "벌금",
            "형사",
            "민사",
            "조사",
            "감사원",
            "규제기관",
        ],
        "ddrl_prefixes": ["L14"],
    },
    "LABOR": {
        "keywords": [
            "근로계약",
            "취업규칙",
            "노동조합",
            "단체협약",
            "퇴직금",
            "퇴직연금",
            "급여",
            "임금",
            "보상",
            "스톡옵션",
        ],
        "ddrl_prefixes": [],
    },
    "IP": {
        "keywords": [
            "특허",
            "실용신안",
            "상표",
            "디자인",
            "저작권",
            "소프트웨어",
            "라이선스",
            "지식재산",
            "IP",
            "발명",
        ],
        "ddrl_prefixes": [],
    },
    "REAL_ESTATE": {
        "keywords": [
            "부동산",
            "토지",
            "건물",
            "건축물대장",
            "등기부등본",
            "임대차",
            "저당권",
            "전세권",
            "환경",
            "오염",
        ],
        "ddrl_prefixes": ["L7"],
    },
    "PERMITS": {
        "keywords": [
            "허가",
            "면허",
            "인가",
            "인허가",
            "영업허가",
            "폐기물",
            "환경부",
            "보조금",
            "그랜트",
            "공정거래",
        ],
        "ddrl_prefixes": ["L15"],
    },
    "TAX": {
        "keywords": [
            "세무",
            "세금",
            "법인세",
            "부가세",
            "부가가치세",
            "이전가격",
            "세무조사",
            "과세",
            "납부",
            "세무신고",
        ],
        "ddrl_prefixes": [],
    },
    "DATA_IT": {
        "keywords": [
            "개인정보",
            "정보보호",
            "ISMS",
            "ISO",
            "보안",
            "데이터",
            "IT",
            "시스템",
            "유출",
            "사고",
        ],
        "ddrl_prefixes": [],
    },
}


# ── 한국 재무 수치 파싱 ───────────────────────────────────────────────────────

_PAREN_NEG_RE = re.compile(r"^\(([0-9,.]+)\)$")
_CURRENCY_RE = re.compile(r"[₩\\$€,원달러]")
_PERCENT_RE = re.compile(r"([0-9,.]+)\s*%")
_NUMBER_RE = re.compile(r"^-?[0-9,.]+$")


def parse_korean_number(text: str) -> float | None:
    """한국어 재무 수치 문자열을 float으로 파싱한다.

    지원 형식:
    - 괄호 음수: "(500)" → -500
    - 통화 기호: "₩1,234", "$1,234", "1,234원"
    - 퍼센트: "12.5%"
    - 천단위 쉼표: "1,234,567"
    - 한국식 단위: "백만원", "억원" (미구현 — Phase 2)
    """
    s = text.strip()
    if not s or s == "-":
        return None

    # 괄호 음수
    m = _PAREN_NEG_RE.match(s)
    if m:
        return -float(m.group(1).replace(",", ""))

    # 통화/기호 제거
    s = _CURRENCY_RE.sub("", s).strip()

    # 퍼센트
    m = _PERCENT_RE.match(s)
    if m:
        return float(m.group(1).replace(",", "")) / 100.0

    # 일반 숫자
    s = s.replace(",", "")
    if _NUMBER_RE.match(s):
        return float(s)

    return None
