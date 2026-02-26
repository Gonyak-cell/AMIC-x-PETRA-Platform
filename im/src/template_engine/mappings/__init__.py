"""템플릿 매핑 데이터 — 각 마스터 PPTX의 shape→data_key 매핑 정의.

각 매핑 파일은 마스터 템플릿의 슬라이드별 shape 이름을 체크리스트 필드 키에
매핑하여, TemplatePopulator가 어떤 shape에 어떤 데이터를 삽입할지 결정한다.
"""

from src.template_engine.mappings._types import SlideMapping, SlotMapping
from src.template_engine.mappings.nx3_dm import NX3_DM_MAPPING
from src.template_engine.mappings.spicy_tm import SPICY_TM_MAPPING
from src.template_engine.mappings.switch_tm import SWITCH_TM_MAPPING
from src.template_engine.mappings.ytn_dm import YTN_DM_MAPPING

# 템플릿 파일명 → 매핑 데이터
MAPPING_REGISTRY: dict[str, list[SlideMapping]] = {
    "NX3 Games - DM - 260116.pptx": NX3_DM_MAPPING,
    "SPICY - TM - 260219 vSHARE.pptx": SPICY_TM_MAPPING,
    "SWITCH - TM - 260119.pptx": SWITCH_TM_MAPPING,
    "YTN - Structure DM - 260116.pptx": YTN_DM_MAPPING,
}

__all__ = [
    "SlideMapping",
    "SlotMapping",
    "MAPPING_REGISTRY",
    "NX3_DM_MAPPING",
    "SPICY_TM_MAPPING",
    "SWITCH_TM_MAPPING",
    "YTN_DM_MAPPING",
]
