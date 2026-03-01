"""생성 매니페스트 테스트.

> 마지막 수정: 2026-02-11 10:30:00
"""


from src.design_renderer.manifest import GenerationManifest, SlideManifestEntry


class TestSlideManifestEntry:
    """SlideManifestEntry 기본 동작."""

    def test_default_values(self):
        entry = SlideManifestEntry(
            slide_index=0, section_id="cover", title="Cover", success=True
        )
        assert entry.error is None
        assert entry.render_time_ms == 0.0
        assert entry.slide_count == 0

    def test_failed_entry(self):
        entry = SlideManifestEntry(
            slide_index=1,
            section_id="financial_analysis",
            title="Financial Analysis",
            success=False,
            error="데이터 없음",
            render_time_ms=5.2,
        )
        assert not entry.success
        assert entry.error == "데이터 없음"


class TestGenerationManifest:
    """GenerationManifest 테스트."""

    def test_empty_manifest(self):
        m = GenerationManifest()
        assert m.total_slides == 0
        assert m.failed_sections == []
        assert m.success_rate == 1.0

    def test_add_entry(self):
        m = GenerationManifest()
        entry = m.add_entry(
            "cover", title="Cover", success=True, slide_count=1, render_time_ms=10.0
        )
        assert len(m.entries) == 1
        assert entry.slide_index == 0
        assert entry.section_id == "cover"

    def test_multiple_entries_indexing(self):
        m = GenerationManifest()
        m.add_entry("cover", success=True, slide_count=1)
        m.add_entry("disclaimer", success=True, slide_count=1)
        m.add_entry("executive_summary", success=True, slide_count=2)
        assert m.entries[2].slide_index == 2

    def test_total_slides(self):
        m = GenerationManifest()
        m.add_entry("cover", success=True, slide_count=1)
        m.add_entry("financial_analysis", success=True, slide_count=3)
        m.add_entry("appendix", success=True, slide_count=2)
        assert m.total_slides == 6

    def test_failed_sections(self):
        m = GenerationManifest()
        m.add_entry("cover", success=True, slide_count=1)
        m.add_entry("financial_analysis", success=False, error="데이터 없음")
        m.add_entry("appendix", success=False, error="렌더링 오류")
        assert m.failed_sections == ["financial_analysis", "appendix"]

    def test_successful_sections(self):
        m = GenerationManifest()
        m.add_entry("cover", success=True, slide_count=1)
        m.add_entry("financial_analysis", success=False, error="에러")
        assert m.successful_sections == ["cover"]

    def test_success_rate(self):
        m = GenerationManifest()
        m.add_entry("cover", success=True)
        m.add_entry("disclaimer", success=True)
        m.add_entry("financial", success=False, error="에러")
        assert abs(m.success_rate - 2 / 3) < 0.01

    def test_summary_string(self):
        m = GenerationManifest()
        m.total_elapsed_ms = 1500.0
        m.add_entry("cover", success=True, slide_count=1, render_time_ms=50)
        m.add_entry("financial", success=False, error="데이터 없음", render_time_ms=10)
        summary = m.summary()
        assert "1/2 성공" in summary
        assert "1개 실패" in summary
        assert "financial" in summary
        assert "데이터 없음" in summary

    def test_summary_all_success(self):
        m = GenerationManifest()
        m.total_elapsed_ms = 500.0
        m.add_entry("cover", success=True, slide_count=1)
        m.add_entry("disclaimer", success=True, slide_count=1)
        summary = m.summary()
        assert "2/2 성공" in summary
        assert "실패 섹션" not in summary

    def test_to_dict(self):
        m = GenerationManifest()
        m.add_entry("cover", title="Cover", success=True, slide_count=1)
        d = m.to_dict()
        assert "generation_timestamp" in d
        assert d["total_slides"] == 1
        assert d["success_rate"] == 1.0
        assert len(d["entries"]) == 1
        assert d["entries"][0]["section_id"] == "cover"

    def test_to_dict_with_failure(self):
        m = GenerationManifest()
        m.add_entry("cover", success=False, error="에러 발생")
        d = m.to_dict()
        assert d["entries"][0]["success"] is False
        assert d["entries"][0]["error"] == "에러 발생"

    def test_default_title_from_section_id(self):
        m = GenerationManifest()
        entry = m.add_entry("financial_analysis", success=True)
        assert entry.title == "financial_analysis"

    def test_generation_timestamp_format(self):
        m = GenerationManifest()
        assert "T" in m.generation_timestamp  # ISO format
