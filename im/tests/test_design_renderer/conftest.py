"""테스트 공유 픽스처 — IMDocumentData (TITAN/COVENANT/FULL) + 보조 픽스처.

데이터 빌더는 tests/visual_diff/sample_builders.py 에 정의.
이 conftest.py 는 pytest fixture 래퍼만 제공한다.
"""

from pathlib import Path

import pytest

from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.im_document import (
    FinancialStatements,
    IMDocumentData,
    NumberFormatConfig,
)
from src.design_renderer.security import SecurityOptions
from tests.visual_diff.sample_builders import (
    build_covenant_data,
    build_financial_statements,
    build_full_data,
    build_number_format_config,
    build_titan_data,
    build_usd_number_format_config,
)


# ---------------------------------------------------------------------------
# 재무 데이터
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_financial_statements() -> FinancialStatements:
    """3개년 재무 데이터 — 모든 렌더러 테스트에 충분한 최소 데이터."""
    return build_financial_statements()


# ---------------------------------------------------------------------------
# IMDocumentData 프리셋
# ---------------------------------------------------------------------------


@pytest.fixture
def titan_data() -> IMDocumentData:
    """TITAN 프리셋 (9개 섹션) — 최소 필수 데이터."""
    return build_titan_data()


@pytest.fixture
def covenant_data() -> IMDocumentData:
    """COVENANT 프리셋 (10개 섹션) — value_creation 포함."""
    return build_covenant_data()


@pytest.fixture
def full_data() -> IMDocumentData:
    """FULL 프리셋 (18개 섹션) — 전체 필드 채움."""
    return build_full_data()


# ---------------------------------------------------------------------------
# 보조 픽스처
# ---------------------------------------------------------------------------


@pytest.fixture
def default_tokens() -> IMDesignTokens:
    """기본 디자인 토큰."""
    return DEFAULT_TOKENS


@pytest.fixture
def number_format_config() -> NumberFormatConfig:
    """기본 숫자 포맷 설정."""
    return build_number_format_config()


@pytest.fixture
def usd_number_format_config() -> NumberFormatConfig:
    """USD 숫자 포맷 설정."""
    return build_usd_number_format_config()


@pytest.fixture
def security_options() -> SecurityOptions:
    """기본 보안 옵션."""
    return SecurityOptions(
        pdf_password="test1234",
        watermark_text="CONFIDENTIAL",
        watermark_opacity=0.2,
        pptx_read_only=True,
    )


@pytest.fixture
def tmp_output(tmp_path: Path) -> Path:
    """임시 출력 디렉토리."""
    out = tmp_path / "output"
    out.mkdir()
    return out
