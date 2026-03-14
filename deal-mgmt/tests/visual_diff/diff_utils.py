"""시각 비교 유틸리티 — PPTX→PNG 변환 + SSIM 계산 + diff heatmap 생성.

> 마지막 수정: 2026-03-13 22:45:00

CI 전용 — LibreOffice headless + scikit-image 필요.
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ── LibreOffice 경로 탐색 ─────────────────────────────────────────

_WINDOWS_LO_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


def _find_libreoffice() -> str:
    """플랫폼에 맞는 LibreOffice 실행 파일 경로를 반환한다."""
    # Linux/macOS: PATH에 libreoffice가 있음
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        return lo
    # Windows: 기본 설치 경로 탐색
    if platform.system() == "Windows":
        for p in _WINDOWS_LO_PATHS:
            if p.exists():
                return str(p)
    raise FileNotFoundError(
        "LibreOffice를 찾을 수 없습니다.\n"
        "  Ubuntu: sudo apt-get install -y libreoffice-impress\n"
        "  macOS:  brew install --cask libreoffice\n"
        "  Windows: https://www.libreoffice.org/download/"
    )


# ── SSIM 임계값 (PLAN.md 명시) ──────────────────────────────────

SSIM_THRESHOLD = 0.985
CHANGED_PIXEL_RATIO_THRESHOLD = 0.008  # 0.8%
STATIC_DRIFT_PX = 2  # 로고/헤더 위치 drift 허용


@dataclass
class SlideComparisonResult:
    """슬라이드별 시각 비교 결과."""

    slide_index: int
    ssim_score: float
    changed_pixel_ratio: float
    passed: bool
    diff_heatmap_path: str | None = None


@dataclass
class VisualDiffReport:
    """전체 시각 비교 보고서."""

    total_slides: int
    passed_slides: int
    failed_slides: int
    min_ssim: float
    max_changed_ratio: float
    slide_results: list[SlideComparisonResult]
    overall_passed: bool


def pptx_to_pngs(pptx_path: str, output_dir: str, dpi: int = 150) -> list[str]:
    """PPTX → PNG 변환 (LibreOffice headless).

    Args:
        pptx_path: PPTX 파일 경로.
        output_dir: PNG 출력 디렉토리.
        dpi: 출력 해상도.

    Returns:
        생성된 PNG 파일 경로 목록 (슬라이드 순서).

    Raises:
        RuntimeError: LibreOffice 실행 실패.
        FileNotFoundError: LibreOffice 미설치.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # LibreOffice headless로 PDF 변환 후 PNG 추출
    lo_bin = _find_libreoffice()
    try:
        result = subprocess.run(
            [
                lo_bin,
                "--headless",
                "--convert-to",
                "png",
                "--outdir",
                str(output_path),
                pptx_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError("LibreOffice 미설치. CI Docker에 libreoffice-impress 필요.") from exc

    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice 변환 실패: {result.stderr[:500]}")

    # LibreOffice는 단일 PNG만 생성 → PDF 거쳐서 페이지별 PNG 추출
    # 대안: python-pptx + Pillow로 각 슬라이드 렌더링
    # CI 환경에서는 LibreOffice가 슬라이드별 PNG를 지원하지 않으므로
    # PDF 중간 변환 사용
    pdf_path = output_path / Path(pptx_path).with_suffix(".pdf").name
    if not pdf_path.exists():
        # PPTX → PDF 변환
        subprocess.run(
            [
                lo_bin,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_path),
                pptx_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        )

    # PDF → 슬라이드별 PNG (pdf2image → PyMuPDF fallback)
    png_paths: list[str] = []

    # 1차: pdf2image (poppler 기반)
    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(pdf_path), dpi=dpi)
        for idx, img in enumerate(images):
            png_file = output_path / f"slide_{idx:02d}.png"
            img.save(str(png_file), "PNG")
            png_paths.append(str(png_file))
        return png_paths
    except (ImportError, Exception) as exc:
        logger.info("pdf2image 변환 실패 (%s) — PyMuPDF fallback 시도.", exc)

    # 2차: PyMuPDF (fitz) — poppler 불필요
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for idx, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            png_file = output_path / f"slide_{idx:02d}.png"
            pix.save(str(png_file))
            png_paths.append(str(png_file))
        doc.close()
        return png_paths
    except ImportError:
        logger.warning("pdf2image/PyMuPDF 모두 미설치 — PNG 변환 불가.")
        return []


def compute_ssim(
    image_a_path: str,
    image_b_path: str,
) -> tuple[float, float]:
    """두 이미지의 SSIM과 변경 픽셀 비율을 계산한다.

    Args:
        image_a_path: 기준 이미지 경로 (승인본).
        image_b_path: 비교 이미지 경로 (생성본).

    Returns:
        (ssim_score, changed_pixel_ratio) 튜플.
    """
    try:
        import numpy as np
        from PIL import Image
        from skimage.metrics import structural_similarity
    except ImportError as exc:
        raise ImportError("scikit-image + Pillow 필요: pip install scikit-image Pillow") from exc

    img_a = np.array(Image.open(image_a_path).convert("RGB"))
    img_b = np.array(Image.open(image_b_path).convert("RGB"))

    # 크기 불일치 시 리사이즈
    if img_a.shape != img_b.shape:
        target_h = min(img_a.shape[0], img_b.shape[0])
        target_w = min(img_a.shape[1], img_b.shape[1])
        img_a = np.array(Image.fromarray(img_a).resize((target_w, target_h), Image.LANCZOS))
        img_b = np.array(Image.fromarray(img_b).resize((target_w, target_h), Image.LANCZOS))

    # SSIM 계산 (채널별 → 평균)
    ssim_score = structural_similarity(img_a, img_b, channel_axis=2, data_range=255)

    # 변경 픽셀 비율 계산
    diff = np.abs(img_a.astype(float) - img_b.astype(float))
    changed_pixels = np.any(diff > 10, axis=2)  # 채널 중 하나라도 10 이상 차이
    changed_ratio = float(changed_pixels.sum()) / changed_pixels.size

    return float(ssim_score), changed_ratio


def generate_diff_heatmap(
    image_a_path: str,
    image_b_path: str,
    output_path: str,
) -> str:
    """두 이미지의 차이 히트맵을 생성한다.

    Args:
        image_a_path: 기준 이미지.
        image_b_path: 비교 이미지.
        output_path: 히트맵 저장 경로.

    Returns:
        저장된 히트맵 파일 경로.
    """
    import numpy as np
    from PIL import Image

    img_a = np.array(Image.open(image_a_path).convert("RGB"))
    img_b = np.array(Image.open(image_b_path).convert("RGB"))

    if img_a.shape != img_b.shape:
        target_h = min(img_a.shape[0], img_b.shape[0])
        target_w = min(img_a.shape[1], img_b.shape[1])
        img_a = np.array(Image.fromarray(img_a).resize((target_w, target_h), Image.LANCZOS))
        img_b = np.array(Image.fromarray(img_b).resize((target_w, target_h), Image.LANCZOS))

    # 절대 차이 → 히트맵
    diff = np.abs(img_a.astype(float) - img_b.astype(float))
    # 채널 평균 → 정규화
    diff_gray = diff.mean(axis=2)
    # 차이를 강조하기 위해 스케일링
    diff_normalized = np.clip(diff_gray * 5, 0, 255).astype(np.uint8)

    # 빨간색 히트맵 생성
    heatmap = np.zeros((*diff_normalized.shape, 3), dtype=np.uint8)
    heatmap[:, :, 0] = diff_normalized  # Red 채널

    heatmap_img = Image.fromarray(heatmap)
    heatmap_img.save(output_path)
    return output_path


def compare_slide_pngs(
    approved_dir: str,
    generated_dir: str,
    diff_output_dir: str | None = None,
) -> VisualDiffReport:
    """승인 PNG와 생성 PNG를 슬라이드별로 비교한다.

    Args:
        approved_dir: 승인된 슬라이드 PNG 디렉토리.
        generated_dir: 생성된 슬라이드 PNG 디렉토리.
        diff_output_dir: diff 히트맵 출력 디렉토리 (None이면 생략).

    Returns:
        VisualDiffReport: 전체 비교 보고서.
    """
    approved_path = Path(approved_dir)
    generated_path = Path(generated_dir)

    approved_pngs = sorted(approved_path.glob("slide_*.png"))
    generated_pngs = sorted(generated_path.glob("slide_*.png"))

    if not approved_pngs:
        return VisualDiffReport(
            total_slides=0,
            passed_slides=0,
            failed_slides=0,
            min_ssim=0.0,
            max_changed_ratio=0.0,
            slide_results=[],
            overall_passed=False,
        )

    if diff_output_dir:
        Path(diff_output_dir).mkdir(parents=True, exist_ok=True)

    slide_results: list[SlideComparisonResult] = []
    min_ssim = 1.0
    max_changed = 0.0

    for idx, approved_png in enumerate(approved_pngs):
        if idx >= len(generated_pngs):
            # 생성된 슬라이드가 부족
            slide_results.append(
                SlideComparisonResult(
                    slide_index=idx,
                    ssim_score=0.0,
                    changed_pixel_ratio=1.0,
                    passed=False,
                )
            )
            continue

        generated_png = generated_pngs[idx]
        ssim_score, changed_ratio = compute_ssim(str(approved_png), str(generated_png))

        heatmap_path = None
        if diff_output_dir and (ssim_score < SSIM_THRESHOLD or changed_ratio > CHANGED_PIXEL_RATIO_THRESHOLD):
            heatmap_path = generate_diff_heatmap(
                str(approved_png),
                str(generated_png),
                str(Path(diff_output_dir) / f"diff_slide_{idx:02d}.png"),
            )

        passed = ssim_score >= SSIM_THRESHOLD and changed_ratio <= CHANGED_PIXEL_RATIO_THRESHOLD
        min_ssim = min(min_ssim, ssim_score)
        max_changed = max(max_changed, changed_ratio)

        slide_results.append(
            SlideComparisonResult(
                slide_index=idx,
                ssim_score=ssim_score,
                changed_pixel_ratio=changed_ratio,
                passed=passed,
                diff_heatmap_path=heatmap_path,
            )
        )

    passed_count = sum(1 for r in slide_results if r.passed)
    failed_count = len(slide_results) - passed_count

    return VisualDiffReport(
        total_slides=len(slide_results),
        passed_slides=passed_count,
        failed_slides=failed_count,
        min_ssim=min_ssim,
        max_changed_ratio=max_changed,
        slide_results=slide_results,
        overall_passed=failed_count == 0,
    )
