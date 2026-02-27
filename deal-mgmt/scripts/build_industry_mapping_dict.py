"""
업종명 마스터 매핑 사전 구축 스크립트
=====================================
20개 기업개황 CSV 파일의 고유 업종명을 KSIC 코드로 매핑하여
industry_master_dict.csv (성공) / manual_review_required.csv (실패)로 분리 저장한다.

매칭 순서:
  0차: 수동 확정 매핑 (MANUAL_OVERRIDE, 45건)
  1차: industry_classification exact (4자리)
  2차: industry_classification fuzzy (4자리, >=0.80)
  3차: Aggressive 정규화 exact/fuzzy (4자리)
  4차: io_name 접미사 제거 exact/fuzzy (5자리)
  5차: HWP 5자리 마스터 exact/fuzzy (한국표준산업분류 제10차 개정)
  6차: KSIC 11차 연계표 exact/fuzzy (10차-11차 혼용 대응)
  7차: 상위분류 매핑 + 복합업종 분해 매칭

사용법:
    cd deal-mgmt
    python scripts/build_industry_mapping_dict.py
"""

import difflib
import glob
import os
import re
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
SI_CSV_DIR = BASE_DIR / "app" / "marketing" / "si_list" / "csv"
MAPPING_DB_DIR = BASE_DIR / "app" / "marketing" / "si_mapping" / "db"
INDUSTRY_CSV = MAPPING_DB_DIR / "industry_classification.csv"
IO_KSIC_CSV = MAPPING_DB_DIR / "io_ksic_mapping.csv"
HWP_PATH = MAPPING_DB_DIR / "한국표준산업분류(2017.1)-제10차개정_20260106085911.hwp"
HWP_CSV = MAPPING_DB_DIR / "ksic_5digit_from_hwp.csv"
LINKAGE_XLSX = (
    MAPPING_DB_DIR
    / "한국표준산업분류 제11차-제10차 연계표_20240509_20240514030911.xlsx"
)
LINKAGE_CSV = MAPPING_DB_DIR / "ksic_11th_linkage.csv"
OUTPUT_DIR = MAPPING_DB_DIR

FUZZY_THRESHOLD = 0.80          # 1~4차 매칭
HWP_FUZZY_THRESHOLD = 0.75      # 5차 HWP 전용 (공식 분류표 신뢰도 높음)

# ---------------------------------------------------------------------------
# 수동 확정 매핑 (자동 파이프라인 1~7차로 해결 불가한 45건)
# 교차검증: industry_classification.csv, ksic_5digit_from_hwp.csv, ksic_11th_linkage.csv
# ---------------------------------------------------------------------------
MANUAL_OVERRIDE: dict[str, tuple[str, str]] = {
    # {정규화_업종명: (KSIC_코드, KSIC_명칭)}
    #
    # --- A. 최근접 후보 정확 (19건) ---
    "건축기술 엔지니어링 및 관련 기술 서비스업": ("72129", "기타 엔지니어링 서비스업"),
    "건축기술 엔지니어링 및 기타 과학기술 서비스업": ("72129", "기타 엔지니어링 서비스업"),
    "건축자재 철물 및 난방장치 도매업": ("46621", "배관 및 냉ㆍ난방장치 도매업"),
    "경비 경호 및 탐정업": ("75310", "경비 및 경호 서비스업"),
    "기타 광고업": ("71391", "옥외 광고업"),
    "사진 촬영 및 처리업": ("73303", "사진 처리업"),
    "실내건축 및 건축마무리 공사업": ("42499", "그 외 기타 건축 마무리 공사업"),
    "예술품 기념품 및 장식용품 소매업": ("47842", "기념품, 관광 민예품 및 장식용품 소매업"),
    "욕탕 마사지 및 기타 신체관리 서비스업": ("96129", "체형 등 기타 신체관리 서비스업"),
    "운송장비용 연료 소매업": ("47712", "운송장비용 수소 충전업"),
    "은행 및 저축기관": ("64132", "상호저축은행 및 기타 저축기관"),
    "외국어학원 및 기타 교습학원": ("85632", "기타 교습학원"),
    "전문 디자인업": ("73202", "제품 디자인업"),
    "철골 철근 및 콘크리트 공사업": ("42131", "철골 및 관련 구조물 공사업"),
    "철물 공구 창호 및 건설자재 소매업": ("47519", "페인트, 창호 및 기타 건설자재 소매업"),
    "콘크리트 레미콘 및 기타 시멘트 플라스터 제품 제조업": ("23420", "콘크리트, 시멘트 및 플라스터제품 제조업"),
    "해체 선별 및 원료 재생업": ("38312", "금속류 원료 재생업"),
    "회사 본부": ("71531", "경영 컨설팅업"),
    "회사 본부 및 경영 컨설팅 서비스업": ("71531", "경영 컨설팅업"),
    #
    # --- B. 오류 정정 (7건) ---
    "건물 및 산업설비 청소업": ("74211", "건축물 일반 청소업"),
    "보건업": ("86909", "그 외 기타 보건업"),
    "서적 및 문구용품 소매업": ("47521", "서적 소매업"),
    "오디오물 출판 및 원판 녹음업": ("59010", "영화, 비디오물, 방송프로그램 제작업"),
    "초등 교육기관": ("85120", "초등학교"),
    "일반 중등 교육기관": ("85211", "일반 중학교"),
    "미용 욕탕 및 유사 서비스업": ("96111", "미용업"),
    #
    # --- C. 상위분류 대표코드 (8건) ---
    "농업": ("01110", "곡물 재배업"),
    "발전업": ("35113", "화력 발전업"),
    "병원": ("86101", "종합병원"),
    "건물 건설업": ("41110", "주거용 건물 건설업"),
    "종합 건설업": ("41110", "주거용 건물 건설업"),
    "출판업": ("58110", "서적 출판업"),
    "도매 및 상품 중개업": ("46101", "농산물 중개업"),
    "전문직별 공사업": ("42311", "일반전기 공사업"),
    #
    # --- D. 복합업종 첫 키워드 기준 (11건) ---
    "가방 시계 안경 및 기타 생활용품 도매업": ("46499", "그 외 기타 생활용품 도매업"),
    "건물산업설비 청소 및 방제 서비스업": ("74211", "건축물 일반 청소업"),
    "생활용 포장위생용품 문구용품 및 출판 인쇄물 도매업": ("46451", "생활용 포장 및 위생용품, 봉투 및 유사 제품 도매업"),
    "음반 및 비디오물 악기 오락 및 경기용품 도매업": ("46461", "음반 및 비디오물 도매업"),
    "석재 쇄석 및 모래 자갈 채취업": ("07122", "모래 및 자갈 채취업"),
    "섬유 직물 및 의복액세서리 소매업": ("47411", "섬유 및 직물류 소매업"),
    "선박 및 수상 부유 구조물 건조업": ("30111", "강선 건조업"),
    "소화물 전문 운송업": ("49224", "특수 화물 자동차 운송업"),
    "신용조합 및 저축기관": ("64139", "기타 저축기관"),
    "어로 어업": ("03112", "연근해 어업"),
    "일반 기계류 수리업": ("34019", "기타 일반 기계 및 장비 수리업"),
}


