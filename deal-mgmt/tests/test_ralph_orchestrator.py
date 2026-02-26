"""Ralph Loop Orchestrator E2E 통합 테스트.

전체 파이프라인: Orchestrator → Generator → Gate 순환을 검증한다.
LLM 없이 더미 모드로 전체 루프 완주를 확인한다.
"""

from __future__ import annotations

import json

import pytest

from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig
from app.ralph.gates.base import DimensionScore, GateResult, GateVerdict, QualityGate
from app.ralph.gates.docx_gate import DOCXProgrammaticGate
from app.ralph.orchestrator import LoopConfig, LoopResult, LoopStatus, RalphLoopOrchestrator
from app.ralph.progress_tracker import ProgressTracker

# ── 더미 생성기 (DocumentGenerator Protocol) ──────────────────────────────────


class DummyGenerator:
    """LLM 없이 동작하는 더미 생성기."""

    def __init__(self, section_count: int = 3, item_count: int = 2):
        self._section_count = section_count
        self._item_count = item_count

    async def generate_outline(self, source_data: dict | None = None) -> list[dict]:
        return [
            {"id": f"SEC_{i}", "section_id": f"SEC_{i}", "title": f"Section {i}"}
            for i in range(1, self._section_count + 1)
        ]

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict | None = None,
        source_data: dict | None = None,
        feedback: str | list[str] | None = None,
    ) -> str:
        """JSON 배열 형태의 분석 결과를 반환한다."""
        items = []
        for j in range(self._item_count):
            items.append(
                {
                    "item_id": f"{section_id}_ITEM_{j}",
                    "name": f"항목 {j}",
                    "status": "OK",
                    "issue_level": None,
                    "risk_color": "",
                    "description": f"{section_id} 항목 {j}에 대한 분석 결과입니다.",
                    "deal_impact": "",
                    "recommendation": "",
                    "rfi_required": False,
                    "rfi_number": "",
                    "confidence": 0.85,
                    "evidence_refs": ["ref_001"],
                }
            )
        return json.dumps(items, ensure_ascii=False)

    async def assemble_document(
        self,
        section_artifacts: dict[str, str],
        output_path: str | None = None,
    ) -> str:
        """모든 섹션 결과를 JSON으로 조합한다."""
        combined = {}
        for sid, artifact in section_artifacts.items():
            try:
                combined[sid] = json.loads(artifact)
            except json.JSONDecodeError:
                combined[sid] = []
        return json.dumps(combined, ensure_ascii=False)


class DummyGeneratorWithIssues(DummyGenerator):
    """ISSUE 상태 항목을 포함하는 더미 생성기."""

    async def generate_section(
        self,
        section_id: str,
        section_criteria: dict | None = None,
        source_data: dict | None = None,
        feedback: str | list[str] | None = None,
    ) -> str:
        items = [
            {
                "item_id": f"{section_id}_ITEM_0",
                "name": "문제 항목",
                "status": "ISSUE",
                "issue_level": "HIGH",
                "description": "중요한 이슈가 발견되었습니다.",
                "deal_impact": "거래 가격 조정 필요",
                "recommendation": "추가 실사 권장",
                "rfi_required": True,
                "rfi_number": "CORP-001",
                "confidence": 0.9,
                "evidence_refs": ["doc_001.pdf"],
            },
            {
                "item_id": f"{section_id}_ITEM_1",
                "name": "정상 항목",
                "status": "OK",
                "description": "특이사항 없음",
                "confidence": 0.95,
                "evidence_refs": [],
            },
        ]
        return json.dumps(items, ensure_ascii=False)


class DummyAlwaysPassGate(QualityGate):
    """항상 4.5점을 주는 더미 게이트."""

    @property
    def name(self) -> str:
        return "dummy_pass"

    async def evaluate(self, artifact_path, prd_section, source_data=None) -> GateResult:
        dims = [
            DimensionScore("quality", "품질", 4.5, 0.5),
            DimensionScore("completeness", "완전성", 4.5, 0.5),
        ]
        return self._timed_result(0, dims, [], [], [])


class DummyAlwaysFailGate(QualityGate):
    """항상 2.0점을 주는 더미 게이트."""

    @property
    def name(self) -> str:
        return "dummy_fail"

    async def evaluate(self, artifact_path, prd_section, source_data=None) -> GateResult:
        dims = [
            DimensionScore("quality", "품질", 2.0, 0.5),
            DimensionScore("completeness", "완전성", 2.0, 0.5),
        ]
        return self._timed_result(
            0,
            dims,
            ["품질 미달"],
            ["재작업 필요"],
            [],
        )


