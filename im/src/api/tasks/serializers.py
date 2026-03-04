"""IMDocumentData ↔ dict 직렬화 변환 모듈 (T-I12, T-I19 보강).

> 마지막 수정: 2026-02-10 23:30:00

Celery 태스크 간 JSON-serializable dict로 데이터를 전달하기 위한 변환 쌍을 제공한다.
dict_to_im_data는 모든 중첩 dataclass를 올바르게 복원한다.
"""

from __future__ import annotations

import dataclasses
import enum
from decimal import Decimal
from typing import Any


def _make_json_serializable(obj: Any) -> Any:
    """객체를 JSON 직렬화 가능한 형태로 변환한다.

    Args:
        obj: 변환할 객체.

    Returns:
        JSON 직렬화 가능한 객체.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, enum.Enum):
        return obj.value
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            k: _make_json_serializable(v) for k, v in dataclasses.asdict(obj).items()
        }
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_serializable(item) for item in obj]
    return obj


def im_data_to_dict(data: Any) -> dict[str, Any]:
    """IMDocumentData → JSON-serializable dict 변환.

    Args:
        data: IMDocumentData 인스턴스.

    Returns:
        JSON 직렬화 가능한 dict.
    """
    if dataclasses.is_dataclass(data) and not isinstance(data, type):
        raw = dataclasses.asdict(data)
    elif isinstance(data, dict):
        raw = data
    else:
        raise TypeError(f"지원하지 않는 타입입니다: {type(data)}")

    return _make_json_serializable(raw)


def dict_to_im_data(d: dict[str, Any]) -> Any:
    """dict → IMDocumentData 역변환.

    모든 중첩 dataclass를 올바르게 복원한다.
    lazy import로 순환 의존성을 방지한다.

    Args:
        d: JSON dict.

    Returns:
        IMDocumentData 인스턴스.
    """
    from src.design_renderer.im_document import (
        ChartData,
        CompanyOverview,
        ContactInfo,
        Currency,
        DealStructure,
        FinancialStatements,
        GrowthStrategy,
        IMDocumentData,
        IMStyle,
        ManagementMember,
        MarketData,
        NumberFormatConfig,
        SegmentRevenue,
        ShareholderInfo,
        SourceCitation,
        TransactionType,
    )

    data = dict(d)  # 원본 변경 방지

    # ── Enum 복원 ──
    if "im_style" in data and isinstance(data["im_style"], str):
        try:
            data["im_style"] = IMStyle(data["im_style"])
        except ValueError:
            pass

    # ── FinancialStatements ──
    if "financial_statements" in data and isinstance(
        data["financial_statements"], dict
    ):
        data["financial_statements"] = FinancialStatements(
            **data["financial_statements"]
        )

    # ── DealStructure ──
    if "deal_structure" in data and isinstance(data["deal_structure"], dict):
        ds = dict(data["deal_structure"])
        if "transaction_type" in ds and isinstance(ds["transaction_type"], str):
            try:
                ds["transaction_type"] = TransactionType(ds["transaction_type"])
            except ValueError:
                pass
        data["deal_structure"] = DealStructure(**ds)

    # ── CompanyOverview ──
    if "company_overview" in data and isinstance(data["company_overview"], dict):
        data["company_overview"] = CompanyOverview(**data["company_overview"])

    # ── MarketData ──
    if "market_data" in data and isinstance(data["market_data"], dict):
        data["market_data"] = MarketData(**data["market_data"])

    # ── GrowthStrategy ──
    if "growth_strategy" in data and isinstance(data["growth_strategy"], dict):
        data["growth_strategy"] = GrowthStrategy(**data["growth_strategy"])

    # ── ManagementMember list ──
    if "management_team" in data and isinstance(data["management_team"], list):
        data["management_team"] = [
            ManagementMember(**m) if isinstance(m, dict) else m
            for m in data["management_team"]
        ]

    # ── ShareholderInfo list ──
    if "shareholders" in data and isinstance(data["shareholders"], list):
        data["shareholders"] = [
            ShareholderInfo(**s) if isinstance(s, dict) else s
            for s in data["shareholders"]
        ]

    # ── NumberFormatConfig ──
    if "number_format" in data and isinstance(data["number_format"], dict):
        nf = dict(data["number_format"])
        if "currency" in nf and isinstance(nf["currency"], str):
            try:
                nf["currency"] = Currency(nf["currency"])
            except ValueError:
                pass
        data["number_format"] = NumberFormatConfig(**nf)

    # ── SegmentRevenue ──
    if "segment_revenue" in data and isinstance(data["segment_revenue"], dict):
        data["segment_revenue"] = SegmentRevenue(**data["segment_revenue"])

    # ── ChartData ──
    if "charts" in data and isinstance(data["charts"], dict):
        charts: dict[str, list[ChartData]] = {}
        for section_id, chart_list in data["charts"].items():
            if isinstance(chart_list, list):
                charts[section_id] = [
                    ChartData(**c) if isinstance(c, dict) else c for c in chart_list
                ]
            else:
                charts[section_id] = chart_list
        data["charts"] = charts

    # ── SourceCitation ──
    if "source_citations" in data and isinstance(data["source_citations"], dict):
        citations: dict[str, list[SourceCitation]] = {}
        for section_id, cit_list in data["source_citations"].items():
            if isinstance(cit_list, list):
                citations[section_id] = [
                    SourceCitation(**c) if isinstance(c, dict) else c for c in cit_list
                ]
            else:
                citations[section_id] = cit_list
        data["source_citations"] = citations

    # ── ContactInfo list ──
    if "contacts" in data and isinstance(data["contacts"], list):
        data["contacts"] = [
            ContactInfo(**c) if isinstance(c, dict) else c for c in data["contacts"]
        ]

    # ── BrandAssets (런타임 import) ──
    if "brand_assets" in data and isinstance(data["brand_assets"], dict):
        try:
            from src.brand_extractor.models import (
                BrandAssets,
                ExtractedColor,
                LogoCandidate,
            )

            ba = dict(data["brand_assets"])
            if "colors" in ba and isinstance(ba["colors"], list):
                restored_colors = []
                for c in ba["colors"]:
                    if isinstance(c, dict):
                        cd = dict(c)
                        # tuple 복원 (asdict가 tuple→list 변환)
                        if "rgb" in cd and isinstance(cd["rgb"], list):
                            cd["rgb"] = tuple(cd["rgb"])
                        if "hsv" in cd and isinstance(cd["hsv"], list):
                            cd["hsv"] = tuple(cd["hsv"])
                        restored_colors.append(ExtractedColor(**cd))
                    else:
                        restored_colors.append(c)
                ba["colors"] = restored_colors
            if "logo_candidates" in ba and isinstance(ba["logo_candidates"], list):
                ba["logo_candidates"] = [
                    LogoCandidate(**lc) if isinstance(lc, dict) else lc
                    for lc in ba["logo_candidates"]
                ]
            data["brand_assets"] = BrandAssets(**ba)
        except ImportError:
            pass  # BrandAssets 미설치 시 dict 유지

    return IMDocumentData(**data)
