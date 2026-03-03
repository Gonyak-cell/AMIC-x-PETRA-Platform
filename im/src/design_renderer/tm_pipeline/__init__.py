"""tm_pipeline — JSON → IMDocumentData → PPTX 자동화 파이프라인.

DocumentRenderingSpec JSON 스펙을 받아 IMDocumentData로 변환 후
IMPipeline을 통해 PPTX를 생성한다.

Usage::

    from src.design_renderer.tm_pipeline import render_from_json

    result = render_from_json(
        "sample_specs/sample_im_full.json",
        "output/AMIC_IM_Sample.pptx",
    )
"""

from src.design_renderer.tm_pipeline.orchestrator import (
    PipelineOutput,
    render_from_dict,
    render_from_json,
    render_from_spec,
)
from src.design_renderer.tm_pipeline.schema import DocumentRenderingSpec
from src.design_renderer.tm_pipeline.validators import (
    AntiHallucinationValidator,
    ValidationResult,
)

__all__ = [
    "AntiHallucinationValidator",
    "DocumentRenderingSpec",
    "PipelineOutput",
    "ValidationResult",
    "render_from_dict",
    "render_from_json",
    "render_from_spec",
]
