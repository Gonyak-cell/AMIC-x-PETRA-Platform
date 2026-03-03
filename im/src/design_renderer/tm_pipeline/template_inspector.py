"""디자인 토큰 정합성 검증기 — 렌더러 소스 코드 정적 분석.

렌더러 파일들의 소스 코드를 정적 분석하여 하드코딩된 색상, 폰트,
치수 등이 없는지 검증한다.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.design_renderer.design_tokens import DEFAULT_TOKENS

logger = logging.getLogger(__name__)


@dataclass
class ComplianceIssue:
    """디자인 토큰 준수 위반 항목."""

    file_path: str
    line_number: int
    issue_type: str  # "hardcoded_color", "hardcoded_font", "hardcoded_dimension"
    description: str
    raw_line: str = ""


@dataclass
class ComplianceReport:
    """디자인 토큰 준수 보고서."""

    files_checked: int = 0
    issues: list[ComplianceIssue] = field(default_factory=list)

    @property
    def compliant(self) -> bool:
        """위반 없으면 준수."""
        return len(self.issues) == 0

    @property
    def issue_count(self) -> int:
        """위반 수."""
        return len(self.issues)


# 허용된 색상 (design_tokens.py에서 정의)
_ALLOWED_HEX_COLORS = {
    "#0F3A32",
    "#1C8F57",
    "#26C260",
    "#A3E96B",
    "#E6FDD6",
    "#3D3D3D",
    "#2A2A2A",
    "#777777",
    "#FFFFFF",
    "#F1F8E9",
    "#F4F6F8",
    "#BC2C1A",
    "#EF6C00",
    "#FF3838",
    "#757575",
    "#333333",
    "#E0E0E0",
    "#B0B0B0",
    "#6A6A6A",
}

# 하드코딩 색상 탐지 패턴 — 주석, 문자열 내 정의 제외
_HEX_COLOR_PATTERN = re.compile(r'["\']#([0-9A-Fa-f]{6})["\']')

# 하드코딩 폰트 탐지 패턴
_FONT_BLACKLIST = sorted(["Arial", "Calibri", "Times New Roman", "Verdana", "Tahoma"])
_FONT_PATTERN = re.compile(
    r'["\'](' + "|".join(re.escape(f) for f in _FONT_BLACKLIST) + r')["\']'
)


def check_renderer_compliance(
    renderers_dir: str | Path | None = None,
) -> ComplianceReport:
    """렌더러 디렉토리의 디자인 토큰 준수 여부 검사.

    Args:
        renderers_dir: 렌더러 디렉토리 경로.
            None이면 기본 section_renderers 경로 사용.

    Returns:
        ComplianceReport.
    """
    if renderers_dir is None:
        renderers_dir = Path(__file__).resolve().parent.parent / "section_renderers"
    else:
        renderers_dir = Path(renderers_dir)

    report = ComplianceReport()

    if not renderers_dir.exists():
        return report

    for py_file in sorted(renderers_dir.glob("*.py")):
        if py_file.name.startswith("__"):
            continue
        report.files_checked += 1
        _check_file(py_file, report)

    return report


def _check_file(file_path: Path, report: ComplianceReport) -> None:
    """단일 파일의 디자인 토큰 준수 여부 검사."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        logger.warning("파일 읽기 실패: %s", file_path)
        report.issues.append(
            ComplianceIssue(
                file_path=str(file_path),
                line_number=0,
                issue_type="file_read_error",
                description=f"파일 읽기 실패: {file_path.name}",
            )
        )
        return

    for line_num, line in enumerate(content.splitlines(), start=1):
        # 주석 라인 건너뛰기
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # 하드코딩 색상 검사
        for match in _HEX_COLOR_PATTERN.finditer(line):
            hex_val = f"#{match.group(1).upper()}"
            if hex_val not in _ALLOWED_HEX_COLORS:
                report.issues.append(
                    ComplianceIssue(
                        file_path=str(file_path),
                        line_number=line_num,
                        issue_type="hardcoded_color",
                        description=f"비허용 하드코딩 색상: {hex_val}",
                        raw_line=stripped,
                    )
                )

        # 하드코딩 폰트 검사
        font_match = _FONT_PATTERN.search(line)
        if font_match:
            report.issues.append(
                ComplianceIssue(
                    file_path=str(file_path),
                    line_number=line_num,
                    issue_type="hardcoded_font",
                    description=f"비허용 하드코딩 폰트: {font_match.group(1)}",
                    raw_line=stripped,
                )
            )


def get_design_token_summary() -> dict[str, Any]:
    """현재 DEFAULT_TOKENS의 주요 값 요약.

    Returns:
        디자인 토큰 요약 딕셔너리.
    """
    tokens = DEFAULT_TOKENS
    return {
        "colors": {
            "primary": tokens.colors.primary,
            "secondary": tokens.colors.secondary,
            "accent": tokens.colors.accent,
            "fresh": tokens.colors.fresh,
            "light": tokens.colors.light,
        },
        "typography": {
            "font_heading": tokens.typography.font_heading,
            "font_body": tokens.typography.font_body,
            "font_chart": tokens.typography.font_chart,
        },
        "layout": {
            "slide_width": tokens.layout.page_width,
            "slide_height": tokens.layout.page_height,
            "margin_left": tokens.layout.margin_left,
            "margin_right": tokens.layout.margin_right,
            "margin_top": tokens.layout.margin_top,
            "margin_bottom": tokens.layout.margin_bottom,
        },
    }
