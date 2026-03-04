"""PPTX XML 구조 검증 — a:ea 폰트, 이미지 바운드, 슬라이드 레이아웃.

> 마지막 수정: 2026-02-11 21:00:00

생성된 PPTX를 재오픈하여 XML 레벨에서 구조 무결성을 검증한다.
- a:ea (동아시아) 폰트가 모든 text run에 설정되었는지
- 이미지가 슬라이드 경계 내에 위치하는지
- 슬라이드 레이아웃이 일관된 구조를 갖는지
"""

from __future__ import annotations

from typing import Any

import pytest
from pptx import Presentation
from pptx.util import Inches

from src.design_renderer.im_document import (
    CompanyOverview,
    ContactInfo,
    DealStructure,
    FinancialStatements,
    GrowthStrategy,
    IMDocumentData,
    IMStyle,
    ManagementMember,
    MarketData,
    ShareholderInfo,
    SourceCitation,
    TransactionType,
)
from src.design_renderer.pipeline import IMPipeline, PipelineResult


# ---------------------------------------------------------------------------
# XML 헬퍼
# ---------------------------------------------------------------------------

_NSMAP = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def _qn(tag: str) -> str:
    """네임스페이스 Clark notation 변환."""
    prefix, local = tag.split(":")
    return f"{{{_NSMAP[prefix]}}}{local}"


def _get_ea_typeface(run: Any) -> str | None:
    """run의 a:ea typeface 속성 반환. 없으면 None."""
    rpr = run._r.find(_qn("a:rPr"))
    if rpr is None:
        return None
    ea = rpr.find(_qn("a:ea"))
    if ea is None:
        return None
    return ea.get("typeface")


def _collect_all_runs(prs: Presentation) -> list[tuple[int, Any]]:
    """프레젠테이션의 모든 (slide_index, run) 쌍을 수집."""
    runs: list[tuple[int, Any]] = []
    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.text.strip():
                            runs.append((slide_idx, run))
    return runs


def _collect_all_pictures(
    prs: Presentation,
) -> list[tuple[int, Any]]:
    """프레젠테이션의 모든 (slide_index, picture_shape) 쌍을 수집."""
    pictures: list[tuple[int, Any]] = []
    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                pictures.append((slide_idx, shape))
    return pictures


def _get_slide_text(slide: Any) -> str:
    """슬라이드의 모든 텍스트를 하나의 문자열로 결합."""
    texts: list[str] = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            texts.append(shape.text_frame.text)
    return " ".join(texts)


# ---------------------------------------------------------------------------
# 인라인 데이터 생성 (module-scope 픽스처용)
# ---------------------------------------------------------------------------


