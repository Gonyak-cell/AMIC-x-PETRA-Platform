"""NarrativeQualityGate 테스트.

Phase 6: 품질 보증 — 서술 품질 게이트 테스트.
"""

import pytest

from app.ralph.gates.narrative_gate import (
    NarrativeQualityGate,
)


@pytest.fixture
def gate():
    return NarrativeQualityGate()


def _make_block(block_type: str, content: str) -> dict:
    return {"block_type": block_type, "content": content, "word_count": len(content)}


def _make_item(
    item_id: str,
    blocks: list[dict],
    item_name: str = "테스트 항목",
) -> dict:
    return {
        "item_id": item_id,
        "item_name": item_name,
        "section_type": "GOVERNANCE",
        "blocks": blocks,
    }


# ── NarrativeQualityGate 기본 동작 ─────────────────────────────────────


class TestNarrativeQualityGate:
    """게이트 기본 동작 테스트."""

    def test_empty_sections(self, gate):
        result = gate.evaluate({})
        assert result.total_items == 0
        assert result.overall_score == 5.0

    def test_item_with_no_blocks(self, gate):
        result = gate.evaluate(
            {
                "GOVERNANCE": [_make_item("GOV-01", [])],
            }
        )
        assert result.total_items == 1
        assert result.passed_items == 1  # 블록 없으면 OK → 통과

    def test_result_to_dict(self, gate):
        result = gate.evaluate({"GOVERNANCE": [_make_item("GOV-01", [])]})
        d = result.to_dict()
        assert "total_items" in d
        assert "pass_rate" in d
        assert "items" in d


# ── 분량 검사 ──────────────────────────────────────────────────────────


