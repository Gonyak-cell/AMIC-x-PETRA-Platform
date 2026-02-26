"""실사자료 파일 분류기 — 파일명+내용 기반 DDRL 섹션 자동 매핑."""

from __future__ import annotations

import logging
from pathlib import Path

from app.ralph.korean_finance_dict import DDRL_FILE_KEYWORDS
from app.ralph.parsers.base import ParsedFile

logger = logging.getLogger(__name__)

# 파일명에서 섹션을 추론할 수 있는 폴더명 패턴
_FOLDER_SECTION_MAP: dict[str, str] = {
    "정관": "GOVERNANCE",
    "등기": "GOVERNANCE",
    "법인": "GOVERNANCE",
    "임원": "GOVERNANCE",
    "주주": "CAPITAL",
    "주식": "CAPITAL",
    "계약": "CONTRACTS",
    "거래처": "CONTRACTS",
    "소송": "LITIGATION",
    "분쟁": "LITIGATION",
    "행정처분": "LITIGATION",
    "인사": "LABOR",
    "노무": "LABOR",
    "급여": "LABOR",
    "퇴직": "LABOR",
    "특허": "IP",
    "지식재산": "IP",
    "부동산": "REAL_ESTATE",
    "토지": "REAL_ESTATE",
    "건물": "REAL_ESTATE",
    "환경": "REAL_ESTATE",
    "허가": "PERMITS",
    "인허가": "PERMITS",
    "폐기물": "PERMITS",
    "세무": "TAX",
    "세금": "TAX",
    "법인세": "TAX",
    "개인정보": "DATA_IT",
    "정보보호": "DATA_IT",
    "IT": "DATA_IT",
}

# DDRL 접두어(L1, L2, ...) → 섹션 매핑
_PREFIX_TO_SECTION: dict[str, str] = {}
for _section, _info in DDRL_FILE_KEYWORDS.items():
    for _prefix in _info.get("ddrl_prefixes", []):
        _PREFIX_TO_SECTION[_prefix] = _section

# 지원 확장자
SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".pdf", ".docx", ".hwp", ".hwpx"}


def classify_file(file_path: str, parsed: ParsedFile | None = None) -> list[str]:
    """파일 경로와 파싱 결과를 기반으로 DDRL 섹션을 추론한다.

    Returns:
        매핑된 섹션 이름 리스트 (예: ["GOVERNANCE", "CAPITAL"])
    """
    sections: set[str] = set()
    path = Path(file_path)
    full_path_str = str(path).lower()

    # 1단계: 폴더/파일명에서 DDRL 접두어 탐색 (L1, L2, ...)
    for prefix, section in _PREFIX_TO_SECTION.items():
        if prefix.lower() in full_path_str:
            sections.add(section)

    # 2단계: 폴더명 패턴 매칭
    for part in path.parts:
        part_lower = part.lower()
        for keyword, section in _FOLDER_SECTION_MAP.items():
            if keyword in part_lower:
                sections.add(section)

    # 3단계: 파일명 키워드 매칭
    filename = path.stem.lower()
    for section, info in DDRL_FILE_KEYWORDS.items():
        for kw in info["keywords"]:
            if kw.lower() in filename:
                sections.add(section)
                break

    # 4단계: 파싱된 텍스트 내용에서 키워드 매칭 (상위 500자만)
    if parsed and parsed.text:
        text_sample = parsed.text[:500].lower()
        for section, info in DDRL_FILE_KEYWORDS.items():
            match_count = sum(1 for kw in info["keywords"] if kw.lower() in text_sample)
            if match_count >= 2:  # 2개 이상 키워드 매칭 시
                sections.add(section)

    return sorted(sections)


def scan_directory(root_dir: str) -> list[dict]:
    """디렉토리를 스캔하여 지원 파일 목록과 예비 분류를 반환한다.

    Returns:
        [{"path": str, "ext": str, "size_kb": int, "sections": list[str]}, ...]
    """
    results: list[dict] = []
    root = Path(root_dir)

    if not root.exists():
        logger.warning("디렉토리가 존재하지 않습니다: %s", root_dir)
        return results

    for entry in root.rglob("*"):
        if not entry.is_file():
            continue
        ext = entry.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        # 파일명 기반 예비 분류 (파싱 없이)
        sections = classify_file(str(entry))
        size_kb = entry.stat().st_size // 1024

        results.append(
            {
                "path": str(entry),
                "ext": ext,
                "size_kb": size_kb,
                "sections": sections,
            }
        )

    logger.info("스캔 완료: %d개 파일 발견 (%s)", len(results), root_dir)
    return results


def parse_and_classify(file_path: str) -> ParsedFile:
    """파일을 파싱하고 DDRL 섹션을 자동 매핑한다."""
    from app.ralph.parsers import parse_file

    parsed = parse_file(file_path)
    parsed.ddrl_sections = classify_file(file_path, parsed)
    return parsed
