"""SWITCH TM 템플릿 매핑 — 24슬라이드, 차트 7개, 테이블 15개.

실측 데이터 기반 shape 매핑 (2026-02-26 분석).
구조: Cover → Disclaimer → [TOC → 섹션] × 4그룹 → Contact
Andersen 공동 브랜딩 포함.
"""

from __future__ import annotations

from src.template_engine.mappings._types import SlideMapping, SlotMapping

SWITCH_TM_MAPPING: list[SlideMapping] = [
    # Slide 0: Cover
    SlideMapping(slide_idx=0, description="Cover", slots=[]),

    # Slide 1: Disclaimer
    SlideMapping(slide_idx=1, description="Disclaimer", slots=[]),

    # ── Group 1: Executive Summary ──
    # Slide 2: TOC
    SlideMapping(slide_idx=2, description="Table of Contents", slots=[]),

    # Slide 3: Executive Summary
    SlideMapping(
        slide_idx=3,
        description="Executive Summary — 거래 개요 테이블",
        slots=[],  # 복합 테이블 + 텍스트
    ),

    # Slide 4: Target Positioning (62 shapes!)
    SlideMapping(
        slide_idx=4,
        description="Target Positioning — 62 shapes 포지셔닝 맵",
        slots=[],  # 매우 복잡한 시각적 레이아웃
    ),

    # Slide 5: Investment Highlights
    SlideMapping(
        slide_idx=5,
        description="Investment Highlights — 핵심 투자 매력",
        slots=[],
    ),

    # ── Group 2: Market Opportunity ──
    # Slide 6: TOC
    SlideMapping(slide_idx=6, description="Table of Contents", slots=[]),

    # Slide 7: Global Market Outlook
    SlideMapping(
        slide_idx=7,
        description="Global Market Outlook — 시장 규모 차트",
        slots=[
            SlotMapping("차트 12", "global_market_chart", "chart"),
        ],
    ),

    # Slide 8: Key Market Driver (1) — AI Supercycle
    SlideMapping(
        slide_idx=8,
        description="AI Supercycle — 2 line charts",
        slots=[],  # LINE_MARKERS × 2
    ),

    # Slide 9: Key Market Driver (2) — Electrification
    SlideMapping(
        slide_idx=9,
        description="Electrification — 2 bar charts",
        slots=[],  # COLUMN_CLUSTERED × 2
    ),

    # Slide 10: Key Market Driver (3) — Aging Grid
    SlideMapping(
        slide_idx=10,
        description="Aging Grid — bar chart",
        slots=[
            SlotMapping("차트 12", "aging_grid_chart", "chart"),
        ],
    ),

    # Slide 11: Opportunity for Korean Suppliers
    SlideMapping(
        slide_idx=11,
        description="Korean Suppliers Opportunity — stacked bar + table",
        slots=[
            SlotMapping("차트 12", "korean_supplier_chart", "chart"),
        ],
    ),

    # ── Group 3: Target Highlights ──
    # Slide 12: TOC
    SlideMapping(slide_idx=12, description="Table of Contents", slots=[]),

    # Slide 13: Full-Range Product Portfolio
    SlideMapping(
        slide_idx=13,
        description="Product Portfolio — 이미지 + 테이블",
        slots=[],
    ),

    # Slide 14: Competitive Landscape
    SlideMapping(
        slide_idx=14,
        description="Competitive Landscape — 비교 테이블",
        slots=[],
    ),

    # Slide 15: US Production Advantage
    SlideMapping(
        slide_idx=15,
        description="US Production Advantage — 테이블",
        slots=[],
    ),

    # Slide 16: US Market Track Record & Pipeline
    SlideMapping(
        slide_idx=16,
        description="Track Record — 프로젝트 테이블 + 로고",
        slots=[],
    ),

    # Slide 17: Key Production Strategy
    SlideMapping(
        slide_idx=17,
        description="Production Strategy — 테이블 + 이미지",
        slots=[],
    ),

    # Slide 18: US Market Growth Roadmap
    SlideMapping(
        slide_idx=18,
        description="Growth Roadmap — AutoShape 프로세스 다이어그램",
        slots=[],
    ),

    # ── Group 4: Financial Summary ──
    # Slide 19: TOC
    SlideMapping(slide_idx=19, description="Table of Contents", slots=[]),

    # Slide 20: S社 재무제표 — 손익계산서
    SlideMapping(
        slide_idx=20,
        description="S社 손익계산서",
        slots=[
            SlotMapping("표 7", "s_company_is_table", "table"),
        ],
    ),

    # Slide 21: S社 재무제표 — 대차대조표
    SlideMapping(
        slide_idx=21,
        description="S社 대차대조표",
        slots=[
            SlotMapping("표 7", "s_company_bs_table", "table"),
        ],
    ),

    # Slide 22: N社 재무제표
    SlideMapping(
        slide_idx=22,
        description="N社 재무제표",
        slots=[
            SlotMapping("표 7", "n_company_financial_table", "table"),
        ],
    ),

    # Slide 23: Contact
    SlideMapping(slide_idx=23, description="Contact", slots=[]),
]