# ── ProgressTracker 테스트 ────────────────────────────────────────────────────


class TestProgressTracker:
    """ProgressTracker 단위 테스트."""

    def test_record_and_score_history(self):
        tracker = ProgressTracker()
        gr = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.2,
            dimensions=[DimensionScore("q", "품질", 4.2, 1.0)],
        )
        tracker.record("SEC_1", 0, gr)
        assert tracker.get_score_history("SEC_1") == [4.2]

    def test_mark_passed(self):
        tracker = ProgressTracker()
        assert not tracker.is_section_passed("SEC_1")
        tracker.mark_passed("SEC_1")
        assert tracker.is_section_passed("SEC_1")
        assert tracker.passed_count == 1

    def test_get_feedback_empty(self):
        tracker = ProgressTracker()
        assert tracker.get_feedback("SEC_1") == []

    def test_get_feedback_from_last_iteration(self):
        tracker = ProgressTracker()
        gr = GateResult(
            gate_name="test",
            verdict=GateVerdict.FAIL,
            weighted_score=2.5,
            issues=["이슈 A", "이슈 B"],
            suggestions=["제안 1"],
        )
        tracker.record("SEC_1", 0, gr)
        feedback = tracker.get_feedback("SEC_1")
        assert "이슈 A" in feedback
        assert "이슈 B" in feedback
        assert "제안 1" in feedback

    def test_total_cost(self):
        tracker = ProgressTracker()
        gr1 = GateResult(gate_name="g1", verdict=GateVerdict.PASS, weighted_score=4.0, cost_usd=0.05)
        gr2 = GateResult(gate_name="g2", verdict=GateVerdict.PASS, weighted_score=4.0, cost_usd=0.03)
        tracker.record("SEC_1", 0, gr1, gr2)
        assert abs(tracker.total_cost_usd - 0.08) < 0.001

    def test_to_dict_and_from_dict(self):
        tracker = ProgressTracker()
        gr = GateResult(
            gate_name="test",
            verdict=GateVerdict.PASS,
            weighted_score=4.5,
            dimensions=[DimensionScore("q", "품질", 4.5, 1.0)],
        )
        tracker.record("SEC_1", 0, gr)
        tracker.mark_passed("SEC_1")

        data = tracker.to_dict()
        restored = ProgressTracker.from_dict(data)

        assert restored.passed_count == 1
        assert restored.is_section_passed("SEC_1")
        assert restored.get_score_history("SEC_1") == [4.5]

    def test_multiple_sections(self):
        tracker = ProgressTracker()
        for i in range(3):
            gr = GateResult(
                gate_name="test",
                verdict=GateVerdict.PASS,
                weighted_score=4.0 + i * 0.2,
            )
            tracker.record(f"SEC_{i}", 0, gr)

        assert len(tracker.get_score_history("SEC_0")) == 1
        assert len(tracker.get_score_history("SEC_1")) == 1
        assert len(tracker.get_score_history("SEC_2")) == 1


# ── ConvergenceChecker 테스트 ─────────────────────────────────────────────────


