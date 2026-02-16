"""IM 문서 생성 마스터 태스크 (T-I12).

> 마지막 수정: 2026-02-10 17:39:59

Celery Chord 패턴으로 5단계 파이프라인을 오케스트레이션한다.
Stage 1: 데이터 수집 (group) → merge
Stage 2: 재무 분석 (chain)
Stage 3: 콘텐츠 생성 (chain)
Stage 4: 문서 렌더링 (chain)
Stage 5: 완료 처리 (chain)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Any

from celery import chain, chord, group

from src.api.tasks.base_task import PipelineTask
from src.api.tasks.celery_app import celery_app
from src.api.tasks.progress import update_progress
from src.api.tasks.serializers import dict_to_im_data, im_data_to_dict

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Celery 워커에서 코루틴을 안전하게 실행한다.

    이미 이벤트 루프가 실행 중이면 (gevent/eventlet 풀) 별도 스레드에서 실행하고,
    그렇지 않으면 asyncio.run()을 사용한다.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # 실행 중인 루프 없음 — 일반적인 prefork 풀
        return asyncio.run(coro)
    else:
        # 이미 루프가 실행 중 — gevent/eventlet 풀
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


@celery_app.task(name="handle_pipeline_error")
def handle_pipeline_error(
    request: Any,
    exc: Exception,
    traceback: Any,
    document_id: str | None = None,
) -> None:
    """파이프라인 실패 핸들러 — Document를 FAILED로 전환한다.

    chord/chain의 link_error/on_error로 바인딩되며,
    PipelineTask.on_failure와 함께 2중 안전장치를 구성한다.
    """
    from src.api.tasks.progress import sync_fail_document

    if document_id is None:
        logger.error("handle_pipeline_error called without document_id: exc=%s", exc)
        return

    logger.error(
        "파이프라인 실패: document=%s error=%s",
        document_id,
        exc,
    )
    sync_fail_document(document_id, error=str(exc))


@celery_app.task(bind=True, name="generate_im", max_retries=0, acks_late=True)
def generate_im_task(
    self: Any,
    document_id: str,
    corp_code: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """마스터 태스크: Chord 5단계 파이프라인을 dispatch한다.

    Args:
        document_id: 문서 UUID 문자열.
        corp_code: DART 기업 코드.
        config: 생성 설정 dict.

    Returns:
        chord_id, document_id를 포함하는 dict.
    """
    cfg = config or {}
    website_url = cfg.get("website_url", "")

    update_progress(self, document_id, "PENDING", 0)

    error_cb = handle_pipeline_error.s(document_id)

    # Stage 1: 데이터 수집 (chord) — callback에 on_error 적용
    collection = chord(
        group(
            fetch_dart_task.s(corp_code),
            fetch_web_task.s(corp_code),
            extract_brand_task.s(corp_code, website_url),
        ),
        merge_collected_data.s(document_id).on_error(error_cb),
    )

    # Stage 2-5: 처리 체인 — 각 태스크에 on_error 적용
    processing = chain(
        analyze_financials_task.s(document_id).on_error(error_cb),
        generate_content_task.s(document_id).on_error(error_cb),
        render_document_task.s(document_id).on_error(error_cb),
        finalize_document_task.s(document_id).on_error(error_cb),
    )

    pipeline = collection | processing
    result = pipeline.apply_async(link_error=error_cb)
    return {"chord_id": result.id, "document_id": document_id}


@celery_app.task(bind=True, name="fetch_dart", base=PipelineTask, max_retries=3, acks_late=True)
def fetch_dart_task(self: Any, corp_code: str) -> dict[str, Any]:
    """DART API에서 기업 데이터를 수집한다.

    Args:
        corp_code: DART 기업 코드.

    Returns:
        수집된 DART 데이터 dict.
    """
    try:
        from src.api.config import get_config
        from src.data_ingestor.pipeline import DataCollectionPipeline, PipelineConfig

        api_config = get_config()
        config = PipelineConfig(dart_api_key=api_config.dart_api_key)
        result = _run_async(_run_collection(config, corp_code))
        if result.data is not None:
            return im_data_to_dict(result.data)
        return {"corp_code": corp_code, "error": "수집 실패", "warnings": result.warnings}
    except Exception as exc:
        logger.error("DART 수집 실패: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


async def _run_collection(config: Any, corp_code: str) -> Any:
    """DataCollectionPipeline을 비동기로 실행한다."""
    from src.data_ingestor.pipeline import DataCollectionPipeline

    async with DataCollectionPipeline(config) as pipeline:
        return await pipeline.collect(corp_code)


@celery_app.task(bind=True, name="fetch_web", base=PipelineTask, max_retries=3, acks_late=True)
def fetch_web_task(self: Any, corp_code: str) -> dict[str, Any]:
    """웹 크롤링으로 추가 데이터를 수집한다.

    Args:
        corp_code: DART 기업 코드.

    Returns:
        수집된 웹 데이터 dict.
    """
    return {"corp_code": corp_code, "web_data": {}}


@celery_app.task(bind=True, name="extract_brand", base=PipelineTask, max_retries=3, acks_late=True)
def extract_brand_task(
    self: Any, corp_code: str, website_url: str
) -> dict[str, Any]:
    """브랜드 자산(로고, 색상)을 추출한다.

    Args:
        corp_code: DART 기업 코드.
        website_url: 기업 웹사이트 URL.

    Returns:
        추출된 브랜드 자산 dict.
    """
    if not website_url:
        return {"corp_code": corp_code, "brand_assets": None}

    try:
        from src.brand_extractor import extract_brand

        result = _run_async(extract_brand(website_url, company_name=""))
        return im_data_to_dict(result)
    except Exception as exc:
        logger.warning("브랜드 추출 실패 (비필수): %s", exc)
        return {"corp_code": corp_code, "brand_assets": None}


@celery_app.task(bind=True, name="merge_collected_data", base=PipelineTask, max_retries=0, acks_late=True)
def merge_collected_data(
    self: Any,
    results: list[dict[str, Any]],
    document_id: str,
) -> dict[str, Any]:
    """Stage 1 결과를 병합하여 IMDocumentData dict를 구성한다.

    Args:
        results: group 태스크 결과 리스트 [dart, web, brand].
        document_id: 문서 UUID 문자열.

    Returns:
        병합된 im_data dict.
    """
    update_progress(self, document_id, "COLLECTING", 25)

    dart_data = results[0] if len(results) > 0 else {}
    web_data = results[1] if len(results) > 1 else {}
    brand_data = results[2] if len(results) > 2 else {}

    merged = {**dart_data}

    if web_data.get("web_data"):
        merged.update(web_data["web_data"])

    if brand_data.get("brand_assets") is not None:
        merged["brand_assets"] = brand_data.get("brand_assets") or brand_data

    merged["_document_id"] = document_id
    return merged


@celery_app.task(bind=True, name="analyze_financials", base=PipelineTask, max_retries=3, acks_late=True)
def analyze_financials_task(
    self: Any,
    im_data_dict: dict[str, Any],
    document_id: str,
) -> dict[str, Any]:
    """재무 데이터를 분석하고 지표를 산출한다.

    Args:
        im_data_dict: IMDocumentData dict.
        document_id: 문서 UUID 문자열.

    Returns:
        재무 분석이 추가된 im_data dict.
    """
    update_progress(self, document_id, "ANALYZING", 40)

    try:
        from src.financial_engine.processor import FinancialProcessor

        processor = FinancialProcessor()
        raw_financial = im_data_dict.get("financial_statements", {})

        if raw_financial:
            result = processor.process(raw_financial)
            fs = result.to_financial_statements()
            im_data_dict["financial_statements"] = im_data_to_dict(fs)
            im_data_dict["derived_metrics"] = {
                "profitability": im_data_to_dict(result.profitability),
                "growth": im_data_to_dict(result.growth),
            }

    except Exception as exc:
        logger.error("재무 분석 실패: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))

    return im_data_dict


@celery_app.task(bind=True, name="generate_content", base=PipelineTask, max_retries=2, acks_late=True)
def generate_content_task(
    self: Any,
    im_data_dict: dict[str, Any],
    document_id: str,
) -> dict[str, Any]:
    """내러티브 및 차트를 생성한다.

    Args:
        im_data_dict: IMDocumentData dict.
        document_id: 문서 UUID 문자열.

    Returns:
        콘텐츠가 추가된 im_data dict.
    """
    update_progress(self, document_id, "GENERATING", 55)

    try:
        from src.narrative_generator.engine.orchestrator import NarrativeOrchestrator

        orchestrator = NarrativeOrchestrator()
        data = dict_to_im_data(im_data_dict)
        result = orchestrator.generate(data)
        im_data_dict["narratives"] = result.narratives

    except Exception as exc:
        logger.error("콘텐츠 생성 실패: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))

    update_progress(self, document_id, "GENERATING", 70)
    return im_data_dict


@celery_app.task(bind=True, name="render_document", base=PipelineTask, max_retries=2, acks_late=True)
def render_document_task(
    self: Any,
    im_data_dict: dict[str, Any],
    document_id: str,
) -> dict[str, Any]:
    """PPTX/PDF 문서를 렌더링한다.

    Args:
        im_data_dict: IMDocumentData dict.
        document_id: 문서 UUID 문자열.

    Returns:
        파일 경로가 추가된 im_data dict.
    """
    update_progress(self, document_id, "RENDERING", 80)

    try:
        data = dict_to_im_data(im_data_dict)
        # Design Renderer 호출
        from src.design_renderer.pipeline import IMPipeline

        pipeline_result = IMPipeline().generate(data)
        im_data_dict["pptx_path"] = getattr(pipeline_result, "pptx_path", None)
        im_data_dict["pdf_path"] = getattr(pipeline_result, "pdf_path", None)

    except Exception as exc:
        logger.error("문서 렌더링 실패: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))

    update_progress(self, document_id, "RENDERING", 95)
    return im_data_dict


@celery_app.task(bind=True, name="finalize_document", base=PipelineTask, max_retries=0, acks_late=True)
def finalize_document_task(
    self: Any,
    im_data_dict: dict[str, Any],
    document_id: str,
) -> dict[str, Any]:
    """문서 생성을 완료하고 DB를 갱신한다.

    Args:
        im_data_dict: 최종 IMDocumentData dict.
        document_id: 문서 UUID 문자열.

    Returns:
        최종 결과 dict.
    """
    from src.api.tasks.progress import sync_finalize_document

    pptx_path = im_data_dict.get("pptx_path")
    pdf_path = im_data_dict.get("pdf_path")

    # Celery 상태 + DB 동시 갱신
    update_progress(self, document_id, "COMPLETED", 100)
    sync_finalize_document(document_id, pptx_path=pptx_path, pdf_path=pdf_path)

    return {
        "document_id": document_id,
        "status": "COMPLETED",
        "pptx_path": pptx_path,
        "pdf_path": pdf_path,
    }