class TestMinChars:
    """최소 분량 검사."""

    def test_critical_item_short(self, gate):
        """CRITICAL 항목 2000자 미만 → 이슈."""
        blocks = [
            _make_block("FACTS", "사실" * 50),
            _make_block("LEGAL_REVIEW", "법률" * 50),
            _make_block("ANALYSIS", "분석" * 50),
            _make_block("DEAL_IMPACT", "영향 50억원 감소"),
            _make_block("PENALTY", "벌금" * 20),
            _make_block("RECOMMENDATION", "권고" * 20),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        # 6블록 → CRITICAL로 판정, 분량 미달 이슈 예상
        assert any("분량 미달" in i for i in item.issues)

    def test_sufficient_chars(self, gate):
        """충분한 분량 → 분량 이슈 없음."""
        long_text = "상법 제382조에 따라 이사는 주주총회에서 선임되며, 관련 문서 검토 결과 " * 100
        blocks = [
            _make_block("FACTS", long_text),
            _make_block("LEGAL_REVIEW", long_text),
            _make_block("ANALYSIS", long_text[:500]),
            _make_block("DEAL_IMPACT", "매매가격 50억원 감소 가능성. 2026년 3월까지 해결 필요."),
            _make_block("PENALTY", "과태료 5000만원"),
            _make_block("RECOMMENDATION", "SPA 진술보장에 반영 필요"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert not any("분량 미달" in i for i in item.issues)


# ── 법률 인용 검사 ─────────────────────────────────────────────────────


class TestCitationCheck:
    """법률 인용 존재 검사."""

    def test_no_citation_issue(self, gate):
        """인용 없는 ISSUE 항목 → 이슈."""
        blocks = [
            _make_block("FACTS", "대상회사를 검토한 결과"),
            _make_block("LEGAL_REVIEW", "관련 규정에 따르면"),
            _make_block("ANALYSIS", "분석 결과"),
            _make_block("DEAL_IMPACT", "영향 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert any("법률 인용 없음" in i for i in item.issues)

    def test_with_citation(self, gate):
        """인용 있는 항목 → 인용 이슈 없음."""
        blocks = [
            _make_block("FACTS", "대상회사를 검토한 결과"),
            _make_block("LEGAL_REVIEW", "상법 제382조에 따르면 이사는 선임된다"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "영향 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert not any("법률 인용 없음" in i for i in item.issues)
        assert item.citation_count >= 1

    def test_cite_tag_counted(self, gate):
        """[cite:ID] 태그도 인용으로 카운트."""
        blocks = [
            _make_block("FACTS", "문서 검토"),
            _make_block("LEGAL_REVIEW", "관련 규정 [cite:상법_382]에 따르면"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "영향 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        assert result.items[0].citation_count >= 1


# ── 블록 수 검사 ──────────────────────────────────────────────────────


class TestBlockCount:
    """최소 블록 수 검사."""

    def test_too_few_blocks(self, gate):
        """ISSUE 항목에 블록 2개 → 이슈."""
        blocks = [
            _make_block("FACTS", "사실관계"),
            _make_block("LEGAL_REVIEW", "상법 제382조 법률 검토"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert any("블록 수 부족" in i for i in item.issues)

    def test_sufficient_blocks(self, gate):
        """4블록 이상 → 블록 수 이슈 없음."""
        blocks = [
            _make_block("FACTS", "사실관계"),
            _make_block("LEGAL_REVIEW", "상법 제382조 법률 검토"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "영향 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert not any("블록 수 부족" in i for i in item.issues)


# ── 모호한 표현 탐지 ──────────────────────────────────────────────────


class TestVagueExpressions:
    """모호한 표현 탐지."""

    def test_vague_detected(self, gate):
        blocks = [
            _make_block("FACTS", "주의가 필요하고, 검토가 필요하며, 확인이 필요하다"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "영향"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert len(item.vague_expressions) >= 3
        assert any("모호한 표현" in i for i in item.issues)

    def test_no_vague(self, gate):
        blocks = [
            _make_block("FACTS", "대상회사의 이사회 구성을 검토한 결과"),
            _make_block("LEGAL_REVIEW", "상법 제382조에 따르면"),
            _make_block("ANALYSIS", "분석 결과 위반 사항 없음"),
            _make_block("DEAL_IMPACT", "거래 가격 조정 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert not any("모호한 표현" in i for i in item.issues)


# ── 구체성 검사 ────────────────────────────────────────────────────────


class TestSpecificity:
    """거래 영향 구체성 검사."""

    def test_no_specificity(self, gate):
        blocks = [
            _make_block("FACTS", "사실관계"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "거래에 영향이 있을 수 있다"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert any("구체적 수치" in i for i in item.issues)

    def test_with_amount(self, gate):
        blocks = [
            _make_block("FACTS", "사실관계"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "매매가격에서 50억원 감액 조정이 필요하다"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert not any("구체적 수치" in i for i in item.issues)
        assert item.specificity_count >= 1

    def test_with_percentage(self, gate):
        blocks = [
            _make_block("FACTS", "사실관계"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "EBITDA의 15% 수준에서 가격 조정"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        assert result.items[0].specificity_count >= 1

    def test_with_period(self, gate):
        blocks = [
            _make_block("FACTS", "사실관계"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "분석"),
            _make_block("DEAL_IMPACT", "클로징이 3개월 지연될 수 있다"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        assert result.items[0].specificity_count >= 1


# ── 소스 문서 참조 ────────────────────────────────────────────────────


class TestSourceRef:
    """소스 문서 참조 검사."""

    def test_no_source_ref(self, gate):
        blocks = [
            _make_block("FACTS", "분석 결과"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "결론"),
            _make_block("DEAL_IMPACT", "영향 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        assert not result.items[0].has_source_ref

    def test_with_source_ref(self, gate):
        blocks = [
            _make_block("FACTS", "감사보고서에 따르면 대상회사의 매출은"),
            _make_block("LEGAL_REVIEW", "상법 제382조"),
            _make_block("ANALYSIS", "결론"),
            _make_block("DEAL_IMPACT", "영향 10억원"),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        assert result.items[0].has_source_ref


# ── 통합 테스트 ────────────────────────────────────────────────────────


class TestIntegration:
    """전체 품질 게이트 통합 테스트."""

    def test_perfect_item_passes(self, gate):
        """모든 기준을 충족하는 항목."""
        long_facts = (
            "감사보고서에 따르면 대상회사는 2025년 12월 설립되었으며, 정관 제3조에 사업목적이 기재되어 있다. "
        ) * 30
        blocks = [
            _make_block("FACTS", long_facts),
            _make_block(
                "LEGAL_REVIEW",
                "상법 제289조 [cite:상법_289]에 따르면 정관에는 절대적 기재사항이 포함되어야 한다. " * 20,
            ),
            _make_block("ANALYSIS", "상기 검토 결과 정관의 절대적 기재사항은 모두 구비되어 있음이 확인된다. " * 10),
            _make_block(
                "DEAL_IMPACT", "매매가격에서 약 30억원의 할인 요인이 존재하며, 클로징이 2개월 지연될 가능성이 있다."
            ),
            _make_block("PENALTY", "상법 제635조에 따라 과태료 500만원 이하가 부과될 수 있다."),
            _make_block("RECOMMENDATION", "SPA 진술보장 조항에 반영하고, 에스크로 계좌 5억원 설정을 권고한다."),
        ]
        result = gate.evaluate({"GOV": [_make_item("GOV-01", blocks)]})
        item = result.items[0]
        assert item.passed, f"이슈: {item.issues}"

    def test_multiple_sections(self, gate):
        """여러 섹션의 항목 평가."""
        result = gate.evaluate(
            {
                "GOVERNANCE": [
                    _make_item(
                        "GOV-01",
                        [
                            _make_block("FACTS", "감사보고서 기반 사실관계 " * 100),
                            _make_block("LEGAL_REVIEW", "상법 제382조에 따르면 " * 50),
                            _make_block("ANALYSIS", "분석 결과 " * 30),
                            _make_block("DEAL_IMPACT", "가격 50억원 조정 필요"),
                        ],
                    )
                ],
                "LABOR": [
                    _make_item(
                        "LAB-01",
                        [
                            _make_block("FACTS", "근로계약서 검토 결과 " * 50),
                        ],
                    )
                ],
            }
        )
        assert result.total_items == 2

    def test_overall_score_reflects_pass_rate(self, gate):
        """전체 점수가 통과율을 반영하는지."""
        result = gate.evaluate(
            {
                "GOV": [
                    _make_item("GOV-01", []),  # OK → 통과
                    _make_item("GOV-02", []),  # OK → 통과
                ]
            }
        )
        assert result.overall_score == 5.0
        assert result.pass_rate == 1.0

    def test_duration_measured(self, gate):
        """실행 시간이 측정되는지."""
        result = gate.evaluate({"GOV": [_make_item("GOV-01", [])]})
        assert result.duration_ms >= 0


# ── 파이프라인 통합 형식 테스트 ──────────────────────────────────────────


class TestPipelineIntegrationFormat:
    """NarrativeQualityGate 결과가 파이프라인 qa_result에 올바르게 저장되는 형식 검증."""

    def test_to_dict_has_required_keys(self, gate):
        """to_dict()가 파이프라인에서 필요한 모든 키를 포함하는지."""
        result = gate.evaluate(
            {
                "GOV": [
                    _make_item(
                        "GOV-01",
                        [
                            _make_block("FACTS", "감사보고서 검토 결과" * 50),
                        ],
                    )
                ]
            }
        )
        d = result.to_dict()

        required_keys = [
            "total_items",
            "passed_items",
            "failed_items",
            "pass_rate",
            "overall_score",
            "duration_ms",
            "summary_issues",
            "items",
        ]
        for key in required_keys:
            assert key in d, f"to_dict()에 '{key}' 키 누락"

    def test_to_dict_items_structure(self, gate):
        """to_dict().items의 각 항목이 올바른 구조를 갖는지."""
        result = gate.evaluate(
            {
                "GOV": [
                    _make_item(
                        "GOV-01",
                        [
                            _make_block("FACTS", "사실관계"),
                            _make_block("LEGAL_REVIEW", "상법 제382조에 따르면"),
                            _make_block("ANALYSIS", "분석"),
                            _make_block("DEAL_IMPACT", "영향 10억원"),
                        ],
                    )
                ]
            }
        )
        d = result.to_dict()
        assert len(d["items"]) == 1

        item_dict = d["items"][0]
        item_keys = [
            "item_id",
            "item_name",
            "status",
            "issue_level",
            "total_chars",
            "block_count",
            "citation_count",
            "vague_count",
            "specificity_count",
            "has_source_ref",
            "issues",
            "passed",
        ]
        for key in item_keys:
            assert key in item_dict, f"item에 '{key}' 키 누락"

    def test_qa_result_narrative_quality_integration(self, gate):
        """qa_result['narrative_quality']에 저장할 때의 시뮬레이션."""
        result = gate.evaluate({"GOV": [_make_item("GOV-01", [])]})
        d = result.to_dict()

        # 파이프라인에서의 저장 시뮬레이션
        qa_result: dict = {}
        qa_result["narrative_quality"] = d

        assert "narrative_quality" in qa_result
        assert qa_result["narrative_quality"]["total_items"] == 1
        assert qa_result["narrative_quality"]["overall_score"] == 5.0

    def test_to_dict_json_serializable(self, gate):
        """to_dict() 결과가 JSON 직렬화 가능한지."""
        import json

        result = gate.evaluate(
            {
                "GOV": [
                    _make_item(
                        "GOV-01",
                        [
                            _make_block("FACTS", "사실관계 " * 100),
                            _make_block("LEGAL_REVIEW", "상법 제382조 검토 " * 50),
                            _make_block("ANALYSIS", "분석 결과 " * 30),
                            _make_block("DEAL_IMPACT", "거래 영향 50억원"),
                            _make_block("PENALTY", "과태료 5000만원"),
                            _make_block("RECOMMENDATION", "권고사항"),
                        ],
                    )
                ]
            }
        )
        d = result.to_dict()
        # JSON 직렬화가 예외 없이 성공해야 함
        serialized = json.dumps(d, ensure_ascii=False)
        assert len(serialized) > 0
        # 역직렬화 후 구조 유지
        restored = json.loads(serialized)
        assert restored["total_items"] == d["total_items"]