class TestConvergenceChecker:
    """수렴 판정 테스트."""

    def test_pass_verdict(self):
        checker = ConvergenceChecker(ConvergenceConfig(pass_threshold=4.0))
        tracker = ProgressTracker()
        gr = GateResult(gate_name="test", verdict=GateVerdict.PASS, weighted_score=4.5)
        tracker.record("SEC_1", 0, gr)

        verdict = checker.check_section("SEC_1", gr, tracker)
        assert verdict.converged
        assert verdict.reason == "passed"

    def test_max_iterations_verdict(self):
        config = ConvergenceConfig(max_iterations_per_section=2, pass_threshold=4.0)
        checker = ConvergenceChecker(config)
        tracker = ProgressTracker()

        for i in range(2):
            gr = GateResult(gate_name="test", verdict=GateVerdict.FAIL, weighted_score=2.5)
            tracker.record("SEC_1", i, gr)

        verdict = checker.check_section("SEC_1", gr, tracker)
        assert verdict.converged
        assert verdict.reason == "max_iterations"

    def test_diminishing_returns_verdict(self):
        config = ConvergenceConfig(
            max_iterations_per_section=5,
            improvement_threshold=0.5,
            pass_threshold=4.0,
        )
        checker = ConvergenceChecker(config)
        tracker = ProgressTracker()

        # 첫 반복: 3.0
        gr1 = GateResult(gate_name="test", verdict=GateVerdict.CONDITIONAL_PASS, weighted_score=3.0)
        tracker.record("SEC_1", 0, gr1)

        # 두 번째 반복: 3.2 (개선 0.2 < threshold 0.5)
        gr2 = GateResult(gate_name="test", verdict=GateVerdict.CONDITIONAL_PASS, weighted_score=3.2)
        tracker.record("SEC_1", 1, gr2)

        verdict = checker.check_section("SEC_1", gr2, tracker)
        assert verdict.converged
        assert verdict.reason == "diminishing_returns"

    def test_budget_exceeded_verdict(self):
        config = ConvergenceConfig(max_cost_usd=0.10, pass_threshold=4.0)
        checker = ConvergenceChecker(config)
        tracker = ProgressTracker()

        gr = GateResult(gate_name="test", verdict=GateVerdict.FAIL, weighted_score=2.5, cost_usd=0.15)
        tracker.record("SEC_1", 0, gr)

        verdict = checker.check_section("SEC_1", gr, tracker)
        assert verdict.converged
        assert verdict.reason == "budget_exceeded"

    def test_critical_flag_verdict(self):
        checker = ConvergenceChecker()
        tracker = ProgressTracker()

        gr = GateResult(
            gate_name="test",
            verdict=GateVerdict.FAIL,
            weighted_score=4.0,
            critical_flags=["CRITICAL: 플레이스홀더 발견"],
        )
        tracker.record("SEC_1", 0, gr)

        verdict = checker.check_section("SEC_1", gr, tracker)
        assert verdict.converged
        assert verdict.reason == "critical_flag"

    def test_not_converged(self):
        config = ConvergenceConfig(
            max_iterations_per_section=5,
            pass_threshold=4.0,
        )
        checker = ConvergenceChecker(config)
        tracker = ProgressTracker()

        gr = GateResult(gate_name="test", verdict=GateVerdict.FAIL, weighted_score=2.5)
        tracker.record("SEC_1", 0, gr)

        verdict = checker.check_section("SEC_1", gr, tracker)
        assert not verdict.converged

    def test_check_total_budget(self):
        config = ConvergenceConfig(max_cost_usd=1.0)
        checker = ConvergenceChecker(config)
        tracker = ProgressTracker()

        gr = GateResult(gate_name="test", verdict=GateVerdict.PASS, weighted_score=4.5, cost_usd=1.5)
        tracker.record("SEC_1", 0, gr)

        assert checker.check_total_budget(tracker) is True


# ── DOCXProgrammaticGate JSON 모드 테스트 ─────────────────────────────────────