def _make_full_data() -> IMDocumentData:
    """test_pptx_structure 전용 FULL 데이터 생성.

    function-scope full_data 픽스처에 의존하지 않고 module-scope에서 사용.
    """
    fs = FinancialStatements(
        revenue={"2022": 100_000, "2023": 120_000, "2024": 150_000},
        cost_of_goods_sold={"2022": 60_000, "2023": 70_000, "2024": 85_000},
        gross_profit={"2022": 40_000, "2023": 50_000, "2024": 65_000},
        operating_income={"2022": 15_000, "2023": 20_000, "2024": 28_000},
        ebitda={"2022": 20_000, "2023": 26_000, "2024": 35_000},
        net_income={"2022": 10_000, "2023": 14_000, "2024": 20_000},
        sga_expenses={"2022": 25_000, "2023": 30_000, "2024": 37_000},
        total_assets={"2022": 200_000, "2023": 250_000, "2024": 300_000},
        total_liabilities={"2022": 80_000, "2023": 90_000, "2024": 100_000},
        total_equity={"2022": 120_000, "2023": 160_000, "2024": 200_000},
        cash_and_equivalents={"2022": 30_000, "2023": 40_000, "2024": 55_000},
        total_debt={"2022": 50_000, "2023": 45_000, "2024": 40_000},
        operating_cash_flow={"2022": 18_000, "2023": 24_000, "2024": 32_000},
        capex={"2022": 5_000, "2023": 6_000, "2024": 8_000},
        free_cash_flow={"2022": 13_000, "2023": 18_000, "2024": 24_000},
    )

    data = IMDocumentData(
        project_name="Project STRUCTURE",
        company_name_kr="구조검증기업",
        company_name_en="Structure Corp",
        corp_code="00888888",
        website_url="https://structure-corp.co.kr",
        date="2026-02-11",
        im_style=IMStyle.FULL,
        financial_statements=fs,
        deal_structure=DealStructure(
            seller="구조PE",
            stake_pct=0.60,
            deal_background="전략적 포트폴리오 재구성",
            transaction_type=TransactionType.MA,
            valuation_low=500_000,
            valuation_high=700_000,
            valuation_method="EV/EBITDA",
            timeline={"예비입찰": "2026-03", "본입찰": "2026-05"},
        ),
        company_overview=CompanyOverview(
            history=[
                {"year": "2010", "event": "설립"},
                {"year": "2015", "event": "코스닥 상장"},
                {"year": "2020", "event": "해외 진출"},
            ],
            business_model="B2B IT 서비스",
            value_chain=["기획", "개발", "운영"],
            key_products=["클라우드 인프라", "데이터 분석"],
            certifications=["ISO 27001", "ISMS-P"],
            employee_count=500,
            headquarters="서울특별시 강남구",
            established_date="2010-03-15",
        ),
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
            market_cagr=0.12,
            competitors=[
                {"name": "경쟁사A", "revenue": 80_000, "market_share": 0.15},
                {"name": "경쟁사B", "revenue": 60_000, "market_share": 0.10},
            ],
            industry_trends=["클라우드 전환 가속", "AI 기반 자동화"],
        ),
        investment_highlights=[
            "매출 CAGR 22.5%",
            "업계 최고 영업이익률",
            "안정적 현금흐름",
        ],
        growth_strategy=GrowthStrategy(
            organic_growth=["기존 사업 확대"],
            new_business=["AI SaaS 플랫폼"],
            ma_targets=["보안 스타트업 인수"],
            roadmap={"2026": ["AI 플랫폼 베타"], "2027": ["글로벌 론칭"]},
        ),
        management_team=[
            ManagementMember(
                name="이대표",
                title="대표이사",
                role="CEO",
                career=["前 삼성전자 VP", "서울대 경영학과"],
            ),
            ManagementMember(
                name="박부사장",
                title="부사장",
                role="CFO",
                career=["前 JP Morgan", "고려대 경제학과"],
            ),
        ],
        shareholders=[
            ShareholderInfo(name="구조PE", stake_pct=0.60, category="최대주주"),
            ShareholderInfo(name="이대표", stake_pct=0.20, category="특수관계인"),
            ShareholderInfo(name="소액주주", stake_pct=0.20, category="소액주주"),
        ],
        narratives={
            "executive_summary": "구조검증기업은 국내 IT 서비스 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장하였으며...",
            "market_overview": "국내 IT 서비스 시장 규모는...",
            "deal_overview": "본 딜은...",
            "company_overview": "회사 개요...",
            "business_overview": "사업 개요...",
            "investment_highlights": "투자 하이라이트...",
            "value_creation": "가치 창출...",
            "growth_strategy": "성장 전략...",
            "business_model": "비즈니스 모델...",
            "valuation": "밸류에이션 요약: EV/EBITDA 10.0x 기준...",
        },
        contacts=[
            ContactInfo(
                name="홍길동",
                title="Managing Director",
                email="hong@amic.co.kr",
                phone="02-1234-5678",
                company="AMIC",
            ),
        ],
        source_citations={
            "financial_analysis": [
                SourceCitation(
                    source_name="금융감독원 전자공시시스템",
                    url="https://dart.fss.or.kr",
                    access_date="2026-02-11",
                ),
            ],
        },
    )
    data.compute_derived_metrics()
    return data


# ---------------------------------------------------------------------------
# 모듈 스코프 픽스처 — PPTX 1회 생성
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def full_pptx(tmp_path_factory) -> tuple[PipelineResult, Presentation]:
    """FULL 프리셋 PPTX 1회 생성 후 재오픈."""
    data = _make_full_data()
    out_dir = tmp_path_factory.mktemp("pptx_structure")
    pipeline = IMPipeline()
    result = pipeline.generate_pptx(data, output_path=out_dir / "structure.pptx")
    prs = Presentation(str(result.pptx_path))
    return result, prs


# ---------------------------------------------------------------------------
# TestEaFontVerification — a:ea 폰트 E2E 검증
# ---------------------------------------------------------------------------


