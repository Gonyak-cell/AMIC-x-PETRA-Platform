"""VDR 파일 다차원 자동 분류 서비스 — 스코어링 기반 폴더 라우팅."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.models.enums import VdrFolderCategory


@dataclass
class FolderRule:
    """VDR 폴더 자동 분류 규칙."""

    category: VdrFolderCategory
    keywords: list[str]  # 파일명 포함 시 +60점 (첫 매칭)
    preferred_extensions: set[str]  # 확장자 일치 시 +20점
    preferred_mimes: set[str]  # MIME 일치 시 +20점 (extensions OR mimes)
    regex_patterns: list[str]  # 파일명 정규식 일치 시 +20점 (첫 매칭)
    size_bonus_threshold_bytes: int  # 이상이면 size_bonus_score 추가
    size_bonus_score: int  # 크기 보너스 점수
    personal_info_flag: bool = False  # HR: 주민번호 패턴 매칭 시 개인정보 플래그
    tiebreak_group: int = 3  # 1=도메인특화, 2=재무/세무, 3=기타


# ── 카테고리별 분류 규칙 (12개) ──────────────────────────────────────────────
#
# 타이브레이크 그룹 (동점 시 낮을수록 우선):
#   Group 1 — 도메인 특화: HR, REAL_ESTATE, IP, TECHNICAL, ENVIRONMENT, INSURANCE
#   Group 2 — 재무/세무:   FINANCIAL, TAX
#   Group 3 — 기타:        CORPORATE, COMMERCIAL, LEGAL, MARKET_RESEARCH
#
# 스코어링 구성 (최대 100점):
#   파일명 키워드 일치: +60점 (첫 매칭에서 중단)
#   확장자/MIME 일치:  +20점 (OR 조건)
#   파일명 정규식 일치: +20점 (첫 매칭에서 중단)
#   크기 보너스 (TECHNICAL 전용): threshold 이상 시 +size_bonus_score
# ─────────────────────────────────────────────────────────────────────────────

_FOLDER_RULES: list[FolderRule] = [
    # ── 기업 일반 (Group 3) ──────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.CORPORATE,
        keywords=[
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
            # 추가
            "조직도",
            "주권",
            "사업자등록증",
            "주주총회",
            "AoA",
            "BOD",
        ],
        preferred_extensions={".pdf", ".docx"},
        preferred_mimes={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        regex_patterns=[
            r"\d{6}-\d{7}",  # 법인등록번호 (XXXXXX-XXXXXXX)
            r"\d{3}-\d{2}-\d{5}",  # 사업자등록번호 (XXX-XX-XXXXX)
        ],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=3,
    ),
    # ── 재무 자료 (Group 2) ──────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.FINANCIAL,
        keywords=[
            "재무",
            "감사보고서",
            "손익",
            "재무상태표",
            "시산표",
            "현금흐름",
            "BS",
            "IS",
            "PL",
            "CF",
            "financial",
            "audit",
            # 추가
            "원장",
            "차입금",
            "부채",
            "자본",
            "결산",
            "FS",
            "Trial Balance",
        ],
        preferred_extensions={".xlsx", ".csv", ".xls"},
        preferred_mimes={
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "text/csv",
            "application/vnd.ms-excel",
        },
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=2,
    ),
    # ── 세무 자료 (Group 2) ──────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.TAX,
        keywords=[
            "세금",
            "세무",
            "법인세",
            "부가세",
            "원천세",
            "이전가격",
            "tax",
            "transfer pricing",
            # 추가
            "세무조정",
            "세무조사",
            "납세증명",
            "원천징수",
            "지방세",
            "Tax",
            "NTS",
            "홈택스",
        ],
        preferred_extensions={".xlsx", ".pdf", ".hwp"},
        preferred_mimes={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/haansofthwp",
            "application/x-hwp",
        },
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=2,
    ),
    # ── 인사/노무 (Group 1) ──────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.HR,
        keywords=[
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
            # 추가
            "급여대장",
            "노동조합",
            "단체협약",
            "징계",
            "퇴직금",
            "4대보험",
            "Payroll",
        ],
        preferred_extensions={".xlsx", ".pdf", ".docx"},
        preferred_mimes={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        regex_patterns=[r"\d{6}-[1-4]\d{6}"],  # 주민등록번호 (앞 6자리-성별포함 7자리)
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        personal_info_flag=True,
        tiebreak_group=1,
    ),
    # ── 부동산/자산 (Group 1) ────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.REAL_ESTATE,
        keywords=[
            "부동산",
            "임대",
            "토지",
            "건물",
            "등기",
            "감정평가",
            "real estate",
            "property",
            "lease",
            # 추가
            "토지대장",
            "건축물대장",
            "고정자산",
            "설비명세",
            "Lease",
        ],
        preferred_extensions={".pdf", ".docx", ".dwg", ".dxf"},
        preferred_mimes={
            "application/pdf",
            "image/vnd.dwg",
            "application/dxf",
        },
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=1,
    ),
    # ── 지식재산권 (Group 1) ─────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.IP,
        keywords=[
            "특허",
            "상표",
            "저작권",
            "지식재산",
            "라이선스",
            "디자인권",
            "patent",
            "trademark",
            "IP",
            # 추가
            "발명",
            "특허증",
            "출원",
            "Patent",
            "Trademark",
        ],
        preferred_extensions={".pdf", ".docx"},
        preferred_mimes={"application/pdf"},
        regex_patterns=[r"\d{2}-\d{4}-\d{7}"],  # 출원번호/등록번호 (XX-XXXX-XXXXXXX)
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=1,
    ),
    # ── 기술/IT (Group 1) ────────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.TECHNICAL,
        keywords=[
            "기술",
            "시스템",
            "소프트웨어",
            "IT",
            "서버",
            "technical",
            "software",
            # 추가
            "아키텍처",
            "정보보안",
            "개인정보보호",
            "데이터베이스",
        ],
        preferred_extensions={".pdf", ".docx", ".zip", ".tar", ".gz", ".sql", ".json"},
        preferred_mimes={
            "application/pdf",
            "application/zip",
            "application/x-tar",
            "application/gzip",
            "application/json",
        },
        regex_patterns=[],
        # NOTE: 500MB 임계값은 현재 업로드 제한(100MB)으로 실제 발동 불가.
        # 추후 청크 업로드 지원 시 활성화됨.
        size_bonus_threshold_bytes=500 * 1024 * 1024,
        size_bonus_score=20,
        tiebreak_group=1,
    ),
    # ── 환경 (Group 1) ───────────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.ENVIRONMENT,
        keywords=[
            "환경",
            "폐기물",
            "오염",
            "환경영향",
            "토양",
            "environment",
            "pollution",
            # 추가
            "배출시설",
            "수질",
            "대기",
            "유해물질",
            "ESG",
        ],
        preferred_extensions={".pdf", ".shp", ".kml"},
        preferred_mimes={
            "application/pdf",
            "application/vnd.google-earth.kml+xml",
        },
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=1,
    ),
    # ── 보험 (Group 1) ───────────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.INSURANCE,
        keywords=[
            "보험",
            "보상",
            "보험증권",
            "insurance",
            "policy",
            # 추가
            "산재보험",
            "화재보험",
            "임원배상",
            "Insurance",
            "Policy",
        ],
        preferred_extensions={".pdf", ".docx"},
        preferred_mimes={"application/pdf"},
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=1,
    ),
    # ── 영업/마케팅 (Group 3) ────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.COMMERCIAL,
        keywords=[
            "영업",
            "매출",
            "고객",
            "마케팅",
            "수주",
            "파이프라인",
            "commercial",
            "sales",
            "customer",
            # 추가
            "사업계획",
            "단가표",
            "주요고객",
            "공급망",
            "Business Plan",
        ],
        preferred_extensions={".pptx", ".key", ".pdf"},
        preferred_mimes={
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/x-iwork-keynote-sffkey",
            "application/pdf",
        },
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=3,
    ),
    # ── 법률 자료 (Group 3) ──────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.LEGAL,
        keywords=[
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
            # 추가
            "판결문",
            "인허가",
            "Agreement",
            "Contract",
        ],
        preferred_extensions={".pdf", ".docx", ".eml", ".msg"},
        preferred_mimes={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "message/rfc822",
            "application/vnd.ms-outlook",
        },
        regex_patterns=[r"\d{4}[가-힣]+\d+"],  # 한국 법원 사건번호 (예: 2024가합12345)
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=3,
    ),
    # ── 시장자료 (Group 3) ───────────────────────────────────────────────────
    FolderRule(
        category=VdrFolderCategory.MARKET_RESEARCH,
        keywords=[
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
        preferred_extensions={".pdf", ".pptx", ".xlsx"},
        preferred_mimes={
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
        regex_patterns=[],
        size_bonus_threshold_bytes=0,
        size_bonus_score=0,
        tiebreak_group=3,
    ),
]

# 타이브레이크 맵: 카테고리 → 그룹 번호 (낮을수록 우선, 모듈 로드 시 1회 생성)
_TIEBREAK_MAP: dict[VdrFolderCategory, int] = {rule.category: rule.tiebreak_group for rule in _FOLDER_RULES}

# 라우팅 결정을 위한 최소 점수 (키워드 1회 매칭 = 60점).
# 확장자/MIME만 매칭된 20점짜리 결과는 폴백 처리하여 오분류 방지.
_MIN_SCORE_TO_ROUTE = 60

# 짧은 ASCII 키워드(≤3글자)의 단어 경계 매칭 임계값.
# "BS", "IS", "IT", "IP" 등이 "risk", "business" 등의 부분 문자열로
# 잘못 매칭되는 것을 방지한다.
_SHORT_KW_BOUNDARY_LEN = 3


def _keyword_matches(kw_lower: str, name_lower: str) -> bool:
    """키워드 매칭. 짧은 ASCII 키워드는 영문 글자 경계 매칭을 적용한다.

    ``\\b``는 ``_``를 word character로 취급하여 ``ESG_보고서``에서 실패하므로,
    영문 글자(a-zA-Z) 경계만 확인하는 lookaround를 사용한다.
    """
    if len(kw_lower) <= _SHORT_KW_BOUNDARY_LEN and kw_lower.isascii():
        return bool(re.search(rf"(?<![a-zA-Z]){re.escape(kw_lower)}(?![a-zA-Z])", name_lower, re.IGNORECASE))
    return kw_lower in name_lower


def score_document(
    filename: str,
    extension: str,
    mime_type: str,
    file_size_bytes: int,
) -> list[tuple[VdrFolderCategory, int]]:
    """모든 카테고리에 대한 점수를 계산해 내림차순으로 반환한다.

    점수 구성 (최대 100점, TECHNICAL은 size_bonus로 초과 가능):
      - 파일명 키워드 일치: +60점 (첫 매칭에서 중단)
      - 확장자 또는 MIME 일치: +20점 (OR 조건)
      - 파일명 정규식 패턴 일치: +20점 (첫 매칭에서 중단)
      - 크기 보너스 (TECHNICAL 전용): size_bonus_threshold 이상 시 추가

    Note:
        3글자 이하 ASCII 키워드(BS, IS, IT 등)는 단어 경계 매칭을 사용하여
        부분 문자열 오매칭을 방지한다. 한글 키워드에는 적용하지 않는다.

    Args:
        filename: 원본 파일명 (확장자 포함)
        extension: 소문자 확장자 (예: ".pdf")
        mime_type: 선언된 MIME 타입 (예: "application/pdf")
        file_size_bytes: 파일 크기 (바이트)

    Returns:
        (카테고리, 점수) 튜플 목록, 점수 내림차순 정렬. 점수 0인 카테고리 제외.
    """
    name_lower = filename.lower()
    scores: list[tuple[VdrFolderCategory, int]] = []

    for rule in _FOLDER_RULES:
        score = 0

        # 1) 키워드 매칭: +60점 (첫 매칭에서 중단)
        #    짧은 ASCII 키워드는 단어 경계 매칭 적용
        for kw in rule.keywords:
            if _keyword_matches(kw.lower(), name_lower):
                score += 60
                break

        # 2) 확장자/MIME 매칭: +20점 (OR 조건)
        if extension in rule.preferred_extensions or mime_type in rule.preferred_mimes:
            score += 20

        # 3) 정규식 패턴 매칭: +20점 (파일명, 첫 매칭에서 중단)
        for pattern in rule.regex_patterns:
            if re.search(pattern, filename):
                score += 20
                break

        # 4) 크기 보너스 (TECHNICAL 카테고리용)
        if rule.size_bonus_threshold_bytes > 0 and file_size_bytes >= rule.size_bonus_threshold_bytes:
            score += rule.size_bonus_score

        if score > 0:
            scores.append((rule.category, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores


def auto_route(
    filename: str,
    extension: str,
    mime_type: str,
    file_size_bytes: int,
) -> VdrFolderCategory | None:
    """스코어링 결과에서 최적 카테고리를 반환한다.

    동점 시 tiebreak_group 오름차순 (낮을수록 우선):
      1 = 도메인 특화 (HR, REAL_ESTATE, IP, TECHNICAL, ENVIRONMENT, INSURANCE)
      2 = 재무/세무   (FINANCIAL, TAX)
      3 = 기타        (CORPORATE, COMMERCIAL, LEGAL, MARKET_RESEARCH)

    Args:
        filename: 원본 파일명
        extension: 소문자 확장자 (예: ".xlsx")
        mime_type: MIME 타입
        file_size_bytes: 파일 크기 (바이트)

    Returns:
        최적 VdrFolderCategory. 점수 0이면 None (폴백 필요).
    """
    scored = score_document(filename, extension, mime_type, file_size_bytes)
    if not scored:
        return None

    max_score = scored[0][1]
    if max_score < _MIN_SCORE_TO_ROUTE:
        # 키워드 매칭 없이 확장자/MIME만 매칭된 경우 → 폴백 사용
        return None

    tied = [cat for cat, s in scored if s == max_score]

    if len(tied) == 1:
        return tied[0]

    # 동점: tiebreak_group 오름차순 정렬 (stable sort 보장)
    tied.sort(key=lambda cat: _TIEBREAK_MAP.get(cat, 99))
    return tied[0]


def suggest_category(filename: str) -> VdrFolderCategory | None:
    """파일명 기반 VDR 폴더 카테고리를 추천한다. (하위 호환 래퍼)

    기존 API 시그니처를 유지하며 내부적으로 auto_route()에 위임한다.
    MIME 타입·파일 크기 정보 없이 파일명과 확장자만으로 판단한다.

    Returns:
        매칭된 카테고리, 또는 매칭 실패 시 None.
    """
    ext = Path(filename).suffix.lower()
    return auto_route(filename, ext, "application/octet-stream", 0)