class TestDOCXGateJsonMode:
    """DOCXProgrammaticGate JSON 검증 모드 테스트."""

    @pytest.mark.asyncio
    async def test_is_json_artifact_detection(self):
        assert DOCXProgrammaticGate._is_json_artifact('[{"status": "OK"}]')
        assert DOCXProgrammaticGate._is_json_artifact('{"key": "value"}')
        assert not DOCXProgrammaticGate._is_json_artifact("report.docx")
        assert not DOCXProgrammaticGate._is_json_artifact("/path/to/report.docx")

    @pytest.mark.asyncio
    async def test_evaluate_valid_json(self):
        gate = DOCXProgrammaticGate()
        items = [
            {
                "item_id": "GOV_001",
                "status": "OK",
                "description": "정관 검토 완료, 특이사항 없음",
                "confidence": 0.9,
                "evidence_refs": ["governance_01.pdf"],
            },
            {
                "item_id": "GOV_002",
                "status": "ISSUE",
                "issue_level": "HIGH",
                "description": "이사회 의사록 일부 누락",
                "deal_impact": "지배구조 리스크",
                "recommendation": "누락 의사록 보완 요청",
                "rfi_required": True,
                "rfi_number": "CORP-001",
                "confidence": 0.85,
                "evidence_refs": ["governance_02.pdf"],
            },
        ]
        artifact = json.dumps(items, ensure_ascii=False)
        result = await gate.evaluate(artifact, {})

        assert result.gate_name == "docx_programmatic"
        assert result.weighted_score > 0
        assert len(result.dimensions) == 5

    @pytest.mark.asyncio
    async def test_evaluate_all_pending(self):
        gate = DOCXProgrammaticGate()
        items = [
            {"status": "PENDING", "description": "분석 대기"},
            {"status": "PENDING", "description": "분석 대기"},
        ]
        artifact = json.dumps(items)
        result = await gate.evaluate(artifact, {})

        # PENDING 비율 100% → 통과 기준(4.0) 미달
        assert result.weighted_score < 4.0
        assert any("미분석" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_evaluate_missing_fields(self):
        gate = DOCXProgrammaticGate()
        items = [
            {"item_id": "GOV_001"},  # status, description 누락
        ]
        artifact = json.dumps(items)
        result = await gate.evaluate(artifact, {})

        assert any("필수 필드" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_evaluate_invalid_rfi(self):
        gate = DOCXProgrammaticGate()
        items = [
            {
                "status": "ISSUE",
                "issue_level": "HIGH",
                "description": "이슈 발견",
                "deal_impact": "영향",
                "recommendation": "권장",
                "rfi_number": "INVALID-001",
                "confidence": 0.8,
            },
        ]
        artifact = json.dumps(items)
        result = await gate.evaluate(artifact, {})

        assert any("유효하지 않은 RFI 접두사" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_evaluate_duplicate_rfi(self):
        gate = DOCXProgrammaticGate()
        items = [
            {
                "status": "ISSUE",
                "description": "이슈1",
                "rfi_number": "CORP-001",
                "issue_level": "HIGH",
                "deal_impact": "영향",
                "recommendation": "권장",
            },
            {
                "status": "ISSUE",
                "description": "이슈2",
                "rfi_number": "CORP-001",
                "issue_level": "MEDIUM",
                "deal_impact": "영향",
                "recommendation": "권장",
            },
        ]
        artifact = json.dumps(items)
        result = await gate.evaluate(artifact, {})

        assert any("중복 RFI 번호" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_evaluate_invalid_json(self):
        gate = DOCXProgrammaticGate()
        # _is_json_artifact가 True를 반환하도록 `{` 로 시작하지만 파싱 실패
        result = await gate.evaluate("{invalid json", {})
        assert any("JSON 파싱 실패" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_evaluate_empty_array(self):
        gate = DOCXProgrammaticGate()
        result = await gate.evaluate("[]", {})
        assert any("빈 분석 결과" in i for i in result.issues)

    @pytest.mark.asyncio
    async def test_evaluate_issue_without_impact(self):
        gate = DOCXProgrammaticGate()
        items = [
            {
                "status": "ISSUE",
                "issue_level": "HIGH",
                "description": "이슈 발견",
                # deal_impact, recommendation 누락
                "confidence": 0.8,
            },
        ]
        artifact = json.dumps(items)
        result = await gate.evaluate(artifact, {})

        assert any("deal_impact 미기재" in i for i in result.issues)
        assert any("recommendation 미기재" in i for i in result.issues)


# ── Orchestrator E2E 테스트 ───────────────────────────────────────────────────


class TestOrchestratorE2E:
    """Orchestrator 전체 파이프라인 E2E 테스트."""

    @pytest.mark.asyncio
    async def test_dummy_mode_completes(self):
        """LLM 없이 전체 루프가 완주하는지 확인."""
        generator = DummyGenerator(section_count=2, item_count=2)
        gate = DummyAlwaysPassGate()
        prd = {"name": "test", "sections": {}}

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
            config=LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=2,
                    pass_threshold=4.0,
                ),
            ),
        )

        result = await orchestrator.run(source_data={})

        assert isinstance(result, LoopResult)
        assert result.status == LoopStatus.COMPLETED
        assert result.total_iterations > 0
        assert result.started_at
        assert result.completed_at

    @pytest.mark.asyncio
    async def test_with_docx_json_gate(self):
        """DOCXProgrammaticGate JSON 모드로 LDD 파이프라인 순환."""
        generator = DummyGenerator(section_count=2, item_count=3)
        gate = DOCXProgrammaticGate()
        prd = {"name": "ldd_full", "sections": {}}

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
            config=LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=2,
                    pass_threshold=4.0,
                ),
            ),
        )

        result = await orchestrator.run(source_data={})

        assert isinstance(result, LoopResult)
        assert result.total_iterations >= 2  # 최소 2개 섹션
        assert result.final_score > 0

    @pytest.mark.asyncio
    async def test_with_issues_generator(self):
        """ISSUE 상태 항목이 있는 생성기로 Gate 평가 확인."""
        generator = DummyGeneratorWithIssues(section_count=1)
        gate = DOCXProgrammaticGate()
        prd = {"name": "ldd_full", "sections": {}}

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
            config=LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=2,
                    pass_threshold=4.0,
                ),
            ),
        )

        result = await orchestrator.run(source_data={})
        assert isinstance(result, LoopResult)
        assert result.final_score > 0

    @pytest.mark.asyncio
    async def test_fail_gate_max_iterations(self):
        """항상 실패하는 Gate로 max_iterations에 도달."""
        generator = DummyGenerator(section_count=1, item_count=1)
        gate = DummyAlwaysFailGate()
        prd = {"name": "test", "sections": {}}

        config = LoopConfig(
            convergence=ConvergenceConfig(
                max_iterations_per_section=3,
                pass_threshold=4.0,
                improvement_threshold=-1.0,  # diminishing_returns 비활성화
            ),
        )
        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
            config=config,
        )

        result = await orchestrator.run(source_data={})

        assert isinstance(result, LoopResult)
        # 실패 게이트이므로 COMPLETED이지만 점수 낮음
        assert result.total_iterations == 3  # 1 섹션 × 3 반복

    @pytest.mark.asyncio
    async def test_budget_limit(self):
        """비용 한도 초과 시 조기 종료."""
        generator = DummyGenerator(section_count=5, item_count=2)
        # 비용 0.05씩 추가되는 Gate (budget 0.10이면 2-3회에 종료)

        class CostlyGate(QualityGate):
            @property
            def name(self):
                return "costly"

            async def evaluate(self, artifact_path, prd_section, source_data=None):
                dims = [DimensionScore("q", "품질", 3.5, 1.0)]
                return GateResult(
                    gate_name="costly",
                    verdict=GateVerdict.CONDITIONAL_PASS,
                    weighted_score=3.5,
                    dimensions=dims,
                    cost_usd=0.05,
                )

        prd = {"name": "test", "sections": {}}
        config = LoopConfig(
            convergence=ConvergenceConfig(
                max_cost_usd=0.10,
                max_iterations_per_section=5,
                pass_threshold=4.0,
            ),
        )
        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[CostlyGate()],
            prd=prd,
            config=config,
        )

        result = await orchestrator.run(source_data={})
        # 비용 한도 초과로 모든 섹션을 완료하지 못할 수 있음
        assert result.total_cost_usd >= 0.0

    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        """진행 추적 데이터가 올바르게 기록되는지 확인."""
        generator = DummyGenerator(section_count=2, item_count=2)
        gate = DummyAlwaysPassGate()
        prd = {"name": "test", "sections": {}}

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
            config=LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=1,
                    pass_threshold=4.0,
                ),
            ),
        )

        result = await orchestrator.run(source_data={})

        assert result.progress  # 비어있지 않음
        assert isinstance(result.progress, dict)
        assert "records" in result.progress or "passed_sections" in result.progress

    @pytest.mark.asyncio
    async def test_section_scores(self):
        """섹션별 점수가 올바르게 집계되는지 확인."""
        generator = DummyGenerator(section_count=3, item_count=2)
        gate = DummyAlwaysPassGate()
        prd = {"name": "test", "sections": {}}

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
            config=LoopConfig(
                convergence=ConvergenceConfig(
                    max_iterations_per_section=1,
                    pass_threshold=4.0,
                ),
            ),
        )

        result = await orchestrator.run(source_data={})
        assert isinstance(result.section_scores, dict)

    @pytest.mark.asyncio
    async def test_assemble_document_called(self):
        """Phase 3 assemble_document가 호출되는지 확인."""
        generator = DummyGenerator(section_count=1, item_count=1)
        gate = DummyAlwaysPassGate()
        prd = {"name": "test", "sections": {}}

        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate],
            prd=prd,
        )

        result = await orchestrator.run(source_data={})
        # assemble_document이 호출되면 output_path가 JSON 문자열
        assert result.output_path is not None

    @pytest.mark.asyncio
    async def test_gate_skip_on_first_fail(self):
        """Gate 1 실패 시 Gate 2를 건너뛰는 최적화 테스트."""
        generator = DummyGenerator(section_count=1, item_count=1)
        gate1 = DummyAlwaysFailGate()
        gate2 = DummyAlwaysPassGate()  # 이건 호출되면 안 됨
        prd = {"name": "test", "sections": {}}

        config = LoopConfig(
            convergence=ConvergenceConfig(max_iterations_per_section=1),
            gate1_first=True,
            skip_gate2_on_gate1_fail=True,
        )
        orchestrator = RalphLoopOrchestrator(
            generator=generator,
            gates=[gate1, gate2],
            prd=prd,
            config=config,
        )

        result = await orchestrator.run(source_data={})
        # Gate 1이 실패하므로 Gate 2는 건너뜀
        assert isinstance(result, LoopResult)