# ---------------------------------------------------------------------------
# Step 1: 문자열 정규화 함수
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    """업종명 텍스트를 정규화한다 (공백/특수문자 제거, 소문자 변환)."""
    if not isinstance(text, str):
        return ""
    s = text.strip()
    s = s.lower()
    # 괄호 내용 제거 (예: "(가금류 제외)", "(소프트웨어 개발 및 공급업 제외)")
    s = re.sub(r"\([^)]*\)", "", s)
    # 세미콜론 이후 구문 제거 (예: "화학물질 및 화학제품 제조업; 의약품 제외")
    s = re.sub(r";.*$", "", s)
    # 괄호, 쉼표, 세미콜론, 중점(ㆍ·), 기타 특수기호 제거
    s = re.sub(r"[(),;·ㆍ\[\]{}\"'`~!@#$%^&*+=|\\/<>?]", "", s)
    # 다중 공백 → 단일 공백
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_aggressive(text: str) -> str:
    """추가 정규화: '그 외 기타' → '기타', '1차' 제거, 접두사 노이즈 제거."""
    s = normalize(text)
    if not s:
        return s
    # "그 외 기타" → "기타" (KSIC 명명 규칙에서 세세분류의 잔여 카테고리)
    s = re.sub(r"^그\s*외\s*기타\s*", "기타 ", s)
    # "그 외" → "" (단독 사용)
    s = re.sub(r"^그\s*외\s*", "", s)
    # "그외" → "" (붙여쓰기)
    s = re.sub(r"^그외\s*", "", s)
    # "1차 " 접두사 제거 (예: "1차 철강 제조업" → "철강 제조업")
    s = re.sub(r"^1차\s+", "", s)
    # "달리 분류되지 않은 " 제거 (예: "달리 분류되지 않은 개인 서비스업")
    s = re.sub(r"달리\s*분류되지\s*않은\s*", "", s)
    return s.strip()


# 업종 접미사 목록 (긴 것부터 매칭하여 가장 구체적인 접미사 우선 제거)
_INDUSTRY_SUFFIXES = [
    "임가공업", "제조업", "도매업", "소매업", "건설업", "수리업",
    "서비스업", "가공업", "재배업", "사육업", "발전업", "광업",
    "어업", "운송업", "중개업", "보험업", "사업", "업",
]


def normalize_strip_suffix(text: str) -> str:
    """정규화 + 업종 접미사 제거 (io_name 매칭용)."""
    s = normalize(text)
    if not s:
        return s
    for suf in _INDUSTRY_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)].strip()
            break
    return s


# ---------------------------------------------------------------------------
# HWP 파싱: 한국표준산업분류 제10차 개정에서 5자리 코드 추출
# ---------------------------------------------------------------------------
def extract_hwp_text(hwp_path: Path) -> list[str]:
    """HWP 파일에서 본문 텍스트 청크 리스트를 추출한다 (hwp5 이벤트 기반)."""
    from hwp5.treeop import STARTEVENT
    from hwp5.xmlmodel import Hwp5File

    hwpfile = Hwp5File(str(hwp_path))
    chunks = []
    for section_name in sorted(hwpfile.bodytext):
        section = hwpfile.bodytext[section_name]
        for event, item in section.events():
            if event is not STARTEVENT:
                continue
            if isinstance(item, tuple) and len(item) >= 2:
                payload = item[1]
                if isinstance(payload, dict) and "text" in payload:
                    t = payload["text"]
                    if isinstance(t, str) and t.strip():
                        chunks.append(t.strip())
    return chunks


