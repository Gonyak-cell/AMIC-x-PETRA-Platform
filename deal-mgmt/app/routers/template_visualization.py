"""템플릿 시각화 API 엔드포인트."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.core.security import JWTClaims, get_jwt_claims
from app.schemas.template_visualization import (
    TemplateVisualizationRequest,
    TemplateVisualizationResponse,
)
from app.services.template_visualization_service import GENERATED_DIR, generate_visualization

logger = logging.getLogger(__name__)

router = APIRouter(tags=["template-visualization"])

# 보안: 템플릿/생성 파일 경로 화이트리스트
_TEMPLATE_BASE_DIR = (Path(__file__).parent.parent.parent / "templates").resolve()
_GENERATED_BASE_DIR = GENERATED_DIR.resolve()


def _validate_path_within(path: Path, base_dir: Path, label: str) -> Path:
    """경로가 base_dir 내부인지 검증. Path Traversal 방어."""
    resolved = path.resolve()
    if not resolved.is_relative_to(base_dir):
        raise HTTPException(
            status_code=403,
            detail=f"허용되지 않은 {label} 경로입니다.",
        )
    return resolved


@router.post(
    "/transactions/{transaction_id}/template-visualizations",
    response_model=TemplateVisualizationResponse,
    status_code=201,
)
async def create_template_visualization(
    transaction_id: UUID,
    request: TemplateVisualizationRequest,
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """템플릿 PPTX에 시각화 데이터를 적용하여 결과 PPTX를 생성한다.

    - 차트 데이터 교체 (chart.replace_data)
    - 동적 테이블 데이터 삽입 (행 추가, 폰트 축소)
    - 이미지/다이어그램 삽입 (Aspect Ratio 보존)
    - 텍스트 교체 (서식 보존)
    """
    # 템플릿 파일 경로 검증 (Path Traversal 방어)
    template_path = Path(request.template_path)
    resolved_template = _validate_path_within(template_path, _TEMPLATE_BASE_DIR, "템플릿")

    if not resolved_template.exists():
        raise HTTPException(status_code=404, detail="템플릿 파일이 없습니다.")

    instructions = {
        "slides": [slide.model_dump() for slide in request.slides],
    }

    result = await generate_visualization(
        transaction_id=str(transaction_id),
        template_path=str(resolved_template),
        instructions=instructions,
    )

    return TemplateVisualizationResponse(
        output_path=result.output_path,
        charts_updated=result.charts_updated,
        tables_updated=result.tables_updated,
        images_placed=result.images_placed,
        texts_replaced=result.texts_replaced,
        slides_added=result.slides_added,
        errors=result.errors,
    )


@router.get(
    "/transactions/{transaction_id}/template-visualizations/download",
)
async def download_visualization(
    transaction_id: UUID,
    file_path: str,
    claims: JWTClaims = Depends(get_jwt_claims),
):
    """생성된 시각화 PPTX를 다운로드한다."""
    path = Path(file_path)

    # 경로 탐색 방어: generated 디렉토리 내부인지 엄격 검증
    resolved = _validate_path_within(path, _GENERATED_BASE_DIR, "다운로드")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="파일이 없습니다.")

    return FileResponse(
        path=str(resolved),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=resolved.name,
    )
