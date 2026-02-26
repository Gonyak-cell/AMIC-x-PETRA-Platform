"""YTN Structure DM 템플릿 매핑 — 6슬라이드, 차트 0개, 테이블 3개.

실측 데이터 기반 shape 매핑 (2026-02-26 분석):
- Slide 0: Cover
- Slide 1: 거래 구조 설계 고려사항 (AutoShape 듀얼 패널)
- Slide 2: 구주 매입 대상 선정 및 전략 (AutoShape 5단계 카드)
- Slide 3: 매입가액 및 투자금 (표 11: 15×9 + AutoShape 설명)
- Slide 4: 법률·세무 의견 (표 8: 3×3)
- Slide 5: Key Man Retention 방안 (표 5: 3×2)
"""

from __future__ import annotations

from src.template_engine.mappings._types import SlideMapping, SlotMapping

YTN_DM_MAPPING: list[SlideMapping] = [
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
    # Slide 1: 거래 구조 설계 고려사항
    SlideMapping(
        slide_idx=1,
        description="거래 구조 설계 고려사항 — 듀얼 패널 (전제 조건 / 구조 설계)",
        slots=[
            SlotMapping("직사각형 5", "deal_preconditions", "text"),
            SlotMapping("직사각형 6", "structure_design", "text"),
        ],
    ),
    # Slide 2: 구주 매입 대상 선정 및 전략
    SlideMapping(
        slide_idx=2,
        description="구주 매입 대상 선정 및 전략 — 5단계 우선순위 카드",
        slots=[
            SlotMapping("직사각형 6", "priority_1", "text"),
            SlotMapping("직사각형 7", "priority_2", "text"),
            SlotMapping("직사각형 8", "priority_3", "text"),
            SlotMapping("직사각형 9", "priority_4", "text"),
            SlotMapping("직사각형 10", "priority_5", "text"),
            SlotMapping("직사각형 24", "acquisition_strategy", "text"),
        ],
    ),
    # Slide 3: 매입가액 및 투자금
    SlideMapping(
        slide_idx=3,
        description="매입가액 및 투자금 — 상세 재무 테이블 + 설명 박스",
        slots=[
            SlotMapping("표 11", "acquisition_pricing_table", "table"),
            SlotMapping("직사각형 17", "series_acquisition_desc", "text"),
            SlotMapping("직사각형 23", "new_share_investment_desc", "text"),
            SlotMapping("직사각형 24", "call_option_desc", "text"),
        ],
    ),
    # Slide 4: 법률·세무 의견
    SlideMapping(
        slide_idx=4,
        description="법률·세무 의견 — 주주별 차등 거래가액",
        slots=[
            SlotMapping("표 8", "legal_tax_opinions_table", "table"),
        ],
    ),
    # Slide 5: Key Man Retention 방안
    SlideMapping(
        slide_idx=5,
        description="Key Man Retention 방안",
        slots=[
            SlotMapping("표 5", "key_man_retention_table", "table"),
        ],
    ),
]