def parse_ksic_5digit(text_chunks: list[str]) -> list[dict]:
    """텍스트 청크 리스트에서 5자리 KSIC 코드+명칭 쌍을 추출한다."""
    results = []
    seen = set()
    n = len(text_chunks)

    for i, line in enumerate(text_chunks):
        # 5자리 숫자만 있는 행 → 다음 행이 한글 명칭
        if not re.match(r"^\d{5}$", line):
            continue
        code = line
        if i + 1 >= n:
            continue
        name_line = text_chunks[i + 1]
        if not re.match(r"^[\uAC00-\uD7A3]", name_line):
            continue

        # 다음 행이 명칭 연속인지 확인 (줄바꿈으로 잘린 경우)
        full_name = name_line
        j = i + 2
        while j < n:
            nxt = text_chunks[j]
            if not nxt or re.match(r"^\d", nxt) or re.match(r"^[A-Z]", nxt):
                break
            if re.match(r"^<", nxt):  # <제 외> 등 주석
                break
            if re.match(r"^[\uAC00-\uD7A3]", nxt) and len(nxt) < 30:
                full_name += " " + nxt  # 공백 추가하여 결합
                j += 1
            else:
                break

        # 중복 제거 (HWP 본문에 목차+본문 두 번 등장)
        if code not in seen:
            seen.add(code)
            # 다중 공백 정리
            full_name = re.sub(r"\s+", " ", full_name).strip()
            results.append({"ksic_code_5": code, "ksic_name": full_name})

    results.sort(key=lambda x: x["ksic_code_5"])
    return results


def load_or_extract_hwp_5digit() -> dict:
    """
    HWP 5자리 룩업을 로드한다.
    캐시 CSV가 있으면 사용하고, 없으면 HWP에서 추출 후 CSV로 저장한다.
    반환: {normalized_name: (orig_name, ksic_5digit_code)}
    """
    if HWP_CSV.exists():
        df = pd.read_csv(HWP_CSV, dtype=str)
        print(f"  HWP 5자리 캐시 로드: {HWP_CSV.name} ({len(df)}행)")
    elif HWP_PATH.exists():
        print(f"  HWP 파싱 시작: {HWP_PATH.name}")
        chunks = extract_hwp_text(HWP_PATH)
        print(f"    텍스트 청크: {len(chunks):,}개")
        records = parse_ksic_5digit(chunks)
        print(f"    5자리 코드 추출: {len(records)}개")
        df = pd.DataFrame(records)
        df.to_csv(HWP_CSV, encoding="utf-8-sig", index=False)
        print(f"    캐시 저장: {HWP_CSV.name}")
    else:
        print(f"  경고: HWP 파일 없음 - 5차 매칭 건너뜀")
        return {}

    lookup = {}
    for _, row in df.iterrows():
        name = str(row["ksic_name"]).strip()
        code = str(row["ksic_code_5"]).strip()
        norm = normalize(name)
        if norm and norm not in lookup:
            lookup[norm] = (name, code)
    return lookup


# ---------------------------------------------------------------------------
# KSIC 11차-10차 연계표 로드
# ---------------------------------------------------------------------------
def load_or_extract_linkage_11th():
    """
    KSIC 11차-10차 연계표를 로드한다.
    캐시 CSV가 있으면 사용하고, 없으면 Excel에서 추출 후 CSV로 저장한다.

    반환:
        linkage_lookup: {normalized_11th_name: (orig_name, ksic_11th_code)}
        reverse_map: {ksic_11th_code: [(ksic_10th_code, ksic_10th_name, change_type), ...]}
    """
    if LINKAGE_CSV.exists():
        df = pd.read_csv(LINKAGE_CSV, dtype=str)
        print(f"  11차 연계표 캐시 로드: {LINKAGE_CSV.name} ({len(df)}행)")
    elif LINKAGE_XLSX.exists():
        print(f"  11차 연계표 Excel 파싱: {LINKAGE_XLSX.name}")
        df = pd.read_excel(LINKAGE_XLSX, sheet_name=0, header=None, skiprows=2)
        df.columns = ["ksic11_code", "ksic11_name", "ksic10_code", "ksic10_name", "change_type"]
        # 문자열 정리
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip().replace("nan", "")
        df.to_csv(LINKAGE_CSV, encoding="utf-8-sig", index=False)
        print(f"    {len(df)}행 추출, 캐시 저장: {LINKAGE_CSV.name}")
    else:
        print("  경고: 11차 연계표 없음 - 6차 매칭 건너뜀")
        return {}, {}

    # 11차 이름 룩업 (5자리 코드만)
    linkage_lookup = {}
    for _, row in df.iterrows():
        code = row["ksic11_code"]
        name = row["ksic11_name"]
        if not code or not name or not re.match(r"^\d{5}$", code):
            continue
        norm = normalize(name)
        if norm and norm not in linkage_lookup:
            linkage_lookup[norm] = (name, code)

    # 역매핑: 11차 코드 → [(10차 코드, 10차 명칭, 변경유형)]
    reverse_map = {}
    for _, row in df.iterrows():
        c11 = row["ksic11_code"]
        c10 = row["ksic10_code"]
        n10 = row["ksic10_name"]
        chg = row["change_type"]
        if not c11 or not re.match(r"^\d{5}$", c11):
            continue
        if c11 not in reverse_map:
            reverse_map[c11] = []
        reverse_map[c11].append((c10, n10, chg))

    print(f"    11차 룩업: {len(linkage_lookup)}개, 역매핑: {len(reverse_map)}개")
    return linkage_lookup, reverse_map


# ---------------------------------------------------------------------------
# 복합 업종명 분해
# ---------------------------------------------------------------------------
def _split_complex_name(raw_name: str) -> str | None:
    """
    복합 업종명에서 첫 번째 키워드 + 접미사를 추출한다.
    예: "가방, 시계, 안경 및 기타 생활용품 도매업" -> "가방 도매업"
    반환: 분해된 이름, 또는 분해 불가 시 None
    """
    # 접미사 추출
    suffix = ""
    for suf in _INDUSTRY_SUFFIXES:
        if raw_name.endswith(suf):
            suffix = suf
            break
    if not suffix:
        return None

    # 접미사 제거 후 본문
    body = raw_name[: -len(suffix)].strip()
    if not body:
        return None

    # 쉼표 또는 " 및 " 기준으로 분할
    # "A, B 및 C" → ["A", "B", "C"] 또는 "A 및 B" → ["A", "B"]
    parts = re.split(r"[,]\s*|\s+및\s+", body)
    if len(parts) < 2:
        return None  # 분할할 게 없으면 복합이 아님

    first = parts[0].strip()
    if not first or len(first) < 2:
        return None

    return first + " " + suffix