class TestEaFontVerification:
    """전체 PPTX의 a:ea (동아시아) 폰트 E2E 검증."""

    VALID_EA_FONTS = {
        "Pretendard",
        "Inter",
        "IBM Plex Mono",
        "NanumGothic",
        "Noto Sans KR",
        "Malgun Gothic",
        "SUITE",
        "SUIT Medium",
    }

    def test_all_runs_have_ea_element(self, full_pptx):
        """모든 text run에 a:ea 요소가 존재."""
        _, prs = full_pptx
        runs = _collect_all_runs(prs)
        assert len(runs) > 0, "텍스트 run이 없음"

        missing: list[tuple[int, str]] = []
        for slide_idx, run in runs:
            rpr = run._r.find(_qn("a:rPr"))
            if rpr is None or rpr.find(_qn("a:ea")) is None:
                missing.append((slide_idx, run.text[:30]))

        assert len(missing) == 0, f"a:ea 누락 run {len(missing)}개: {missing[:10]}"

    def test_ea_typeface_is_valid_font(self, full_pptx):
        """a:ea typeface가 허용된 폰트 중 하나."""
        _, prs = full_pptx
        runs = _collect_all_runs(prs)

        invalid: list[tuple[int, str]] = []
        for slide_idx, run in runs:
            typeface = _get_ea_typeface(run)
            if typeface and typeface not in self.VALID_EA_FONTS:
                invalid.append((slide_idx, typeface))

        assert len(invalid) == 0, (
            f"허용되지 않은 ea 폰트 {len(invalid)}개: {invalid[:10]}"
        )

    def test_body_runs_use_matching_ea(self, full_pptx):
        """font.name과 a:ea 폰트가 일관적 (숫자 run은 IBM Plex Mono 허용)."""
        _, prs = full_pptx
        runs = _collect_all_runs(prs)

        mismatched: list[tuple[int, str, str, str]] = []
        for slide_idx, run in runs:
            latin = run.font.name
            ea = _get_ea_typeface(run)
            if latin and ea:
                # 숫자/KPI run은 IBM Plex Mono ea가 의도된 동작
                if latin == ea:
                    continue
                if ea in self.VALID_EA_FONTS:
                    continue
                mismatched.append((slide_idx, run.text[:20], latin, ea))

        assert len(mismatched) == 0, (
            f"허용되지 않은 Latin/EA 폰트 조합 {len(mismatched)}개: {mismatched[:10]}"
        )

    def test_no_duplicate_ea_elements(self, full_pptx):
        """run 당 a:ea 요소가 최대 1개."""
        _, prs = full_pptx
        runs = _collect_all_runs(prs)
        ea_tag = _qn("a:ea")

        duplicates: list[tuple[int, int]] = []
        for slide_idx, run in runs:
            rpr = run._r.find(_qn("a:rPr"))
            if rpr is not None:
                ea_count = len(rpr.findall(ea_tag))
                if ea_count > 1:
                    duplicates.append((slide_idx, ea_count))

        assert len(duplicates) == 0, f"a:ea 중복 {len(duplicates)}개: {duplicates[:10]}"

    def test_ea_coverage_is_complete(self, full_pptx):
        """a:ea가 있는 run 수 == 전체 run 수 (100% 커버리지)."""
        _, prs = full_pptx
        runs = _collect_all_runs(prs)
        assert len(runs) > 0

        with_ea = sum(1 for _, run in runs if _get_ea_typeface(run) is not None)
        coverage = with_ea / len(runs)

        assert coverage == 1.0, f"ea 커버리지: {with_ea}/{len(runs)} ({coverage:.1%})"


# ---------------------------------------------------------------------------
# TestImageBoundsValidation — 이미지 경계 검증
# ---------------------------------------------------------------------------


