"""템플릿 시각화 서비스 — 비동기 PPTX 생성 비즈니스 로직."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi.concurrency import run_in_threadpool

from app.pptx.template_engine.engine import TemplateVisualizationResult, process_template

logger = logging.getLogger(__name__)

# 생성 결과 저장 디렉토리
_THIS_DIR = Path(__file__).parent
GENERATED_DIR = _THIS_DIR.parent.parent / "generated" / "visualization"


async def generate_visualization(
    transaction_id: str,
    template_path: str,
    instructions: dict[str, Any],
) -> TemplateVisualizationResult:
    """템플릿 시각화를 비동기로 실행.

    python-pptx의 파일 I/O가 메인 이벤트 루프를 블로킹하지 않도록
    run_in_threadpool로 스레드풀에서 실행한다.

    Args:
        transaction_id: 거래 ID.
        template_path: 입력 템플릿 PPTX 경로.
        instructions: 시각화 지시 사항 JSON.

    Returns:
        TemplateVisualizationResult.
    """
    # 출력 경로 생성
    output_dir = GENERATED_DIR / transaction_id
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"visualization_{uuid.uuid4().hex[:8]}.pptx"
    output_path = str(output_dir / output_filename)

    logger.info(
        "시각화 생성 시작: txn=%s, template=%s",
        transaction_id,
        template_path,
    )

    # 스레드풀에서 동기 PPTX 처리 실행
    result = await run_in_threadpool(
        process_template,
        template_path,
        output_path,
        instructions,
    )

    logger.info(
        "시각화 생성 완료: txn=%s, 차트=%d, 테이블=%d, 이미지=%d, 텍스트=%d, 오류=%d",
        transaction_id,
        result.charts_updated,
        result.tables_updated,
        result.images_placed,
        result.texts_replaced,
        len(result.errors),
    )

    return result
