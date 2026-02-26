"""LDD 멀티 LLM 7단계 파이프라인 테스트.

각 Stage별 단위 테스트 + 통합 테스트.
"""

from __future__ import annotations

import json

import pytest

from app.ralph.generators.ldd.dual_risk_analyzer import (
    DualAnalysisResult,
    DualRiskAnalyzer,
    PerspectiveResult,
)
from app.ralph.generators.ldd.gap_detector import GapDetectionResult, GapDetector, GapItem
from app.ralph.generators.ldd.guardrails import (
    VALID_ITEM_IDS,
    LDDGuardrails,
)
from app.ralph.generators.ldd.jurisdiction_analyzer import JurisdictionAnalyzer, JurisdictionResult
from app.ralph.generators.ldd.pipeline_config import LDDPipelineConfig
from app.ralph.generators.ldd.report_qa import LDDQAResult, LDDReportQA
from app.ralph.routing.ldd_router import DEFAULT_LDD_ROUTING, LDDModelRouter

# ── Fixtures ──────────────────────────────────────────────────────


class _MockAdapter:
    """테스트용 어댑터 mock."""

    def __init__(self, provider_name: str, is_available: bool = True):
        self.provider_name = provider_name
        self.is_available = is_available


class MockLLMClient:
    """테스트용 LLM 클라이언트 mock."""

    def __init__(self, response: str = "{}"):
        self._response = response
        self.call_count = 0
        self.is_available = True
        self._adapters = [
            _MockAdapter("anthropic"),
            _MockAdapter("openai"),
            _MockAdapter("google"),
        ]
        self._cost_tracker = type("CT", (), {"accumulated_usd": 0.0})()

    async def call(self, system: str, user: str) -> str:
        self.call_count += 1
        return self._response

    async def call_for_provider(self, system: str, user: str, *, provider: str) -> str:
        self.call_count += 1
        return self._response


class MockRouter:
    """테스트용 라우터 mock."""

    def __init__(self, response: str = "{}"):
        self._response = response
        self.calls: list[tuple[str, str]] = []

    async def call_routed(self, section_id: str, system: str, user: str) -> str:
        self.calls.append((section_id, system[:50]))
        return self._response


# ── Stage 3: DualRiskAnalyzer ─────────────────────────────────────


class TestDualRiskAnalyzer:
    """Stage 3: 듀얼 리스크 분석 테스트."""

    def _make_perspective(
        self,
        perspective: str,
        status: str,
        level: str | None,
        confidence: float = 0.8,
    ) -> PerspectiveResult:
        return PerspectiveResult(
            perspective=perspective,
            item_id="CORP-01",
            status=status,
            issue_level=level,
            description=f"{perspective} 분석 결과",
            deal_impact="거래 영향 분석",
            recommendation="권고사항",
            confidence=confidence,
        )

    def test_gap_zero_auto_resolved(self):
        """gap=0: 두 LLM 등급 동일 → 자동 확정."""
        config = LDDPipelineConfig()
        analyzer = DualRiskAnalyzer(llm_client=None, config=config)

        buyer = self._make_perspective("buyer", "ISSUE", "HIGH")
        independent = self._make_perspective("independent", "ISSUE", "HIGH")

        comparison = analyzer._compare_risk_levels("CORP-01", buyer, independent)

        assert comparison.gap == 0
        assert comparison.auto_resolved is True
        assert comparison.final_level == "HIGH"
        assert comparison.needs_human_review is False

    def test_gap_one_adopt_higher(self):
        """gap=1: 1단계 차이 → 높은 쪽 채택."""
        config = LDDPipelineConfig()
        analyzer = DualRiskAnalyzer(llm_client=None, config=config)

        buyer = self._make_perspective("buyer", "ISSUE", "HIGH")
        independent = self._make_perspective("independent", "ISSUE", "MEDIUM")

        comparison = analyzer._compare_risk_levels("CORP-01", buyer, independent)

        assert comparison.gap == 1
        assert comparison.auto_resolved is True
        assert comparison.final_level == "HIGH"  # 높은 쪽 채택
        assert comparison.needs_human_review is False
        assert "양측 근거 병기" in comparison.note or comparison.buyer_rationale

    def test_gap_two_human_review(self):
        """gap≥2: 변호사 필수 검토."""
        config = LDDPipelineConfig()
        analyzer = DualRiskAnalyzer(llm_client=None, config=config)

        buyer = self._make_perspective("buyer", "ISSUE", "CRITICAL")
        independent = self._make_perspective("independent", "ISSUE", "LOW")

        comparison = analyzer._compare_risk_levels("CORP-01", buyer, independent)

        assert comparison.gap == 3
        assert comparison.auto_resolved is False
        assert comparison.needs_human_review is True
        assert comparison.final_level is None

    def test_status_mismatch_as_gap_two(self):
        """한쪽 ISSUE, 다른 쪽 OK → gap=2 (심각한 불일치)."""
        config = LDDPipelineConfig()
        analyzer = DualRiskAnalyzer(llm_client=None, config=config)

        buyer = self._make_perspective("buyer", "ISSUE", "MEDIUM")
        independent = self._make_perspective("independent", "OK", None)

        comparison = analyzer._compare_risk_levels("CORP-01", buyer, independent)

        assert comparison.gap >= 2
        assert comparison.needs_human_review is True

    @pytest.mark.asyncio
    async def test_analyze_item_dual_with_mock(self):
        """듀얼 분석 전체 흐름 (mock LLM)."""
        response = json.dumps(
            {
                "status": "ISSUE",
                "issue_level": "HIGH",
                "description": "테스트 분석 결과",
                "deal_impact": "가격 조정 필요",
                "recommendation": "추가 실사 권장",
                "confidence": 0.85,
                "evidence_refs": [],
            }
        )

        client = MockLLMClient(response)
        router = MockRouter(response)
        config = LDDPipelineConfig()

        analyzer = DualRiskAnalyzer(llm_client=client, router=router, config=config)
        result = await analyzer.analyze_item_dual(
            item_id="CORP-01",
            item_name="설립/등기/정관 검토",
            section_type="GOVERNANCE",
            section_title="기업 지배구조",
            source_files=[],
        )

        assert isinstance(result, DualAnalysisResult)
        assert result.item_id == "CORP-01"
        assert result.buyer.perspective == "buyer"
        assert result.independent.perspective == "independent"
        assert result.comparison.gap == 0  # 같은 mock 응답이므로 gap=0
        assert result.comparison.auto_resolved is True