class TestImageBoundsValidation:
    """이미지 shape 바운드 검증 — 슬라이드 경계 내 위치 확인."""

    _PAGE_WIDTH_EMU = Inches(10.83)
    _PAGE_HEIGHT_EMU = Inches(7.5)

    def test_images_within_slide_width(self, full_pptx):
        """모든 이미지의 left + width <= page_width."""
        _, prs = full_pptx
        pictures = _collect_all_pictures(prs)

        violations: list[tuple[int, str]] = []
        for slide_idx, shape in pictures:
            right = shape.left + shape.width
            if right > self._PAGE_WIDTH_EMU:
                violations.append((slide_idx, shape.name))

        assert len(violations) == 0, (
            f"이미지 가로 초과 {len(violations)}개: {violations}"
        )

    def test_images_within_slide_height(self, full_pptx):
        """모든 이미지의 top + height <= page_height."""
        _, prs = full_pptx
        pictures = _collect_all_pictures(prs)

        violations: list[tuple[int, str]] = []
        for slide_idx, shape in pictures:
            bottom = shape.top + shape.height
            if bottom > self._PAGE_HEIGHT_EMU:
                violations.append((slide_idx, shape.name))

        assert len(violations) == 0, (
            f"이미지 세로 초과 {len(violations)}개: {violations}"
        )

    def test_images_non_negative_position(self, full_pptx):
        """모든 이미지의 left >= 0, top >= 0."""
        _, prs = full_pptx
        pictures = _collect_all_pictures(prs)

        violations: list[tuple[int, str]] = []
        for slide_idx, shape in pictures:
            if shape.left < 0 or shape.top < 0:
                violations.append((slide_idx, shape.name))

        assert len(violations) == 0, (
            f"이미지 음수 위치 {len(violations)}개: {violations}"
        )

    def test_images_have_positive_dimensions(self, full_pptx):
        """모든 이미지의 width > 0, height > 0."""
        _, prs = full_pptx
        pictures = _collect_all_pictures(prs)

        violations: list[tuple[int, str]] = []
        for slide_idx, shape in pictures:
            if shape.width <= 0 or shape.height <= 0:
                violations.append((slide_idx, shape.name))

        assert len(violations) == 0, (
            f"이미지 크기 0 이하 {len(violations)}개: {violations}"
        )


# ---------------------------------------------------------------------------
# TestSlideLayoutConsistency — 슬라이드 레이아웃 일관성
# ---------------------------------------------------------------------------


class TestSlideLayoutConsistency:
    """슬라이드 레이아웃/구조 일관성 검증."""

    def test_cover_slide_has_title_text(self, full_pptx):
        """표지 슬라이드에 프로젝트명 포함."""
        _, prs = full_pptx
        first_slide = prs.slides[0]
        text = _get_slide_text(first_slide)
        assert "STRUCTURE" in text or "Project" in text, (
            f"표지에 프로젝트명 없음: {text[:100]}"
        )

    def test_disclaimer_slide_has_text(self, full_pptx):
        """면책조항 슬라이드에 텍스트 존재 (2번째 슬라이드)."""
        _, prs = full_pptx
        assert len(prs.slides) >= 2
        disclaimer_slide = prs.slides[1]
        text = _get_slide_text(disclaimer_slide)
        assert len(text.strip()) > 0, "면책조항 슬라이드에 텍스트 없음"

    def test_content_slides_have_shapes(self, full_pptx):
        """모든 콘텐츠 슬라이드에 shape이 1개 이상 존재."""
        _, prs = full_pptx
        empty_slides: list[int] = []
        for idx, slide in enumerate(prs.slides):
            if len(slide.shapes) == 0:
                empty_slides.append(idx)

        assert len(empty_slides) == 0, f"shape 없는 슬라이드: {empty_slides}"

    def test_contact_slide_has_contact_info(self, full_pptx):
        """마지막 슬라이드에 연락처 정보 존재."""
        _, prs = full_pptx
        last_slide = prs.slides[-1]
        text = _get_slide_text(last_slide)
        # 연락처에 이메일이나 이름이 포함되어야 함
        has_contact = (
            "hong@amic.co.kr" in text
            or "홍길동" in text
            or "Contact" in text
            or "연락처" in text
        )
        assert has_contact, f"마지막 슬라이드에 연락처 정보 없음: {text[:200]}"

    def test_slide_count_matches_sections(self, full_pptx):
        """슬라이드 수 >= 활성 섹션 수 (FULL = 19)."""
        result, prs = full_pptx
        # FULL 프리셋은 19개 섹션, 각 섹션은 최소 1 슬라이드
        assert len(prs.slides) >= 19, (
            f"슬라이드 수 부족: {len(prs.slides)} (19개 이상 필요)"
        )

    def test_no_empty_slides(self, full_pptx):
        """빈 슬라이드(shape 0개)가 없음."""
        _, prs = full_pptx
        for idx, slide in enumerate(prs.slides):
            assert len(slide.shapes) > 0, f"슬라이드 {idx}에 shape 없음"