# ---------------------------------------------------------------------------
# Step 2: 고유 업종명 추출 (메모리 최적화)
# ---------------------------------------------------------------------------
def extract_unique_industry_names() -> pd.Series:
    """20개 CSV 파일에서 고유 업종명만 추출한다."""
    csv_files = sorted(glob.glob(str(SI_CSV_DIR / "*.csv")))
    print(f"[Step 1] CSV 파일 {len(csv_files)}개 발견")

    all_names = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, encoding="utf-8-sig", usecols=["업종명"], dtype=str)
            all_names.extend(df["업종명"].dropna().tolist())
        except Exception as e:
            print(f"  경고: {os.path.basename(f)} 읽기 실패 - {e}")

    series = pd.Series(all_names)
    unique = series.drop_duplicates().sort_values().reset_index(drop=True)
    print(f"  총 행: {len(all_names):,} → 고유 업종명: {len(unique):,}개")
    return unique


# ---------------------------------------------------------------------------
# Step 3: KSIC 분류표 로드 (4개 계층 + 5자리 매핑)
# ---------------------------------------------------------------------------
def load_ksic_lookups():
    """
    industry_classification.csv에서 4개 계층별 이름→코드 룩업을 구성한다.
    io_ksic_mapping.csv에서 4자리→5자리 코드 매핑을 로드한다.
    """
    ic = pd.read_csv(INDUSTRY_CSV, dtype=str)
    print(f"[Step 2] industry_classification.csv 로드: {len(ic)}행")

    # 4개 계층: (레벨명, 이름컬럼, 코드컬럼)
    levels = [
        ("basic", "basic_name", "basic_code"),
        ("sub", "sub_name", "sub_code"),
        ("mid", "mid_name", "mid_code"),
        ("large", "large_name", "large_code"),
    ]

    # 계층별 정규화된_이름 → (원본_이름, 코드, 레벨) 룩업
    # 더 구체적인 레벨이 우선하도록 basic부터 채우고, 이미 있으면 덮어쓰지 않음
    lookup_by_level = {}  # level -> {normalized_name: (original_name, code)}
    for level_name, name_col, code_col in levels:
        pairs = ic[[name_col, code_col]].drop_duplicates()
        level_dict = {}
        for _, row in pairs.iterrows():
            name_val = row[name_col]
            code_val = row[code_col]
            if pd.isna(name_val) or pd.isna(code_val):
                continue
            norm = normalize(name_val)
            if norm and norm not in level_dict:
                level_dict[norm] = (str(name_val).strip(), str(code_val).strip())
        lookup_by_level[level_name] = level_dict
        print(f"  {level_name}: {len(level_dict)}개 고유 정규화 이름")

    # 5자리 매핑 로드
    io_ksic = pd.read_csv(IO_KSIC_CSV, dtype=str)
    print(f"  io_ksic_mapping.csv 로드: {len(io_ksic)}행")

    # 4자리 IO코드 → [5자리 KSIC코드들] (순서 보존)
    code4_to_code5 = {}
    for _, row in io_ksic.iterrows():
        io_code = str(row["io_code"]).strip()
        ksic_code = str(row["ksic_code"]).strip()
        if io_code not in code4_to_code5:
            code4_to_code5[io_code] = []
        if ksic_code not in code4_to_code5[io_code]:
            code4_to_code5[io_code].append(ksic_code)

    print(f"  4자리→5자리 매핑: {len(code4_to_code5)}개 IO코드")

    # io_name 룩업 (접미사 제거된 정규화 io_name → (원본 io_name, io_code, [ksic_codes]))
    io_name_lookup = {}  # stripped_norm -> (orig_io_name, io_code, [ksic_5digit_codes])
    for io_code, codes_5 in code4_to_code5.items():
        io_rows = io_ksic[io_ksic["io_code"] == io_code]
        if io_rows.empty:
            continue
        io_name = str(io_rows.iloc[0]["io_name"]).strip()
        norm_io = normalize_strip_suffix(io_name)
        if norm_io and norm_io not in io_name_lookup:
            io_name_lookup[norm_io] = (io_name, io_code, codes_5)

    print(f"  io_name 룩업: {len(io_name_lookup)}개 고유 io_name")

    return lookup_by_level, code4_to_code5, io_name_lookup


