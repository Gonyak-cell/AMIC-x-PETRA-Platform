"""시각 비교 테스트 Fixture (IM 모듈).

> 마지막 수정: 2026-03-13 22:38:00

CI 전용 — LibreOffice headless + scikit-image + pdf2image 필요.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest


def _has_libreoffice() -> bool:
    """LibreOffice headless 실행 가능 여부."""
    return shutil.which("libreoffice") is not None


def _has_scikit_image() -> bool:
    """scikit-image 설치 여부."""
    try:
        from skimage.metrics import structural_similarity  # noqa: F401

        return True
    except ImportError:
        return False


HAS_LIBREOFFICE = _has_libreoffice()
HAS_SKIMAGE = _has_scikit_image()
VISUAL_DIFF_READY = HAS_LIBREOFFICE and HAS_SKIMAGE
FORCE_VISUAL_DIFF = os.getenv("FORCE_VISUAL_DIFF", "").lower() in ("1", "true")

skip_no_visual = pytest.mark.skipif(
    not (VISUAL_DIFF_READY or FORCE_VISUAL_DIFF),
    reason="LibreOffice 또는 scikit-image 미설치 — 시각 비교 불가 (FORCE_VISUAL_DIFF=1 로 강제 가능)",
)

GOLDEN_SAMPLES_DIR = Path(__file__).parent.parent / "fixtures" / "golden_samples"


@pytest.fixture
def golden_samples_dir() -> Path:
    """골든 샘플 fixture 디렉토리 경로."""
    return GOLDEN_SAMPLES_DIR


@pytest.fixture
def visual_diff_output(tmp_path: Path) -> Path:
    """시각 비교 결과 출력 디렉토리."""
    diff_dir = tmp_path / "visual_diff"
    diff_dir.mkdir(parents=True, exist_ok=True)
    return diff_dir
