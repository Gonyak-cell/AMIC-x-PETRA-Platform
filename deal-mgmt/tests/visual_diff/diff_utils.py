"""Utilities for visual regression testing."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_WINDOWS_LO_PATHS = [
    Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
    Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
]


def _find_libreoffice() -> str:
    """Return the LibreOffice executable path for the current platform."""
    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if lo:
        return lo
    if platform.system() == "Windows":
        for path in _WINDOWS_LO_PATHS:
            if path.exists():
                return str(path)
    raise FileNotFoundError(
        "LibreOffice not found.\n"
        "  Ubuntu: sudo apt-get install -y libreoffice-impress\n"
        "  macOS:  brew install --cask libreoffice\n"
        "  Windows: https://www.libreoffice.org/download/"
    )


SSIM_THRESHOLD = 0.985
CHANGED_PIXEL_RATIO_THRESHOLD = 0.008
STATIC_DRIFT_PX = 2


@dataclass
class SlideComparisonResult:
    slide_index: int
    ssim_score: float
    changed_pixel_ratio: float
    passed: bool
    diff_heatmap_path: str | None = None


@dataclass
class VisualDiffReport:
    total_slides: int
    passed_slides: int
    failed_slides: int
    min_ssim: float
    max_changed_ratio: float
    slide_results: list[SlideComparisonResult]
    overall_passed: bool


def pptx_to_pngs(pptx_path: str, output_dir: str, dpi: int = 150) -> list[str]:
    """Render a PPTX into slide PNGs via LibreOffice PDF export."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    lo_bin = _find_libreoffice()
    try:
        with tempfile.TemporaryDirectory(prefix="lo-profile-") as profile_dir:
            profile_uri = Path(profile_dir).as_uri()
            result = subprocess.run(
                [
                    lo_bin,
                    f"-env:UserInstallation={profile_uri}",
                    "--headless",
                    "--nologo",
                    "--nodefault",
                    "--norestore",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_path),
                    pptx_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "LibreOffice is required for visual diff rendering."
        ) from exc

    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        detail = stderr or stdout or "stdout/stderr empty"
        raise RuntimeError(f"LibreOffice PDF conversion failed: {detail[:500]}")

    pdf_path = output_path / Path(pptx_path).with_suffix(".pdf").name
    if not pdf_path.exists():
        raise RuntimeError(f"LibreOffice did not produce the PDF: {pdf_path}")

    png_paths: list[str] = []

    try:
        from pdf2image import convert_from_path

        images = convert_from_path(str(pdf_path), dpi=dpi)
        for idx, img in enumerate(images):
            png_file = output_path / f"slide_{idx:02d}.png"
            img.save(str(png_file), "PNG")
            png_paths.append(str(png_file))
        return png_paths
    except (ImportError, Exception) as exc:
        logger.info("pdf2image failed (%s); falling back to PyMuPDF.", exc)

    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for idx, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            png_file = output_path / f"slide_{idx:02d}.png"
            pix.save(str(png_file))
            png_paths.append(str(png_file))
        doc.close()
        return png_paths
    except ImportError:
        logger.warning("Neither pdf2image nor PyMuPDF is available for PNG export.")
        return []


def compute_ssim(image_a_path: str, image_b_path: str) -> tuple[float, float]:
    """Compute SSIM and changed-pixel ratio for two slide images."""
    try:
        import numpy as np
        from PIL import Image
        from skimage.metrics import structural_similarity
    except ImportError as exc:
        raise ImportError(
            "scikit-image + Pillow are required for visual diff tests."
        ) from exc

    img_a = np.array(Image.open(image_a_path).convert("RGB"))
    img_b = np.array(Image.open(image_b_path).convert("RGB"))

    if img_a.shape != img_b.shape:
        target_h = min(img_a.shape[0], img_b.shape[0])
        target_w = min(img_a.shape[1], img_b.shape[1])
        img_a = np.array(Image.fromarray(img_a).resize((target_w, target_h), Image.LANCZOS))
        img_b = np.array(Image.fromarray(img_b).resize((target_w, target_h), Image.LANCZOS))

    ssim_score = structural_similarity(img_a, img_b, channel_axis=2, data_range=255)

    diff = np.abs(img_a.astype(float) - img_b.astype(float))
    changed_pixels = np.any(diff > 10, axis=2)
    changed_ratio = float(changed_pixels.sum()) / changed_pixels.size

    return float(ssim_score), changed_ratio


def generate_diff_heatmap(image_a_path: str, image_b_path: str, output_path: str) -> str:
    """Generate a red heatmap highlighting slide differences."""
    import numpy as np
    from PIL import Image

    img_a = np.array(Image.open(image_a_path).convert("RGB"))
    img_b = np.array(Image.open(image_b_path).convert("RGB"))

    if img_a.shape != img_b.shape:
        target_h = min(img_a.shape[0], img_b.shape[0])
        target_w = min(img_a.shape[1], img_b.shape[1])
        img_a = np.array(Image.fromarray(img_a).resize((target_w, target_h), Image.LANCZOS))
        img_b = np.array(Image.fromarray(img_b).resize((target_w, target_h), Image.LANCZOS))

    diff = np.abs(img_a.astype(float) - img_b.astype(float))
    diff_gray = diff.mean(axis=2)
    diff_normalized = np.clip(diff_gray * 5, 0, 255).astype(np.uint8)

    heatmap = np.zeros((*diff_normalized.shape, 3), dtype=np.uint8)
    heatmap[:, :, 0] = diff_normalized

    Image.fromarray(heatmap).save(output_path)
    return output_path


def compare_slide_pngs(
    approved_dir: str,
    generated_dir: str,
    diff_output_dir: str | None = None,
) -> VisualDiffReport:
    """Compare approved and generated slide PNGs."""
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
        if diff_output_dir and (
            ssim_score < SSIM_THRESHOLD or changed_ratio > CHANGED_PIXEL_RATIO_THRESHOLD
        ):
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

    passed_count = sum(1 for result in slide_results if result.passed)
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
