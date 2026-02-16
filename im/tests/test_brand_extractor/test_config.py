"""BrandExtractorConfig 테스트.

> 마지막 수정: 2026-02-10 22:00:00
"""

from __future__ import annotations

import pytest

from src.brand_extractor.config import BrandExtractorConfig


class TestBrandExtractorConfig:
    """BrandExtractorConfig 설정 테스트."""

    def test_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """기본값 확인 (.env 환경변수 격리)."""
        monkeypatch.delenv("BRANDFETCH_API_KEY", raising=False)
        config = BrandExtractorConfig(_env_file=None)
        assert config.brandfetch_api_key == ""
        assert config.timeout == 30
        assert config.min_logo_size == 64
        assert config.preferred_logo_size == 512
        assert config.max_colors == 5
        assert config.fallback_enabled is True

    def test_has_brandfetch_false_when_empty(self) -> None:
        """API 키 없을 때 has_brandfetch가 False."""
        config = BrandExtractorConfig(brandfetch_api_key="")
        assert config.has_brandfetch is False

    def test_has_brandfetch_true_when_set(self) -> None:
        """API 키 있을 때 has_brandfetch가 True."""
        config = BrandExtractorConfig(brandfetch_api_key="test-key")
        assert config.has_brandfetch is True

    def test_preferred_ge_min_validation(self) -> None:
        """preferred_logo_size < min_logo_size일 때 ValidationError."""
        with pytest.raises(Exception):
            BrandExtractorConfig(
                min_logo_size=256,
                preferred_logo_size=64,
            )

    def test_timeout_range(self) -> None:
        """timeout 범위 검증."""
        config = BrandExtractorConfig(timeout=5)
        assert config.timeout == 5

        with pytest.raises(Exception):
            BrandExtractorConfig(timeout=2)  # ge=5 위반

        with pytest.raises(Exception):
            BrandExtractorConfig(timeout=200)  # le=120 위반
