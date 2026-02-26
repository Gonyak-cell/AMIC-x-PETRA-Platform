"""WorkbookBlueprint 단위 테스트."""

import pytest

from app.services.report.blueprint import (
    SheetBlueprint,
    WorkbookBlueprint,
    _CATEGORY_COLORS,
)
from app.services.report.deal_profile import DealProfile


class TestWorkbookBlueprint:
    def test_default_profile_builds(self):
        """기본 프로파일 → 시트 목록 생성."""
        bp = WorkbookBlueprint(DealProfile())
        sheets = bp.build()
        assert len(sheets) > 20
        assert sheets[0].sheet_id == "index"

    def test_sheet_ids_ordered(self):
        """시트 ID 목록이 순서 보장."""
        bp = WorkbookBlueprint(DealProfile())
        ids = bp.get_sheet_ids()
        assert ids[0] == "index"
        assert ids[1] == "cover"
        # 재무제표가 기본 다음
        assert "is_multi" in ids

    def test_get_sheet_by_id(self):
        """특정 시트 조회."""
        bp = WorkbookBlueprint(DealProfile())
        sheet = bp.get_sheet("cover")
        assert sheet is not None
        assert sheet.title_en == "Cover & Summary"
        assert sheet.category == "기본"

    def test_get_sheet_not_found(self):
        """없는 시트 조회."""
        bp = WorkbookBlueprint(DealProfile())
        assert bp.get_sheet("nonexistent") is None

    def test_categories_unique_ordered(self):
        """카테고리 목록 — 순서 유지, 중복 없음."""
        bp = WorkbookBlueprint(DealProfile())
        categories = bp.get_categories()
        assert categories[0] == "기본"
        assert len(categories) == len(set(categories))

    def test_sheets_by_category(self):
        """카테고리별 시트 필터링."""
        bp = WorkbookBlueprint(DealProfile())
        fin_sheets = bp.get_sheets_by_category("재무제표")
        assert len(fin_sheets) == 3  # IS, BS, CF
        ids = [s.sheet_id for s in fin_sheets]
        assert "is_multi" in ids
        assert "bs_multi" in ids
        assert "cf_multi" in ids

    def test_tab_colors_assigned(self):
        """탭 색상이 카테고리별로 할당."""
        bp = WorkbookBlueprint(DealProfile())
        for sheet in bp.build():
            assert sheet.tab_color == _CATEGORY_COLORS.get(sheet.category, "1F4E79")

    def test_skeleton_keys_assigned(self):
        """스켈레톤 키가 해당 시트에 할당."""
        bp = WorkbookBlueprint(DealProfile())
        is_sheet = bp.get_sheet("is_multi")
        assert is_sheet is not None
        assert is_sheet.skeleton_key == "is"

        fcf_sheet = bp.get_sheet("fcf_bridge")
        assert fcf_sheet is not None
        assert fcf_sheet.skeleton_key == "fcf"

    def test_conditional_sheets_excluded(self):
        """기본 프로파일 — 조건부 시트 미포함."""
        bp = WorkbookBlueprint(DealProfile())
        ids = bp.get_sheet_ids()
        assert "backlog_summary" not in ids
        assert "entity_pl" not in ids
        assert "fx_summary" not in ids

    def test_backlog_profile_includes_backlog(self):
        """수주 데이터 → 수주 시트 포함."""
        bp = WorkbookBlueprint(DealProfile(has_backlog_data=True))
        ids = bp.get_sheet_ids()
        assert "backlog_summary" in ids
        assert "backlog_customer" in ids

        backlog_sheets = bp.get_sheets_by_category("수주 분석")
        assert len(backlog_sheets) == 4

    def test_multi_entity_includes_consolidation(self):
        """다법인 → 연결 시트 포함."""
        bp = WorkbookBlueprint(DealProfile(entity_count=3, structure="multi_entity"))
        ids = bp.get_sheet_ids()
        assert "entity_pl" in ids
        assert "ic_elimination" in ids

    def test_full_profile_maximizes(self):
        """전체 조건 충족 → 최대 시트 수."""
        profile = DealProfile(
            deal_type="completion_accounts",
            structure="multi_entity",
            industry="manufacturing",
            entity_count=3,
            has_foreign_subsidiary=True,
            has_backlog_data=True,
            has_interview_data=True,
            has_detailed_cost=True,
        )
        bp = WorkbookBlueprint(profile)
        assert bp.total_sheets() >= 35

    def test_index_data_excludes_index(self):
        """Index 시트용 데이터에서 자기 자신 제외."""
        bp = WorkbookBlueprint(DealProfile())
        index_data = bp.to_index_data()
        all_ids = []
        for cat_entry in index_data:
            for sheet in cat_entry["sheets"]:
                all_ids.append(sheet["sheet_id"])
        assert "index" not in all_ids

    def test_get_summary(self):
        """블루프린트 요약."""
        bp = WorkbookBlueprint(DealProfile(deal_type="locked_box"))
        summary = bp.get_summary()
        assert summary["deal_type"] == "locked_box"
        assert summary["total_sheets"] > 20
        assert isinstance(summary["categories"], list)
        assert isinstance(summary["sheet_ids"], list)

    def test_build_caches(self):
        """build() 결과 캐싱."""
        bp = WorkbookBlueprint(DealProfile())
        sheets1 = bp.build()
        sheets2 = bp.build()
        assert sheets1 is sheets2

    def test_render_types(self):
        """렌더링 타입 — index/cover는 특수 타입."""
        bp = WorkbookBlueprint(DealProfile())
        index = bp.get_sheet("index")
        assert index is not None
        assert index.render_type == "index"

        cover = bp.get_sheet("cover")
        assert cover is not None
        assert cover.render_type == "cover"

        # 일반 시트는 table
        is_sheet = bp.get_sheet("is_multi")
        assert is_sheet is not None
        assert is_sheet.render_type == "table"