# ---------------------------------------------------------------------------
# Step 4: 하이브리드 매칭 (Exact + Fuzzy)
# ---------------------------------------------------------------------------
def match_industry_names(
    unique_names, lookup_by_level, code4_to_code5, io_name_lookup, hwp_lookup,
    linkage_lookup=None, linkage_reverse=None,
):
    """고유 업종명에 대해 1~7차 순서로 매칭."""
    if linkage_lookup is None:
        linkage_lookup = {}
    if linkage_reverse is None:
        linkage_reverse = {}
    matched = []
    unmatched = []

    # 모든 레벨의 정규화 이름을 하나로 합침 (basic 우선)
    all_norm_names = {}  # norm -> (original, code, level)
    for level_name in ["large", "mid", "sub", "basic"]:
        for norm, (orig, code) in lookup_by_level[level_name].items():
            all_norm_names[norm] = (orig, code, level_name)

    # aggressive 정규화 버전도 생성 (대상측)
    all_aggressive_names = {}
    for norm, (orig, code, level_name) in all_norm_names.items():
        agg = normalize_aggressive(orig)
        if agg and agg not in all_aggressive_names:
            all_aggressive_names[agg] = (orig, code, level_name)

    norm_keys = list(all_norm_names.keys())
    agg_keys = list(all_aggressive_names.keys())
    io_keys = list(io_name_lookup.keys())
    hwp_keys = list(hwp_lookup.keys())

    # HWP 룩업에 대한 aggressive 버전도 생성
    hwp_aggressive = {}
    for norm, (orig, code) in hwp_lookup.items():
        agg = normalize_aggressive(orig)
        if agg and agg not in hwp_aggressive:
            hwp_aggressive[agg] = (orig, code)
    hwp_agg_keys = list(hwp_aggressive.keys())

    # 11차 연계표 룩업 키 + aggressive 버전
    link_keys = list(linkage_lookup.keys())
    link_aggressive = {}
    for norm, (orig, code) in linkage_lookup.items():
        agg = normalize_aggressive(orig)
        if agg and agg not in link_aggressive:
            link_aggressive[agg] = (orig, code)
    link_agg_keys = list(link_aggressive.keys())

    print(f"\n[Step 3] 매칭 시작 (총 {len(unique_names)}개)")
    print(f"  레퍼런스: industry_classification {len(norm_keys)}개, "
          f"io_name {len(io_keys)}개, HWP 5자리 {len(hwp_keys)}개, "
          f"11차 연계표 {len(link_keys)}개")

    counts = {
        "manual_override": 0,
        "exact": 0, "fuzzy": 0,
        "exact_agg": 0, "fuzzy_agg": 0,
        "io_exact": 0, "io_fuzzy": 0,
        "hwp_exact": 0, "hwp_fuzzy": 0,
        "hwp_exact_agg": 0, "hwp_fuzzy_agg": 0,
        "link11_exact": 0, "link11_fuzzy": 0, "link11_agg": 0,
        "upper_class": 0, "split_first": 0,
        "fail": 0,
    }

    for raw_name in unique_names:
        norm_name = normalize(raw_name)
        if not norm_name:
            unmatched.append(_fail_row(raw_name, norm_name, "", "", 0.0))
            counts["fail"] += 1
            continue

        # --- 0차: 수동 확정 매핑 (MANUAL_OVERRIDE) ---
        if norm_name in MANUAL_OVERRIDE:
            code, name = MANUAL_OVERRIDE[norm_name]
            k5 = code if len(code) == 5 else ""
            k4 = code[:4] if len(code) >= 4 else code
            matched.append(_success_row(
                raw_name, norm_name, k4, name, "manual", "manual_override", 1.0, k5,
            ))
            counts["manual_override"] += 1
            continue

        # --- 1차: Exact Match (industry_classification) ---
        result = _try_exact(norm_name, lookup_by_level, code4_to_code5)
        if result:
            code, orig, level, k5, amb = result
            matched.append(_success_row(raw_name, norm_name, code, orig, level, "exact", 1.0, k5, amb))
            counts["exact"] += 1
            continue

        # --- 2차: Fuzzy Match (industry_classification) ---
        result = _try_fuzzy(norm_name, norm_keys, all_norm_names, code4_to_code5)
        if result:
            code, orig, level, method, score, k5, amb = result
            matched.append(_success_row(raw_name, norm_name, code, orig, level, "fuzzy", score, k5, amb))
            counts["fuzzy"] += 1
            continue

        # --- 3차: Aggressive 정규화 후 Exact/Fuzzy ---
        agg_name = normalize_aggressive(raw_name)
        if agg_name != norm_name:
            if agg_name in all_aggressive_names:
                orig, code, level = all_aggressive_names[agg_name]
                k5, amb = _extend_to_5digit(code, level, code4_to_code5)
                matched.append(_success_row(raw_name, norm_name, code, orig, level, "exact_agg", 1.0, k5, amb))
                counts["exact_agg"] += 1
                continue

            result = _try_fuzzy(agg_name, agg_keys, all_aggressive_names, code4_to_code5)
            if result:
                code, orig, level, method, score, k5, amb = result
                matched.append(_success_row(raw_name, norm_name, code, orig, level, "fuzzy_agg", score, k5, amb))
                counts["fuzzy_agg"] += 1
                continue

        # --- 4차: io_name 직접 매칭 (접미사 제거 후) ---
        stripped = normalize_strip_suffix(raw_name)
        io_result = _try_io_match(stripped, io_keys, io_name_lookup)
        if io_result:
            io_name, io_code, k5, amb, io_method, score = io_result
            tag = f"io_{io_method}"
            matched.append(_success_row(
                raw_name, norm_name, io_code, io_name, "io_name", tag, score, k5, amb,
            ))
            counts[tag] += 1
            continue

        # --- 5차: HWP 5자리 마스터 매칭 ---
        if hwp_keys:
            hwp_result = _try_hwp_match(norm_name, hwp_keys, hwp_lookup)
            if hwp_result:
                orig, k5, method, score = hwp_result
                k4 = k5[:4]
                matched.append(_success_row(
                    raw_name, norm_name, k4, orig, "hwp_5digit", method, score, k5, False,
                ))
                counts[method] += 1
                continue

            # HWP aggressive 매칭 (양방향: 소스+HWP 모두 aggressive 정규화)
            if hwp_agg_keys:
                # agg_name은 소스 aggressive, hwp_aggressive는 HWP측 aggressive
                hwp_result = _try_hwp_match(agg_name, hwp_agg_keys, hwp_aggressive)
                if hwp_result:
                    orig, k5, method, score = hwp_result
                    k4 = k5[:4]
                    tag = method.replace("hwp_", "hwp_") + "_agg"
                    matched.append(_success_row(
                        raw_name, norm_name, k4, orig, "hwp_5digit", tag, score, k5, False,
                    ))
                    counts[tag] += 1
                    continue

                # norm_name으로 hwp_aggressive 검색 (HWP측만 aggressive인 경우)
                if norm_name != agg_name:
                    hwp_result = _try_hwp_match(norm_name, hwp_agg_keys, hwp_aggressive)
                    if hwp_result:
                        orig, k5, method, score = hwp_result
                        k4 = k5[:4]
                        tag = method.replace("hwp_", "hwp_") + "_agg"
                        matched.append(_success_row(
                            raw_name, norm_name, k4, orig, "hwp_5digit", tag, score, k5, False,
                        ))
                        counts[tag] += 1
                        continue

        # --- 6차: KSIC 11차 연계표 매칭 ---
        if link_keys:
            link_result = _try_hwp_match(norm_name, link_keys, linkage_lookup)
            if link_result:
                orig, k11, method, score = link_result
                k10, chg = _resolve_11th_to_10th(k11, linkage_reverse)
                k5 = k11  # 11차 코드를 5자리로 사용
                tag = "link11_exact" if method == "hwp_exact" else "link11_fuzzy"
                matched.append(_success_row(
                    raw_name, norm_name, k5[:4], orig, "linkage_11th",
                    tag, score, k5, False, k11=k11, change_type=chg,
                ))
                counts[tag] += 1
                continue

            # 11차 aggressive 매칭
            if link_agg_keys:
                link_result = _try_hwp_match(agg_name, link_agg_keys, link_aggressive)
                if link_result:
                    orig, k11, method, score = link_result
                    k10, chg = _resolve_11th_to_10th(k11, linkage_reverse)
                    k5 = k11
                    matched.append(_success_row(
                        raw_name, norm_name, k5[:4], orig, "linkage_11th",
                        "link11_agg", score, k5, False, k11=k11, change_type=chg,
                    ))
                    counts["link11_agg"] += 1
                    continue

        # --- 7차-A: 상위분류 매핑 ---
        # mid/large 레벨 이름에서 exact/fuzzy 매칭 후 첫 번째 하위 코드 사용
        for upper_level in ["mid", "large"]:
            upper_dict = lookup_by_level[upper_level]
            upper_keys_list = list(upper_dict.keys())
            if norm_name in upper_dict:
                orig, upper_code = upper_dict[norm_name]
                # 해당 상위코드에 속하는 basic 코드 중 첫 번째
                first_basic = _find_first_basic(upper_code, lookup_by_level, code4_to_code5)
                if first_basic:
                    k4, k5 = first_basic
                    matched.append(_success_row(
                        raw_name, norm_name, k4, orig, upper_level,
                        "upper_class", 1.0, k5, True,
                    ))
                    counts["upper_class"] += 1
                    break
            else:
                cands = difflib.get_close_matches(
                    norm_name, upper_keys_list, n=1, cutoff=FUZZY_THRESHOLD,
                )
                if cands:
                    best = cands[0]
                    sc = difflib.SequenceMatcher(None, norm_name, best).ratio()
                    if sc >= FUZZY_THRESHOLD:
                        orig, upper_code = upper_dict[best]
                        first_basic = _find_first_basic(
                            upper_code, lookup_by_level, code4_to_code5,
                        )
                        if first_basic:
                            k4, k5 = first_basic
                            matched.append(_success_row(
                                raw_name, norm_name, k4, orig, upper_level,
                                "upper_class", round(sc, 4), k5, True,
                            ))
                            counts["upper_class"] += 1
                            break
        else:
            # 7차-B: 복합 업종명 분해 매칭
            split_name = _split_complex_name(raw_name)
            if split_name:
                split_norm = normalize(split_name)
                # 분해 이름으로 1~6차 전체 레퍼런스 검색 (1회만)
                split_result = _try_split_match(
                    split_norm, all_norm_names, norm_keys, code4_to_code5,
                    hwp_lookup, hwp_keys, linkage_lookup, link_keys,
                    linkage_reverse,
                )
                if split_result:
                    code, orig, level, k5, amb, sc, k11, chg = split_result
                    matched.append(_success_row(
                        raw_name, norm_name, code, orig, level,
                        "split_first", sc, k5, amb, k11=k11, change_type=chg,
                    ))
                    counts["split_first"] += 1
                    continue

            # --- 최종 실패: 최근접 후보 기록 (HWP + 11차 포함) ---
            all_candidate_keys = norm_keys + hwp_keys + link_keys
            all_candidate_lookup = {
                **{k: (v[0], v[1]) for k, v in all_norm_names.items()},
                **hwp_lookup,
                **linkage_lookup,
            }
            candidates = difflib.get_close_matches(
                norm_name, all_candidate_keys, n=1, cutoff=0.0,
            )
            if candidates:
                best = candidates[0]
                score = difflib.SequenceMatcher(None, norm_name, best).ratio()
                orig, code = (
                    all_candidate_lookup[best]
                    if best in all_candidate_lookup
                    else ("", "")
                )
                unmatched.append(
                    _fail_row(raw_name, norm_name, orig, code, round(score, 4))
                )
            else:
                unmatched.append(_fail_row(raw_name, norm_name, "", "", 0.0))
            counts["fail"] += 1
            continue  # 다음 업종명으로

    print(f"  0차 수동 확정 (MANUAL_OVERRIDE): {counts['manual_override']}개")
    print(f"  1차 Exact (industry_classification): {counts['exact']}개")
    print(f"  2차 Fuzzy (industry_classification, >={FUZZY_THRESHOLD}): {counts['fuzzy']}개")
    print(f"  3차 Aggressive Exact: {counts['exact_agg']}개")
    print(f"  3차 Aggressive Fuzzy: {counts['fuzzy_agg']}개")
    print(f"  4차 io_name Exact: {counts['io_exact']}개")
    print(f"  4차 io_name Fuzzy: {counts['io_fuzzy']}개")
    print(f"  5차 HWP Exact: {counts['hwp_exact']}개")
    print(f"  5차 HWP Fuzzy: {counts['hwp_fuzzy']}개")
    print(f"  5차 HWP Aggressive: {counts.get('hwp_exact_agg', 0) + counts.get('hwp_fuzzy_agg', 0)}개")
    print(f"  6차 11차 연계표 Exact: {counts['link11_exact']}개")
    print(f"  6차 11차 연계표 Fuzzy: {counts['link11_fuzzy']}개")
    print(f"  6차 11차 연계표 Aggressive: {counts['link11_agg']}개")
    print(f"  7차 상위분류: {counts['upper_class']}개")
    print(f"  7차 복합분해: {counts['split_first']}개")
    print(f"  미매칭 (수동 리뷰 필요): {counts['fail']}개")
    total = sum(counts.values())
    print(f"  합계: {total}개")

    return matched, unmatched


