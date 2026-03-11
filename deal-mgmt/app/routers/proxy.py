"""PETRA Contract Desk 데스크톱 앱 전용 프록시 API.

데스크톱 앱은 이 엔드포인트를 통해 NDA/SPA Redline 생성 및 AI 조항 제안을 요청한다.
API 키, 프롬프트, lxml 등 서버 전용 의존성은 이 서버에서만 실행된다.
"""

from __future__ import annotations

import io
import json
import logging
import time

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.services import redline_engine
from app.services.nda_analysis_service import generate_nda_redline
from app.services.redline_prompts import build_step4_prompt
from app.services.spa_analysis_service import (
    call_llm_json,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/proxy", tags=["Desktop Proxy"])


# ── 라이선스 키 검증 (Phase 5에서 본격 구현) ─────────────
async def _verify_license(license_key: str | None, machine_id: str | None) -> None:
    """라이선스 키 검증 (MVP 단계에서는 간단 체크만)."""
    if not license_key or not machine_id:
        raise HTTPException(status_code=401, detail="라이선스 키와 머신 ID가 필요합니다.")
    # Phase 5: DB 기반 플랜/일일 한도/만료일 검증 추가 예정
    if license_key == "INVALID":
        raise HTTPException(status_code=403, detail="유효하지 않은 라이선스입니다.")


# ── NDA Redline ─────────────────────────────────────────
@router.post("/redline/nda")
async def proxy_nda_redline(
    file: UploadFile = File(...),
    nda_type: str = Form("MUTUAL"),
    party_side: str = Form("SELL"),
    reference_text: str = Form(""),
    x_license_key: str | None = Header(None),
    x_machine_id: str | None = Header(None),
) -> StreamingResponse:
    """NDA Redline 생성 프록시.

    데스크톱 앱이 DOCX 파일을 업로드하면 서버에서 Redline을 생성하여 DOCX로 반환한다.
    """
    await _verify_license(x_license_key, x_machine_id)

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    t0 = time.monotonic()
    try:
        docx_buf, cost, model, issues_count, skipped, _skipped_reasons = await generate_nda_redline(
            current_file_bytes=file_bytes,
            reference_text=reference_text or "",
            nda_type=nda_type,
            party_side=party_side,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    logger.info(
        "NDA Redline 프록시 완료: elapsed=%.1fs, issues=%d, skipped=%d, cost=%s, model=%s",
        time.monotonic() - t0,
        issues_count,
        skipped,
        cost,
        model,
    )

    docx_buf.seek(0)
    return StreamingResponse(
        docx_buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="redline_{file.filename}"',
            "X-Issues-Count": str(issues_count),
            "X-Skipped-Count": str(skipped),
        },
    )


# ── SPA Redline (교차검증) ──────────────────────────────
@router.post("/redline/spa")
async def proxy_spa_redline(
    file: UploadFile = File(...),
    deal_size: str = Form("MEDIUM"),
    industry_type: str = Form("GENERAL"),
    rwi_status: str = Form("NO_RWI"),
    leverage: str = Form("STRONG"),
    jurisdiction: str = Form("DOMESTIC_KR"),
    dd_report: UploadFile | None = File(None),
    x_license_key: str | None = Header(None),
    x_machine_id: str | None = Header(None),
) -> StreamingResponse:
    """SPA 교차검증 Redline 생성 프록시.

    DOCX 파일 + Deal Context → 산업별/레버리지별 교차검증 Redline 생성.
    """
    await _verify_license(x_license_key, x_machine_id)

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    # DD 보고서 텍스트 (선택)
    dd_text = ""
    if dd_report:
        dd_bytes = await dd_report.read()
        if dd_bytes:
            dd_text = await run_in_threadpool(redline_engine.extract_paragraphs_text, dd_bytes)

    # SPA 텍스트 추출
    spa_text = await run_in_threadpool(redline_engine.extract_paragraphs_text, file_bytes)
    if len(spa_text) < 50:
        raise HTTPException(status_code=422, detail="DOCX에서 추출된 텍스트가 너무 짧습니다.")

    # 교차검증 프롬프트 조립
    system_prompt = build_step4_prompt(
        leverage=leverage,
        deal_size=deal_size,
        industry_type=industry_type,
        rwi_status=rwi_status,
        jurisdiction=jurisdiction,
    )

    user_prompt = f"[대상 계약서]\n{spa_text}"
    if dd_text:
        user_prompt += f"\n\n[실사 보고서 (참조)]\n{dd_text}"

    t0 = time.monotonic()
    try:
        result = await call_llm_json(system_prompt, user_prompt, max_retries=1, max_tokens=16384)
    except Exception as exc:
        logger.error("SPA Redline LLM 호출 실패: %s", exc)
        raise HTTPException(status_code=502, detail="AI 분석 서버 오류") from exc

    parsed = result.data
    del user_prompt, spa_text

    # JSON 정규화
    issues_list: list[dict] = []
    if isinstance(parsed, list):
        issues_list = parsed
    elif isinstance(parsed, dict) and "issues" in parsed:
        issues_list = parsed["issues"]
    elif isinstance(parsed, dict):
        issues_list = [parsed]

    # Pydantic 검증
    from app.schemas.spa_analysis import RedlineIssueSchema

    valid_issues: list[dict] = []
    skipped = 0
    for item in issues_list:
        try:
            validated = RedlineIssueSchema.model_validate(item)
            valid_issues.append(validated.model_dump())
        except (ValueError, TypeError):
            skipped += 1

    if not valid_issues:
        raise HTTPException(
            status_code=422,
            detail=f"LLM이 반환한 {len(issues_list)}건 중 유효 항목 없음.",
        )

    # Redline 적용
    t0_ooxml = time.monotonic()
    docx_buf: io.BytesIO = await run_in_threadpool(
        redline_engine.apply_redlines,
        file_bytes,
        valid_issues,
    )
    logger.info(
        "SPA Redline 프록시 완료: elapsed=%.1fs, ooxml=%.1fs, issues=%d, skipped=%d",
        time.monotonic() - t0,
        time.monotonic() - t0_ooxml,
        len(valid_issues),
        skipped,
    )

    docx_buf.seek(0)
    issues_json = json.dumps(
        [{"issue_id": v["issue_id"], "clause_ref": v["clause_ref"], "severity": v["severity"]} for v in valid_issues],
        ensure_ascii=False,
    )

    return StreamingResponse(
        docx_buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="redline_{file.filename}"',
            "X-Issues-Count": str(len(valid_issues)),
            "X-Skipped-Count": str(skipped),
            "X-Issues-Json": issues_json,
        },
    )


