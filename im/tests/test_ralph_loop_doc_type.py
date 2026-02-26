"""Ralph Loop doc_type 매핑 분기 테스트.

실제 resolve_doc_type() 함수를 import하여 테스트한다.
"""

from __future__ import annotations

import pytest

from src.api.tasks.doc_type_resolver import resolve_doc_type


class TestDocTypeMapping:
    """doc_type 매핑 단위 테스트."""

    def test_teaser_maps_to_im_teaser(self) -> None:
        assert resolve_doc_type("TEASER") == "im_teaser"

    def test_tm_maps_to_im_teaser(self) -> None:
        assert resolve_doc_type("TM") == "im_teaser"

    def test_dm_maps_to_im_dm(self) -> None:
        assert resolve_doc_type("DM") == "im_dm"

    def test_full_maps_to_im_full(self) -> None:
        assert resolve_doc_type("FULL") == "im_full"

    def test_custom_maps_to_im_full(self) -> None:
        assert resolve_doc_type("CUSTOM") == "im_full"

    def test_titan_maps_to_im_full(self) -> None:
        assert resolve_doc_type("TITAN") == "im_full"

    def test_covenant_maps_to_im_full(self) -> None:
        assert resolve_doc_type("COVENANT") == "im_full"

    def test_case_insensitive(self) -> None:
        """대소문자 무관하게 매핑된다."""
        assert resolve_doc_type("teaser") == "im_teaser"
        assert resolve_doc_type("dm") == "im_dm"
        assert resolve_doc_type("full") == "im_full"
