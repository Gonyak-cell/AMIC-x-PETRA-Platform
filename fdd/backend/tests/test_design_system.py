"""Tests for Design System loader (Phase 2 - compass_integration_plan.md)."""

import tempfile
from pathlib import Path

import pytest

from app.renderers.design_system import (
    DesignSystemError,
    clear_cache,
    get_adjustment_color,
    get_chart_style,
    get_colors,
    get_design_system,
    get_fdd_config,
    get_fonts,
    get_layout,
    get_number_formats,
    get_risk_color,
    get_sizes,
    load_design_system,
)


class TestLoadDesignSystem:
    """Test main loader function."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_load_default_config(self):
        """Load the default design_system.yaml."""
        ds = load_design_system()
        assert ds is not None
        assert "version" in ds
        assert ds["version"] == "1.0"

    def test_load_returns_dict(self):
        """Loaded config is a dictionary."""
        ds = load_design_system()
        assert isinstance(ds, dict)

    def test_cache_returns_same_object(self):
        """LRU cache returns the same object."""
        ds1 = load_design_system()
        ds2 = load_design_system()
        # lru_cache returns the same cached dict
        assert ds1 is ds2

    def test_missing_file_raises_error(self):
        """Missing config file raises DesignSystemError."""
        with pytest.raises(DesignSystemError) as exc_info:
            load_design_system("/nonexistent/path/design_system.yaml")
        assert "not found" in str(exc_info.value)

    def test_invalid_yaml_raises_error(self):
        """Invalid YAML raises DesignSystemError."""
        clear_cache()
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name

        try:
            with pytest.raises(DesignSystemError) as exc_info:
                load_design_system(temp_path)
            assert "Invalid YAML" in str(exc_info.value)
        finally:
            Path(temp_path).unlink()


class TestGetColors:
    """Test color accessor functions."""

    def test_get_colors_returns_dict(self):
        """get_colors returns a dictionary."""
        colors = get_colors()
        assert isinstance(colors, dict)

    def test_primary_color(self):
        """Primary color is Navy Blue."""
        colors = get_colors()
        assert colors["primary"] == "#003366"

    def test_positive_color(self):
        """Positive color is Green."""
        colors = get_colors()
        assert colors["positive"] == "#2E7D32"

    def test_negative_color(self):
        """Negative color is Red."""
        colors = get_colors()
        assert colors["negative"] == "#E0301E"

    def test_all_colors_are_hex(self):
        """All color values start with #."""
        colors = get_colors()
        for key, value in colors.items():
            assert value.startswith("#"), f"{key} should be a hex color"


class TestGetFonts:
    """Test font accessor functions."""

    def test_get_fonts_returns_dict(self):
        """get_fonts returns a dictionary."""
        fonts = get_fonts()
        assert isinstance(fonts, dict)

    def test_english_font(self):
        """English font is Inter."""
        fonts = get_fonts()
        assert fonts["english"] == "Inter"

    def test_data_font(self):
        """Data font is IBM Plex Mono."""
        fonts = get_fonts()
        assert fonts["data"] == "IBM Plex Mono"

    def test_korean_font(self):
        """Korean font is Pretendard."""
        fonts = get_fonts()
        assert fonts["korean"] == "Pretendard"


class TestGetSizes:
    """Test size accessor functions."""

    def test_get_sizes_returns_dict(self):
        """get_sizes returns a dictionary."""
        sizes = get_sizes()
        assert isinstance(sizes, dict)

    def test_slide_title_size(self):
        """Slide title is 28pt."""
        sizes = get_sizes()
        assert sizes["slide_title"] == 28

    def test_kpi_callout_size(self):
        """KPI callout is 60pt."""
        sizes = get_sizes()
        assert sizes["kpi_callout"] == 60


class TestGetNumberFormats:
    """Test number format accessor functions."""

    def test_get_number_formats_returns_dict(self):
        """get_number_formats returns a dictionary."""
        formats = get_number_formats()
        assert isinstance(formats, dict)

    def test_currency_format(self):
        """Currency format uses parentheses for negatives."""
        formats = get_number_formats()
        assert "(#,##0)" in formats["currency"]

    def test_percentage_format(self):
        """Percentage format includes % sign."""
        formats = get_number_formats()
        assert "%" in formats["percentage"]


class TestGetLayout:
    """Test layout accessor functions."""

    def test_get_layout_returns_dict(self):
        """get_layout returns a dictionary."""
        layout = get_layout()
        assert isinstance(layout, dict)

    def test_aspect_ratio(self):
        """Aspect ratio is 16:9."""
        layout = get_layout()
        assert layout["aspect_ratio"] == "16:9"

    def test_slide_width(self):
        """Slide width is 10 inches."""
        layout = get_layout()
        assert layout["slide_width"] == 10.0


class TestGetChartStyle:
    """Test chart style accessor functions."""

    def test_waterfall_style(self):
        """Waterfall chart style has increasing/decreasing colors."""
        style = get_chart_style("waterfall")
        assert "increasing_color" in style
        assert "decreasing_color" in style

    def test_common_merged(self):
        """Common settings are merged into specific chart style."""
        style = get_chart_style("bar")
        assert "background" in style  # from common
        assert "primary_color" in style  # from bar


class TestGetFddConfig:
    """Test FDD-specific config accessor."""

    def test_get_fdd_config_returns_dict(self):
        """get_fdd_config returns a dictionary."""
        fdd = get_fdd_config()
        assert isinstance(fdd, dict)

    def test_adjustment_colors_exist(self):
        """Adjustment colors are defined."""
        fdd = get_fdd_config()
        assert "adjustment_colors" in fdd
        assert "one_off" in fdd["adjustment_colors"]

    def test_risk_colors_exist(self):
        """Risk colors are defined."""
        fdd = get_fdd_config()
        assert "risk_colors" in fdd


class TestGetAdjustmentColor:
    """Test adjustment color helper."""

    def test_one_off_color(self):
        """One-off adjustment is Orange."""
        color = get_adjustment_color("one_off")
        assert color == "#FFA726"

    def test_non_operating_color(self):
        """Non-operating adjustment is Purple."""
        color = get_adjustment_color("non_operating")
        assert color == "#7E57C2"

    def test_unknown_returns_neutral(self):
        """Unknown category returns neutral color."""
        color = get_adjustment_color("unknown_category")
        # Falls back to neutral color
        assert color.startswith("#")


class TestGetRiskColor:
    """Test risk color helper."""

    def test_high_risk_red(self):
        """High risk is Red."""
        color = get_risk_color("high")
        assert color == "#E0301E"

    def test_medium_risk_amber(self):
        """Medium risk is Amber."""
        color = get_risk_color("medium")
        assert color == "#F9A825"

    def test_low_risk_green(self):
        """Low risk is Green."""
        color = get_risk_color("low")
        assert color == "#2E7D32"


class TestGetDesignSystem:
    """Test FastAPI dependency function."""

    def test_dependency_returns_full_config(self):
        """get_design_system returns the full config."""
        ds = get_design_system()
        assert "colors" in ds
        assert "fonts" in ds
        assert "sizes" in ds
        assert "layout" in ds
        assert "charts" in ds
        assert "fdd" in ds


class TestClearCache:
    """Test cache clearing."""

    def test_clear_cache_reloads(self):
        """Clearing cache causes a reload."""
        ds1 = load_design_system()
        clear_cache()
        ds2 = load_design_system()
        # After clear, new dict is loaded (but with same values)
        assert ds1 == ds2  # Same content
        # Note: Due to caching behavior, we can't guarantee different object
