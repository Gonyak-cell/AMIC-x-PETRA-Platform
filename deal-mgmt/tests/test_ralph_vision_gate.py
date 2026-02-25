"""Vision Gate 단위 테스트.

VisionGate 폴백 평가, 응답 파싱, 결과 빌드를 검증한다.
LibreOffice/PyMuPDF 없이 동작하는 단위 테스트.
"""

import time

import pytest

from app.ralph.gates.base import DimensionScore, GateResult, GateVerdict
from app.ralph.gates.vision_gate import VISION_WEIGHTS, VisionGate


# ── VisionGate 기본 ──────────────────────────────────────────────────────────


class TestVisionGateBasics:
    def test_name(self):
        gate = VisionGate()
        assert gate.name == "vision"

    def test_weights_sum_to_one(self):
        total = sum(w for w, _ in VISION_WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_all_dimensions_present(self):
        expected = {"layout_balance", "color_harmony", "typography", "data_viz", "professionalism"}
        assert set(VISION_WEIGHTS.keys()) == expected


# ── Fallback 평가 ────────────────────────────────────────────────────────────


class TestVisionGateFallback:
    @pytest.mark.asyncio
    async def test_non_pptx_returns_issues(self):
        """PPTX가 아닌 파일은 이슈와 함께 반환."""
        gate = VisionGate(openai_api_key="test")
        result = await gate.evaluate("report.docx", {})
        assert isinstance(result, GateResult)
        assert result.gate_name == "vision"
        assert any("PPTX" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_no_api_key_uses_fallback(self):
        """API 키가 없으면 규칙 기반 fallback 평가."""
        gate = VisionGate(openai_api_key="")
        result = await gate.evaluate("test.pptx", {})
        assert result.gate_name == "vision"
        assert len(result.dimensions) == 5
        # fallback은 모든 차원에 3.0점
        for dim in result.dimensions:
            assert dim.score == 3.0
        assert any("fallback" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_fallback_weighted_score(self):
        """fallback의 가중 합산 점수 = 3.0 (모든 차원 3.0 × 가중치 합 1.0)."""
        gate = VisionGate()
        result = await gate.evaluate("test.pptx", {})
        assert result.weighted_score == pytest.approx(3.0)
        assert result.verdict == GateVerdict.CONDITIONAL_PASS


# ── 응답 파싱 ────────────────────────────────────────────────────────────────


class TestVisionResponseParsing:
    def _gate(self):
        return VisionGate(openai_api_key="test")

    def test_parse_json_block(self):
        """```json ... ``` 형식 파싱."""
        response = '''Some text
```json
{
  "dimensions": [
    {"name": "layout_balance", "score": 4, "feedback": "Good layout"},
    {"name": "typography", "score": 3, "feedback": "Okay type"}
  ],
  "overall_feedback": "Nice work"
}
```
More text'''
        result = self._gate()._parse_vision_response(response)
        assert len(result["dimensions"]) == 2
        assert result["dimensions"][0]["score"] == 4
        assert result["overall_feedback"] == "Nice work"

    def test_parse_plain_code_block(self):
        """``` ... ``` (언어 태그 없는) 형식 파싱."""
        response = '''```
{"dimensions": [], "overall_feedback": "test"}
```'''
        result = self._gate()._parse_vision_response(response)
        assert result["overall_feedback"] == "test"

    def test_parse_invalid_json(self):
        """잘못된 JSON은 빈 dimensions로 반환."""
        response = "This is not JSON at all"
        result = self._gate()._parse_vision_response(response)
        assert result["dimensions"] == []
        assert "This is not JSON" in result["overall_feedback"]

    def test_parse_truncates_long_feedback(self):
        """200자 초과 피드백은 잘린다."""
        response = "A" * 300
        result = self._gate()._parse_vision_response(response)
        assert len(result["overall_feedback"]) == 200


# ── 결과 빌드 ────────────────────────────────────────────────────────────────


class TestVisionBuildResult:
    def _gate(self):
        return VisionGate(openai_api_key="test")

    def test_build_result_all_dimensions(self):
        data = {
            "dimensions": [
                {"name": "layout_balance", "score": 4.5, "feedback": "Excellent"},
                {"name": "color_harmony", "score": 4.0, "feedback": "Good"},
                {"name": "typography", "score": 3.5, "feedback": "OK"},
                {"name": "data_viz", "score": 4.0, "feedback": "Good"},
                {"name": "professionalism", "score": 4.5, "feedback": "IB level"},
            ],
            "overall_feedback": "Great presentation",
        }
        start = time.perf_counter_ns()
        result = self._gate()._build_result(start, data)

        assert result.gate_name == "vision"
        assert len(result.dimensions) == 5
        # 가중 합산: 4.5*0.25 + 4.0*0.15 + 3.5*0.20 + 4.0*0.20 + 4.5*0.20
        expected = 4.5 * 0.25 + 4.0 * 0.15 + 3.5 * 0.20 + 4.0 * 0.20 + 4.5 * 0.20
        assert result.weighted_score == pytest.approx(expected, abs=0.01)
        assert result.verdict == GateVerdict.PASS

    def test_build_result_low_scores_fail(self):
        data = {
            "dimensions": [
                {"name": "layout_balance", "score": 2, "feedback": "Poor layout"},
                {"name": "color_harmony", "score": 2, "feedback": "Bad colors"},
                {"name": "typography", "score": 2, "feedback": "Hard to read"},
                {"name": "data_viz", "score": 2, "feedback": "Confusing"},
                {"name": "professionalism", "score": 2, "feedback": "Unprofessional"},
            ],
            "overall_feedback": "Needs work",
        }
        start = time.perf_counter_ns()
        result = self._gate()._build_result(start, data)

        assert result.weighted_score == pytest.approx(2.0)
        assert result.verdict == GateVerdict.FAIL
        # 모든 차원이 3점 미만이므로 issues에 피드백 포함
        assert len(result.issues) == 5

    def test_build_result_ignores_unknown_dimensions(self):
        """VISION_WEIGHTS에 없는 차원은 무시."""
        data = {
            "dimensions": [
                {"name": "unknown_dim", "score": 5, "feedback": "?"},
                {"name": "layout_balance", "score": 4, "feedback": "OK"},
            ],
            "overall_feedback": "",
        }
        start = time.perf_counter_ns()
        result = self._gate()._build_result(start, data)
        assert len(result.dimensions) == 1
        assert result.dimensions[0].name == "layout_balance"

    def test_build_result_empty_dimensions(self):
        data = {"dimensions": [], "overall_feedback": "No data"}
        start = time.perf_counter_ns()
        result = self._gate()._build_result(start, data)
        assert result.weighted_score == 0.0
        assert result.verdict == GateVerdict.FAIL


# ── QualityGate 기본 메서드 ──────────────────────────────────────────────────


class TestQualityGateHelpers:
    """QualityGate ABC의 헬퍼 메서드를 VisionGate를 통해 테스트."""

    def _gate(self):
        return VisionGate()

    def test_compute_weighted_score_empty(self):
        assert self._gate()._compute_weighted_score([]) == 0.0

    def test_compute_weighted_score(self):
        dims = [
            DimensionScore("a", "A", 4.0, 0.5),
            DimensionScore("b", "B", 2.0, 0.5),
        ]
        assert self._gate()._compute_weighted_score(dims) == pytest.approx(3.0)

    def test_determine_verdict_pass(self):
        assert self._gate()._determine_verdict(4.5, []) == GateVerdict.PASS

    def test_determine_verdict_conditional(self):
        assert self._gate()._determine_verdict(3.5, []) == GateVerdict.CONDITIONAL_PASS

    def test_determine_verdict_fail_low_score(self):
        assert self._gate()._determine_verdict(2.5, []) == GateVerdict.FAIL

    def test_determine_verdict_fail_critical(self):
        """점수 높아도 Critical Flag 있으면 FAIL."""
        assert self._gate()._determine_verdict(4.5, ["critical issue"]) == GateVerdict.FAIL