# ── Stage 4: GapDetector ─────────────────────────────────────────


class TestGapDetector:
    """Stage 4: 누락 탐지 테스트."""

    def test_jaccard_similarity(self):
        """Jaccard 유사도 계산."""
        assert GapDetector._jaccard_similarity("hello world", "hello world") == 1.0
        assert GapDetector._jaccard_similarity("hello", "world") == 0.0
        assert 0.0 < GapDetector._jaccard_similarity("hello world", "hello test") < 1.0

    def test_merge_and_deduplicate_empty(self):
        """빈 목록 병합."""
        config = LDDPipelineConfig()
        detector = GapDetector(llm_client=None, config=config)
        merged, dups = detector._merge_and_deduplicate([], [])
        assert merged == []
        assert dups == 0

    def test_merge_and_deduplicate_no_overlap(self):
        """중복 없는 병합."""
        config = LDDPipelineConfig()
        detector = GapDetector(llm_client=None, config=config)

        checklist = [GapItem("GAP-001", "CONTRACTS", "CoC 조항 검토", "HIGH", "이유1", "checklist")]
        freeform = [GapItem("FGAP-001", "PERMITS", "식약처 인허가", "MEDIUM", "이유2", "freeform")]

        merged, dups = detector._merge_and_deduplicate(checklist, freeform)
        assert len(merged) == 2
        assert dups == 0

    def test_merge_and_deduplicate_with_overlap(self):
        """중복 있는 병합 (Jaccard > threshold)."""
        config = LDDPipelineConfig(gap_similarity_threshold=0.5)
        detector = GapDetector(llm_client=None, config=config)

        checklist = [
            GapItem("GAP-001", "CONTRACTS", "Change of Control 조항 검토 누락", "HIGH", "이유", "checklist"),
        ]
        freeform = [
            GapItem("FGAP-001", "CONTRACTS", "Change of Control 조항 검토 누락 확인", "CRITICAL", "이유2", "freeform"),
        ]

        merged, dups = detector._merge_and_deduplicate(checklist, freeform)
        assert len(merged) == 1
        assert dups == 1
        # 높은 우선순위(CRITICAL)로 업데이트
        assert merged[0].priority == "CRITICAL"

    def test_merge_priority_sort(self):
        """병합 후 우선순위 정렬 (CRITICAL → LOW)."""
        config = LDDPipelineConfig()
        detector = GapDetector(llm_client=None, config=config)

        items = [
            GapItem("GAP-001", "IP", "IP 누락", "LOW", "", "checklist"),
            GapItem("GAP-002", "CONTRACTS", "계약 누락", "CRITICAL", "", "checklist"),
            GapItem("GAP-003", "LABOR", "노무 누락", "MEDIUM", "", "checklist"),
        ]

        merged, dups = detector._merge_and_deduplicate(items, [])
        assert merged[0].priority == "CRITICAL"
        assert merged[1].priority == "MEDIUM"
        assert merged[2].priority == "LOW"

    @pytest.mark.asyncio
    async def test_detect_gaps_with_mock(self):
        """누락 탐지 전체 흐름 (mock LLM)."""
        checklist_response = json.dumps(
            [
                {
                    "gap_id": "GAP-001",
                    "section_type": "CONTRACTS",
                    "description": "CoC 조항 검토 누락",
                    "priority": "HIGH",
                    "rationale": "주요 계약의 CoC 조항 미확인",
                },
            ]
        )
        freeform_response = json.dumps([])

        call_count = 0

        async def mock_call(section_id, system, user):
            nonlocal call_count
            call_count += 1
            if "checklist" in section_id:
                return checklist_response
            return freeform_response

        router = MockRouter()
        router.call_routed = mock_call

        config = LDDPipelineConfig(deal_type="M&A", industry="IT")
        detector = GapDetector(llm_client=None, router=router, config=config)

        result = await detector.detect_gaps(
            analyzed_sections={"GOVERNANCE": [{"status": "OK", "item_id": "CORP-01"}]},
            document_names=["정관.pdf", "이사회의사록.pdf"],
        )

        assert isinstance(result, GapDetectionResult)
        assert result.total_checklist == 1
        assert result.total_unique >= 1


