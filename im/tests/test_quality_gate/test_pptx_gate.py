"""PPTXProgrammaticGate 단위 테스트.

품질 게이트 엔진의 핵심 경로를 검증한다:
- 정상 PPTX → PASS 판정
- 플레이스홀더 포함 → critical_flags → FAIL
- 빈/손상 PPTX → 게이트 로드 실패 → FAIL
- parse_korean_number 유틸 함수
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch


from src.quality_gate.base import GateResult, GateVerdict
from src.quality_gate.utils import parse_korean_number


# ---------------------------------------------------------------------------
# parse_korean_number 유틸 테스트
# ---------------------------------------------------------------------------
class TestParseKoreanNumber:
    def test_plain_number(self) -> None:
        assert parse_korean_number("1234") == 1234.0

    def test_comma_separated(self) -> None:
        assert parse_korean_number("1,234,567") == 1234567.0

    def test_parenthesis_negative(self) -> None:
        assert parse_korean_number("(500)") == -500.0

    def test_percent(self) -> None:
        result = parse_korean_number("12.5%")
        assert result is not None
        assert abs(result - 0.125) < 1e-6

    def test_currency_won(self) -> None:
        assert parse_korean_number("₩1,234") == 1234.0

    def test_currency_dollar(self) -> None:
        assert parse_korean_number("$1,234") == 1234.0

    def test_empty_string(self) -> None:
        assert parse_korean_number("") is None

    def test_dash(self) -> None:
        assert parse_korean_number("-") is None

    def test_negative_number(self) -> None:
        assert parse_korean_number("-500") == -500.0


# ---------------------------------------------------------------------------
# GateResult 데이터 모델 테스트
# ---------------------------------------------------------------------------
class TestGateResult:
    def test_passed_property_true(self) -> None:
        result = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.5,
        )
        assert result.passed is True

    def test_passed_property_false_with_critical_flags(self) -> None:
        result = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.5,
            critical_flags=["placeholder_found"],
        )
        assert result.passed is False

    def test_passed_property_false_with_fail_verdict(self) -> None:
        result = GateResult(
            gate_name="test",
            verdict=GateVerdict.FAIL,
            weighted_score=2.0,
        )
        assert result.passed is False


# ---------------------------------------------------------------------------
# PPTXProgrammaticGate 통합 테스트 (mock PPTX)
# ---------------------------------------------------------------------------
class TestPPTXProgrammaticGate:
    """PPTXProgrammaticGate의 evaluate를 실제 파일 없이 mock으로 테스트."""

    def _make_mock_slide(
        self,
        title: str = "Cover",
        texts: list[str] | None = None,
        has_table: bool = False,
        has_chart: bool = False,
    ) -> MagicMock:
        """Mock slide 객체를 생성한다.

        python-pptx SlideShapes 인터페이스 모방:
        - slide.shapes.title → 타이틀 placeholder shape
        - for shape in slide.shapes → shape 이터레이션
        """
        slide = MagicMock()

        shapes_list: list[MagicMock] = []
        title_shape_ref: MagicMock | None = None

        if title:
            title_shape = MagicMock()
            title_shape.has_text_frame = True
            tf = MagicMock()
            para = MagicMock()
            run = MagicMock()
            run.text = title
            run.font.name = "SUIT Medium"
            run.font.color.rgb = None
            para.runs = [run]
            tf.paragraphs = [para]
            tf.text = title
            title_shape.text_frame = tf
            title_shape.text = title
            title_shape.has_table = False
            title_shape.has_chart = False
            shapes_list.append(title_shape)
            title_shape_ref = title_shape

        if texts:
            for t in texts:
                shape = MagicMock()
                shape.has_text_frame = True
                tf = MagicMock()
                para = MagicMock()
                run = MagicMock()
                run.text = t
                run.font.name = "SUIT Medium"
                run.font.color.rgb = None
                para.runs = [run]
                tf.paragraphs = [para]
                tf.text = t
                shape.text_frame = tf
                shape.has_table = False
                shape.has_chart = False
                shapes_list.append(shape)

        # SlideShapes mock: .title 속성 + 반복 이터레이션 지원
        shapes_mock = MagicMock()
        shapes_mock.__iter__ = lambda _self: iter(shapes_list)
        shapes_mock.__len__ = lambda _self: len(shapes_list)
        shapes_mock.title = title_shape_ref
        slide.shapes = shapes_mock
        return slide

    def _make_mock_prs(self, slides: list[MagicMock]) -> MagicMock:
        """Mock Presentation 객체를 생성한다."""
        prs = MagicMock()
        prs.slides = slides
        return prs

    @patch("pptx.Presentation")
    def test_evaluate_normal_pptx_returns_result(self, mock_prs_cls: MagicMock) -> None:
        """정상 PPTX → GateResult 반환, score > 0."""
        slides = [
            self._make_mock_slide("Cover"),
            self._make_mock_slide("Disclaimer"),
            self._make_mock_slide("Table of Contents"),
            self._make_mock_slide("Executive Summary", ["회사 개요 텍스트"]),
        ]
        mock_prs_cls.return_value = self._make_mock_prs(slides)

        from src.quality_gate.pptx_gate import PPTXProgrammaticGate

        gate = PPTXProgrammaticGate()
        result = asyncio.run(
            gate.evaluate("fake.pptx", prd_section={"memo_type": "IM"})
        )

        assert isinstance(result, GateResult)
        assert result.weighted_score > 0
        assert result.gate_name == "pptx_programmatic"

    @patch("pptx.Presentation")
    def test_evaluate_placeholder_triggers_critical_flag(
        self, mock_prs_cls: MagicMock
    ) -> None:
        """플레이스홀더 텍스트 포함 → critical_flags 발생."""
        slides = [
            self._make_mock_slide("Cover"),
            self._make_mock_slide("Disclaimer"),
            self._make_mock_slide("Table of Contents"),
            self._make_mock_slide("Content", ["[INSERT HERE] company details"]),
        ]
        mock_prs_cls.return_value = self._make_mock_prs(slides)

        from src.quality_gate.pptx_gate import PPTXProgrammaticGate

        gate = PPTXProgrammaticGate()
        result = asyncio.run(
            gate.evaluate("fake.pptx", prd_section={"memo_type": "IM"})
        )

        assert len(result.critical_flags) > 0
        assert result.verdict == GateVerdict.FAIL

    @patch("pptx.Presentation")
    def test_evaluate_corrupt_pptx_returns_fail_with_critical_flag(
        self, mock_prs_cls: MagicMock
    ) -> None:
        """손상된 PPTX → FAIL + critical_flags (예외를 게이트 내부에서 처리)."""
        mock_prs_cls.side_effect = Exception("Cannot open corrupted file")

        from src.quality_gate.pptx_gate import PPTXProgrammaticGate

        gate = PPTXProgrammaticGate()
        result = asyncio.run(
            gate.evaluate("corrupt.pptx", prd_section={"memo_type": "IM"})
        )

        assert result.verdict == GateVerdict.FAIL
        assert len(result.critical_flags) > 0
        assert any("손상" in f for f in result.critical_flags)

    @patch("pptx.Presentation")
    def test_evaluate_empty_slides_lower_than_perfect(
        self, mock_prs_cls: MagicMock
    ) -> None:
        """빈 슬라이드 → 만점(5.0) 미만 + 구조 이슈 발생."""
        mock_prs_cls.return_value = self._make_mock_prs([])

        from src.quality_gate.pptx_gate import PPTXProgrammaticGate

        gate = PPTXProgrammaticGate()
        result = asyncio.run(
            gate.evaluate("empty.pptx", prd_section={"memo_type": "IM"})
        )

        assert result.weighted_score < 5.0
        # 필수 슬라이드 누락 + 슬라이드 수 부족 이슈 존재
        assert len(result.issues) > 0
        assert any("부족" in i or "누락" in i for i in result.issues)


# ---------------------------------------------------------------------------
# _run_im_quality_gate 통합 테스트
# ---------------------------------------------------------------------------
class TestRunImQualityGate:
    """generate_im.py의 _run_im_quality_gate 함수를 테스트."""

    def test_no_pptx_path_returns_fail(self) -> None:
        """pptx_path=None → FAIL."""
        from src.api.tasks.generate_im import _run_im_quality_gate

        result = _run_im_quality_gate(None, "test-doc-id")
        assert result["quality_status"] == "FAIL"
        assert "PPTX 파일 경로 없음" in result.get("quality_issues", [])

    @patch("pptx.Presentation")
    def test_gate_exception_returns_fail(self, mock_prs_cls: MagicMock) -> None:
        """게이트 실행 중 예외 → FAIL (fail-closed)."""
        mock_prs_cls.side_effect = Exception("File not found")

        from src.api.tasks.generate_im import _run_im_quality_gate

        result = _run_im_quality_gate("/nonexistent/path.pptx", "test-doc-id")
        assert result["quality_status"] == "FAIL"
        assert any("실패" in str(i) for i in result.get("quality_issues", []))

    def test_result_always_has_generation_profile(self) -> None:
        """결과에 항상 generation_profile과 supported_formats가 포함된다."""
        from src.api.tasks.generate_im import _run_im_quality_gate

        result = _run_im_quality_gate(None, "test-doc-id")
        assert result["generation_profile"] == "quality"
        assert result["supported_formats"] == ["pptx"]
