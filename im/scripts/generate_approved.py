"""승인 PNG baseline 생성 스크립트 — IM (tm_default / dm_default / im_full).

> 마지막 수정: 2026-03-14

Usage::

    # 전체 variant (tm_default, dm_default, im_full)
    python scripts/generate_approved.py

    # 특정 variant만
    python scripts/generate_approved.py --variant tm_default dm_default

    # 기존 approved 있어도 강제 덮어쓰기
    python scripts/generate_approved.py --force

사전 요건:
    - LibreOffice headless 설치 (``libreoffice --headless`` 실행 가능)
    - pdf2image + poppler 설치
    - im/ 루트에서 실행 (PYTHONPATH 자동 설정)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.design_renderer.im_document import FinancialStatements, IMDocumentData

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
# 스크립트는 im/scripts/ 에 위치 → 부모의 부모가 im/ 루트
_SCRIPT_DIR = Path(__file__).resolve().parent
_MODULE_ROOT = _SCRIPT_DIR.parent  # im/

if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

_FIXTURES_DIR = _MODULE_ROOT / "tests" / "fixtures" / "golden_samples"
_VISUAL_DIFF_DIR = _MODULE_ROOT / "tests" / "visual_diff"

VARIANTS: list[str] = ["tm_default", "dm_default", "im_full"]


# ── Fixture 함수 (conftest.py 패턴 재사용, pytest 데코레이터 제거) ─────────────


def _make_financial_statements() -> "FinancialStatements":
    """3개년 공통 재무 데이터를 구성한다."""
    from src.design_renderer.im_document import FinancialStatements

    return FinancialStatements(
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


def _make_titan_data() -> "IMDocumentData":
    """TITAN 프리셋 IMDocumentData를 구성한다 (tm_default 사용)."""
    from src.design_renderer.im_document import (
        ContactInfo,
        IMDocumentData,
        IMStyle,
        MarketData,
    )

    data = IMDocumentData(
        project_name="Project TITAN",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        date="2026-02-08",
        im_style=IMStyle.TITAN,
        financial_statements=_make_financial_statements(),
        investment_highlights=[
            "매출 CAGR 22.5% (3개년)",
            "영업이익률 18.7%로 업계 상위",
            "안정적 현금흐름 및 낮은 부채비율",
        ],
        contacts=[
            ContactInfo(
                name="홍길동",
                title="Managing Director",
                email="hong@amic.co.kr",
                phone="02-1234-5678",
                company="AMIC",
            )
        ],
        narratives={
            "executive_summary": "테스트기업은 국내 IT 서비스 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장하였으며...",
            "market_overview": "국내 IT 서비스 시장 규모는...",
            "business_overview": "테스트기업의 사업 구조는...",
            "investment_highlights": "테스트기업의 투자 매력은...",
        },
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
        ),
    )
    data.compute_derived_metrics()
    return data


def _make_covenant_data() -> "IMDocumentData":
    """COVENANT 프리셋 IMDocumentData를 구성한다 (dm_default 사용)."""
    from src.design_renderer.im_document import (
        CompanyOverview,
        ContactInfo,
        DealStructure,
        IMDocumentData,
        IMStyle,
        MarketData,
        TransactionType,
    )

    data = IMDocumentData(
        project_name="Project COVENANT",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        date="2026-02-08",
        im_style=IMStyle.COVENANT,
        financial_statements=_make_financial_statements(),
        investment_highlights=[
            "전략적 파트너십을 통한 시너지. 국내외 파트너 네트워크를 활용한 사업 확장",
            "디지털 전환 선도. 클라우드 및 AI 기반 서비스 전환 가속",
            "안정적 수익 구조. 반복 매출 비중 70% 이상으로 예측 가능한 현금흐름",
        ],
        deal_structure=DealStructure(
            seller="테스트PE",
            stake_pct=0.51,
            transaction_type=TransactionType.MA,
            deal_background="전략적 포트폴리오 재구성을 위한 지분 매각",
        ),
        market_data=MarketData(
            tam=500_000,
            sam=200_000,
            som=50_000,
            market_growth_rate=0.08,
        ),
        company_overview=CompanyOverview(
            history=[{"year": "2010", "event": "설립"}],
            business_model="B2B IT 서비스",
            employee_count=300,
        ),
        contacts=[ContactInfo(name="김철수", title="Partner", email="kim@amic.co.kr")],
        narratives={
            "executive_summary": "테스트기업은...",
            "value_creation": "가치 창출 전략은...",
            "company_overview": "회사 개요...",
            "market_overview": "시장 개요...",
            "financial_analysis": "재무 분석...",
            "investment_highlights": "투자 하이라이트...",
        },
    )
    data.compute_derived_metrics()
    return data


def _make_full_data() -> "IMDocumentData":
    """FULL 프리셋 IMDocumentData를 구성한다 (im_full 사용)."""
    from src.design_renderer.im_document import (
        ChartData,
        CompanyOverview,
        ContactInfo,
        DealStructure,
        GrowthStrategy,
        IMDocumentData,
        IMStyle,
        ManagementMember,
        MarketData,
        ShareholderInfo,
        SourceCitation,
        TransactionType,
        ValuationData,
    )

    data = IMDocumentData(
        project_name="Project FULL",
        company_name_kr="테스트기업",
        company_name_en="Test Corp",
        corp_code="00123456",
        website_url="https://test-corp.co.kr",
        date="2026-02-08",
        im_style=IMStyle.FULL,
        financial_statements=_make_financial_statements(),
        deal_structure=DealStructure(
            seller="테스트PE",
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
            ShareholderInfo(name="테스트PE", stake_pct=0.60, category="최대주주"),
            ShareholderInfo(name="이대표", stake_pct=0.20, category="특수관계인"),
            ShareholderInfo(name="소액주주", stake_pct=0.20, category="소액주주"),
        ],
        narratives={
            "executive_summary": "테스트기업은 국내 IT 서비스 시장의 선도기업으로...",
            "financial_analysis": "최근 3개년 매출은 연평균 22.5% 성장하였으며...",
            "market_overview": "국내 IT 서비스 시장은...",
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
            ),
        ],
        source_citations={
            "financial_analysis": [
                SourceCitation(
                    source_name="금융감독원 전자공시시스템",
                    url="https://dart.fss.or.kr",
                    access_date="2026-02-08",
                ),
            ],
            "market_overview": [
                SourceCitation(
                    source_name="한국IDC 보고서",
                    access_date="2026-01",
                    document_title="2025 IT 서비스 시장 전망",
                ),
            ],
        },
        valuation_data=ValuationData(
            ev_ebitda={"2022": 8.5, "2023": 9.2, "2024": 10.0},
            pe_ratio={"2022": 15.0, "2023": 16.5, "2024": 18.0},
            ev_revenue={"2022": 2.0, "2023": 2.5, "2024": 3.0},
            moic_scenarios={"base": 2.5, "upside": 3.2, "downside": 1.8},
            irr_scenarios={
                "base": {"irr": 0.20, "holding_period": 5, "exit_multiple": 10.0},
                "upside": {"irr": 0.28, "holding_period": 4, "exit_multiple": 12.0},
                "downside": {"irr": 0.12, "holding_period": 6, "exit_multiple": 8.0},
            },
        ),
        charts={
            "financial_analysis": [
                ChartData(
                    chart_type="combo",
                    title="매출 및 영업이익 추이",
                    data={
                        "categories": ["2022", "2023", "2024"],
                        "bar_series": [
                            {"name": "매출", "values": [100_000, 120_000, 150_000]}
                        ],
                        "line_series": [
                            {
                                "name": "영업이익률",
                                "values": [0.15, 0.167, 0.187],
                            }
                        ],
                    },
                ),
            ],
        },
    )
    data.compute_derived_metrics()
    return data


# variant → fixture 함수 매핑
_FIXTURE_BUILDERS: dict[str, object] = {
    "tm_default": _make_titan_data,
    "dm_default": _make_covenant_data,
    "im_full": _make_full_data,
}


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────


def check_libreoffice() -> None:
    """LibreOffice 설치 여부를 확인한다. 없으면 에러 메시지 출력 후 exit(1)."""
    from tests.visual_diff.diff_utils import _find_libreoffice

    try:
        _find_libreoffice()
    except FileNotFoundError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)


def clean_approved_pngs(approved_dir: Path) -> int:
    """approved/ 디렉토리의 기존 slide_*.png를 삭제하고 삭제 수를 반환한다."""
    if not approved_dir.exists():
        approved_dir.mkdir(parents=True, exist_ok=True)
        return 0
    removed = 0
    for png in approved_dir.glob("slide_*.png"):
        png.unlink()
        removed += 1
    return removed


def generate_variant(variant: str, force: bool) -> None:
    """단일 variant의 승인 PNG를 생성한다."""
    from src.design_renderer.pipeline import IMPipeline
    from tests.visual_diff.diff_utils import pptx_to_pngs

    approved_dir = _FIXTURES_DIR / variant / "approved"

    # --force 없이 기존 PNG가 있으면 건너뜀
    if not force and any(approved_dir.glob("slide_*.png")):
        existing = list(approved_dir.glob("slide_*.png"))
        print(
            f"[{variant}] approved/ 에 이미 {len(existing)}개의 PNG가 있습니다.\n"
            f"  덮어쓰려면 --force 옵션을 사용하세요. 건너뜁니다."
        )
        return

    print(f"[{variant}] 생성 시작...")

    # 1. IMDocumentData 구성
    builder = _FIXTURE_BUILDERS[variant]
    data = builder()  # type: ignore[operator]

    # 2. PPTX 생성 (임시 디렉토리 사용)
    pipeline = IMPipeline()
    with tempfile.TemporaryDirectory() as tmpdir:
        pptx_path = Path(tmpdir) / f"{variant}.pptx"
        result = pipeline.generate_pptx(data, output_path=str(pptx_path))

        if not result.success:
            errors_str = "; ".join(result.errors)
            raise RuntimeError(f"PPTX 생성 실패: {errors_str}")

        print(
            f"  PPTX 생성 완료: {result.total_pptx_slides}개 슬라이드"
            f" (경고 {len(result.warnings)}건)"
        )

        # 3. PNG 변환
        png_tmp_dir = Path(tmpdir) / "pngs"
        png_paths = pptx_to_pngs(str(pptx_path), str(png_tmp_dir), dpi=150)

        if not png_paths:
            print(
                "  경고: PNG 변환 결과가 없습니다. LibreOffice/pdf2image 확인 필요.",
                file=sys.stderr,
            )
            return

        print(f"  PNG 변환 완료: {len(png_paths)}개")

        # 4. 기존 approved PNG 정리
        removed = clean_approved_pngs(approved_dir)
        if removed:
            print(f"  기존 PNG {removed}개 삭제")

        # 5. 새 PNG를 approved/ 에 복사
        for png_src in sorted(Path(png_tmp_dir).glob("slide_*.png")):
            dst = approved_dir / png_src.name
            shutil.copy2(str(png_src), str(dst))

    # 6. 결과 출력
    final_pngs = sorted(approved_dir.glob("slide_*.png"))
    print(f"  저장 완료: {approved_dir}")
    for p in final_pngs:
        print(f"    {p.name}")
    print(f"  슬라이드 수: {len(final_pngs)}개\n")


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """CLI 인수를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="IM golden sample 승인 PNG baseline 생성",
    )
    parser.add_argument(
        "--variant",
        nargs="*",
        choices=VARIANTS,
        default=None,
        metavar="VARIANT",
        help=f"생성할 variant ({', '.join(VARIANTS)}). 미지정 시 전체 생성.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 approved PNG가 있어도 덮어쓰기.",
    )
    return parser.parse_args()


def main() -> None:
    """메인 진입점."""
    args = parse_args()
    targets: list[str] = args.variant if args.variant else VARIANTS

    check_libreoffice()

    print(f"=== IM 승인 PNG 생성 (variant: {targets}) ===\n")

    errors: list[str] = []
    for variant in targets:
        try:
            generate_variant(variant, force=args.force)
        except FileNotFoundError as exc:
            msg = f"[{variant}] 파일 없음: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)
        except Exception as exc:
            msg = f"[{variant}] 생성 실패: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)

    if errors:
        print(f"\n오류 {len(errors)}건 발생:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    print("=== 완료 ===")


if __name__ == "__main__":
    main()