def _try_exact(norm_name, lookup_by_level, code4_to_code5):
    """계층별 exact match. 성공 시 (code, orig, level, k5, amb) 반환."""
    for level_name in ["basic", "sub", "mid", "large"]:
        level_dict = lookup_by_level[level_name]
        if norm_name in level_dict:
            orig, code = level_dict[norm_name]
            k5, amb = _extend_to_5digit(code, level_name, code4_to_code5)
            return code, orig, level_name, k5, amb
    return None


def _try_fuzzy(query, keys, lookup, code4_to_code5):
    """fuzzy match. 성공 시 (code, orig, level, method, score, k5, amb) 반환."""
    candidates = difflib.get_close_matches(query, keys, n=1, cutoff=FUZZY_THRESHOLD)
    if not candidates:
        return None
    best = candidates[0]
    score = difflib.SequenceMatcher(None, query, best).ratio()
    if score < FUZZY_THRESHOLD:
        return None
    orig, code, level = lookup[best]
    k5, amb = _extend_to_5digit(code, level, code4_to_code5)
    return code, orig, level, "fuzzy", round(score, 4), k5, amb


def _success_row(raw, norm, code, orig, level, method, score, k5="", amb=False,
                  k11="", change_type=""):
    row = {
        "원본_업종명": raw,
        "정규화_업종명": norm,
        "KSIC_코드_4자리": code,
        "KSIC_명칭": orig,
        "매칭_레벨": level,
        "매칭_방식": method,
        "매칭_스코어": score,
        "KSIC_코드_5자리": k5,
        "5자리_모호성": amb,
        "KSIC_코드_11차": k11,
        "변경유형": change_type,
    }
    return row