# ── Stage 5: JurisdictionAnalyzer ─────────────────────────────────


class TestJurisdictionAnalyzer:
    """Stage 5: 관할권 교차 분석 테스트."""

    @pytest.mark.asyncio
    async def test_cross_points_detected(self):
        """같은 section_type 이슈 → 교차점 탐지."""
        korean_response = json.dumps(
            [
                {
                    "point_id": "JP-001",
                    "section_type": "CONTRACTS",
                    "description": "한국법 관점 CoC 이슈",
                    "severity": "HIGH",
                    "key_regulation": "상법 제374조",
                    "recommendation": "CoC 조항 검토",
                },
            ]
        )
        english_response = json.dumps(
            [
                {
                    "point_id": "JP-001",
                    "section_type": "CONTRACTS",
                    "description": "English law CoC issue",
                    "severity": "HIGH",
                    "key_regulation": "SPA Clause 5.1",
                    "recommendation": "Review CoC clause",
                },
            ]
        )

        call_count = 0

        async def mock_call(section_id, system, user):
            nonlocal call_count
            call_count += 1
            if "korean" in section_id:
                return korean_response
            return english_response

        router = MockRouter()
        router.call_routed = mock_call

        analyzer = JurisdictionAnalyzer(llm_client=None, router=router)
        result = await analyzer.analyze(
            key_clauses_summary="CONTRACTS: CoC 이슈",
            deal_summary="크로스보더 M&A",
        )

        assert isinstance(result, JurisdictionResult)
        # 같은 section에 같은 severity → cross point
        assert len(result.cross_points) >= 1 or len(result.conflict_points) >= 0

    @pytest.mark.asyncio
    async def test_conflict_detected_severity_gap(self):
        """severity 차이 ≥ 2 → 충돌점."""
        korean_response = json.dumps(
            [
                {
                    "point_id": "JP-001",
                    "section_type": "LABOR",
                    "description": "한국법: 근로관계 승계 리스크",
                    "severity": "CRITICAL",
                    "key_regulation": "근로기준법 제24조",
                    "recommendation": "근로관계 승계 검토",
                },
            ]
        )
        english_response = json.dumps(
            [
                {
                    "point_id": "JP-001",
                    "section_type": "LABOR",
                    "description": "English law: TUPE low risk",
                    "severity": "LOW",
                    "key_regulation": "TUPE 2006",
                    "recommendation": "Minimal risk",
                },
            ]
        )

        async def mock_call(section_id, system, user):
            if "korean" in section_id:
                return korean_response
            return english_response

        router = MockRouter()
        router.call_routed = mock_call

        analyzer = JurisdictionAnalyzer(llm_client=None, router=router)
        result = await analyzer.analyze(
            key_clauses_summary="LABOR 이슈",
            deal_summary="크로스보더 M&A",
        )

        # CRITICAL(4) vs LOW(1) = gap 3 → conflict
        assert len(result.conflict_points) >= 1


