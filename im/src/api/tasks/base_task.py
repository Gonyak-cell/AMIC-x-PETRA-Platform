"""Pipeline-aware base task — 실패 시 자동으로 Document를 FAILED 상태로 전환한다.

모든 파이프라인 태스크는 PipelineTask를 base로 사용하여,
on_failure 시 sync_fail_document가 자동 호출되도록 한다 (2중 안전장치).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from celery import Task

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


class PipelineTask(Task):
    """Base task class — 영구 실패 시 Document를 FAILED로 전환한다.

    Celery의 on_failure 콜백을 오버라이드하여, 모든 재시도가 소진된 후
    자동으로 sync_fail_document()를 호출한다.
    """

    abstract = True

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        document_id = self._extract_document_id(args, kwargs)
        if document_id:
            logger.error(
                "Pipeline task %s failed permanently: document=%s error=%s",
                self.name,
                document_id,
                exc,
            )
            try:
                from src.api.tasks.progress import sync_fail_document

                sync_fail_document(document_id, error=f"[{self.name}] {exc}")
            except Exception:
                logger.exception(
                    "CRITICAL: Failed to mark document %s as FAILED",
                    document_id,
                )
        else:
            logger.error(
                "Pipeline task %s failed but could not extract document_id: error=%s",
                self.name,
                exc,
            )

        super().on_failure(exc, task_id, args, kwargs, einfo)

    def _extract_document_id(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> str | None:
        """태스크 args/kwargs에서 document_id를 추출한다."""
        # kwargs 우선
        if "document_id" in kwargs:
            return str(kwargs["document_id"])

        # args에서 UUID 패턴 또는 _document_id 키 탐색
        for arg in args:
            if isinstance(arg, str) and _UUID_RE.match(arg):
                return arg
            if isinstance(arg, dict) and "_document_id" in arg:
                return str(arg["_document_id"])

        return None