def _fail_row(raw, norm, candidate, code, score):
    return {
        "원본_업종명": raw,
        "정규화_업종명": norm,
        "최근접_후보": candidate,
        "최근접_코드": code,
        "유사도_스코어": score,
        "비고": "",
    }


def _try_hwp_match(query, keys, lookup):
    """HWP 5자리 매칭. 성공 시 (orig_name, ksic_5, method, score)."""
    # exact
    if query in lookup:
        orig, code = lookup[query]
        return orig, code, "hwp_exact", 1.0
    # fuzzy (HWP 전용 낮은 threshold - 공식 분류표이므로 신뢰도 높음)
    candidates = difflib.get_close_matches(query, keys, n=1, cutoff=HWP_FUZZY_THRESHOLD)
    if candidates:
        best = candidates[0]
        score = difflib.SequenceMatcher(None, query, best).ratio()
        if score >= HWP_FUZZY_THRESHOLD:
            orig, code = lookup[best]
            return orig, code, "hwp_fuzzy", round(score, 4)
    return None


def _resolve_11th_to_10th(k11_code, linkage_reverse):
    """11차 코드에서 연계표를 통해 10차 코드와 변경유형을 찾는다."""
    entries = linkage_reverse.get(k11_code, [])
    if not entries:
        return "", ""
    # 첫 번째 10차 매핑 사용
    k10, _n10, chg = entries[0]
    return k10, chg


def _find_first_basic(upper_code, lookup_by_level, code4_to_code5):
    """상위분류 코드에 속하는 첫 번째 basic(4자리) 코드를 찾는다."""
    basic_dict = lookup_by_level.get("basic", {})
    # basic 코드 중 상위 코드로 시작하는 것 찾기
    for _norm, (orig, code) in basic_dict.items():
        if code.startswith(upper_code):
            k5_list = code4_to_code5.get(code, [])
            k5 = k5_list[0] if k5_list else ""
            return code, k5
    return None


