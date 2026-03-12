"""워크스페이스 요약 — 탭 배지 카운트용 경량 응답."""

from __future__ import annotations

from pydantic import BaseModel


class WorkspaceSummary(BaseModel):
    """거래 워크스페이스 탭별 항목 수 (배지 카운트).

    단일 API 호출로 모든 탭 배지를 한 번에 채울 수 있도록
    13개 엔티티의 COUNT(*)를 집계한다.
    """

    buyer_count: int = 0
    engagement_count: int = 0
    timeline_count: int = 0
    nda_count: int = 0
    bid_count: int = 0
    dd_item_count: int = 0
    contract_count: int = 0
    closing_item_count: int = 0
    pmi_count: int = 0
    earnout_count: int = 0
    marketing_material_count: int = 0
    financial_model_count: int = 0
    legal_document_count: int = 0
