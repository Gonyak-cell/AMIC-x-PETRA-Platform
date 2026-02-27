"""QoE Analyzer Agent — Sprint 6.

QoE 조정항목을 분석하고 분류하는 에이전트.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.agents.base import AgentResponse, BaseAgent
from app.agents.guardrails import (
    check_hallucination_patterns,
    enforce_confidence_threshold,
    validate_amounts_exist,
    validate_entry_ids_exist,
    validate_no_calculations,
)
from app.core.log_decorators import log_error_with_input
from app.core.logging import get_logger

logger = get_logger(__name__)


class QoEAnalyzerAgent(BaseAgent):
    """QoE 조정항목 분석 에이전트.

    GL 전표와 조정 후보를 분석하여 다음을 판단:
    - NON_RECURRING: 비경상 (소송, 구조조정, M&A 등)
    - NORMALIZATION: 정상화 (관계사 거래, 오너 관련)
    - section_id: 라우터 사용 시 "qoe_adjustment_classification" → OpenAI 라우팅
    - OPERATING: 정상 영업활동 (조정 불필요)
    - UNCLEAR: 추가 정보 필요
    """

    prompt_version = "1.0"
    agent_name = "qoe_analyzer"
    section_id = "qoe_adjustment_classification"

    def build_prompt(self, context: dict[str, Any]) -> str:
        """QoE 분석용 프롬프트를 구성한다.

        Args:
            context: 다음 키 포함
                - deal_name: 딜 이름
                - ebitda_definition: EBITDA 정의
                - addback_policy: Add-back 정책
                - gl_entries: 분석 대상 GL 전표 리스트
                - adjustment_candidates: 룰 엔진 탐지 후보

        Returns:
            구성된 프롬프트
        """
        template = self.load_prompt_template()
        user_template = template.get("user_prompt_template", "")

        # 컨텍스트 변수 치환
        prompt = user_template.format(
            deal_name=context.get("deal_name", "Unknown Deal"),
            ebitda_definition=context.get("ebitda_definition", "Standard EBITDA"),
            addback_policy=context.get("addback_policy", "Conservative"),
            entry_count=len(context.get("gl_entries", [])),
            entries_json=json.dumps(
                context.get("gl_entries", [])[:50],  # 최대 50개
                ensure_ascii=False,
                indent=2,
            ),
            candidates_json=json.dumps(
                context.get("adjustment_candidates", []),
                ensure_ascii=False,
                indent=2,
            ),
        )

        return prompt

    def parse_response(self, raw_response: str) -> dict[str, Any]:
        """LLM 응답을 파싱한다.

        Expected output format:
        {
          "analysis_results": [{
            "entry_id": "GL-12345",
            "assessment": "NON_RECURRING | NORMALIZATION | OPERATING | UNCLEAR",
            "rationale": "설명...",
            "confidence": 0.85,
            "recommended_action": "ADD_BACK | EXCLUDE | REVIEW_REQUIRED",
            "additional_context_needed": ["필요한 추가 정보"]
          }],
          "summary": "요약...",
          "warnings": []
        }
        """
        try:
            # JSON 블록 추출 (```json ... ``` 형태일 수 있음)
            json_str = raw_response
            if "```json" in raw_response:
                start = raw_response.find("```json") + 7
                end = raw_response.find("```", start)
                json_str = raw_response[start:end].strip()
            elif "```" in raw_response:
                start = raw_response.find("```") + 3
                end = raw_response.find("```", start)
                json_str = raw_response[start:end].strip()

            parsed = json.loads(json_str)

            # 기본 구조 보장
            if "analysis_results" not in parsed:
                parsed["analysis_results"] = []
            if "summary" not in parsed:
                parsed["summary"] = ""
            if "warnings" not in parsed:
                parsed["warnings"] = []

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse QoE analyzer response: {e}")
            return {
                "analysis_results": [],
                "summary": "",
                "warnings": [f"JSON 파싱 실패: {e!s}"],
            }

    def validate_output(
        self,
        output: dict[str, Any],
        source_data: dict[str, Any],
    ) -> list[str]:
        """출력을 검증한다.

        Args:
            output: 파싱된 LLM 출력
            source_data: 다음 키 포함
                - gl_entries: 원본 GL 전표 리스트
                - known_account_codes: 알려진 계정 코드 집합

        Returns:
            검증 오류 목록
        """
        errors: list[str] = []

        gl_entries = source_data.get("gl_entries", [])
        known_codes = source_data.get("known_account_codes", set())

        # 전표 ID 검증
        errors.extend(validate_entry_ids_exist(output, gl_entries))

        # 금액 검증
        errors.extend(validate_amounts_exist(output, gl_entries))

        # 할루시네이션 패턴 검사
        if known_codes:
            errors.extend(check_hallucination_patterns(output, known_codes))

        # 계산 시도 검사
        errors.extend(validate_no_calculations(output))

        return errors

    @log_error_with_input
    def run(
        self,
        context: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """QoE 분석을 실행한다.

        BaseAgent.run()으로 LLM 호출 후, 추가 후처리 수행.
        """
        logger.info(
            f"QoE Analyzer run started: deal={context.get('deal_name')}, "
            f"entry_count={len(context.get('gl_entries', []))}"
        )

        # BaseAgent.run()이 LLM 호출 + 파싱 + 기본 검증 수행
        response = super().run(context, source_data)

        if not response.success or response.result is None:
            return response

        # 신뢰도 필터링
        filtered_result = enforce_confidence_threshold(
            response.result,
            min_confidence=Decimal("0.30"),
        )

        # 추가 검증
        warnings = list(response.warnings)
        if source_data:
            gl_entries = source_data.get("gl_entries", [])
            known_codes = source_data.get("known_account_codes", set())

            # 금액 검증
            amount_errors = validate_amounts_exist(filtered_result, gl_entries)
            if amount_errors:
                warnings.extend(amount_errors)

            # 할루시네이션 패턴 검사
            if known_codes:
                hallucination_errors = check_hallucination_patterns(
                    filtered_result, known_codes
                )
                if hallucination_errors:
                    warnings.extend(hallucination_errors)

        # 계산 시도 검사
        calc_errors = validate_no_calculations(filtered_result)
        if calc_errors:
            warnings.extend(calc_errors)

        return AgentResponse(
            success=response.success,
            result=filtered_result,
            raw_output=response.raw_output,
            token_usage=response.token_usage,
            validation_errors=response.validation_errors,
            confidence=response.confidence,
            warnings=warnings,
        )
