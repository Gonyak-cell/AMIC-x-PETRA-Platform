"""VDR 데이터 추출 Celery 태스크 — VDR 문서 → 체크리스트 아이템 자동 추출.

> 마지막 수정: 2026-02-25 21:00:00

VDR(Virtual Data Room) 문서를 파싱하여 체크리스트 아이템의
추출값(extracted_value), 신뢰도(confidence), 소스 정보를 업데이트한다.
추출 완료 후 체크리스트 상태를 REVIEW로 전환한다.

단계:
  1. DB에서 체크리스트 + 아이템 로드
  2. deal-mgmt 내부 API로 VDR 문서 메타 조회 (httpx)
  3. 공유 볼륨에서 파일 경로 확인 (/vdr-shared/...)
  4. VdrAnalysisService.extract_from_vdr_documents() 호출
  5. 추출 결과 → IMChecklistItem 레코드 업데이트
  6. IMChecklist.status → REVIEW
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import Any

from src.api.tasks.base_task import PipelineTask
from src.api.tasks.celery_app import celery_app
from src.api.tasks.progress import update_progress

logger = logging.getLogger(__name__)

# VDR 공유 볼륨 기본 경로
_VDR_SHARED_BASE = "/vdr-shared"


def _get_sync_engine() -> Any:
    """동기 SQLAlchemy 엔진을 생성한다."""
    from sqlalchemy import create_engine

    from src.api.config import get_config

    config = get_config()
    sync_url = config.database_url.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True)


def _fetch_vdr_document_metas(
    transaction_id: str,
    vdr_document_ids: list[str],
) -> list[dict[str, Any]]:
    """deal-mgmt 내부 API를 호출하여 VDR 문서 메타데이터를 조회한다.

    Args:
        transaction_id: 거래 ID.
        vdr_document_ids: VDR 문서 ID 목록.

    Returns:
        VDR 문서 메타 목록 [{id, file_name, file_path, ...}, ...].
    """
    import httpx

    from src.api.config import get_config

    config = get_config()
    base_url = config.deal_mgmt_internal_url
    internal_key = config.internal_service_key
    headers = {"X-Internal-Key": internal_key} if internal_key else {}

    metas: list[dict[str, Any]] = []

    try:
        with httpx.Client(timeout=30.0, headers=headers) as client:
            for doc_id in vdr_document_ids:
                try:
                    # 1. 문서 메타데이터 조회
                    resp = client.get(
                        f"{base_url}/api/v1/internal/vdr"
                        f"/transactions/{transaction_id}"
                        f"/documents/{doc_id}/metadata",
                    )
                    if resp.status_code != 200:
                        logger.warning(
                            "VDR 문서 메타 조회 실패: doc_id=%s status=%d",
                            doc_id, resp.status_code,
                        )
                        continue

                    meta = resp.json()

                    # 2. 파일 경로 조회 (공유 볼륨 경로)
                    path_resp = client.get(
                        f"{base_url}/api/v1/internal/vdr"
                        f"/transactions/{transaction_id}"
                        f"/documents/{doc_id}/file-path",
                    )
                    if path_resp.status_code == 200:
                        path_data = path_resp.json()
                        dir_path = path_data.get("file_path", "")
                        original_name = path_data.get("original_name", "")
                        if dir_path and original_name:
                            meta["file_path"] = f"{dir_path}/{original_name}"
                        elif dir_path:
                            meta["file_path"] = dir_path

                    metas.append(meta)
                except httpx.HTTPError as exc:
                    logger.warning(
                        "VDR 문서 메타 조회 HTTP 에러: doc_id=%s — %s",
                        doc_id, exc,
                    )
    except Exception as exc:
        logger.error("deal-mgmt API 연결 실패: %s", exc)

    return metas


def _resolve_vdr_file_paths(
    metas: list[dict[str, Any]],
    transaction_id: str,
) -> list[str]:
    """VDR 메타에서 공유 볼륨 상의 실제 파일 경로를 확인한다.

    Args:
        metas: VDR 문서 메타 리스트.
        transaction_id: 거래 ID.

    Returns:
        존재하는 파일 경로 목록.
    """
    import os

    paths: list[str] = []

    for meta in metas:
        # 메타에 file_path가 있으면 우선 사용
        file_path = meta.get("file_path")
        if not file_path:
            # 규약: /vdr-shared/{transaction_id}/{filename}
            file_name = meta.get("file_name", "")
            if file_name:
                file_path = os.path.join(
                    _VDR_SHARED_BASE, transaction_id, file_name,
                )

        if file_path and os.path.exists(file_path):
            paths.append(file_path)
        elif file_path:
            logger.warning(
                "VDR 파일 없음: %s (doc_id=%s)",
                file_path, meta.get("id"),
            )

    return paths


@celery_app.task(
    bind=True,
    name="extract_vdr_data",
    base=PipelineTask,
    max_retries=2,
    acks_late=True,
    soft_time_limit=300,
    time_limit=360,
)
def extract_vdr_data_task(
    self: Any,
    document_id: str,
    checklist_id: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """VDR 문서에서 데이터를 추출하여 체크리스트 아이템을 업데이트한다.

    Args:
        document_id: IM Document UUID 문자열.
        checklist_id: IMChecklist UUID 문자열.
        config: 추가 설정 (선택).

    Returns:
        추출 결과 요약 dict.

    Raises:
        ValueError: 체크리스트를 찾을 수 없을 때.
        self.retry: 재시도 가능한 오류 시.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import Session, selectinload

    from src.api.db.models.im_checklist import ChecklistStatus, IMChecklist
    from src.api.db.models.im_checklist_item import ChecklistItemStatus, IMChecklistItem
    from src.api.services.vdr_analysis_service import VdrAnalysisService

    update_progress(self, document_id, "COLLECTING", 10)

    engine = _get_sync_engine()

    try:
        with Session(engine) as session:
            # 1. 체크리스트 + 아이템 로드
            stmt = (
                select(IMChecklist)
                .options(selectinload(IMChecklist.items))
                .where(IMChecklist.id == uuid_mod.UUID(checklist_id))
            )
            checklist = session.execute(stmt).scalar_one_or_none()

            if checklist is None:
                raise ValueError(f"IMChecklist not found: {checklist_id}")

            # 2. VDR 문서 메타 조회
            vdr_doc_ids = checklist.vdr_document_ids or []
            transaction_id = str(checklist.transaction_id) if checklist.transaction_id else ""

            update_progress(self, document_id, "COLLECTING", 20)

            if vdr_doc_ids and transaction_id:
                metas = _fetch_vdr_document_metas(transaction_id, vdr_doc_ids)
            else:
                metas = []
                logger.warning(
                    "VDR 문서 ID 또는 transaction_id 없음: "
                    "checklist=%s, vdr_docs=%d, transaction=%s",
                    checklist_id, len(vdr_doc_ids), transaction_id,
                )

            # 3. 파일 경로 확인
            file_paths = _resolve_vdr_file_paths(metas, transaction_id)

            if not file_paths:
                logger.warning(
                    "추출 가능한 VDR 파일 없음: checklist=%s", checklist_id,
                )
                # 모든 아이템을 MISSING으로 표시
                for item in checklist.items:
                    item.status = ChecklistItemStatus.MISSING.value
                checklist.status = ChecklistStatus.REVIEW.value
                checklist.update_counts()
                session.commit()

                update_progress(self, document_id, "COLLECTING", 100)
                return {
                    "document_id": document_id,
                    "checklist_id": checklist_id,
                    "status": "REVIEW",
                    "extracted_count": 0,
                    "missing_count": len(checklist.items),
                }

            # 4. VDR 문서 파싱 + 추출
            update_progress(self, document_id, "COLLECTING", 40)

            service = VdrAnalysisService()
            checklist_field_keys = [item.field_key for item in checklist.items]
            extraction_results = service.extract_from_vdr_documents(
                vdr_doc_paths=file_paths,
                checklist_items=checklist_field_keys,
            )

            update_progress(self, document_id, "COLLECTING", 70)

            # 5. 추출 결과 → 체크리스트 아이템 업데이트
            # field_key + fiscal_year 로 인덱싱
            result_index: dict[tuple[str, str | None], Any] = {}
            for r in extraction_results:
                key = (r.field_key, r.fiscal_year)
                result_index[key] = r

            extracted_count = 0
            missing_count = 0

            for item in checklist.items:
                # fiscal_year가 있으면 (field_key, fiscal_year), 없으면 (field_key, None) 탐색
                match = result_index.get((item.field_key, str(item.fiscal_year) if item.fiscal_year else None))
                if match is None and item.fiscal_year:
                    # fiscal_year 없이도 시도
                    match = result_index.get((item.field_key, None))

                if match is not None:
                    item.extracted_value = match.value
                    item.confidence = match.confidence
                    item.source_location = match.source_location
                    item.source_vdr_doc_name = match.source_doc_name
                    item.status = ChecklistItemStatus.EXTRACTED.value
                    extracted_count += 1
                else:
                    item.status = ChecklistItemStatus.MISSING.value
                    missing_count += 1

            # 6. 체크리스트 상태 → REVIEW
            checklist.status = ChecklistStatus.REVIEW.value
            checklist.raw_extraction = {
                "total_results": len(extraction_results),
                "file_count": len(file_paths),
                "files": [str(p) for p in file_paths],
            }
            checklist.update_counts()

            session.commit()

        update_progress(self, document_id, "COLLECTING", 100)

        logger.info(
            "VDR 추출 완료: document=%s, checklist=%s, "
            "추출=%d, 누락=%d, 파일=%d",
            document_id, checklist_id,
            extracted_count, missing_count, len(file_paths),
        )

        return {
            "document_id": document_id,
            "checklist_id": checklist_id,
            "status": "REVIEW",
            "extracted_count": extracted_count,
            "missing_count": missing_count,
            "file_count": len(file_paths),
        }

    except ValueError:
        raise
    except Exception as exc:
        logger.error(
            "VDR 추출 실패: document=%s checklist=%s — %s",
            document_id, checklist_id, exc,
        )
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        engine.dispose()
