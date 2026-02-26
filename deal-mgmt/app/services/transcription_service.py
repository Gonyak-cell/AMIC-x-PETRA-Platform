"""녹음 변환 서비스 — Clova Speech STT + LLM 자동 회의록 생성."""

from __future__ import annotations

import json
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import TranscriptionJobStatus
from app.models.transcription_job import TranscriptionJob

logger = logging.getLogger(__name__)

# Clova Speech API 관련 설정
CLOVA_SPEECH_URL = "https://clovaspeech-gw.ncloud.com/recog/v1/stt"
ALLOWED_AUDIO_TYPES = {"audio/mpeg", "audio/wav", "audio/x-wav", "audio/mp4", "audio/webm", "audio/m4a", "audio/ogg"}
MAX_AUDIO_SIZE_BYTES = 100 * 1024 * 1024  # 100MB

# LLM 시스템 프롬프트
MEETING_MINUTES_SYSTEM_PROMPT = """당신은 M&A 전문 회의록 작성 AI입니다.
미팅 녹취록(transcript)을 분석하여 아래 JSON 형식으로 정확히 응답해야 합니다.

출력 JSON 형식:
{
  "minutes": "회의록 전문 (마크다운 형식, 시간순 정리)",
  "summary": "회의 핵심 요약 2-3문장",
  "key_issues": [
    {"title": "이슈 제목", "description": "상세 내용", "priority": "HIGH|MEDIUM|LOW"}
  ],
  "action_items": [
    {"title": "액션아이템 제목", "description": "내용", "assignee_name": "담당자명", "due_date": "YYYY-MM-DD 또는 null", "priority": "HIGH|MEDIUM|LOW"}
  ],
  "condition_assessment": {
    "match_level": "FULL_MATCH|PARTIAL_MATCH|MISMATCH|NOT_ASSESSED",
    "notes": "매수자의 조건과 매도측 기대의 일치도 평가"
  },
  "buyer_reaction": "VERY_POSITIVE|POSITIVE|NEUTRAL|NEGATIVE|VERY_NEGATIVE"
}

규칙:
- 회의록은 한국어로 작성
- 발언자 구분이 가능하면 "발언자: 내용" 형식 사용
- 이슈와 액션아이템은 회의에서 언급된 것만 추출
- buyer_reaction은 매수자의 전반적 반응을 평가 (마케팅 미팅인 경우)
- 반드시 유효한 JSON만 출력 (다른 텍스트 없이)"""


async def process_transcription_job(
    db: AsyncSession,
    job_id: uuid.UUID,
) -> None:
    """전체 파이프라인 실행 (BackgroundTask에서 호출).

    1. STT (Clova Speech) — 오디오 → 텍스트
    2. LLM — 텍스트 → 구조화된 회의록 JSON
    """
    # 작업 로드
    result = await db.execute(select(TranscriptionJob).where(TranscriptionJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        logger.error("TranscriptionJob %s not found", job_id)
        return

    try:
        # ── Stage 1: STT ──────────────────────────────────
        job.status = TranscriptionJobStatus.TRANSCRIBING
        await db.commit()

        transcript = await _run_stt(job.audio_file_path)
        job.transcript = transcript

        # ── Stage 2: LLM 구조화 ──────────────────────────
        job.status = TranscriptionJobStatus.ANALYZING
        await db.commit()

        minutes_json, llm_cost = await _run_llm_analysis(transcript, job)
        job.minutes_json = minutes_json
        job.llm_cost_usd = llm_cost

        # ── 완료 ──────────────────────────────────────────
        job.status = TranscriptionJobStatus.COMPLETED
        await db.commit()
        logger.info("TranscriptionJob %s completed", job_id)

    except Exception as e:
        logger.exception("TranscriptionJob %s failed: %s", job_id, e)
        job.status = TranscriptionJobStatus.FAILED
        job.error_message = str(e)[:2000]
        await db.commit()


async def _run_stt(audio_file_path: str) -> str:
    """Clova Speech API로 오디오를 텍스트로 변환한다."""
    import httpx

    clova_client_id = getattr(settings, "CLOVA_CLIENT_ID", "") or ""
    clova_client_secret = getattr(settings, "CLOVA_CLIENT_SECRET", "") or ""

    if not clova_client_id or not clova_client_secret:
        raise RuntimeError(
            "Clova Speech API 설정이 없습니다. .env에 CLOVA_CLIENT_ID와 CLOVA_CLIENT_SECRET을 설정해 주세요."
        )

    headers = {
        "X-NCP-APIGW-API-KEY-ID": clova_client_id,
        "X-NCP-APIGW-API-KEY": clova_client_secret,
        "Content-Type": "application/octet-stream",
    }
    params = {"lang": "ko"}

    async with httpx.AsyncClient(timeout=300) as client:
        # 스트리밍 업로드 — 파일 전체를 메모리에 올리지 않고 파일 핸들 직접 전달
        with open(audio_file_path, "rb") as f:
            resp = await client.post(
                CLOVA_SPEECH_URL,
                headers=headers,
                params=params,
                content=f,
            )
        resp.raise_for_status()

        # 응답 검증 — HTML 에러 응답이나 빈 텍스트 감지
        try:
            result = resp.json()
        except json.JSONDecodeError:
            raise RuntimeError(f"Clova API 응답 형식이 유효하지 않습니다: {resp.text[:500]}")

        text = result.get("text")
        if not text:
            raise RuntimeError("Clova API에서 텍스트를 반환하지 않았습니다")

    return text


async def _run_llm_analysis(
    transcript: str,
    job: TranscriptionJob,
) -> tuple[dict, float]:
    """LLM으로 녹취록을 구조화된 회의록으로 변환한다."""
    from app.ralph.llm_client import RalphLLMClient

    llm = RalphLLMClient(
        anthropic_api_key=getattr(settings, "ANTHROPIC_API_KEY", "") or "",
        openai_api_key=getattr(settings, "OPENAI_API_KEY", "") or "",
        google_api_key=getattr(settings, "GOOGLE_API_KEY", "") or "",
        primary_model="claude-sonnet-4-20250514",
    )

    # 컨텍스트 구성
    attendees_desc = ""
    if job.attendees_json:
        attendees_desc = "\n참석자 정보:\n"
        for att in job.attendees_json:
            name = att.get("name", "?")
            role = att.get("role", "")
            org = att.get("organization", "")
            attendees_desc += f"- {name} ({role}, {org})\n"

    user_prompt = f"""미팅 정보:
- 제목: {job.title}
- 날짜: {job.meeting_date}
- 단계: {job.meeting_phase.value}
{attendees_desc}

녹취록:
{transcript[:30000]}"""

    raw = await llm.call(MEETING_MINUTES_SYSTEM_PROMPT, user_prompt)

    # JSON 파싱
    try:
        # LLM이 ```json ... ``` 블록으로 감쌀 수 있으므로 추출
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        minutes_json = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM 응답 JSON 파싱 실패 — 안전 기본값 사용 (원문은 transcript 필드 참조)")
        minutes_json = {
            "minutes": "[LLM 응답 파싱 실패 — transcript 필드의 원문을 참조하세요]",
            "summary": "",
            "key_issues": [],
            "action_items": [],
        }

    return minutes_json, llm.total_cost_usd
