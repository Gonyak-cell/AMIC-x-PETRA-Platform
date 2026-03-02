"""VDR 데이터 추출 Celery 태스크 — VDR 문서 → 체크리스트 아이템 자동 추출.

> 마지막 수정: 2026-02-26 22:12:00

VDR(Virtual Data Room) 문서를 파싱하여 체크리스트 아이템의
추출값(extracted_value), 신뢰도(confidence), 소스 정보를 업데이트한다.
추출 완료 후 체크리스트 상태를 REVIEW로 전환한다.

단계:
  1. DB에서 체크리스트 + 아이템 로드
  2. deal-mgmt 내부 API로 VDR 문서 메타 + 콘텐츠 다운로드 (httpx)
  3. 임시 파일에 저장 → VdrAnalysisService 파싱
  4. 추출 결과 → IMChecklistItem 레코드 업데이트
  5. IMChecklist.status → REVIEW
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid as uuid_mod
from pathlib import Path
from typing import Any

from src.api.tasks.base_task import PipelineTask
from src.api.tasks.celery_app import celery_app
from src.api.tasks.progress import update_progress

logger = logging.getLogger(__name__)


def _get_sync_engine() -> Any:
    """동기 SQLAlchemy 엔진을 생성한다."""
    from sqlalchemy import create_engine

    from src.api.config import get_config

    config = get_config()
    sync_url = config.database_url.replace("+asyncpg", "")
    return create_engine(sync_url, pool_pre_ping=True)


def _download_single_doc(
    client: Any,
    base_url: str,
    transaction_id: str,
    doc_id: str,
) -> tuple[str, dict[str, Any]] | None:
    """단일 VDR 문서를 다운로드하여 임시 파일로 저장한다."""
    import httpx

    try:
        meta_resp = client.get(
            f"{base_url}/api/v1/internal/vdr"
            f"/transactions/{transaction_id}"
            f"/documents/{doc_id}/metadata",
        )
        if meta_resp.status_code != 200:
            logger.warning(
                "VDR 문서 메타 조회 실패: doc_id=%s status=%d",
                doc_id,
                meta_resp.status_code,
            )
            return None

        meta = meta_resp.json()

        content_resp = client.get(
            f"{base_url}/api/v1/internal/vdr"
            f"/transactions/{transaction_id}"
            f"/documents/{doc_id}/content",
        )
        if content_resp.status_code != 200:
            logger.warning(
                "VDR 문서 콘텐츠 다운로드 실패: doc_id=%s status=%d",
                doc_id,
                content_resp.status_code,
            )
            return None

        original_name = meta.get("original_name", f"{doc_id}.bin")
        suffix = Path(original_name).suffix
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, prefix=f"vdr_{doc_id}_"
        ) as tmp:
            tmp.write(content_resp.content)
            tmp_path = tmp.name

        logger.debug(
            "VDR 문서 다운로드 완료: doc_id=%s → %s (%d bytes)",
            doc_id,
            tmp_path,
            len(content_resp.content),
        )
        return (tmp_path, meta)
    except httpx.HTTPError as exc:
        logger.warning(
            "VDR 문서 다운로드 HTTP 에러: doc_id=%s — %s",
            doc_id,
            exc,
        )
        return None


def _download_vdr_documents(
    transaction_id: str,
    vdr_document_ids: list[str],
) -> list[tuple[str, dict[str, Any]]]:
    """deal-mgmt 내부 API에서 VDR 문서를 병렬 다운로드하여 임시 파일로 저장한다.

    Args:
        transaction_id: 거래 ID.
        vdr_document_ids: VDR 문서 ID 목록.

    Returns:
        [(temp_file_path, metadata), ...] — 호출자가 임시 파일 정리 책임.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    import httpx

    from src.api.config import get_config

    config = get_config()
    base_url = config.deal_mgmt_internal_url
    internal_key = config.internal_service_key
    headers = {"X-Internal-Key": internal_key} if internal_key else {}

    results: list[tuple[str, dict[str, Any]]] = []

    try:
        with httpx.Client(timeout=60.0, headers=headers) as client:
            if len(vdr_document_ids) <= 1:
                # 단일 문서면 병렬화 불필요
                for doc_id in vdr_document_ids:
                    result = _download_single_doc(
                        client, base_url, transaction_id, doc_id
                    )
                    if result:
                        results.append(result)
            else:
                # 다중 문서: ThreadPoolExecutor로 병렬 다운로드 (최대 4 워커)
                with ThreadPoolExecutor(
                    max_workers=min(4, len(vdr_document_ids))
                ) as executor:
                    futures = {
                        executor.submit(
                            _download_single_doc,
                            client,
                            base_url,
                            transaction_id,
                            doc_id,
                        ): doc_id
                        for doc_id in vdr_document_ids
                    }
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            if result:
                                results.append(result)
                        except Exception as exc:
                            doc_id = futures[future]
                            logger.warning(
                                "VDR 문서 다운로드 실패: doc_id=%s — %s",
                                doc_id,
                                exc,
                            )
    except Exception as exc:
        logger.error("deal-mgmt API 연결 실패: %s", exc)

    return results


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
    from src.api.db.models.im_checklist_item import ChecklistItemStatus
    from src.api.services.vdr_analysis_service import VdrAnalysisService

    update_progress(self, document_id, "COLLECTING", 10)

    engine = _get_sync_engine()
    downloaded_files: list[str] = []

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

            # 2. VDR 문서 다운로드
            vdr_doc_ids = checklist.vdr_document_ids or []
            transaction_id = (
                str(checklist.transaction_id) if checklist.transaction_id else ""
            )

            update_progress(self, document_id, "COLLECTING", 20)

            if vdr_doc_ids and transaction_id:
                doc_results = _download_vdr_documents(transaction_id, vdr_doc_ids)
            else:
                doc_results = []
                logger.warning(
                    "VDR 문서 ID 또는 transaction_id 없음: "
                    "checklist=%s, vdr_docs=%d, transaction=%s",
                    checklist_id,
                    len(vdr_doc_ids),
                    transaction_id,
                )

            # 3. 다운로드된 파일 경로 목록
            file_paths = [path for path, _ in doc_results]
            downloaded_files = list(file_paths)

            if not file_paths:
                logger.warning(
                    "추출 가능한 VDR 파일 없음: checklist=%s",
                    checklist_id,
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
                match = result_index.get(
                    (
                        item.field_key,
                        str(item.fiscal_year) if item.fiscal_year else None,
                    )
                )
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
            "VDR 추출 완료: document=%s, checklist=%s, 추출=%d, 누락=%d, 파일=%d",
            document_id,
            checklist_id,
            extracted_count,
            missing_count,
            len(file_paths),
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
            document_id,
            checklist_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    finally:
        # 임시 파일 정리
        for tmp_path in downloaded_files:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        engine.dispose()