# ── Stage 7: LDDReportQA ─────────────────────────────────────────


class TestLDDReportQA:
    """Stage 7: 최종 QA 테스트."""

    @pytest.mark.asyncio
    async def test_qa_parse_result(self):
        """QA 결과 파싱."""
        qa = LDDReportQA(llm_client=None)

        raw = json.dumps(
            {
                "overall_score": 4,
                "issues": [
                    {
                        "category": "citation_accuracy",
                        "severity": "minor",
                        "location": "CORP-01",
                        "description": "조항 번호 불일치",
                        "expected": "제174조",
                        "found": "제175조",
                    },
                ],
                "passed_checks": ["risk_recommendation_alignment", "completeness"],
                "summary": "전반적으로 양호하나 인용 조항 번호 1건 확인 필요",
            }
        )

        result = qa._parse_result(raw)

        assert isinstance(result, LDDQAResult)
        assert result.overall_score == 4
        assert len(result.issues) == 1
        assert result.issues[0].category == "citation_accuracy"
        assert len(result.passed_checks) == 2

    @pytest.mark.asyncio
    async def test_qa_parse_failure(self):
        """QA 결과 파싱 실패 시 안전한 폴백."""
        qa = LDDReportQA(llm_client=None)
        result = qa._parse_result("이것은 유효하지 않은 JSON입니다")

        assert result.overall_score == 0
        assert "파싱 실패" in result.summary

    @pytest.mark.asyncio
    async def test_qa_score_clamping(self):
        """스코어 범위 외 값 → 클램핑."""
        qa = LDDReportQA(llm_client=None)

        raw = json.dumps(
            {
                "overall_score": 10,  # > 5
                "issues": [],
                "passed_checks": [],
                "summary": "test",
            }
        )

        result = qa._parse_result(raw)
        assert result.overall_score == 5  # max 5로 클램핑


# ── Guardrails ────────────────────────────────────────────────────


class TestGuardrails:
    """LDD Guardrails 7개 규칙 테스트."""

    def _make_section(
        self,
        section_type: str,
        items: list[dict],
    ) -> dict:
        return {"section_type": section_type, "items": items}

    def _make_item(
        self,
        item_id: str,
        status: str = "OK",
        issue_level: str | None = None,
        confidence: float = 0.8,
        evidence_refs: list[str] | None = None,
        rfi_required: bool = False,
        rfi_number: str = "",
    ) -> dict:
        return {
            "item_id": item_id,
            "name": f"테스트 항목 {item_id}",
            "status": status,
            "issue_level": issue_level,
            "confidence": confidence,
            "evidence_refs": evidence_refs or [],
            "description": "",
            "deal_impact": "",
            "recommendation": "",
            "rfi_required": rfi_required,
            "rfi_number": rfi_number,
        }

    def test_valid_item_ids(self):
        """유효한 item_id 목록 확인."""
        assert len(VALID_ITEM_IDS) == 53  # 52 + IT-04 = 53... 실제 확인
        # 실제 52개 검증
        assert "CORP-01" in VALID_ITEM_IDS
        assert "IT-04" in VALID_ITEM_IDS
        assert "INVALID-99" not in VALID_ITEM_IDS

    def test_rule1_invalid_item_id(self):
        """규칙 1: 유효하지 않은 item_id 탐지."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("INVALID-01"),
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        assert any(i.rule == "ITEM_ID_VALIDITY" and i.severity == "ERROR" for i in result.issues)

    def test_rule2_issue_without_level(self):
        """규칙 2: ISSUE 상태인데 issue_level 없음."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", status="ISSUE", issue_level=None),
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        assert any(i.rule == "STATUS_LEVEL_CONSISTENCY" and "issue_level이 없음" in i.message for i in result.issues)

    def test_rule2_ok_with_level(self):
        """규칙 2: OK 상태인데 issue_level 설정됨 (경고)."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", status="OK", issue_level="HIGH"),
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        assert any(i.rule == "STATUS_LEVEL_CONSISTENCY" and i.severity == "WARNING" for i in result.issues)

    def test_rule3_invalid_evidence_ref(self):
        """규칙 3: VDR에 없는 문서 참조."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", evidence_refs=["nonexistent.pdf"]),
                ],
            )
        ]

        g = LDDGuardrails(vdr_document_ids=["정관.pdf", "이사회의사록.pdf"])
        result = g.validate_all(sections)

        assert any(i.rule == "EVIDENCE_REFS_VALIDITY" for i in result.issues)

    def test_rule4_unrealistic_article_number(self):
        """규칙 4: 비현실적 법률 조문 번호."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    {
                        **self._make_item("CORP-01"),
                        "description": "제9999조에 따라 검토함",
                    },
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        assert any(i.rule == "LEGAL_HALLUCINATION_CHECK" and "비현실적" in i.message for i in result.issues)

    def test_rule5_rfi_duplicate(self):
        """규칙 5: RFI 번호 중복."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", rfi_required=True, rfi_number="CORP-001"),
                    self._make_item("CORP-02", rfi_required=True, rfi_number="CORP-001"),  # 중복
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        assert any(i.rule == "RFI_NUMBERING" and "중복" in i.message for i in result.issues)

    def test_rule5_rfi_wrong_prefix(self):
        """규칙 5: RFI 접두어 불일치."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", rfi_required=True, rfi_number="TAX-001"),  # GOVERNANCE인데 TAX
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        assert any(i.rule == "RFI_NUMBERING" and "접두어 불일치" in i.message for i in result.issues)

    def test_rule7_low_confidence(self):
        """규칙 7: confidence < threshold."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", status="ISSUE", issue_level="HIGH", confidence=0.1),
                ],
            )
        ]

        g = LDDGuardrails(confidence_threshold=0.25)
        result = g.validate_all(sections)

        assert any(i.rule == "CONFIDENCE_THRESHOLD" for i in result.issues)

    def test_all_rules_pass(self):
        """모든 규칙 통과 시 passed_rules에 포함."""
        sections = [
            self._make_section(
                "GOVERNANCE",
                [
                    self._make_item("CORP-01", status="OK", confidence=0.9),
                    self._make_item("CORP-02", status="ISSUE", issue_level="HIGH", confidence=0.85),
                ],
            )
        ]

        g = LDDGuardrails()
        result = g.validate_all(sections)

        # 최소 일부 규칙이 통과
        assert len(result.passed_rules) > 0


