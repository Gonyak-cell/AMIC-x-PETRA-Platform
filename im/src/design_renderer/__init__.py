"""Design Renderer — PPTX/PDF IM 문서 생성 엔진.

AMIC 디자인 토큰 + SL Template (TITAN/COVENANT) 레이아웃 기반으로
Information Memorandum을 PPTX와 PDF 듀얼 출력한다.
"""

__version__ = "0.4.0"

from src.design_renderer.assets import (
    font_data_uri,
    font_path,
    font_uri,
    generate_font_face_css,
    image_data_uri,
    image_path,
)
from src.design_renderer.design_tokens import DEFAULT_TOKENS, IMDesignTokens
from src.design_renderer.pdf_engine import generate_pdf
from src.design_renderer.pipeline import IMPipeline, PipelineResult, SectionResult
from src.design_renderer.security import SecurityOptions, WatermarkPosition
from src.design_renderer.templates import create_jinja_env

__all__ = [
    # design_tokens (Sprint 1)
    "DEFAULT_TOKENS",
    "IMDesignTokens",
    # assets (Sprint 2)
    "font_data_uri",
    "font_path",
    "font_uri",
    "generate_font_face_css",
    "image_data_uri",
    "image_path",
    # templates (Sprint 2)
    "create_jinja_env",
    # pdf_engine (Sprint 3)
    "generate_pdf",
    # pipeline (Sprint 5)
    "IMPipeline",
    "PipelineResult",
    "SectionResult",
    # security (Sprint 5)
    "SecurityOptions",
    "WatermarkPosition",
]
