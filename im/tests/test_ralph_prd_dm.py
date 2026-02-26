"""DM PRD 유효성 테스트.

IM_DM_PRD가 올바른 구조와 값을 가지는지 검증한다.
"""

from __future__ import annotations

import pytest

from src.ralph.prd import get_prd


class TestDmPrd:
    """IM DM PRD 단위 테스트."""

    def test_get_prd_im_dm_exists(self) -> None:
        """im_dm PRD가 존재한다."""
        prd = get_prd("im_dm")
        assert prd is not None

    def test_dm_memo_type(self) -> None:
        """memo_type이 'DM'이다."""
        prd = get_prd("im_dm")
        assert prd["memo_type"] == "DM"

    def test_dm_slide_range(self) -> None:
        """min_slides 6, max_slides 15."""
        prd = get_prd("im_dm")
        assert prd["min_slides"] == 6
        assert prd["max_slides"] == 15

    def test_dm_pass_threshold(self) -> None:
        """DM은 내부 문서이므로 pass_threshold가 3.5."""
        prd = get_prd("im_dm")
        assert prd["pass_threshold"] == 3.5

    def test_dm_max_iterations(self) -> None:
        """DM은 짧은 문서이므로 max_iterations가 2."""
        prd = get_prd("im_dm")
        assert prd["max_iterations"] == 2

    def test_dm_budget(self) -> None:
        """DM 예산은 $3."""
        prd = get_prd("im_dm")
        assert prd["budget_usd"] == 3.0

    def test_dm_quality_dimensions_weight_sum(self) -> None:
        """quality_dimensions weight 합계가 1.0이다."""
        prd = get_prd("im_dm")
        total = sum(d["weight"] for d in prd["quality_dimensions"].values())
        assert abs(total - 1.0) < 0.001

    def test_dm_required_sections(self) -> None:
        """DM 필수 섹션 3개가 포함되어 있다."""
        prd = get_prd("im_dm")
        required = prd["required_sections"]
        assert "dm_deal_structure" in required
        assert "dm_investment_thesis" in required
        assert "dm_valuation" in required

    def test_dm_design_standards_amic(self) -> None:
        """DM 디자인 시스템이 AMIC 공식 팔레트를 사용한다."""
        prd = get_prd("im_dm")
        ds = prd["design_standards"]
        assert ds["color_primary"] == "#0F3A32"
        assert ds["font_heading"] == "SUITE"

    def test_existing_prd_still_works(self) -> None:
        """기존 im_full, im_teaser PRD가 여전히 동작한다."""
        assert get_prd("im_full")["memo_type"] == "IM"
        assert get_prd("im_teaser")["memo_type"] == "TM"

    def test_invalid_prd_raises(self) -> None:
        """존재하지 않는 PRD 요청 시 ValueError."""
        with pytest.raises(ValueError):
            get_prd("im_nonexistent")
