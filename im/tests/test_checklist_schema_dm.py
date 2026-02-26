"""Checklist 스키마 DM 스타일 검증 테스트.

CreateFromVdrRequest가 DM을 포함한 유효 스타일을 수용하고,
잘못된 스타일을 거부하는지 검증한다.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from src.api.schemas.checklist import CreateFromVdrRequest


class TestChecklistSchemaDm:
    """DM 스타일 스키마 검증."""

    _BASE = {
        "transaction_id": str(uuid.uuid4()),
        "vdr_document_ids": [str(uuid.uuid4())],
        "company_name": "테스트기업",
        "project_name": "Project Alpha",
    }

    def test_dm_style_accepted(self) -> None:
        """DM 스타일이 정상적으로 수용된다."""
        req = CreateFromVdrRequest(**self._BASE, im_style="DM")
        assert req.im_style == "DM"

    def test_teaser_style_accepted(self) -> None:
        """TEASER 스타일이 정상적으로 수용된다."""
        req = CreateFromVdrRequest(**self._BASE, im_style="TEASER")
        assert req.im_style == "TEASER"

    def test_full_style_default(self) -> None:
        """im_style 미지정 시 기본값 FULL."""
        req = CreateFromVdrRequest(**self._BASE)
        assert req.im_style == "FULL"

    def test_invalid_style_rejected(self) -> None:
        """잘못된 스타일은 ValidationError를 발생시킨다."""
        with pytest.raises(ValidationError, match="im_style"):
            CreateFromVdrRequest(**self._BASE, im_style="INVALID")
