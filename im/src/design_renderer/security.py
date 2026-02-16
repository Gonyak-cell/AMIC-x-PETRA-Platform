"""보안 옵션 — PPTX/PDF 공통 보안 설정.

워터마크, 암호화, 편집/인쇄/복사 제한 등을
단일 SecurityOptions 데이터클래스로 관리한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WatermarkPosition(str, Enum):
    """워터마크 배치 위치."""

    CENTER_DIAGONAL = "center_diagonal"  # 중앙 45도 회전
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"


@dataclass
class SecurityOptions:
    """문서 보안 설정 (PPTX + PDF 공통).

    Args:
        pdf_password: PDF 열기 비밀번호. None이면 암호화 안 함.
        pdf_owner_password: PDF 소유자 비밀번호 (권한 제어).
            None이면 pdf_password와 동일하게 설정.
        pdf_restrict_print: True이면 인쇄 제한.
        pdf_restrict_copy: True이면 텍스트/이미지 복사 제한.
        pdf_restrict_modify: True이면 수정 제한.
        watermark_text: 워터마크 텍스트. None이면 워터마크 없음.
        watermark_opacity: 워터마크 불투명도 (0.0~1.0).
        watermark_position: 워터마크 배치 스타일.
        watermark_color: 워터마크 색상 (hex).
        watermark_font_size: 워터마크 폰트 크기 (pt).
        pptx_read_only: PPTX 읽기 전용 권장 모드 활성화.
        pptx_edit_password: PPTX 편집 제한 비밀번호.
            None이면 기본 읽기 전용 플래그만 설정.
    """

    # PDF 보안
    pdf_password: str | None = None
    pdf_owner_password: str | None = None
    pdf_restrict_print: bool = True
    pdf_restrict_copy: bool = True
    pdf_restrict_modify: bool = True

    # 워터마크 (PPTX/PDF 공용)
    watermark_text: str | None = "CONFIDENTIAL"
    watermark_opacity: float = 0.2
    watermark_position: WatermarkPosition = WatermarkPosition.CENTER_DIAGONAL
    watermark_color: str = "#CCCCCC"
    watermark_font_size: int = 60

    # PPTX 보안
    pptx_read_only: bool = True
    pptx_edit_password: str | None = None

    def __post_init__(self) -> None:
        """소유자 비밀번호 기본값 + 불투명도 범위 검증."""
        if self.pdf_owner_password is None:
            self.pdf_owner_password = self.pdf_password
        if not 0.0 <= self.watermark_opacity <= 1.0:
            raise ValueError(
                f"watermark_opacity는 0.0~1.0이어야 합니다. "
                f"입력값: {self.watermark_opacity}"
            )