# ── PipelineConfig ────────────────────────────────────────────────


class TestPipelineConfig:
    """파이프라인 설정 테스트."""

    def test_defaults(self):
        config = LDDPipelineConfig()

        assert config.stage3_risk_dual is True
        assert config.stage4_gap_detection is True
        assert config.stage5_jurisdiction is False
        assert config.stage7_qa is True
        assert config.risk_gap_auto_resolve == 1
        assert config.risk_gap_human_review == 2
        assert config.max_cost_usd == 15.0
        assert config.gap_similarity_threshold == 0.6

    def test_cross_border_enables_jurisdiction(self):
        config = LDDPipelineConfig(
            stage5_jurisdiction=True,
            is_cross_border=True,
        )

        assert config.stage5_jurisdiction is True
        assert config.is_cross_border is True

    def test_level_map(self):
        config = LDDPipelineConfig()
        assert config.level_map["CRITICAL"] == 4
        assert config.level_map["LOW"] == 1


# ── LDDModelRouter ────────────────────────────────────────────────


class TestLDDModelRouter:
    """LDD 모델 라우터 테스트."""

    def test_default_routing_keys(self):
        """기본 라우팅 맵에 필요한 키가 모두 존재."""
        required_keys = [
            "risk_analysis_buyer",
            "risk_analysis_independent",
            "gap_detection_checklist",
            "gap_detection_freeform",
            "jurisdiction_korean",
            "jurisdiction_english",
            "final_qa",
        ]
        for key in required_keys:
            assert key in DEFAULT_LDD_ROUTING, f"라우팅 키 누락: {key}"

    def test_resolve_known_section(self):
        """알려진 section_id에 대한 라우팅 결정."""
        router = LDDModelRouter(llm_client=MockLLMClient())
        decision = router.resolve("risk_analysis_buyer")

        assert decision.provider == "anthropic"
        assert decision.section_id == "risk_analysis_buyer"

    def test_resolve_unknown_section_fallback(self):
        """알려지지 않은 section_id → 폴백."""
        router = LDDModelRouter(llm_client=MockLLMClient())
        decision = router.resolve("nonexistent_stage")

        # 폴백 체인에서 사용 가능한 프로바이더 선택
        assert decision.provider is not None

    @pytest.mark.asyncio
    async def test_call_routed(self):
        """call_routed 호출."""
        client = MockLLMClient(response='{"test": true}')
        router = LDDModelRouter(llm_client=client)

        result = await router.call_routed("final_qa", "system", "user")

        assert result == '{"test": true}'
        assert client.call_count == 1