def _try_split_match(split_norm, all_norm_names, norm_keys, code4_to_code5,
                     hwp_lookup, hwp_keys, linkage_lookup, link_keys,
                     linkage_reverse):
    """분해된 업종명으로 전체 레퍼런스를 검색한다."""
    # 1. industry_classification exact/fuzzy
    if split_norm in all_norm_names:
        orig, code, level = all_norm_names[split_norm]
        k5, amb = _extend_to_5digit(code, level, code4_to_code5)
        return code, orig, level, k5, amb, 1.0, "", ""

    cands = difflib.get_close_matches(split_norm, norm_keys, n=1, cutoff=FUZZY_THRESHOLD)
    if cands:
        best = cands[0]
        sc = difflib.SequenceMatcher(None, split_norm, best).ratio()
        if sc >= FUZZY_THRESHOLD:
            orig, code, level = all_norm_names[best]
            k5, amb = _extend_to_5digit(code, level, code4_to_code5)
            return code, orig, level, k5, amb, round(sc, 4), "", ""

    # 2. HWP exact/fuzzy
    if hwp_keys:
        hwp_r = _try_hwp_match(split_norm, hwp_keys, hwp_lookup)
        if hwp_r:
            orig, k5, _method, sc = hwp_r
            return k5[:4], orig, "hwp_5digit", k5, False, sc, "", ""

    # 3. 11차 연계표 exact/fuzzy
    if link_keys:
        link_r = _try_hwp_match(split_norm, link_keys, linkage_lookup)
        if link_r:
            orig, k11, _method, sc = link_r
            k10, chg = _resolve_11th_to_10th(k11, linkage_reverse)
            return k11[:4], orig, "linkage_11th", k11, False, sc, k11, chg

    return None


def _try_io_match(stripped_name, io_keys, io_name_lookup):
    """io_name 매칭. 성공 시 (io_name, io_code, ksic_5, ambiguous, method, score)."""
    if not stripped_name:
        return None
    # exact
    if stripped_name in io_name_lookup:
        io_name, io_code, codes_5 = io_name_lookup[stripped_name]
        k5 = codes_5[0] if codes_5 else ""
        amb = len(codes_5) > 1
        return io_name, io_code, k5, amb, "exact", 1.0
    # fuzzy
    candidates = difflib.get_close_matches(stripped_name, io_keys, n=1, cutoff=FUZZY_THRESHOLD)
    if candidates:
        best = candidates[0]
        score = difflib.SequenceMatcher(None, stripped_name, best).ratio()
        if score >= FUZZY_THRESHOLD:
            io_name, io_code, codes_5 = io_name_lookup[best]
            k5 = codes_5[0] if codes_5 else ""
            amb = len(codes_5) > 1
            return io_name, io_code, k5, amb, "fuzzy", round(score, 4)
    return None


def _extend_to_5digit(code_4, level_name, code4_to_code5):
    """4자리 코드를 io_ksic_mapping으로 5자리로 확장 시도한다."""
    # basic 레벨(4자리)만 io_ksic_mapping의 io_code와 직접 매핑 가능
    if level_name != "basic":
        return "", False

    codes_5 = code4_to_code5.get(code_4, [])
    if not codes_5:
        return "", False
    if len(codes_5) == 1:
        return codes_5[0], False
    # 1:N → 첫 번째 사용, 모호성 플래그
    return codes_5[0], True


# ---------------------------------------------------------------------------
# Step 5: 결과물 저장
# ---------------------------------------------------------------------------
def save_results(matched, unmatched):
    """매칭 성공/실패 결과를 CSV로 분리 저장한다."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    matched_path = OUTPUT_DIR / "industry_master_dict.csv"
    review_path = OUTPUT_DIR / "manual_review_required.csv"

    df_matched = pd.DataFrame(matched)
    df_unmatched = pd.DataFrame(unmatched)

    df_matched.to_csv(matched_path, encoding="utf-8-sig", index=False)
    df_unmatched.to_csv(review_path, encoding="utf-8-sig", index=False)

    print(f"\n[Step 4] 결과 저장 완료")
    print(f"  성공: {matched_path} ({len(df_matched)}행)")
    print(f"  실패: {review_path} ({len(df_unmatched)}행)")

    # 매칭 통계
    if len(df_matched) > 0:
        print("\n=== 매칭 통계 ===")
        print(f"  매칭 방식별:")
        for method in [
            "manual_override",
            "exact", "fuzzy", "exact_agg", "fuzzy_agg",
            "io_exact", "io_fuzzy",
            "hwp_exact", "hwp_fuzzy", "hwp_exact_agg", "hwp_fuzzy_agg",
            "link11_exact", "link11_fuzzy", "link11_agg",
            "upper_class", "split_first",
        ]:
            cnt = (df_matched["매칭_방식"] == method).sum()
            if cnt > 0:
                print(f"    {method}: {cnt}")
        print(f"  매칭 레벨별:")
        for level in ["manual", "basic", "sub", "mid", "large", "io_name",
                      "hwp_5digit", "linkage_11th"]:
            cnt = (df_matched["매칭_레벨"] == level).sum()
            if cnt > 0:
                print(f"    {level}: {cnt}")
        # 5자리 통계
        has_5 = (df_matched["KSIC_코드_5자리"] != "").sum()
        ambiguous = (df_matched["5자리_모호성"] == True).sum()  # noqa: E712
        print(f"  5자리 코드 확장 성공: {has_5}건 (모호성 있음: {ambiguous}건)")

    total = len(df_matched) + len(df_unmatched)
    rate = len(df_matched) / total * 100 if total > 0 else 0
    print(f"\n  전체 매핑률: {rate:.1f}% ({len(df_matched)}/{total})")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  업종명 마스터 매핑 사전 구축 (v5.1 - 수동 확정 45건 통합)")
    print("=" * 60)

    unique_names = extract_unique_industry_names()
    lookup_by_level, code4_to_code5, io_name_lookup = load_ksic_lookups()
    hwp_lookup = load_or_extract_hwp_5digit()
    linkage_lookup, linkage_reverse = load_or_extract_linkage_11th()
    matched, unmatched = match_industry_names(
        unique_names, lookup_by_level, code4_to_code5, io_name_lookup, hwp_lookup,
        linkage_lookup, linkage_reverse,
    )
    save_results(matched, unmatched)

    print("\n완료.")


if __name__ == "__main__":
    main()
