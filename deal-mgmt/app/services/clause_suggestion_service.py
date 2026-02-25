"""AI 조항 수정 제안 서비스 — MVP stub.

향후 LLM 연동 시:
- 우리측 입장 + 상대측 입장 + 법률검토 → 절충안 생성
- M&A 법률 문맥 프롬프트 적용
"""

from __future__ import annotations

from app.schemas.negotiation_issue import AIClauseSuggestionResponse


async def suggest_clause_revision(
    issue_title: str,
    clause_reference: str | None,
    our_position: str | None,
    counterpart_position: str | None,
    legal_review: str | None,
) -> AIClauseSuggestionResponse:
    """AI 조항 수정 제안 생성 (MVP stub)."""
    return AIClauseSuggestionResponse(
        suggested_text="AI 조항 수정 제안 기능은 향후 업데이트에서 LLM 연동 시 제공됩니다.",
        rationale="현재 MVP 단계에서는 stub 응답을 반환합니다.",
        confidence=0.0,
    )
