"""IM 문서 생성 마스터 태스크 (T-I12).

> 마지막 수정: 2026-03-13 17:21:37

Celery Chord 패턴으로 5단계 파이프라인을 오케스트레이션한다.
Stage 1: 데이터 수집 (group) → merge  |  수동 입력  |  Excel 로드
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


@celery_app.task(
    bind=True,
    name="generate_im",
    max_retries=0,
    acks_late=True,
    soft_time_limit=900,
    time_limit=960,
)
def generate_im_task(
    self: Any,
    document_id: str,
    corp_code: str | None,
    config: dict[str, Any] | None = None,
    data_source: str = "DART",
) -> dict[str, Any]:
    """마스터 태스크: 데이터 소스에 따라 파이프라인을 dispatch한다.

    Args:
        document_id: 문서 UUID 문자열.
        corp_code: DART 기업 코드 (None 가능).
        config: 생성 설정 dict.
        data_source: 데이터 소스 ("DART", "MANUAL", "EXCEL").

    Returns:
        chord_id, document_id를 포함하는 dict.
    """
    cfg = config or {}
    website_url = cfg.get("website_url", "")

    update_progress(self, document_id, "PENDING", 0)

    error_cb = handle_pipeline_error.s(document_id)

    # Stage 1: 데이터 소스별 분기
    if data_source == "DART" and corp_code:
        # 경로 A: DART 파이프라인 (기존 방식)
        collection = chord(
            group(
                fetch_dart_task.s(corp_code),
                fetch_web_task.s(corp_code),
                extract_brand_task.s(corp_code, website_url),
            ),
            merge_collected_data.s(document_id).on_error(error_cb),
        )
    elif data_source == "EXCEL":
        # 경로 B: Excel 업로드 데이터 로드
        collection = load_excel_data_task.si(document_id).on_error(error_cb)
    else:
        # 경로 C: 수동 입력 (최소 데이터)
        collection = build_manual_data_task.si(document_id).on_error(error_cb)

    # Stage 2-5: 처리 체인 — 데이터 소스와 무관하게 동일
    processing = chain(
        analyze_financials_task.s(document_id).on_error(error_cb),
        generate_content_task.s(document_id).on_error(error_cb),
        render_document_task.s(document_id).on_error(error_cb),
        finalize_document_task.s(document_id).on_error(error_cb),
    )

    pipeline = collection | processing
    result = pipeline.apply_async(link_error=error_cb)
    return {"chord_id": result.id, "document_id": document_id}


# ---------------------------------------------------------------------------
# Stage 1 태스크: DART 수집 (기존)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True, name="fetch_dart", base=PipelineTask, max_retries=3, acks_late=True
)
def fetch_dart_task(self: Any, corp_code: str) -> dict[str, Any]:
    """DART API에서 기업 데이터를 수집한다.

    Args:
        corp_code: DART 기업 코드.

    Returns:
        수집된 DART 데이터 dict.
    """
    try:
        from src.api.config import get_config
        from src.data_ingestor.pipeline import PipelineConfig

        api_config = get_config()
        config = PipelineConfig(dart_api_key=api_config.dart_api_key)
        result = _run_async(_run_collection(config, corp_code))
        if result.data is not None:
            return im_data_to_dict(result.data)
        return {
            "corp_code": corp_code,
            "error": "수집 실패",
            "warnings": result.warnings,
        }
    except Exception as exc:
        logger.error("DART 수집 실패: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


async def _run_collection(config: Any, corp_code: str) -> Any:
    """DataCollectionPipeline을 비동기로 실행한다."""
    from src.data_ingestor.pipeline import DataCollectionPipeline

    async with DataCollectionPipeline(config) as pipeline:
        return await pipeline.collect(corp_code)


@celery_app.task(
    bind=True, name="fetch_web", base=PipelineTask, max_retries=3, acks_late=True
)
def fetch_web_task(self: Any, corp_code: str) -> dict[str, Any]:
    """웹 크롤링으로 추가 데이터를 수집한다.

    Args:
        corp_code: DART 기업 코드.

    Returns:
        수집된 웹 데이터 dict.
    """
    return {"corp_code": corp_code, "web_data": {}}


@celery_app.task(
    bind=True, name="extract_brand", base=PipelineTask, max_retries=3, acks_late=True
)
def extract_brand_task(self: Any, corp_code: str, website_url: str) -> dict[str, Any]:
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


@celery_app.task(
    bind=True,
    name="merge_collected_data",
    base=PipelineTask,
    max_retries=0,
    acks_late=True,
)
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


# ---------------------------------------------------------------------------
# Stage 1 태스크: 수동 입력 / Excel 로드 (신규)
# ---------------------------------------------------------------------------


def _load_document_from_db(document_id: str) -> dict[str, Any]:
    """DB에서 Document를 동기적으로 조회하여 기본 정보를 반환한다."""
    from src.api.db.session import get_sync_session

    with get_sync_session() as session:
        from src.api.db.models.document import Document

        doc = session.get(Document, document_id)
        if doc is None:
            raise ValueError(f"Document not found: {document_id}")
        return {
            "company_name_kr": doc.company_name,
            "company_name_en": "",
            "corp_code": doc.corp_code or "",
            "industry": (doc.generation_config or {}).get("industry", "general"),
            "project_name": doc.project_name or "",
            "_document_id": document_id,
        }


@celery_app.task(
    bind=True,
    name="build_manual_data",
    base=PipelineTask,
    max_retries=0,
    acks_late=True,
)
def build_manual_data_task(self: Any, document_id: str) -> dict[str, Any]:
    """수동 입력 모드: DB에서 기본 정보를 읽어 최소 im_data_dict를 구성한다.

    Args:
        document_id: 문서 UUID 문자열.

    Returns:
        최소 im_data dict (재무데이터 없음).
    """
    update_progress(self, document_id, "COLLECTING", 25)

    im_data = _load_document_from_db(document_id)
    im_data["financial_statements"] = {}
    im_data["data_source"] = "MANUAL"
    return im_data


@celery_app.task(
    bind=True, name="load_excel_data", base=PipelineTask, max_retries=1, acks_late=True
)
def load_excel_data_task(self: Any, document_id: str) -> dict[str, Any]:
    """Excel 업로드 모드: 업로드된 Excel 파일에서 재무데이터를 파싱한다.

    Args:
        document_id: 문서 UUID 문자열.

    Returns:
        재무데이터가 포함된 im_data dict.
    """
    update_progress(self, document_id, "COLLECTING", 15)

    im_data = _load_document_from_db(document_id)

    # generation_config에서 Excel 파일 경로 확인
    excel_path = (im_data.get("generation_config") or {}).get("excel_file_path")
    if not excel_path:
        # DB에서 직접 조회
        from src.api.db.session import get_sync_session

        with get_sync_session() as session:
            from src.api.db.models.document import Document

            doc = session.get(Document, document_id)
            if doc:
                excel_path = (doc.generation_config or {}).get("excel_file_path")

    if excel_path:
        try:
            from src.data_ingestor.parsers.excel_parser import ExcelParser

            parser = ExcelParser(data_only=True)
            workbook = _run_async(parser.parse(excel_path))
            # 첫 번째 시트를 재무데이터로 사용
            sheet = workbook.get_sheet_by_index(0)
            if sheet:
                im_data["financial_statements"] = {
                    "_raw_excel": sheet.to_dict_list(),
                    "_sheet_name": sheet.name,
                }
            else:
                im_data["financial_statements"] = {}
        except Exception as exc:
            logger.error("Excel 파싱 실패: %s", exc)
            im_data["financial_statements"] = {}
    else:
        im_data["financial_statements"] = {}

    update_progress(self, document_id, "COLLECTING", 25)
    im_data["data_source"] = "EXCEL"
    return im_data


# ---------------------------------------------------------------------------
# Stage 2-5: 처리 체인 (데이터 소스와 무관)
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="analyze_financials",
    base=PipelineTask,
    max_retries=3,
    acks_late=True,
)
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


@celery_app.task(
    bind=True, name="generate_content", base=PipelineTask, max_retries=2, acks_late=True
)
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


@celery_app.task(
    bind=True, name="render_document", base=PipelineTask, max_retries=2, acks_late=True
)
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
        from src.api.tasks.output_utils import (
            compute_im_output_dir,
            compute_im_pptx_path,
        )
        from src.design_renderer.pipeline import IMPipeline

        # 출력 경로 계산 및 디렉토리 생성
        output_dir = compute_im_output_dir(document_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        pptx_output = compute_im_pptx_path(document_id)

        data = dict_to_im_data(im_data_dict)
        pipeline_result = IMPipeline().generate(data, pptx_path=pptx_output)

        im_data_dict["pptx_path"] = (
            str(pipeline_result.pptx_path) if pipeline_result.pptx_path else None
        )
        im_data_dict["pdf_path"] = None  # PDF 미지원

        # 파이프라인 메트릭을 finalize_document_task에 전달
        render_ms = int(pipeline_result.elapsed_seconds * 1000)
        im_data_dict["pipeline_metrics"] = {
            "render_ms": render_ms,
            "generation_ms": render_ms,  # FE 하위 호환
            "slide_count": pipeline_result.total_pptx_slides,
            "warning_count": len(pipeline_result.warnings),
            "error_count": len(pipeline_result.errors),
            "sections_rendered": len(pipeline_result.successful_sections),
            "sections_failed": len(pipeline_result.failed_sections),
        }

    except Exception as exc:
        logger.error("문서 렌더링 실패: %s", exc)
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))

    update_progress(self, document_id, "RENDERING", 95)
    return im_data_dict


def _run_im_quality_gate(pptx_path: str | None, document_id: str) -> dict[str, Any]:
    """IM 품질 게이트를 실행하고 DB 갱신용 kwargs를 반환한다.

    PPTXProgrammaticGate 5차원 검증을 수행하고, 결과에 따라
    quality_score, quality_status, quality_issues 등을 dict로 반환한다.
    게이트 예외 시 fail-closed(FAIL) 처리한다.

    Args:
        pptx_path: 생성된 PPTX 파일 경로.
        document_id: 문서 UUID 문자열 (로깅용).

    Returns:
        DB 갱신용 kwargs dict.
    """
    import time as _time

    result: dict[str, Any] = {
        "generation_profile": "quality",
        "supported_formats": ["pptx"],
    }
    if not pptx_path:
        result["quality_status"] = "FAIL"
        result["quality_issues"] = ["PPTX 파일 경로 없음"]
        return result

    try:
        from src.quality_gate.pptx_gate import PPTXProgrammaticGate

        gate_start = _time.perf_counter_ns()
        gate = PPTXProgrammaticGate()
        gate_result = asyncio.run(
            gate.evaluate(pptx_path, prd_section={"memo_type": "IM"})
        )
        gate_ms = int((_time.perf_counter_ns() - gate_start) / 1_000_000)

        result["quality_score"] = gate_result.weighted_score
        result["quality_issues"] = [str(i) for i in gate_result.issues]
        result["_gate_metrics"] = {"gate_ms": gate_ms}

        # slide_count — render_document_task에서 이미 pipeline_metrics에 포함되어
        # 있으므로 여기서는 fallback으로만 사용
        try:
            from pptx import Presentation

            result["slide_count"] = len(Presentation(pptx_path).slides)
        except Exception:
            pass

        if gate_result.critical_flags:
            result["quality_status"] = "FAIL"
        else:
            result["quality_status"] = (
                "PASS" if gate_result.weighted_score >= 3.5 else "CONDITIONAL"
            )
    except Exception as exc:
        logger.warning(
            "IM 품질 게이트 실패 (fail-closed): document=%s — %s",
            document_id,
            exc,
        )
        result["quality_status"] = "FAIL"
        result["quality_issues"] = [f"품질 게이트 실행 실패: {exc}"]

    return result


@celery_app.task(
    bind=True,
    name="finalize_document",
    base=PipelineTask,
    max_retries=0,
    acks_late=True,
)
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
    from pathlib import Path as _Path

    from src.api.tasks.progress import sync_finalize_document

    pptx_path = im_data_dict.get("pptx_path")
    pdf_path = im_data_dict.get("pdf_path")

    # 성능/품질 메트릭 수집
    stage_details: dict[str, Any] = {}
    if pptx_path:
        try:
            stage_details["file_size_bytes"] = _Path(pptx_path).stat().st_size
        except OSError:
            pass
    # render_document_task에서 전달된 파이프라인 메트릭
    if "pipeline_metrics" in im_data_dict:
        stage_details.update(im_data_dict["pipeline_metrics"])

    # 품질 게이트 실행
    quality_kwargs = _run_im_quality_gate(pptx_path, document_id)

    # stage_details에 gate_ms + total_ms 추가
    gate_metrics = quality_kwargs.pop("_gate_metrics", {})
    stage_details.update(gate_metrics)
    render_ms = stage_details.get("render_ms", 0)
    gate_ms = gate_metrics.get("gate_ms", 0)
    stage_details["total_ms"] = render_ms + gate_ms

    # Celery 상태 + DB 동시 갱신
    final_status = (
        "QUALITY_FAILED"
        if quality_kwargs.get("quality_status") == "FAIL"
        else "COMPLETED"
    )
    update_progress(self, document_id, final_status, 100)
    sync_finalize_document(
        document_id,
        pptx_path=pptx_path,
        pdf_path=pdf_path,
        stage_details=stage_details or None,
        **quality_kwargs,
    )

    # Ralph Loop Pass 1 (Draft) — PPTX 디자인 품질 개선
    if pptx_path:
        try:
            from src.api.tasks.ralph_loop import run_im_ralph_loop_task

            run_im_ralph_loop_task.delay(
                document_id=document_id,
                pass_number=1,
                im_data_dict=im_data_dict,
            )
            logger.info("Ralph Loop Pass 1 시작: document=%s", document_id)
        except Exception as exc:
            logger.warning("Ralph Loop 체이닝 실패 (비필수): %s", exc)

    return {
        "document_id": document_id,
        "status": "COMPLETED",
        "pptx_path": pptx_path,
        "pdf_path": pdf_path,
    }
