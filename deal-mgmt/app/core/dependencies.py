"""외부 클라이언트 DI Provider — ENV 기반 환경 분기.

- 프로덕션/스테이징: Real 클라이언트 (KIIS/FDD/IM 실제 API 호출)
- 테스트 (TESTING=true): Mock 클라이언트 (정적 더미 응답)
- FastAPI Depends()를 통해 라우터에 주입, conftest.py에서 오버라이드 가능.

환경 전환 우선순위:
  1. conftest.py ``dependency_overrides`` — 테스트 시 최우선 적용 (FastAPI DI 메커니즘)
  2. ``_is_testing`` 플래그 — TESTING 환경변수 기반 폴백 (dependency_overrides 미적용 시)

즉, 테스트 환경에서는 conftest.py의 오버라이드가 이 모듈의 ``_is_testing`` 분기보다
우선하므로 항상 MockClient가 주입된다.
"""

from __future__ import annotations

import logging
import os

from app.services.protocols import FDDClientProtocol, IMClientProtocol, KIISClientProtocol

logger = logging.getLogger(__name__)

_is_testing = os.getenv("TESTING", "").lower() in ("true", "1")
if _is_testing:
    _env = os.getenv("ENV", "").lower()
    if _env in ("production", "prod", "staging", "stg"):
        raise RuntimeError("CRITICAL: TESTING=true is forbidden in production/staging")

# 싱글턴 캐시 (앱 lifespan 동안 유지)
_kiis_instance: KIISClientProtocol | None = None
_fdd_instance: FDDClientProtocol | None = None
_im_instance: IMClientProtocol | None = None


def get_kiis_client() -> KIISClientProtocol:
    """KIIS 클라이언트 DI Provider — FastAPI ``Depends()`` 에서 사용."""
    global _kiis_instance
    if _kiis_instance is None:
        if _is_testing:
            from app.services.mock_clients import MockKIISClient

            _kiis_instance = MockKIISClient()
            logger.debug("KIIS client: MockKIISClient (testing)")
        else:
            from app.services.kiis_client import KIISClient

            _kiis_instance = KIISClient()
            logger.debug("KIIS client: KIISClient (real)")
    return _kiis_instance


def get_fdd_client() -> FDDClientProtocol:
    """FDD 클라이언트 DI Provider."""
    global _fdd_instance
    if _fdd_instance is None:
        if _is_testing:
            from app.services.mock_clients import MockFDDClient

            _fdd_instance = MockFDDClient()
        else:
            from app.services.fdd_client import FDDClient

            _fdd_instance = FDDClient()
    return _fdd_instance


def get_im_client() -> IMClientProtocol:
    """IM 클라이언트 DI Provider."""
    global _im_instance
    if _im_instance is None:
        if _is_testing:
            from app.services.mock_clients import MockIMClient

            _im_instance = MockIMClient()
        else:
            from app.services.im_client import IMClient

            _im_instance = IMClient()
    return _im_instance


async def close_all_clients() -> None:
    """lifespan shutdown — 모든 클라이언트 커넥션 정리."""
    global _kiis_instance, _fdd_instance, _im_instance
    if _kiis_instance is not None and hasattr(_kiis_instance, "close"):
        try:
            await _kiis_instance.close()
        except Exception:
            logger.warning("KIIS client close failed", exc_info=True)
    _kiis_instance = None
    _fdd_instance = None
    _im_instance = None
