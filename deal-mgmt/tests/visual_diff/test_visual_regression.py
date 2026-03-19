"""시각 회귀 테스트 — 정규 입력 → PPTX → PNG → 승인 PNG 비교.

> 마지막 수정: 2026-03-13 22:55:00

CI/nightly 전용. 런타임 미실행.
deal-mgmt/app/pptx/** 또는 templates/** 변경 시에만 트리거.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.pptx.memo_generator import TEMPLATE_PATH, generate_memo

from .conftest import GOLDEN_SAMPLES_DIR, skip_no_visual
from .diff_utils import (
    SSIM_THRESHOLD,
    VisualDiffReport,
    compare_slide_pngs,
    pptx_to_pngs,
)

_check_template = TEMPLATE_PATH.exists()
skip_no_template = pytest.mark.skipif(
    not _check_template,
    reason=f"마스터 템플릿 없음: {TEMPLATE_PATH}",
)


def _load_input(variant: str) -> dict:
    """정규 입력 fixture 로드."""
    path = GOLDEN_SAMPLES_DIR / variant / "input.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ── 시각 회귀 테스트 ──────────────────────────────────────────────


@skip_no_visual
@skip_no_template
class TestVisualRegression:
    """승인 PNG 대비 시각 회귀 검증."""

    @pytest.mark.parametrize("variant", ["tm", "dm"])
    def test_visual_regression(
        self,
        variant: str,
        tmp_path: Path,
        visual_diff_output: Path,
    ) -> None:
        """정규 입력 → PPTX → PNG → 승인 PNG SSIM 비교."""
        approved_dir = GOLDEN_SAMPLES_DIR / variant / "approved"

        if not approved_dir.exists() or not list(approved_dir.glob("slide_*.png")):
            pytest.skip(f"승인 PNG 없음: {approved_dir} — 먼저 승인 PNG를 생성하세요.")

        # 1. PPTX 생성
        input_data = _load_input(variant)
        output_pptx = str(tmp_path / f"visual_{variant}.pptx")
        generate_memo(
            memo_type=input_data["memo_type"],
            project_code=input_data["project_code"],
            output_path=output_pptx,
            content=input_data["content"],
        )

        # 2. PNG 변환
        generated_dir = str(tmp_path / f"generated_{variant}")
        generated_pngs = pptx_to_pngs(output_pptx, generated_dir)
        assert len(generated_pngs) > 0, "PNG 변환 실패"

        # 3. SSIM 비교
        diff_dir = str(visual_diff_output / variant)
        report: VisualDiffReport = compare_slide_pngs(str(approved_dir), generated_dir, diff_dir)

        # 4. 결과 검증
        assert report.overall_passed, (
            f"시각 회귀 감지 ({variant}):\n"
            f"  총 슬라이드: {report.total_slides}\n"
            f"  통과: {report.passed_slides}, 실패: {report.failed_slides}\n"
            f"  최소 SSIM: {report.min_ssim:.4f} (기준: {SSIM_THRESHOLD})\n"
            f"  최대 변경 비율: {report.max_changed_ratio:.4f}\n"
            + "\n".join(
                f"  슬라이드 {r.slide_index}: SSIM={r.ssim_score:.4f}, 변경={r.changed_pixel_ratio:.4f}"
                for r in report.slide_results
                if not r.passed
            )
        )

    @pytest.mark.parametrize("variant", ["tm", "dm"])
    def test_deterministic_rendering(
        self,
        variant: str,
        tmp_path: Path,
    ) -> None:
        """동일 입력 2회 생성 → 모든 슬라이드 SSIM ≥ 0.999 (렌더링 결정론)."""
        input_data = _load_input(variant)

        pngs_list: list[list[str]] = []
        for run in range(2):
            output = str(tmp_path / f"det_{variant}_{run}.pptx")
            generate_memo(
                memo_type=input_data["memo_type"],
                project_code=input_data["project_code"],
                output_path=output,
                content=input_data["content"],
            )
            png_dir = str(tmp_path / f"det_pngs_{variant}_{run}")
            pngs = pptx_to_pngs(output, png_dir)
            pngs_list.append(pngs)

        assert len(pngs_list[0]) == len(pngs_list[1]), f"슬라이드 수 불일치: {len(pngs_list[0])} vs {len(pngs_list[1])}"

        report = compare_slide_pngs(
            str(tmp_path / f"det_pngs_{variant}_0"),
            str(tmp_path / f"det_pngs_{variant}_1"),
        )

        assert report.min_ssim >= 0.999, f"결정론 위반: 최소 SSIM {report.min_ssim:.4f} < 0.999"


# ── 유틸리티 함수 테스트 ──────────────────────────────────────────


class TestDiffUtils:
    """diff_utils 단위 테스트 (scikit-image 없이도 일부 동작)."""

    def test_ssim_threshold_defined(self) -> None:
        """SSIM 임계값이 PLAN.md 기준대로 정의."""
        assert SSIM_THRESHOLD == 0.985

    def test_golden_samples_dir_exists(self) -> None:
        """골든 샘플 디렉토리 존재."""
        assert GOLDEN_SAMPLES_DIR.exists()

    @pytest.mark.parametrize("variant", ["tm", "dm"])
    def test_input_json_loadable(self, variant: str) -> None:
        """정규 입력 JSON 로드 가능."""
        data = _load_input(variant)
        assert "memo_type" in data
        assert "content" in data