# ── SPA 분석 Step 1: 변수 추출 ────────────────────────────
@router.post("/spa-analysis/step1")
async def proxy_spa_analysis_step1(
    file: UploadFile = File(...),
    language_hint: str = Form(""),
    doc_type_hint: str = Form(""),
    x_license_key: str | None = Header(None),
    x_machine_id: str | None = Header(None),
) -> dict:
    """SPA 분석 Step 1 프록시 — DOCX 업로드 → 변수 추출.

    데스크톱 앱이 DOCX 파일을 업로드하면 텍스트를 추출하고
    LLM으로 변수를 추출하여 JSON으로 반환한다.
    """
    from app.services.spa_analysis_service import analyze_step1_variables

    await _verify_license(x_license_key, x_machine_id)

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="빈 파일입니다.")
    if len(file_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    # DOCX → 텍스트 추출
    spa_text = await run_in_threadpool(redline_engine.extract_paragraphs_text, file_bytes)
    if len(spa_text) < 100:
        raise HTTPException(status_code=422, detail="DOCX에서 추출된 텍스트가 너무 짧습니다 (최소 100자).")

    t0 = time.monotonic()
    try:
        result = await analyze_step1_variables(
            spa_text=spa_text,
            language_hint=language_hint or None,
            doc_type_hint=doc_type_hint or None,
        )
    except (ValueError, RuntimeError) as exc:
        logger.error("SPA Step 1 실패: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "SPA Step 1 프록시 완료: elapsed=%.1fs, variables=%d, doc_type=%s",
        time.monotonic() - t0,
        len(result["variables"]),
        result["detected_doc_type"],
    )

    # Step1Result TypedDict → JSON 직렬화 가능 dict 변환
    variables_dicts = [v.model_dump() if hasattr(v, "model_dump") else v for v in result["variables"]]
    booleans_dicts = [b.model_dump() if hasattr(b, "model_dump") else b for b in result["discovered_booleans"]]

    return {
        "session_id": result["session_id"],
        "variables": variables_dicts,
        "deal_structure": result["deal_structure"],
        "industry_type": result["industry_type"],
        "detected_doc_type": result["detected_doc_type"],
        "discovered_booleans": booleans_dicts,
        "sha_type": result.get("sha_type"),
        "exit_strategy": result.get("exit_strategy"),
        "bta_scope": result.get("bta_scope"),
        "cost": result.get("cost"),
        "model": result.get("model"),
        "spa_text": spa_text,
    }


# ── SPA 분석 Step 2: 조항 분해 ────────────────────────────
class SpaStep2ProxyRequest(BaseModel):
    """Step 2 프록시 요청 — 확정 변수 기반 조항 분해."""

    session_id: str
    variables: list[dict]
    deal_structure: str = "PURE_SHARE_TRANSFER"
    industry_type: str = "GENERAL"
    spa_text: str = ""
    doc_type_hint: str = ""


@router.post("/spa-analysis/step2")
async def proxy_spa_analysis_step2(
    body: SpaStep2ProxyRequest,
    x_license_key: str | None = Header(None),
    x_machine_id: str | None = Header(None),
) -> dict:
    """SPA 분석 Step 2 프록시 — 확정 변수 → 조항 분해.

    Step 1 결과에서 사용자가 편집/확정한 변수를 받아
    LLM으로 조항을 분해하여 JSON으로 반환한다.
    """
    from app.schemas.spa_analysis import ExtractedVariable
    from app.services.spa_analysis_service import analyze_step2_clauses

    await _verify_license(x_license_key, x_machine_id)

    # dict → Pydantic 모델 변환
    confirmed_variables: list[ExtractedVariable] = []
    for var_dict in body.variables:
        try:
            confirmed_variables.append(ExtractedVariable.model_validate(var_dict))
        except (ValueError, TypeError) as exc:
            logger.warning("변수 검증 실패 (무시): %s — %s", var_dict.get("variable_key", "?"), exc)

    if not confirmed_variables:
        raise HTTPException(status_code=422, detail="유효한 변수가 없습니다.")

    t0 = time.monotonic()
    try:
        clauses, cost, model = await analyze_step2_clauses(
            session_id=body.session_id,
            confirmed_variables=confirmed_variables,
            deal_structure=body.deal_structure,
            industry_type=body.industry_type,
            spa_text=body.spa_text or None,
            doc_type_hint=body.doc_type_hint or None,
        )
    except (ValueError, RuntimeError) as exc:
        logger.error("SPA Step 2 실패: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "SPA Step 2 프록시 완료: elapsed=%.1fs, clauses=%d",
        time.monotonic() - t0,
        len(clauses),
    )

    clauses_dicts = [c.model_dump() if hasattr(c, "model_dump") else c for c in clauses]

    return {
        "clauses": clauses_dicts,
        "cost": cost,
        "model": model,
    }


# ── AI 조항 제안 ────────────────────────────────────────
class ClauseSuggestionRequest(BaseModel):
    issue_context: str
    our_position: str = ""
    counterpart_position: str = ""
    contract_type: str = "SPA"


class ClauseSuggestionResponse(BaseModel):
    suggested_text: str
    rationale: str
    confidence: float


@router.post("/ai/suggest", response_model=ClauseSuggestionResponse)
async def proxy_ai_suggest(
    body: ClauseSuggestionRequest,
    x_license_key: str | None = Header(None),
    x_machine_id: str | None = Header(None),
) -> ClauseSuggestionResponse:
    """AI 조항 수정 제안 프록시."""
    await _verify_license(x_license_key, x_machine_id)

    system_prompt = f"""\
당신은 M&A 거래 전문 법률 자문 AI입니다.
계약 유형: {body.contract_type}

쟁점 사항에 대해 양 당사자의 입장을 분석하고,
합리적인 조항 수정안과 근거를 제시하세요.

반드시 JSON으로 응답하세요:
{{"suggested_text": "수정 제안 조항 전문", "rationale": "제안 근거", "confidence": 0.0~1.0}}
"""
    user_prompt = f"쟁점: {body.issue_context}\n우리측: {body.our_position}\n상대측: {body.counterpart_position}"

    try:
        result = await call_llm_json(system_prompt, user_prompt, max_retries=1, max_tokens=4096)
        data = result.data if isinstance(result.data, dict) else {}
        return ClauseSuggestionResponse(
            suggested_text=data.get("suggested_text", ""),
            rationale=data.get("rationale", ""),
            confidence=float(data.get("confidence", 0.7)),
        )
    except Exception as exc:
        logger.error("AI 조항 제안 실패: %s", exc)
        raise HTTPException(status_code=502, detail="AI 분석 서버 오류") from exc


# ── 라이선스 검증 ────────────────────────────────────────
class LicenseVerifyRequest(BaseModel):
    license_key: str
    machine_id: str


class LicenseVerifyResponse(BaseModel):
    valid: bool
    plan: str = "basic"
    expires_at: str | None = None
    daily_remaining: int = 10


@router.post("/license/verify", response_model=LicenseVerifyResponse)
async def verify_license(body: LicenseVerifyRequest) -> LicenseVerifyResponse:
    """라이선스 검증 (MVP: 간단 체크, Phase 5에서 DB 기반으로 확장)."""
    # MVP: 모든 키를 유효로 처리 (Phase 5에서 본격 구현)
    if body.license_key == "INVALID":
        return LicenseVerifyResponse(valid=False, plan="none", daily_remaining=0)
    return LicenseVerifyResponse(
        valid=True,
        plan="professional",
        daily_remaining=50,
    )
