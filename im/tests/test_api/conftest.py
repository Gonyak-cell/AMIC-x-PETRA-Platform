"""API 테스트 공유 fixture.

> 마지막 수정: 2026-02-10 16:29:08

비동기 테스트 클라이언트, DB 세션, 모킹 fixture 등을 제공한다.
"""

from __future__ import annotations

import uuid
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import create_app
from src.api.config import APIConfig
from src.api.db.models.document import DocumentStatus


@pytest.fixture
def test_config() -> APIConfig:
    """테스트용 APIConfig를 반환한다."""
    return APIConfig(
        database_url="postgresql+asyncpg://test:test@localhost:5434/imgen_test",
        redis_url="redis://localhost:6380/15",
        redis_result_backend="redis://localhost:6380/14",
        jwt_secret_key="test-secret-key-for-unit-tests",
        debug=True,
        log_level="DEBUG",
    )


@pytest.fixture
def app():
    """테스트용 FastAPI 앱을 반환한다."""
    return create_app()


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """비동기 테스트 클라이언트."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def sample_user_data() -> dict:
    """샘플 사용자 데이터."""
    return {
        "id": uuid.uuid4(),
        "email": "test@example.com",
        "hashed_password": "hashed_password_value",
        "full_name": "테스트 사용자",
        "role": "USER",
        "is_active": True,
    }


@pytest.fixture
def sample_document_data() -> dict:
    """샘플 문서 데이터."""
    return {
        "corp_code": "00123456",
        "company_name": "테스트 주식회사",
        "project_name": "Project TITAN",
        "im_style": "FULL",
        "sections": ["executive_summary", "company_overview", "financial_analysis"],
        "status": DocumentStatus.PENDING.value,
        "progress_pct": 0,
    }


@pytest.fixture
def sample_company_data() -> dict:
    """샘플 기업 데이터."""
    return {
        "corp_code": "00123456",
        "corp_name": "테스트 주식회사",
        "corp_name_en": "Test Corp",
        "stock_code": "123456",
        "industry": "tech",
        "homepage_url": "https://test.co.kr",
    }
