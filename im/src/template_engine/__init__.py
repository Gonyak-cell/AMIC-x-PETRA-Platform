"""Template Engine — 마스터 PPTX 템플릿 기반 콘텐츠 삽입 엔진.

샘플 TM/DM PPTX를 마스터 템플릿으로 사용하여 시각적 완성도를 보존하면서,
Ralph Loop이 생성한 콘텐츠(텍스트, 차트 데이터, 테이블 데이터)를 삽입한다.

사용 예시::

    from src.template_engine import TemplatePopulator, ContentInjector
    from src.template_engine.registry import get_template_path

    tpl_path = get_template_path("TM", "default")
    populator = TemplatePopulator(tpl_path, ContentInjector())
    output_path = populator.populate(content)
"""

from src.template_engine.content_injector import ContentInjector
from src.template_engine.populator import TemplatePopulator
from src.template_engine.registry import get_template_path
from src.template_engine.schemas import (
    ChartContent,
    SeriesData,
    SlideContent,
    TableContent,
    TemplateContent,
)

__all__ = [
    "ChartContent",
    "ContentInjector",
    "SeriesData",
    "SlideContent",
    "TableContent",
    "TemplateContent",
    "TemplatePopulator",
    "get_template_path",
]
