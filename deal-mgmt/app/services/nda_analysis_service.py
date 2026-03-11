"""NDA 교차 검증 + Tracked Changes 생성 서비스.

redline_engine.py와 spa_analysis_service.py의 LLM 호출 유틸을 재사용하여
NDA 버전 비교 → Redline .docx를 생성한다.
"""

from __future__ import annotations

import io
import logging
import re
import time
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.schemas.spa_analysis import RedlineIssueSchema
from app.services import redline_engine
from app.services.nda_redline_prompts import build_nda_redline_prompt
from app.services.spa_analysis_service import call_llm_json

logger = logging.getLogger(__name__)

_ISSUE_ID_RE = re.compile(r"(?:ISS|ISSUE)-?(\d+)", re.IGNORECASE)


async def generate_nda_redline(
    current_file_bytes: bytes,
    reference_text: str,
    *,
    nda_type: str = "MUTUAL",
    party_side: str = "SELL",
    owner_user_id: str = "",
) -> tuple[io.BytesIO, float | None, str | None, int, int, list[str]]:
    """NDA Redline 생성: 현재 NDA .docx + 참조 텍스트 비교 → Tracked Changes .docx.

    반환: (docx_bytesio, llm_cost_usd, model_used, issues_count, skipped_count, skipped_reasons)
    """
    logger.info(
        "NDA Redline 서비스 진입: owner=%s, nda_type=%s, party_side=%s, file_size=%d",
        owner_user_id,
        nda_type,
        party_side,
        len(current_file_bytes),
    )

    # 1. DOCX -> plain text 추출
    nda_text = await run_in_threadpool(redline_engine.extract_paragraphs_text, current_file_bytes)
    if len(nda_text) < 50:
        raise ValueError("DOCX에서 추출된 텍스트가 너무 짧습니다 (최소 50자 필요).")

    # 2. 시스템 프롬프트 조립
    system_prompt = build_nda_redline_prompt(nda_type=nda_type, party_side=party_side)

    # 3. User 메시지 조립
    user_prompt = f"[현재 NDA 문서]\n{nda_text}\n\n[참조 문서 (이전 버전)]\n{reference_text}"

    # 4. LLM 호출
    t0_llm = time.monotonic()
    result = await call_llm_json(system_prompt, user_prompt, max_retries=1, max_tokens=16384)
    logger.info("NDA Redline LLM 호출 완료: elapsed=%.1fs", time.monotonic() - t0_llm)
    cost = result.cost
    model_name = result.model
    parsed = result.data
    del user_prompt, nda_text  # 대용량 문자열 메모리 조기 해제

    # 5. JSON 구조 정규화
    issues_list: list[dict[str, Any]] = []
    if isinstance(parsed, list):
        issues_list = parsed
    elif isinstance(parsed, dict) and "issues" in parsed:
        issues_list = parsed["issues"]
    elif isinstance(parsed, dict):
        issues_list = [parsed]

    # 6. issue_id 정규화 + Pydantic 검증
    valid_issues: list[dict[str, Any]] = []
    skipped_count = 0
    skipped_reasons: list[str] = []
    for i, item in enumerate(issues_list):
        try:
            if isinstance(item, dict) and "issue_id" in item:
                m = _ISSUE_ID_RE.match(str(item["issue_id"]))
                if m:
                    item["issue_id"] = f"ISS-{int(m.group(1)):03d}"

            validated = RedlineIssueSchema.model_validate(item)
            valid_issues.append(validated.model_dump())
        except (ValueError, TypeError) as exc:
            issue_id = item.get("issue_id", "N/A") if isinstance(item, dict) else "N/A"
            reason = f"항목 {i} (issue={issue_id}): {exc}"
            logger.warning("NDA Redline 이슈 검증 실패: %s", reason)
            skipped_reasons.append(reason)
            skipped_count += 1

    if not valid_issues:
        raise ValueError(
            f"LLM이 반환한 {len(issues_list)}건의 이슈 중 유효한 항목이 없습니다. NDA 문서 또는 참조 문서를 확인하세요."
        )

    # 7. Redline 적용 (CPU 바운드 → 스레드 풀)
    t0_ooxml = time.monotonic()
    result_docx: io.BytesIO = await run_in_threadpool(redline_engine.apply_redlines, current_file_bytes, valid_issues)
    logger.info(
        "NDA Redline OOXML 처리 완료: elapsed=%.1fs, issues=%d",
        time.monotonic() - t0_ooxml,
        len(valid_issues),
    )

    return result_docx, cost, model_name, len(valid_issues), skipped_count, skipped_reasons
