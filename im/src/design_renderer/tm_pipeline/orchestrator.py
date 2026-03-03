"""오케스트레이터 — JSON → IMDocumentData → PPTX 엔드투엔드 파이프라인.

외부 JSON 파일 또는 DocumentRenderingSpec을 받아 PPTX를 생성한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.design_renderer.manifest import GenerationManifest
from src.design_renderer.pipeline import IMPipeline, PipelineResult
from src.design_renderer.tm_pipeline.schema import DocumentRenderingSpec
from src.design_renderer.tm_pipeline.validators import (
    AntiHallucinationValidator,
    ValidationResult,
)

logger = logging.getLogger(__name__)

# 허용된 JSON 확장자
_ALLOWED_JSON_EXTENSIONS = {".json"}


@dataclass
class PipelineOutput:
    """JSON → PPTX 파이프라인 최종 출력."""

    success: bool = True
    pipeline_result: PipelineResult | None = None
    validation_result: ValidationResult | None = None
    spec: DocumentRenderingSpec | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def manifest(self) -> GenerationManifest | None:
        """파이프라인 매니페스트."""
        if self.pipeline_result:
            return self.pipeline_result.manifest
        return None

    @property
    def failed_sections(self) -> list[str]:
        """실패한 섹션 ID 목록."""
        if self.pipeline_result:
            return [r.section_id for r in self.pipeline_result.failed_sections]
        return []


def render_from_json(
    json_path: str | Path,
    output_path: str | Path,
    *,
    validate: bool = True,
    continue_on_error: bool = True,
) -> PipelineOutput:
    """JSON 파일 → PPTX 생성.

    Args:
        json_path: DocumentRenderingSpec JSON 파일 경로.
        output_path: 출력 PPTX 경로.
        validate: Anti-Hallucination 검증 수행 여부.
        continue_on_error: 섹션 실패 시 계속 진행.

    Returns:
        PipelineOutput (성공 여부, 검증 결과, 매니페스트 포함).
    """
    output = PipelineOutput()
    json_file = Path(json_path).resolve()

    if not json_file.exists():
        output.success = False
        output.errors.append("JSON 파일을 찾을 수 없습니다")
        return output

    if json_file.suffix.lower() not in _ALLOWED_JSON_EXTENSIONS:
        output.success = False
        output.errors.append("허용되지 않는 파일 확장자입니다")
        return output

    try:
        raw = json_file.read_text(encoding="utf-8")
        spec = DocumentRenderingSpec.model_validate_json(raw)
    except Exception as exc:
        logger.error("JSON 파싱 실패: %s — %s", json_file, exc)
        output.success = False
        output.errors.append("JSON 파싱에 실패하였습니다")
        return output

    return render_from_spec(
        spec,
        output_path=output_path,
        validate=validate,
        continue_on_error=continue_on_error,
    )


def render_from_spec(
    spec: DocumentRenderingSpec,
    *,
    output_path: str | Path,
    validate: bool = True,
    continue_on_error: bool = True,
) -> PipelineOutput:
    """DocumentRenderingSpec → PPTX 생성.

    Args:
        spec: 문서 렌더링 스펙.
        output_path: 출력 PPTX 경로.
        validate: Anti-Hallucination 검증 수행 여부.
        continue_on_error: 섹션 실패 시 계속 진행.

    Returns:
        PipelineOutput.
    """
    output = PipelineOutput(spec=spec)

    # 1. 스펙 → IMDocumentData 변환
    try:
        data = spec.to_im_document_data()
    except Exception as exc:
        logger.error("스펙 변환 실패: %s", exc)
        output.success = False
        output.errors.append("문서 스펙 변환에 실패하였습니다")
        return output

    # 2. Anti-Hallucination 검증 (선택)
    if validate:
        validator = AntiHallucinationValidator(data)
        output.validation_result = validator.run_all()
        if output.validation_result.issues:
            logger.warning(
                "검증 이슈 %d건 발견",
                len(output.validation_result.issues),
            )
            for issue in output.validation_result.issues:
                output.warnings.append(f"[{issue.check_type}] {issue.message}")

    # 3. PPTX 생성 (compute_derived_metrics는 pipeline.generate 내부에서 호출)
    try:
        pipeline = IMPipeline(continue_on_error=continue_on_error)
        result = pipeline.generate(data, pptx_path=output_path)
        output.pipeline_result = result
        output.success = result.success
        if result.errors:
            output.errors.extend(result.errors)
    except Exception as exc:
        logger.error("파이프라인 실행 실패: %s", exc)
        output.success = False
        output.errors.append("PPTX 생성에 실패하였습니다")

    return output


def render_from_dict(
    spec_dict: dict[str, Any],
    *,
    output_path: str | Path,
    validate: bool = True,
    continue_on_error: bool = True,
) -> PipelineOutput:
    """딕셔너리 → PPTX 생성 (API 엔드포인트용).

    Args:
        spec_dict: DocumentRenderingSpec 딕셔너리.
        output_path: 출력 PPTX 경로.
        validate: Anti-Hallucination 검증 수행 여부.
        continue_on_error: 섹션 실패 시 계속 진행.

    Returns:
        PipelineOutput.
    """
    output = PipelineOutput()
    try:
        spec = DocumentRenderingSpec.model_validate(spec_dict)
    except Exception as exc:
        logger.error("스펙 검증 실패: %s", exc)
        output.success = False
        output.errors.append("문서 스펙 검증에 실패하였습니다")
        return output

    return render_from_spec(
        spec,
        output_path=output_path,
        validate=validate,
        continue_on_error=continue_on_error,
    )
