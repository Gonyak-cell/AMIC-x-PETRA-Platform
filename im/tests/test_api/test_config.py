"""API 설정 및 앱 팩토리 테스트 (T-I01, T-I02).

> 마지막 수정: 2026-02-10 16:29:08

APIConfig 설정 로딩, 유효성 검증, FastAPI 앱 팩토리 동작을 검증한다.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI

from src.api import __version__, create_app
from src.api.config import APIConfig, get_config
from src.api.exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    TaskError,
    ValidationError,
)


class TestAPIConfig:
    """APIConfig 설정 테스트."""

    def test_default_values(self) -> None:
        """기본값이 올바르게 로드되는지 확인 (.env 무시)."""
        with patch.dict("os.environ", {}, clear=False):
            config = APIConfig(_env_file=None)
            assert config.db_pool_size == 5
            assert config.db_max_overflow == 10
            assert config.jwt_algorithm == "RS256"
            assert config.rate_limit_per_minute == 60
            assert config.debug is False

    def test_database_url_default(self) -> None:
        """DB URL 기본값이 올바른지 확인."""
        config = APIConfig()
        assert "postgresql+asyncpg" in config.database_url
        assert "5434" in config.database_url

    def test_redis_url_default(self) -> None:
        """Redis URL 기본값이 올바른지 확인."""
        config = APIConfig()
        assert config.redis_url.startswith("redis://")
        assert "6380" in config.redis_url

    def test_invalid_database_url_raises(self) -> None:
        """잘못된 DB URL은 ValueError를 발생시킨다."""
        with pytest.raises(ValueError, match="postgresql"):
            APIConfig(database_url="mysql://localhost/test")

    def test_invalid_redis_url_raises(self) -> None:
        """잘못된 Redis URL은 ValueError를 발생시킨다."""
        with pytest.raises(ValueError, match="redis://"):
            APIConfig(redis_url="http://localhost:6379")

    def test_hard_time_limit_gt_soft(self) -> None:
        """hard_time_limit이 soft_time_limit보다 커야 한다."""
        with pytest.raises(ValueError, match="hard_time_limit"):
            APIConfig(
                celery_task_soft_time_limit=300,
                celery_task_hard_time_limit=200,
            )

    def test_has_dart_property(self) -> None:
        """has_dart가 API 키 존재 여부를 반환한다."""
        config = APIConfig(dart_api_key="")
        assert config.has_dart is False
        config2 = APIConfig(dart_api_key="test-key")
        assert config2.has_dart is True

    def test_has_openai_property(self) -> None:
        """has_openai가 API 키 존재 여부를 반환한다."""
        config = APIConfig(openai_api_key="")
        assert config.has_openai is False
        config2 = APIConfig(openai_api_key="sk-test")
        assert config2.has_openai is True

    def test_get_config_returns_singleton(self) -> None:
        """get_config()는 싱글턴을 반환한다."""
        get_config.cache_clear()
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
        get_config.cache_clear()

    def test_allowed_origins_default(self) -> None:
        """기본 CORS 허용 오리진이 설정되어 있다."""
        config = APIConfig()
        assert isinstance(config.allowed_origins, list)
        assert len(config.allowed_origins) >= 1

    def test_env_override(self) -> None:
        """환경변수로 설정을 오버라이드할 수 있다."""
        with patch.dict("os.environ", {"DEBUG": "true", "LOG_LEVEL": "DEBUG"}):
            config = APIConfig()
            assert config.debug is True
            assert config.log_level == "DEBUG"


class TestCreateApp:
    """FastAPI 앱 팩토리 테스트."""

    def test_creates_fastapi_instance(self) -> None:
        """create_app()이 FastAPI 인스턴스를 반환한다."""
        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_title(self) -> None:
        """앱 제목이 올바르게 설정된다."""
        app = create_app()
        assert app.title == "Auto-IM Generator API"

    def test_app_version(self) -> None:
        """앱 버전이 __version__과 일치한다."""
        app = create_app()
        assert app.version == __version__

    def test_health_router_registered(self) -> None:
        """헬스체크 라우터가 등록되어 있다."""
        app = create_app()
        routes = [route.path for route in app.routes]
        assert "/health" in routes
        assert "/ready" in routes

    def test_docs_url_configured(self) -> None:
        """OpenAPI docs URL이 설정되어 있다."""
        app = create_app()
        assert app.docs_url == "/docs"

    def test_exception_handler_registered(self) -> None:
        """APIError 예외 핸들러가 등록되어 있다."""
        app = create_app()
        assert APIError in app.exception_handlers


class TestExceptions:
    """API 예외 계층 테스트."""

    def test_api_error_base(self) -> None:
        """APIError가 message와 details를 포함한다."""
        err = APIError("테스트 오류", {"key": "value"})
        assert err.message == "테스트 오류"
        assert err.details == {"key": "value"}

    def test_api_error_default_details(self) -> None:
        """APIError의 기본 details가 빈 dict이다."""
        err = APIError("오류")
        assert err.details == {}

    def test_authentication_error(self) -> None:
        """AuthenticationError가 기본 메시지를 갖는다."""
        err = AuthenticationError()
        assert "인증" in err.message

    def test_authorization_error_with_role(self) -> None:
        """AuthorizationError가 required_role을 포함한다."""
        err = AuthorizationError(required_role="ADMIN")
        assert err.details["required_role"] == "ADMIN"

    def test_not_found_error(self) -> None:
        """NotFoundError가 리소스 타입과 식별자를 포함한다."""
        err = NotFoundError("문서", "abc-123")
        assert "문서" in err.message
        assert err.details["resource_type"] == "문서"
        assert err.details["identifier"] == "abc-123"

    def test_conflict_error(self) -> None:
        """ConflictError가 리소스 타입과 식별자를 포함한다."""
        err = ConflictError("기업", "00123456")
        assert "이미 존재" in err.message

    def test_task_error(self) -> None:
        """TaskError가 task_id와 stage를 포함한다."""
        err = TaskError(task_id="task-123", stage="COLLECTING")
        assert err.details["task_id"] == "task-123"
        assert err.details["stage"] == "COLLECTING"

    def test_validation_error(self) -> None:
        """ValidationError가 필드와 이유를 포함한다."""
        err = ValidationError("corp_code", "8자리 숫자여야 합니다")
        assert "corp_code" in err.message
        assert err.details["field"] == "corp_code"

    def test_exception_hierarchy(self) -> None:
        """모든 예외가 APIError를 상속한다."""
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(AuthorizationError, APIError)
        assert issubclass(NotFoundError, APIError)
        assert issubclass(ConflictError, APIError)
        assert issubclass(TaskError, APIError)
        assert issubclass(ValidationError, APIError)
