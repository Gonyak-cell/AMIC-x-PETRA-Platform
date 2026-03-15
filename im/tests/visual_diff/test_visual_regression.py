"""시각 회귀 테스트 — IM 프리셋별 PPTX → PNG → 승인 PNG 비교.

> 마지막 수정: 2026-03-13 22:14:00

CI/nightly 전용. 런타임 미실행.
im/src/design_renderer/** 또는 templates/** 변경 시에만 트리거.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import GOLDEN_SAMPLES_DIR, skip_no_visual
from .diff_utils import (
    SSIM_THRESHOLD,
    VisualDiffReport,
    compare_slide_pngs,
    pptx_to_pngs,
)


def _has_pptx_templates() -> bool:
    """IM PPTX 마스터 템플릿 존재 여부."""
    try:
        from src.template_engine.registry import get_template_path

        get_template_path("TM")
        return True
    except (FileNotFoundError, KeyError, ImportError):
        return False


TEMPLATES_READY = _has_pptx_templates()
skip_no_template = pytest.mark.skipif(
    not TEMPLATES_READY,
    reason="IM 마스터 템플릿 파일 없음",
)


# ── 시각 회귀 테스트 ──────────────────────────────────────────────


@skip_no_visual
@skip_no_template
class TestVisualRegression:
    """승인 PNG 대비 시각 회귀 검증 (IM 프리셋)."""

    @pytest.mark.parametrize(
        "variant,preset",
        [
            ("tm_default", "TITAN"),
            ("dm_default", "COVENANT"),
            ("im_full", "FULL"),
        ],
    )
    def test_visual_regression(
        self,
        variant: str,
        preset: str,
        tmp_path: Path,
        visual_diff_output: Path,
    ) -> None:
        """프리셋별 PPTX → PNG → 승인 PNG SSIM 비교."""
        approved_dir = GOLDEN_SAMPLES_DIR / variant / "approved"

        if not approved_dir.exists() or not list(approved_dir.glob("slide_*.png")):
            pytest.skip(f"승인 PNG 없음: {approved_dir}")

        from src.design_renderer.pipeline import IMPipeline

        from .sample_builders import VARIANT_BUILDERS

        data = VARIANT_BUILDERS[variant]()  # type: ignore[operator]
        pipeline = IMPipeline()
        output_path = tmp_path / f"{variant}.pptx"
        result = pipeline.generate_pptx(data, output_path=str(output_path))

        if not result.success or result.pptx_path is None:
            pytest.fail(f"PPTX 생성 실패: {result.errors}")

        # PNG 변환
        generated_dir = str(tmp_path / f"generated_{variant}")
        generated_pngs = pptx_to_pngs(str(result.pptx_path), generated_dir)
        assert len(generated_pngs) > 0, "PNG 변환 실패"

        # SSIM 비교
        diff_dir = str(visual_diff_output / variant)
        report: VisualDiffReport = compare_slide_pngs(
            str(approved_dir), generated_dir, diff_dir
        )

        assert report.overall_passed, (
            f"시각 회귀 감지 ({variant}/{preset}):\n"
            f"  총 슬라이드: {report.total_slides}\n"
            f"  통과: {report.passed_slides}, 실패: {report.failed_slides}\n"
            f"  최소 SSIM: {report.min_ssim:.4f} (기준: {SSIM_THRESHOLD})\n"
            + "\n".join(
                f"  슬라이드 {r.slide_index}: SSIM={r.ssim_score:.4f}"
                for r in report.slide_results
                if not r.passed
            )
        )

    @pytest.mark.slow
    @pytest.mark.deterministic
    @pytest.mark.parametrize(
        "variant,preset",
        [
            ("tm_default", "TITAN"),
            ("dm_default", "COVENANT"),
            ("im_full", "FULL"),
        ],
    )
    def test_deterministic_rendering(
        self,
        variant: str,
        preset: str,
        tmp_path: Path,
    ) -> None:
        """동일 입력 2회 생성 → 모든 슬라이드 SSIM ≥ 0.999 (렌더링 결정론).

        실행: FORCE_VISUAL_DIFF=1 pytest -m deterministic tests/visual_diff/
        제외: pytest -m 'not slow' tests/
        """
        from src.design_renderer.pipeline import IMPipeline

        from .sample_builders import VARIANT_BUILDERS

        data = VARIANT_BUILDERS[variant]()  # type: ignore[operator]  # dict[str, object] 타입

        pngs_list: list[list[str]] = []
        for run in range(2):
            pipeline = IMPipeline()
            output_path = tmp_path / f"det_{variant}_{run}.pptx"
            result = pipeline.generate_pptx(data, output_path=str(output_path))
            if not result.success or result.pptx_path is None:
                pytest.fail(f"PPTX 생성 실패 (run {run}): {result.errors}")
            png_dir = str(tmp_path / f"det_pngs_{variant}_{run}")
            pngs = pptx_to_pngs(str(result.pptx_path), png_dir)
            assert len(pngs) > 0, f"PNG 변환 실패 (run {run})"
            pngs_list.append(pngs)

        assert len(pngs_list[0]) == len(pngs_list[1]), (
            f"슬라이드 수 불일치: {len(pngs_list[0])} vs {len(pngs_list[1])}"
        )

        report: VisualDiffReport = compare_slide_pngs(
            str(tmp_path / f"det_pngs_{variant}_0"),
            str(tmp_path / f"det_pngs_{variant}_1"),
        )
        assert report.min_ssim >= 0.999, (
            f"결정론 위반 ({variant}/{preset}): 최소 SSIM {report.min_ssim:.4f} < 0.999"
        )


# ── 유틸리티 테스트 ──────────────────────────────────────────────


class TestDiffUtils:
    """diff_utils 단위 테스트."""

    def test_ssim_threshold_defined(self) -> None:
        """SSIM 임계값이 PLAN.md 기준대로 정의."""
        assert SSIM_THRESHOLD == 0.985

    def test_golden_samples_dir_exists(self) -> None:
        """골든 샘플 디렉토리 존재."""
        assert GOLDEN_SAMPLES_DIR.exists()

    @pytest.mark.parametrize("variant", ["tm_default", "dm_default", "im_full"])
    def test_manifest_exists(self, variant: str) -> None:
        """매니페스트 파일 존재."""
        manifest_path = GOLDEN_SAMPLES_DIR / variant / "manifest.json"
        assert manifest_path.exists(), f"매니페스트 없음: {manifest_path}"
