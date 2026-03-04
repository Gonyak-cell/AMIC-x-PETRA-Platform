"""SPICY TM 템플릿 매핑 — 25슬라이드, 차트 10개, 테이블 18개.

실측 데이터 기반 shape 매핑 (2026-02-26 분석).
구조: Cover → Disclaimer → [TOC → 섹션] × 4그룹 → Contact
"""

from __future__ import annotations

from src.template_engine.mappings._types import SlideMapping, SlotMapping

SPICY_TM_MAPPING: list[SlideMapping] = [
    # Slide 0: Cover
    SlideMapping(slide_idx=0, description="Cover", slots=[]),
    # Slide 1: Disclaimer
    SlideMapping(slide_idx=1, description="Disclaimer", slots=[]),
    # ── Group 1: Executive Summary ──
    # Slide 2: TOC
    SlideMapping(slide_idx=2, description="Table of Contents", slots=[]),
    # Slide 3: Execution Summary
    SlideMapping(
        slide_idx=3,
        description="Execution Summary — 회사 개요 테이블 + 거래 조건",
        slots=[
            SlotMapping("표 15", "execution_summary_table", "table"),
        ],
    ),
    # Slide 4: Target Positioning (40 shapes — 포지셔닝 맵)
    SlideMapping(
        slide_idx=4,
        description="Target Positioning — 시장 포지셔닝 다이어그램",
        slots=[],  # 복잡한 shape 레이아웃: LLM이 텍스트만 교체
    ),
    # Slide 5: Investment Highlights
    SlideMapping(
        slide_idx=5,
        description="Investment Highlights — 핵심 투자 매력",
        slots=[],  # Group shapes — 구조적 교체 어려움
    ),
    # ── Group 2: Market Opportunity ──
    # Slide 6: TOC
    SlideMapping(slide_idx=6, description="Table of Contents", slots=[]),
    # Slide 7: Market Outlook
    SlideMapping(
        slide_idx=7,
        description="Market Outlook — 시장 규모 추이 차트",
        slots=[
            SlotMapping("차트 12", "market_size_chart", "chart"),
        ],
    ),
    # Slide 8: Key Demand Driver (1)
    SlideMapping(
        slide_idx=8,
        description="Key Demand Driver (1) — 수요 요인 + 차트 + 테이블",
        slots=[
            SlotMapping("차트 12", "demand_driver_1_chart", "chart"),
        ],
    ),
    # Slide 9: Key Demand Driver (2)
    SlideMapping(
        slide_idx=9,
        description="Key Demand Driver (2) — 글로벌 수요 트렌드",
        slots=[
            SlotMapping("차트 12", "demand_driver_2_chart", "chart"),
        ],
    ),
    # Slide 10: Key Supply Driver (1)
    SlideMapping(
        slide_idx=10,
        description="Key Supply Driver (1) — 공급 요인 차트",
        slots=[
            SlotMapping("차트 12", "supply_driver_1_chart", "chart"),
        ],
    ),
    # Slide 11: Key Supply Driver (2)
    SlideMapping(
        slide_idx=11,
        description="Key Supply Driver (2) — 공급 집중 트렌드",
        slots=[],
    ),
    # ── Group 3: Target Highlights ──
    # Slide 12: TOC
    SlideMapping(slide_idx=12, description="Table of Contents", slots=[]),
    # Slide 13: Target Overview
    SlideMapping(
        slide_idx=13,
        description="Target Overview — 회사 개요 + 매출 차트",
        slots=[
            SlotMapping("차트 12", "target_revenue_chart", "chart"),
        ],
    ),
    # Slide 14: Target Highlights (1) — 제품 포트폴리오
    SlideMapping(
        slide_idx=14,
        description="제품 포트폴리오 — 도넛 차트 + 테이블",
        slots=[],  # 도넛 차트 2개 + 테이블 + 텍스트 복합
    ),
    # Slide 15: Target Highlights (2) — 고객 네트워크
    SlideMapping(
        slide_idx=15,
        description="고객 네트워크 — 도넛 차트 + 테이블 + 로고",
        slots=[],  # 도넛 차트 2개 + 테이블 + Picture
    ),
    # Slide 16: Target Highlights (3) — 제조 인프라
    SlideMapping(
        slide_idx=16,
        description="제조 인프라 — 이미지 + 테이블",
        slots=[],
    ),
    # Slide 17: Target Highlights (4) — 원재료 수급
    SlideMapping(
        slide_idx=17,
        description="원재료 수급 — 누적 막대 차트",
        slots=[
            SlotMapping("차트 12", "raw_material_chart", "chart"),
        ],
    ),
    # Slide 18: Target Highlights (5) — 확장 전략
    SlideMapping(
        slide_idx=18,
        description="수직·수평 확장 — Upside 실현 전략",
        slots=[],
    ),
    # ── Group 4: Financial Summary ──
    # Slide 19: TOC
    SlideMapping(slide_idx=19, description="Table of Contents", slots=[]),
    # Slide 20: Pro-Forma 사업계획
    SlideMapping(
        slide_idx=20,
        description="Pro-Forma 사업계획 — 전략 개요",
        slots=[],
    ),
    # Slide 21: Pro-Forma 재무제표
    SlideMapping(
        slide_idx=21,
        description="대상회사 Pro-Forma 재무제표",
        slots=[
            SlotMapping("표 7", "proforma_financial_table", "table"),
        ],
    ),
    # Slide 22: 자회사 H 재무제표
    SlideMapping(
        slide_idx=22,
        description="H 자회사 재무제표",
        slots=[
            SlotMapping("표 7", "subsidiary_h_financial_table", "table"),
        ],
    ),
    # Slide 23: 자회사 E 재무제표
    SlideMapping(
        slide_idx=23,
        description="E 자회사 재무제표",
        slots=[
            SlotMapping("표 7", "subsidiary_e_financial_table", "table"),
        ],
    ),
    # Slide 24: Contact
    SlideMapping(slide_idx=24, description="Contact", slots=[]),
]
