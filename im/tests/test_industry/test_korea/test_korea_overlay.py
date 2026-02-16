"""Korea Overlay Module 테스트.

> 마지막 수정: 2026-02-11 15:00:00

Korea Overlay 데이터 모델, 규제/K-IFRS/노동/ESG 데이터,
get_korea_overlay_data 집계 함수, IndustryModule.get_korea_overlay 통합 테스트.
"""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from src.industry.korea import get_korea_overlay_data
from src.industry.korea.kifrs import KIFRS_NOTES
from src.industry.korea.labor_esg import ESG_REQUIREMENTS, LABOR_ITEMS
from src.industry.korea.models import (
    ESGFramework,
    ESGRequirement,
    KIFRSNote,
    KoreaOverlayData,
    LaborItem,
    RegulatoryItem,
    Severity,
)
from src.industry.korea.regulatory import REGULATORY_ITEMS
from src.industry.registry import get_industry_module


# ---------------------------------------------------------------------------
# 모델 테스트
# ---------------------------------------------------------------------------


class TestKoreaOverlayModels:
    """Korea Overlay 데이터 모델 테스트."""

    def test_regulatory_item_frozen(self) -> None:
        """RegulatoryItem은 수정 불가 (frozen=True)."""
        item = RegulatoryItem(
            regulation_id="test",
            law_name_kr="테스트법",
            law_name_en="Test Act",
            authority="테스트기관",
            description="설명",
            deal_impact="영향",
        )
        with pytest.raises(FrozenInstanceError):
            item.regulation_id = "changed"  # type: ignore[misc]

    def test_kifrs_note_frozen(self) -> None:
        """KIFRSNote는 수정 불가."""
        note = KIFRSNote(
            note_id="test",
            standard_number="9999",
            topic_kr="테스트",
            topic_en="Test",
            description="설명",
            deal_consideration="고려사항",
        )
        with pytest.raises(FrozenInstanceError):
            note.note_id = "changed"  # type: ignore[misc]

    def test_labor_item_frozen(self) -> None:
        """LaborItem은 수정 불가."""
        item = LaborItem(
            labor_id="test",
            law_name_kr="테스트법",
            law_name_en="Test Act",
            description="설명",
            deal_impact="영향",
        )
        with pytest.raises(FrozenInstanceError):
            item.labor_id = "changed"  # type: ignore[misc]

    def test_esg_requirement_frozen(self) -> None:
        """ESGRequirement는 수정 불가."""
        req = ESGRequirement(
            esg_id="test",
            framework=ESGFramework.KCGS,
            category="테스트",
            description="설명",
        )
        with pytest.raises(FrozenInstanceError):
            req.esg_id = "changed"  # type: ignore[misc]

    def test_korea_overlay_data_mutable(self) -> None:
        """KoreaOverlayData는 수정 가능 (mutable container)."""
        data = KoreaOverlayData(industry_id="tech")
        data.industry_id = "manufacturing"
        assert data.industry_id == "manufacturing"

    def test_severity_enum_values(self) -> None:
        """Severity enum: HIGH, MEDIUM, LOW."""
        assert Severity.HIGH == "high"
        assert Severity.MEDIUM == "medium"
        assert Severity.LOW == "low"
        assert len(Severity) == 3

    def test_esg_framework_enum_values(self) -> None:
        """ESGFramework enum: KCGS, TCFD, K_TAXONOMY, CSRD."""
        assert ESGFramework.KCGS == "KCGS"
        assert ESGFramework.TCFD == "TCFD"
        assert ESGFramework.K_TAXONOMY == "K-Taxonomy"
        assert ESGFramework.CSRD == "CSRD"
        assert len(ESGFramework) == 4


# ---------------------------------------------------------------------------
# 규제 항목 데이터 테스트
# ---------------------------------------------------------------------------


class TestRegulatoryItems:
    """규제 항목 데이터 테스트."""

    def test_regulatory_items_not_empty(self) -> None:
        """REGULATORY_ITEMS가 비어있지 않다."""
        assert len(REGULATORY_ITEMS) == 14

    def test_all_valid_regulatory_structure(self) -> None:
        """모든 항목이 RegulatoryItem 인스턴스이고 필수 필드가 있다."""
        for item in REGULATORY_ITEMS:
            assert isinstance(item, RegulatoryItem)
            assert item.regulation_id
            assert item.law_name_kr
            assert item.law_name_en
            assert item.authority
            assert item.description
            assert item.deal_impact
            assert len(item.applicable_industries) > 0

    def test_common_regulations_apply_to_all_industries(self) -> None:
        """MRFTA, FSCMA, FIPA, PIPA가 4개 산업 모두에 적용된다."""
        common_ids = {"mrfta_merger", "fscma", "foreign_investment", "pipa"}
        common_items = [r for r in REGULATORY_ITEMS if r.regulation_id in common_ids]
        assert len(common_items) == 4

        all_industries = {"tech", "manufacturing", "healthcare", "logistics"}
        for item in common_items:
            assert set(item.applicable_industries) == all_industries

    def test_tech_specific_regulations(self) -> None:
        """전기통신사업법, 정보통신망법, 클라우드컴퓨팅법이 tech에만 적용된다."""
        tech_ids = {"telecom_business", "ict_network", "cloud_computing"}
        tech_items = [r for r in REGULATORY_ITEMS if r.regulation_id in tech_ids]
        assert len(tech_items) == 3
        for item in tech_items:
            assert item.applicable_industries == ["tech"]


