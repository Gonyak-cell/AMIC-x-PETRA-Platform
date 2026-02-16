"""내러티브 생성 태스크 (T-I14).

> 마지막 수정: 2026-02-10 17:39:59

단일 섹션 내러티브를 생성하는 Celery 태스크.
"""

from __future__ import annotations

import logging
from typing import Any

from src.api.tasks.celery_app import celery_app
from src.api.tasks.serializers import dict_to_im_data

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="generate_narrative",
    max_retries=2,
    acks_late=True,
    soft_time_limit=180,
)
def generate_narrative_task(
    self: Any,
    im_data_dict: dict[str, Any],
    section_id: str,
) -> dict[str, Any]:
    """단일 섹션 내러티브를 생성한다.

    Args:
        im_data_dict: IMDocumentData dict.
        section_id: 생성할 섹션 ID.

    Returns:
        section_id, narrative 텍스트를 포함하는 dict.
    """
    try:
        from src.narrative_generator.engine.orchestrator import NarrativeOrchestrator

        data = dict_to_im_data(im_data_dict)
        orchestrator = NarrativeOrchestrator()
        section_result = orchestrator.generate_section(section_id, data)

        return {
            "section_id": section_id,
            "narrative": section_result.text if hasattr(section_result, "text") else str(section_result),
            "status": "COMPLETED",
        }

    except Exception as exc:
        logger.error("내러티브 생성 실패 (section=%s): %s", section_id, exc)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
        return {
            "section_id": section_id,
            "narrative": "",
            "status": "FAILED",
            "error": str(exc),
        }
