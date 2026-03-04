"""정성적 분석 엔진 단위 테스트."""

import pytest

from app.engines.qualitative_engine import (
    InterviewNote,
    InterviewStructureResult,
    ThemeExtractionResult,
    extract_themes,
    structure_interviews,
)

# ── Interview Structuring ────────────────────────────────


class TestStructureInterviews:
    def test_basic_structuring(self):
        """기본 인터뷰 구조화."""
        notes = [
            {
                "content": "매출은 전년 대비 성장했습니다.",
                "source": "management",
                "topic": "revenue",
            },
            {
                "content": "인건비가 증가하고 있어 비용 관리가 필요합니다.",
                "source": "employee",
                "topic": "cost",
            },
        ]
        result, evidence = structure_interviews(notes)

        assert result.total_notes == 2
        assert result.notes[0].note_id == "INT-001"
        assert result.notes[0].source == "management"
        assert result.notes[0].topic == "revenue"

    def test_auto_topic_classification(self):
        """토픽 미지정 시 자동 분류."""
        notes = [
            {"content": "매출액이 크게 증가했습니다.", "source": "management"},
            {
                "content": "IT 시스템이 노후화되어 교체가 필요합니다.",
                "source": "employee",
            },
        ]
        result, _ = structure_interviews(notes)

        assert result.notes[0].topic == "revenue"
        assert result.notes[1].topic == "it"

    def test_risk_flag_detection(self):
        """리스크 키워드 감지."""
        notes = [
            {
                "content": "소송 건이 진행 중이며 우발 부채 가능성이 있습니다.",
                "source": "management",
            },
        ]
        result, _ = structure_interviews(notes)

        assert len(result.notes[0].risk_flags) >= 2
        assert "소송" in result.notes[0].risk_flags
        assert result.risk_flag_count >= 2

    def test_sentiment_analysis(self):
        """감정 분석."""
        notes = [
            {
                "content": "매출이 크게 성장하고 시장이 확대되고 있습니다.",
                "source": "management",
            },
            {
                "content": "매출이 감소하고 시장이 위축되고 있어 위험합니다.",
                "source": "management",
            },
            {"content": "시스템을 교체할 예정입니다.", "source": "management"},
        ]
        result, _ = structure_interviews(notes)

        assert result.notes[0].sentiment == "positive"
        assert result.notes[1].sentiment == "negative"
        assert result.notes[2].sentiment == "neutral"

    def test_source_distribution(self):
        """출처별 분포."""
        notes = [
            {"content": "Test 1", "source": "management"},
            {"content": "Test 2", "source": "management"},
            {"content": "Test 3", "source": "employee"},
        ]
        result, _ = structure_interviews(notes)

        assert result.source_distribution == {"management": 2, "employee": 1}

    def test_single_source_warning(self):
        """단일 출처 경고."""
        notes = [
            {"content": "Test 1", "source": "management"},
            {"content": "Test 2", "source": "management"},
        ]
        result, _ = structure_interviews(notes)
        assert any("INTERVIEW_SINGLE_SOURCE" in w for w in result.warnings)

    def test_high_risk_warning(self):
        """높은 리스크 비율 경고."""
        notes = [
            {"content": "소송 관련 분쟁 건", "source": "management"},
            {"content": "횡령 의혹 조사", "source": "management"},
            {"content": "일반적인 업무", "source": "management"},
        ]
        result, _ = structure_interviews(notes)
        assert any("INTERVIEW_HIGH_RISK" in w for w in result.warnings)

    def test_empty_notes(self):
        """빈 입력."""
        result, _ = structure_interviews([])
        assert result.total_notes == 0
        assert any("INTERVIEW_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        """Evidence 링크."""
        notes = [{"content": "Test", "source": "management"}]
        _, evidence = structure_interviews(notes)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "interview_structure"

    def test_theme_extraction_in_notes(self):
        """노트 내 테마 추출."""
        notes = [
            {"content": "매출 성장과 고객 확대가 기대됩니다.", "source": "management"},
        ]
        result, _ = structure_interviews(notes)
        assert "revenue" in result.notes[0].themes
        assert "customer" in result.notes[0].themes


# ── Theme Extraction ─────────────────────────────────────


class TestExtractThemes:
    def test_basic_extraction(self):
        """기본 테마 추출."""
        notes = [
            InterviewNote(
                "INT-001", "management", "revenue", "매출 성장", themes=["revenue"]
            ),
            InterviewNote("INT-002", "employee", "cost", "비용 관리", themes=["cost"]),
            InterviewNote(
                "INT-003", "management", "revenue", "매출 확대", themes=["revenue"]
            ),
        ]
        result, _ = extract_themes(notes)

        assert result.total_themes >= 2
        assert result.themes[0].theme == "revenue"  # 빈도 높은 순
        assert result.themes[0].frequency == 2

    def test_multi_source_tracking(self):
        """출처 다양성 추적."""
        notes = [
            InterviewNote(
                "INT-001", "management", "revenue", "매출", themes=["revenue"]
            ),
            InterviewNote("INT-002", "employee", "revenue", "매출", themes=["revenue"]),
        ]
        result, _ = extract_themes(notes)

        rev_theme = next(t for t in result.themes if t.theme == "revenue")
        assert set(rev_theme.sources) == {"management", "employee"}

    def test_sentiment_distribution(self):
        """테마별 감정 분포."""
        notes = [
            InterviewNote(
                "INT-001",
                "mgmt",
                "rev",
                "good",
                themes=["revenue"],
                sentiment="positive",
            ),
            InterviewNote(
                "INT-002",
                "mgmt",
                "rev",
                "bad",
                themes=["revenue"],
                sentiment="negative",
            ),
            InterviewNote(
                "INT-003", "mgmt", "rev", "ok", themes=["revenue"], sentiment="neutral"
            ),
        ]
        result, _ = extract_themes(notes)

        rev = next(t for t in result.themes if t.theme == "revenue")
        assert rev.sentiment_distribution == {
            "positive": 1,
            "neutral": 1,
            "negative": 1,
        }

    def test_risk_themes(self):
        """리스크 관련 테마."""
        notes = [
            InterviewNote(
                "INT-001",
                "mgmt",
                "compliance",
                "소송",
                themes=["compliance"],
                risk_flags=["소송"],
            ),
            InterviewNote(
                "INT-002", "mgmt", "revenue", "매출 성장", themes=["revenue"]
            ),
        ]
        result, _ = extract_themes(notes)

        assert "compliance" in result.risk_themes
        assert "revenue" not in result.risk_themes

    def test_top_n(self):
        """Top N 제한."""
        notes = [
            InterviewNote(f"INT-{i}", "mgmt", "t", "c", themes=[f"theme_{i}"])
            for i in range(20)
        ]
        result, _ = extract_themes(notes, top_n=5)
        assert len(result.top_themes) == 5

    def test_empty_notes(self):
        """빈 입력."""
        result, _ = extract_themes([])
        assert result.total_themes == 0
        assert any("THEME_EMPTY" in w for w in result.warnings)

    def test_evidence_generated(self):
        """Evidence 링크."""
        notes = [InterviewNote("INT-001", "mgmt", "rev", "test", themes=["revenue"])]
        _, evidence = extract_themes(notes)
        assert len(evidence) >= 1
        assert evidence[0].target_type == "theme_extraction"
