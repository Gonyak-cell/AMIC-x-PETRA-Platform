"""Celery 태스크 진행률 추적 유틸리티 (T-I11).

> 마지막 수정: 2026-03-13 17:21:37

Celery 태스크 상태 및 DB Document 진행률을 동기적으로 갱신한다.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from celery import Task

logger = logging.getLogger(__name__)


def update_progress(
    task: Task,
    document_id: str,
    stage: str,
    pct: int,
    details: dict[str, Any] | None = None,
) -> None:
    """Celery 태스크 상태 및 DB 진행률을 갱신한다.

    Args:
        task: 현재 Celery 태스크 인스턴스 (bind=True).
        document_id: 문서 UUID 문자열.
        stage: 현재 단계명 (COLLECTING, ANALYZING, ...).
        pct: 진행률 (0-100).
        details: 추가 메타데이터.
    """
    meta: dict[str, Any] = {
        "document_id": document_id,
        "stage": stage,
        "progress_pct": pct,
    }
    if details:
        meta["details"] = details

    task.update_state(state=stage, meta=meta)

    # DB에도 진행률 반영
    _sync_update_document(document_id, status=stage, progress_pct=pct)

    logger.info(
        "진행률 업데이트: document=%s stage=%s pct=%d",
        document_id,
        stage,
        pct,
    )


def _sync_update_document(document_id: str, **kwargs: Any) -> None:
    """Document 레코드를 동기적으로 업데이트한다.

    Celery 워커(동기 컨텍스트)에서 호출되므로 sync engine을 사용한다.

    Args:
        document_id: 문서 UUID 문자열.
        **kwargs: 업데이트할 컬럼과 값.
    """
    try:
        from sqlalchemy import create_engine, update

        from src.api.config import get_config
        from src.api.db.models.document import Document

        config = get_config()
        sync_url = config.database_url.replace("+asyncpg", "")
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.begin() as conn:
            conn.execute(
                update(Document).where(Document.id == document_id).values(**kwargs)
            )
        engine.dispose()
    except Exception:
        logger.exception(
            "DB 진행률 업데이트 실패: document=%s kwargs=%s",
            document_id,
            kwargs,
        )
        raise


def sync_finalize_document(
    document_id: str,
    *,
    pptx_path: str | None = None,
    pdf_path: str | None = None,
    stage_details: dict[str, Any] | None = None,
    quality_score: float | None = None,
    quality_status: str | None = None,
    quality_issues: list[str] | None = None,
    slide_count: int | None = None,
    generation_profile: str | None = None,
    supported_formats: list[str] | None = None,
) -> None:
    """파이프라인 완료 시 Document 상태를 갱신한다.

    품질 게이트 결과에 따라 COMPLETED/QUALITY_CONDITIONAL/QUALITY_FAILED로 설정한다.

    Args:
        document_id: 문서 UUID 문자열.
        pptx_path: 생성된 PPTX 파일 경로.
        pdf_path: 생성된 PDF 파일 경로.
        stage_details: 생성 성능/품질 메트릭 (render_ms, gate_ms 등).
        quality_score: 품질 게이트 가중 합산 점수 (0.0~5.0).
        quality_status: 품질 판정 (PASS/CONDITIONAL/FAIL/LEGACY_UNVERIFIED).
        quality_issues: 품질 게이트에서 발견된 이슈 목록.
        slide_count: 생성된 PPTX 슬라이드 수.
        generation_profile: 생성 프로파일 (fast/balanced/quality).
        supported_formats: 지원 형식 목록 (["pptx"]).
    """
    if quality_status == "FAIL":
        final_status = "QUALITY_FAILED"
    elif quality_status == "CONDITIONAL":
        final_status = "QUALITY_CONDITIONAL"
    else:
        final_status = "COMPLETED"
    kwargs: dict[str, Any] = {
        "status": final_status,
        "progress_pct": 100,
        "pptx_path": pptx_path,
        "pdf_path": pdf_path,
        "completed_at": datetime.now(timezone.utc),
    }
    if stage_details is not None:
        kwargs["stage_details"] = stage_details
    if quality_score is not None:
        kwargs["quality_score"] = quality_score
    if quality_status is not None:
        kwargs["quality_status"] = quality_status
    if quality_issues is not None:
        kwargs["quality_issues"] = quality_issues
    if slide_count is not None:
        kwargs["slide_count"] = slide_count
    if generation_profile is not None:
        kwargs["generation_profile"] = generation_profile
    if supported_formats is not None:
        kwargs["supported_formats"] = supported_formats
    _sync_update_document(document_id, **kwargs)


def sync_fail_document(document_id: str, error: str = "") -> None:
    """파이프라인 실패 시 Document를 FAILED로 갱신한다 (멱등).

    이미 완료 상태(COMPLETED/QUALITY_CONDITIONAL/QUALITY_FAILED/FAILED)인 문서는 건너뛴다.
    여러 에러 콜백이 동시에 호출될 수 있으므로 멱등성을 보장한다.

    Args:
        document_id: 문서 UUID 문자열.
        error: 에러 메시지.
    """
    try:
        from sqlalchemy import create_engine, update

        from src.api.config import get_config
        from src.api.db.models.document import Document

        config = get_config()
        sync_url = config.database_url.replace("+asyncpg", "")
        engine = create_engine(sync_url, pool_pre_ping=True)
        with engine.begin() as conn:
            result = conn.execute(
                update(Document)
                .where(
                    Document.id == document_id,
                    Document.status.notin_(
                        ["COMPLETED", "QUALITY_CONDITIONAL", "QUALITY_FAILED", "FAILED"]
                    ),
                )
                .values(
                    status="FAILED",
                    stage_details={"error": error} if error else {},
                )
            )
            if result.rowcount == 0:
                logger.info(
                    "Document %s already in terminal state, skipping FAILED transition",
                    document_id,
                )
        engine.dispose()
    except Exception:
        logger.exception(
            "DB failure update failed: document=%s",
            document_id,
        )
        raise