# ---------------------------------------------------------------------------
# K-IFRS 테스트
# ---------------------------------------------------------------------------


class TestKIFRSNotes:
    """K-IFRS 조정사항 테스트."""

    def test_kifrs_notes_not_empty(self) -> None:
        """KIFRS_NOTES가 비어있지 않다."""
        assert len(KIFRS_NOTES) == 8

    def test_all_valid_kifrs_structure(self) -> None:
        """모든 항목이 KIFRSNote 인스턴스이고 필수 필드가 있다."""
        for note in KIFRS_NOTES:
            assert isinstance(note, KIFRSNote)
            assert note.note_id
            assert note.standard_number
            assert note.topic_kr
            assert note.topic_en

    def test_common_kifrs_apply_to_all_industries(self) -> None:
        """K-IFRS 1115, 1116, 1037, 1103, 1019가 전 산업에 적용."""
        common_standards = {"1115", "1116", "1037", "1103", "1019"}
        all_industries = {"tech", "manufacturing", "healthcare", "logistics"}

        for note in KIFRS_NOTES:
            if note.standard_number in common_standards:
                assert set(note.applicable_industries) == all_industries


# ---------------------------------------------------------------------------
# 노동/ESG 테스트
# ---------------------------------------------------------------------------


class TestLaborESG:
    """노동법·ESG 요구사항 테스트."""

    def test_labor_items_not_empty(self) -> None:
        """LABOR_ITEMS가 비어있지 않다."""
        assert len(LABOR_ITEMS) == 6

    def test_labor_items_valid_structure(self) -> None:
        """모든 노동법 항목이 LaborItem 인스턴스이고 필수 필드가 있다."""
        for item in LABOR_ITEMS:
            assert isinstance(item, LaborItem)
            assert item.labor_id
            assert item.law_name_kr
            assert item.law_name_en
            assert len(item.applicable_industries) > 0

    def test_esg_requirements_not_empty(self) -> None:
        """ESG_REQUIREMENTS가 비어있지 않다."""
        assert len(ESG_REQUIREMENTS) == 8

    def test_esg_requirements_valid_structure(self) -> None:
        """모든 ESG 항목이 ESGRequirement 인스턴스이고 필수 필드가 있다."""
        for req in ESG_REQUIREMENTS:
            assert isinstance(req, ESGRequirement)
            assert req.esg_id
            assert isinstance(req.framework, ESGFramework)
            assert req.category
            assert len(req.applicable_industries) > 0


# ---------------------------------------------------------------------------
# 집계 함수 테스트
# ---------------------------------------------------------------------------


class TestGetKoreaOverlayData:
    """get_korea_overlay_data 집계 함수 테스트."""

    @pytest.mark.parametrize(
        "industry_id",
        ["tech", "manufacturing", "healthcare", "logistics"],
    )
    def test_overlay_returns_for_supported_industries(
        self, industry_id: str
    ) -> None:
        """지원 산업에 대해 KoreaOverlayData를 반환한다."""
        result = get_korea_overlay_data(industry_id)
        assert result is not None
        assert isinstance(result, KoreaOverlayData)
        assert result.industry_id == industry_id
        assert len(result.regulatory_items) > 0
        assert len(result.kifrs_notes) > 0
        assert len(result.labor_items) > 0
        assert len(result.esg_requirements) > 0

    def test_overlay_unknown_industry_returns_none(self) -> None:
        """미등록 산업은 None을 반환한다."""
        result = get_korea_overlay_data("unknown_industry")
        assert result is None

    def test_overlay_data_contains_regulatory_items(self) -> None:
        """tech 오버레이에 규제 항목이 포함된다."""
        result = get_korea_overlay_data("tech")
        assert result is not None
        reg_ids = {r.regulation_id for r in result.regulatory_items}
        # 공통 규제 포함
        assert "mrfta_merger" in reg_ids
        assert "pipa" in reg_ids
        # tech 전용 규제 포함
        assert "telecom_business" in reg_ids

    def test_overlay_filters_by_industry(self) -> None:
        """tech 오버레이에 healthcare 전용 규제가 포함되지 않는다."""
        result = get_korea_overlay_data("tech")
        assert result is not None
        reg_ids = {r.regulation_id for r in result.regulatory_items}
        assert "pharmaceutical" not in reg_ids
        assert "medical_devices" not in reg_ids


# ---------------------------------------------------------------------------
# IndustryModule.get_korea_overlay 통합 테스트
# ---------------------------------------------------------------------------


class TestBaseModuleIntegration:
    """IndustryModule.get_korea_overlay() 통합 테스트."""

    def test_tech_module_get_korea_overlay(self) -> None:
        """TechSaaSModule.get_korea_overlay() → KoreaOverlayData."""
        module = get_industry_module("tech")
        overlay = module.get_korea_overlay()
        assert overlay is not None
        assert isinstance(overlay, KoreaOverlayData)
        assert overlay.industry_id == "tech"

    @pytest.mark.parametrize(
        "industry_id",
        ["tech", "manufacturing", "healthcare", "logistics"],
    )
    def test_all_modules_return_overlay(self, industry_id: str) -> None:
        """4개 산업 모듈 모두 get_korea_overlay()가 데이터를 반환한다."""
        module = get_industry_module(industry_id)
        overlay = module.get_korea_overlay()
        assert overlay is not None
        assert overlay.industry_id == industry_id
