"""산업 모듈 예외 테스트."""

from src.industry.exceptions import IndustryError, UnsupportedIndustryError


class TestIndustryError:
    """IndustryError 기반 예외."""

    def test_industry_error_base(self):
        """IndustryError message + details 속성 검증."""
        err = IndustryError(
            message="산업 모듈 오류 발생",
            details={"key": "value"},
        )
        assert err.message == "산업 모듈 오류 발생"
        assert err.details == {"key": "value"}
        assert str(err) == "산업 모듈 오류 발생"

    def test_industry_error_default_details(self):
        """details 미지정 시 빈 딕셔너리."""
        err = IndustryError(message="테스트")
        assert err.details == {}


class TestUnsupportedIndustryError:
    """UnsupportedIndustryError 예외."""

    def test_unsupported_industry_error(self):
        """UnsupportedIndustryError 메시지 포맷 + industry_id 속성."""
        err = UnsupportedIndustryError(
            industry_id="unknown",
            available=["tech", "manufacturing"],
        )
        assert err.industry_id == "unknown"
        assert "unknown" in err.message
        assert "tech" in err.message
        assert err.details["industry_id"] == "unknown"
        assert err.details["available"] == ["tech", "manufacturing"]
