"""AI 계약 분석 서비스 — MVP stub.

향후 OpenAI/Claude API 연동하여 실제 분석 수행 예정.
"""

from __future__ import annotations

import uuid

from app.schemas.contract import AIAnalysisResult


async def analyze_contract(contract_id: uuid.UUID, document_url: str | None) -> AIAnalysisResult:
    """계약서 텍스트에서 핵심 조항 추출 + 리스크 플래깅.

    MVP: stub 반환. 향후 실제 AI 분석 수행.
    """
    return AIAnalysisResult(
        status="PENDING",
        message="AI 계약 분석 기능은 향후 업데이트에서 제공됩니다.",
        clauses=[],
    )
