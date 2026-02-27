"""PPTX 메모랜덤 생성 패키지 — TM / DM / IM / Proposal.

memo_generator: JSON 콘텐츠 기반 자유 형식 PPTX 생성
template_engine: 사전 디자인된 템플릿의 Shape Name 기반 데이터 교체
"""

from .memo_generator import GenerationResult, generate_memo
from .template_engine import TemplateVisualizationResult, process_template

__all__ = [
    "GenerationResult",
    "TemplateVisualizationResult",
    "generate_memo",
    "process_template",
]
