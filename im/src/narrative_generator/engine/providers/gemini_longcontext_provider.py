"""Gemini Long-Context 프로바이더 — VDR 문서 기반 번들 내러티브 생성.

1M 토큰 컨텍스트 윈도우를 활용하여 VDR 문서 전체를 Gemini에 전달하고,
여러 섹션의 내러티브를 단일 호출로 생성한다.

사용 대상 섹션:
  - market_overview
  - company_overview
  - investment_highlights

기존 RAG(top_k=5 청킹) 대비 전체 문서 기반이므로 문맥 손실이 없다.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.narrative_generator.engine.llm_provider import (
    LLMResponse,
    ProviderName,
)
from src.narrative_generator.exceptions import LLMAPIError

logger = logging.getLogger(__name__)

# 번들 생성 대상 섹션
LONG_CONTEXT_SECTIONS = frozenset(
    {
        "market_overview",
        "company_overview",
        "investment_highlights",
    }
)

_BUNDLE_SYSTEM_PROMPT = """\
당신은 M&A Information Memorandum(IM) 작성 전문가입니다.
첨부된 VDR(Virtual Data Room) 문서들을 분석하여 아래 3개 섹션의 내러티브를 작성하세요.

각 섹션은 반드시 아래 JSON 형식으로 응답하세요:
{{
  "market_overview": "시장 분석 내러티브 (한국어, 2000-4000자)",
  "company_overview": "기업 개요 내러티브 (한국어, 2000-4000자)",
  "investment_highlights": "투자 하이라이트 내러티브 (한국어, 2000-4000자)"
}}

작성 지침:
- 정량적 데이터(매출, 성장률, 시장규모)를 적극 인용하세요.
- 추측이나 가정을 배제하고 문서에 기반한 사실만 서술하세요.
- 각 섹션은 독립적으로 읽을 수 있어야 하지만, 전체적으로 일관된 스토리를 유지하세요.
{industry_context}
"""

_BUNDLE_USER_PROMPT = """\
대상 기업: {company_name}
산업: {industry}

첨부된 VDR 문서들을 참고하여 위 3개 섹션을 작성해 주세요.

추가 컨텍스트:
{additional_context}
"""


class GeminiLongContextProvider:
    """Gemini File API 기반 Long-Context 프로바이더.

    VDR 문서를 Gemini File API로 업로드한 후,
    1M 토큰 컨텍스트로 번들 내러티브를 생성한다.

    Args:
        api_key: Google AI API 키.
        model_name: Gemini 모델명 (기본: gemini-2.0-flash).
    """

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gemini-2.0-flash",
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._genai: Any = None
        self._available = False

        if api_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=api_key)
                self._genai = genai
                self._available = True
            except ImportError:
                logger.warning(
                    "google-generativeai 패키지 미설치 — Long-Context 프로바이더 비활성"
                )

    @property
    def provider_name(self) -> ProviderName:
        return ProviderName.GOOGLE

    @property
    def is_available(self) -> bool:
        return self._available

    def generate_bundle(
        self,
        file_paths: list[str],
        *,
        company_name: str = "",
        industry: str = "",
        additional_context: str = "",
        temperature: float = 0.3,
        max_tokens: int = 16384,
    ) -> dict[str, LLMResponse]:
        """VDR 문서 기반으로 3개 섹션 내러티브를 번들 생성한다.

        Args:
            file_paths: VDR 문서 로컬 경로 리스트.
            company_name: 대상 기업명.
            industry: 산업 분류.
            additional_context: 추가 컨텍스트 (기업 데이터 요약 등).
            temperature: 생성 온도.
            max_tokens: 최대 응답 토큰.

        Returns:
            {section_id: LLMResponse} 딕셔너리.
            키: "market_overview", "company_overview", "investment_highlights"

        Raises:
            LLMAPIError: 업로드/생성 실패 시.
        """
        if not self._available:
            raise LLMAPIError(
                provider="google_long_context",
                original_error="프로바이더 비활성 (API 키 없음 또는 패키지 미설치)",
            )

        try:
            # 1. 파일 업로드
            uploaded_files = []
            for path in file_paths:
                uploaded = self._genai.upload_file(path=path)
                uploaded_files.append(uploaded)

            # 2. 프롬프트 조립
            industry_context = ""
            if industry:
                industry_context = f"\n산업 특화 지침: {industry} 산업에 맞는 용어와 분석 프레임워크를 사용하세요."

            system_prompt = _BUNDLE_SYSTEM_PROMPT.format(
                industry_context=industry_context,
            )
            user_prompt = _BUNDLE_USER_PROMPT.format(
                company_name=company_name or "대상 기업",
                industry=industry or "일반",
                additional_context=additional_context or "(없음)",
            )

            # 3. 생성 호출 (파일 + 프롬프트)
            model = self._genai.GenerativeModel(
                model_name=self._model_name,
                system_instruction=system_prompt,
            )
            contents = [*uploaded_files, user_prompt]
            response = model.generate_content(
                contents,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )

            raw_text = response.text if response.text else ""

            # 4. 토큰 사용량
            usage = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                um = response.usage_metadata
                usage = {
                    "prompt_tokens": getattr(um, "prompt_token_count", 0),
                    "completion_tokens": getattr(um, "candidates_token_count", 0),
                    "total_tokens": getattr(um, "total_token_count", 0),
                }

            # 5. JSON 파싱
            sections = self._parse_bundle_response(raw_text)

            # 6. LLMResponse 매핑
            result: dict[str, LLMResponse] = {}
            for section_id in LONG_CONTEXT_SECTIONS:
                text = sections.get(section_id, "")
                if text:
                    result[section_id] = LLMResponse(
                        text=text,
                        provider=ProviderName.GOOGLE,
                        model=self._model_name,
                        usage=usage,
                    )

            return result

        except Exception as exc:
            raise LLMAPIError(
                provider="google_long_context",
                original_error=str(exc),
            ) from exc

    @staticmethod
    def _parse_bundle_response(raw: str) -> dict[str, str]:
        """번들 JSON 응답 파싱."""
        try:
            # JSON 블록 추출 (```json ... ``` 감싸기 대응)
            json_match = re.search(r"\{[\s\S]*\}", raw)
            if not json_match:
                logger.warning("번들 응답에서 JSON을 찾을 수 없음")
                return {}
            data = json.loads(json_match.group())
            result: dict[str, str] = {}
            for key in LONG_CONTEXT_SECTIONS:
                val = data.get(key, "")
                if isinstance(val, str) and val.strip():
                    result[key] = val.strip()
            return result
        except (json.JSONDecodeError, TypeError):
            logger.warning("번들 응답 JSON 파싱 실패")
            return {}
