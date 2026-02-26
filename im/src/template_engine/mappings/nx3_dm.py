"""NX3 Games DM 템플릿 매핑 — 7슬라이드, 차트 3개, 테이블 3개.

실측 데이터 기반 shape 매핑 (2026-02-26 분석):
- Slide 1: Cover (TextBox 1, 3, 4, 12, Picture 2)
- Slide 2: 글로벌 M&A 시장 회복 (차트 12: COLUMN_CLUSTERED, 2 series)
- Slide 3: 글로벌 M&A 거래액 추이 (차트 12: COLUMN_CLUSTERED, 1 series)
- Slide 4: 주요 글로벌 M&A 현황 (표 10: 8×5)
- Slide 5: 주요 글로벌 M&A 핵심 트렌드 (표 10: 8×3)
- Slide 6: 미국 투자 전략 (표 9: 4×3, 차트 12: COLUMN_CLUSTERED)
- Slide 7: 미국 SPAC 합병 절차 (24 AutoShapes — 프로세스 다이어그램)
"""

from __future__ import annotations

from src.template_engine.mappings._types import SlideMapping, SlotMapping


NX3_DM_MAPPING: list[SlideMapping] = [
    # Slide 0: Cover
    SlideMapping(
        slide_idx=0,
        description="Cover",
        slots=[
            SlotMapping("TextBox 3", "project_name", "text"),
            SlotMapping("TextBox 12", "date", "text"),
            SlotMapping("TextBox 4", "memo_type_label", "text"),
        ],
    ),
    # Slide 1: 글로벌 M&A 시장 회복
    SlideMapping(
        slide_idx=1,
        description="글로벌 M&A 시장 회복 — 연도별 거래금액 + YoY 성장률",
        slots=[
            SlotMapping("차트 12", "global_ma_volume_chart", "chart"),
        ],
    ),
    # Slide 2: 글로벌 M&A 거래액 추이
    SlideMapping(
        slide_idx=2,
        description="글로벌 M&A 거래액 추이 — 분기별 거래건수",
        slots=[
            SlotMapping("차트 12", "global_ma_quarterly_chart", "chart"),
        ],
    ),
    # Slide 3: 주요 M&A 현황
    SlideMapping(
        slide_idx=3,
        description="주요 글로벌 M&A 현황 — Comparable deals 테이블",
        slots=[
            SlotMapping("표 10", "comparable_deals_table", "table"),
        ],
    ),
    # Slide 4: 주요 M&A 핵심 트렌드
    SlideMapping(
        slide_idx=4,
        description="주요 글로벌 M&A 핵심 트렌드 — 거래 비교 요약",
        slots=[
            SlotMapping("표 10", "deal_trends_table", "table"),
        ],
    ),
    # Slide 5: 미국 투자 전략
    SlideMapping(
        slide_idx=5,
        description="미국 투자 전략 — 상장방법 비교 + SPAC 통계",
        slots=[
            SlotMapping("표 9", "listing_methods_table", "table"),
            SlotMapping("차트 12", "spac_volume_chart", "chart"),
        ],
    ),
    # Slide 6: SPAC 합병 상장 절차 (프로세스 다이어그램 — 텍스트만 교체)
    SlideMapping(
        slide_idx=6,
        description="미국 SPAC 합병 상장 절차 — 프로세스 다이어그램",
        slots=[],  # AutoShape 15개 + TextBox 6개: LLM이 구조 생성, 텍스트만 교체
    ),
]
