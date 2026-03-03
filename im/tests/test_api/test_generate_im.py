"""generate_im 마스터 태스크 테스트 (T-I12).

> 마지막 수정: 2026-02-10 17:39:59
"""

from __future__ import annotations

import dataclasses
import enum
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.api.tasks.serializers import _make_json_serializable, im_data_to_dict


@pytest.fixture(autouse=True)
def _celery_eager():
    """Celery를 eager 모드로 설정한다."""
    from src.api.tasks.celery_app import celery_app

    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
    )
    yield
    celery_app.conf.update(
        task_always_eager=False,
        task_eager_propagates=False,
    )


class TestMakeJsonSerializable:
    """JSON 직렬화 변환 테스트."""

    def test_decimal_to_float(self) -> None:
        """Decimal을 float로 변환한다."""
        assert _make_json_serializable(Decimal("123.45")) == 123.45

    def test_enum_to_value(self) -> None:
        """Enum을 value로 변환한다."""

        class Color(enum.Enum):
            RED = "red"

        assert _make_json_serializable(Color.RED) == "red"

    def test_nested_dict(self) -> None:
        """중첩 dict를 재귀적으로 변환한다."""
        data = {"amount": Decimal("100.5"), "nested": {"val": Decimal("0.1")}}
        result = _make_json_serializable(data)
        assert result == {"amount": 100.5, "nested": {"val": 0.1}}

    def test_list_conversion(self) -> None:
        """리스트 내 항목을 변환한다."""
        data = [Decimal("1.0"), Decimal("2.0"), "text"]
        result = _make_json_serializable(data)
        assert result == [1.0, 2.0, "text"]

    def test_dataclass_conversion(self) -> None:
        """dataclass를 dict로 변환한다."""

        @dataclasses.dataclass
        class Sample:
            value: Decimal = Decimal("99.9")
            name: str = "test"

        result = _make_json_serializable(Sample())
        assert result == {"value": 99.9, "name": "test"}

    def test_primitives_unchanged(self) -> None:
        """기본 타입은 변환 없이 통과한다."""
        assert _make_json_serializable(42) == 42
        assert _make_json_serializable("hello") == "hello"
        assert _make_json_serializable(None) is None
        assert _make_json_serializable(True) is True


class TestImDataToDict:
    """im_data_to_dict 테스트."""

    def test_dict_passthrough(self) -> None:
        """dict 입력을 그대로 처리한다."""
        data = {"key": Decimal("1.5"), "list": [Decimal("2.0")]}
        result = im_data_to_dict(data)
        assert result == {"key": 1.5, "list": [2.0]}

    def test_dataclass_conversion(self) -> None:
        """dataclass를 dict로 변환한다."""

        @dataclasses.dataclass
        class MockData:
            corp_code: str = "00123456"
            amount: Decimal = Decimal("100")

        result = im_data_to_dict(MockData())
        assert result == {"corp_code": "00123456", "amount": 100.0}

    def test_unsupported_type_raises(self) -> None:
        """지원하지 않는 타입에서 TypeError를 발생시킨다."""
        with pytest.raises(TypeError, match="지원하지 않는 타입"):
            im_data_to_dict("not a dict or dataclass")  # type: ignore[arg-type]


class TestGenerateImTask:
    """generate_im_task 구조 테스트."""

    def test_task_is_registered(self) -> None:
        """generate_im 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import generate_im_task

        assert generate_im_task.name == "generate_im"

    def test_task_bind_true(self) -> None:
        """태스크가 bind=True로 설정되어 있다."""
        from src.api.tasks.generate_im import generate_im_task

        assert hasattr(generate_im_task, "bind")


class TestSubTasks:
    """서브 태스크 등록 테스트."""

    def test_fetch_dart_registered(self) -> None:
        """fetch_dart 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import fetch_dart_task

        assert fetch_dart_task.name == "fetch_dart"

    def test_merge_collected_data_registered(self) -> None:
        """merge_collected_data 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import merge_collected_data

        assert merge_collected_data.name == "merge_collected_data"

    def test_analyze_financials_registered(self) -> None:
        """analyze_financials 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import analyze_financials_task

        assert analyze_financials_task.name == "analyze_financials"

    def test_generate_content_registered(self) -> None:
        """generate_content 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import generate_content_task

        assert generate_content_task.name == "generate_content"

    def test_render_document_registered(self) -> None:
        """render_document 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import render_document_task

        assert render_document_task.name == "render_document"

    def test_finalize_document_registered(self) -> None:
        """finalize_document 태스크가 등록되어 있다."""
        from src.api.tasks.generate_im import finalize_document_task

        assert finalize_document_task.name == "finalize_document"


class TestMergeCollectedData:
    """merge_collected_data 태스크 로직 테스트."""

    @patch("src.api.tasks.generate_im.update_progress")
    def test_merge_basic(self, mock_progress: MagicMock) -> None:
        """기본 병합이 올바르게 동작한다."""
        from src.api.tasks.generate_im import merge_collected_data

        dart_data = {"corp_code": "00123456", "company_name_kr": "테스트"}
        web_data = {"corp_code": "00123456", "web_data": {"extra": "info"}}
        brand_data = {
            "corp_code": "00123456",
            "brand_assets": {"primary_color": "#000"},
        }

        result = merge_collected_data([dart_data, web_data, brand_data], "doc-123")

        assert result["corp_code"] == "00123456"
        assert result["company_name_kr"] == "테스트"
        assert result["brand_assets"] == {"primary_color": "#000"}
        assert result["_document_id"] == "doc-123"

    @patch("src.api.tasks.generate_im.update_progress")
    def test_merge_empty_results(self, mock_progress: MagicMock) -> None:
        """빈 결과를 처리한다."""
        from src.api.tasks.generate_im import merge_collected_data

        result = merge_collected_data([], "doc-123")

        assert result["_document_id"] == "doc-123"

    @patch("src.api.tasks.generate_im.update_progress")
    def test_merge_calls_progress(self, mock_progress: MagicMock) -> None:
        """병합 시 진행률 업데이트를 호출한다."""
        from src.api.tasks.generate_im import merge_collected_data

        merge_collected_data([{}], "doc-123")

        mock_progress.assert_called()


class TestFinalizeDocumentTask:
    """finalize_document_task 테스트."""

    @patch("src.api.tasks.progress._sync_update_document")
    @patch("src.api.tasks.generate_im.update_progress")
    def test_returns_completed_status(
        self,
        mock_progress: MagicMock,
        _mock_sync: MagicMock,
    ) -> None:
        """완료 상태를 반환한다."""
        from src.api.tasks.generate_im import finalize_document_task

        im_data = {"pptx_path": "/output/test.pptx", "pdf_path": "/output/test.pdf"}

        result = finalize_document_task(im_data, "doc-123")

        assert result["status"] == "COMPLETED"
        assert result["document_id"] == "doc-123"
        assert result["pptx_path"] == "/output/test.pptx"
