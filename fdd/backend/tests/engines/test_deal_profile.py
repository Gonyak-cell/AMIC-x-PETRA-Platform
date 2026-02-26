"""DealProfileResolver 단위 테스트."""

import pytest

from app.services.report.deal_profile import (
    DealProfile,
    DealProfileResolver,
    SheetSpec,
)


class TestDealProfileResolver:
    def test_default_profile_includes_basic_sheets(self):
        """기본 프로파일 — 필수 시트 포함."""
        resolver = DealProfileResolver(DealProfile())
        ids = resolver.resolve_sheet_ids()

        assert "index" in ids
        assert "cover" in ids
        assert "is_multi" in ids
        assert "qoe_bridge" in ids
        assert "debt_schedule" in ids

    def test_default_excludes_conditional(self):
        """기본 프로파일 — 조건부 시트 미포함."""
        resolver = DealProfileResolver(DealProfile())
        ids = resolver.resolve_sheet_ids()

        assert "backlog_summary" not in ids
        assert "entity_pl" not in ids
        assert "fx_summary" not in ids
        assert "interview_notes" not in ids

    def test_backlog_data_includes_backlog_sheets(self):
        """수주 데이터 있으면 수주 시트 포함."""
        profile = DealProfile(has_backlog_data=True)
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "backlog_summary" in ids
        assert "backlog_customer" in ids
        assert "backlog_aging" in ids
        assert "negative_margin" in ids

    def test_multi_entity_includes_consolidation(self):
        """다법인 → 연결 시트 포함."""
        profile = DealProfile(entity_count=3, structure="multi_entity")
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "entity_pl" in ids
        assert "ic_elimination" in ids

    def test_foreign_subsidiary_includes_fx(self):
        """해외 자회사 → FX 시트 포함."""
        profile = DealProfile(has_foreign_subsidiary=True)
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "fx_summary" in ids

    def test_interview_data_includes_qualitative(self):
        """인터뷰 데이터 → 정성적 시트 포함."""
        profile = DealProfile(has_interview_data=True)
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "interview_notes" in ids
        assert "key_themes" in ids

    def test_manufacturing_includes_cost(self):
        """제조업 + 상세 원가 → 제조원가 시트 포함."""
        profile = DealProfile(industry="manufacturing", has_detailed_cost=True)
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "cost_mfg" in ids

    def test_completion_accounts_includes_nwc_peg(self):
        """Completion Accounts → NWC Peg 시트 포함."""
        profile = DealProfile(deal_type="completion_accounts")
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "nwc_peg" in ids

    def test_locked_box_includes_leakage(self):
        """Locked Box → Leakage Check 시트 포함."""
        profile = DealProfile(deal_type="locked_box")
        resolver = DealProfileResolver(profile)
        ids = resolver.resolve_sheet_ids()

        assert "leakage_check" in ids
        assert "nwc_peg" not in ids

    def test_is_sheet_included(self):
        """개별 시트 포함 여부 확인."""
        resolver = DealProfileResolver(DealProfile())

        assert resolver.is_sheet_included("index") is True
        assert resolver.is_sheet_included("backlog_summary") is False

    def test_get_summary(self):
        """Summary 출력."""
        profile = DealProfile(
            deal_type="completion_accounts",
            entity_count=2,
            has_backlog_data=True,
        )
        resolver = DealProfileResolver(profile)
        summary = resolver.get_summary()

        assert summary["profile"]["deal_type"] == "completion_accounts"
        assert summary["total_sheets"] > 20
        assert "수주 분석" in summary["categories"]

    def test_full_profile_maximizes_sheets(self):
        """모든 조건 충족 → 최대 시트 수."""
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
        resolver = DealProfileResolver(profile)
        sheets = resolver.resolve_sheets()

        # 전체 카탈로그에서 locked_box 조건만 제외
        assert len(sheets) >= 35
