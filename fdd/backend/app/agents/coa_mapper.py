"""CoA Mapper Agent — Sprint 6.

미매핑 계정에 대한 표준 라인아이템 매핑을 제안하는 에이전트.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.agents.base import AgentResponse, BaseAgent
from app.agents.guardrails import (
    check_hallucination_patterns,
    enforce_confidence_threshold,
    validate_no_calculations,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class CoAMapperAgent(BaseAgent):
    """CoA 매핑 제안 에이전트.

    미매핑/저신뢰도 계정을 분석하여 표준 라인아이템 매핑 제안.
    """

    prompt_version = "1.0"
    agent_name = "coa_mapper"
    section_id = "coa_mapping"

    def build_prompt(self, context: dict[str, Any]) -> str:
        """CoA 매핑용 프롬프트를 구성한다.

        Args:
            context: 다음 키 포함
                - unmapped_accounts: 미매핑/저신뢰도 계정 리스트
                - standard_line_items: 80개 표준 라인아이템
                - example_mappings: 기존 APPROVED 매핑 (few-shot 예시)
                - deal_industry: 딜 산업군 (선택)

        Returns:
            구성된 프롬프트
        """
        template = self.load_prompt_template()
        user_template = template.get("user_prompt_template", "")

        # 표준 라인아이템 요약 (전체 80개를 모두 포함하면 토큰 낭비)
        standard_items = context.get("standard_line_items", [])
        standard_summary = [
            {"code": item.get("code"), "name": item.get("name")}
            for item in standard_items
        ]

        # 컨텍스트 변수 치환
        prompt = user_template.format(
            deal_industry=context.get("deal_industry", "일반"),
            account_count=len(context.get("unmapped_accounts", [])),
            unmapped_json=json.dumps(
                context.get("unmapped_accounts", [])[:30],  # 최대 30개
                ensure_ascii=False,
                indent=2,
            ),
            standard_items_json=json.dumps(
                standard_summary,
                ensure_ascii=False,
                indent=2,
            ),
            example_mappings_json=json.dumps(
                context.get("example_mappings", [])[:10],  # few-shot 10개
                ensure_ascii=False,
                indent=2,
            ),
        )

        return prompt

    def parse_response(self, raw_response: str) -> dict[str, Any]:
        """LLM 응답을 파싱한다.

        Expected output format:
        {
          "mapping_suggestions": [{
            "source_account_code": "54100",
            "source_account_name": "복리후생비",
            "suggested_target_code": "IS-SGA-001",
            "suggested_target_name": "Selling, General & Administrative",
            "rationale": "설명...",
            "confidence": 0.78,
            "alternative_mappings": [
              {"code": "IS-SGA-002", "confidence": 0.65}
            ]
          }]
        }
        """
        try:
            # JSON 블록 추출
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
            if "mapping_suggestions" not in parsed:
                parsed["mapping_suggestions"] = []

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse CoA mapper response: {e}")
            return {
                "mapping_suggestions": [],
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
                - unmapped_accounts: 원본 미매핑 계정 리스트
                - standard_codes: 표준 라인아이템 코드 집합

        Returns:
            검증 오류 목록
        """
        errors: list[str] = []

        # 미매핑 계정 코드 집합
        unmapped = source_data.get("unmapped_accounts", [])
        source_codes = {str(acc.get("account_code", "")) for acc in unmapped}

        # 표준 라인아이템 코드 집합
        standard_codes = source_data.get("standard_codes", set())

        suggestions = output.get("mapping_suggestions", [])

        for sugg in suggestions:
            # 소스 계정 코드가 원본에 있는지
            src_code = sugg.get("source_account_code")
            if src_code and str(src_code) not in source_codes:
                errors.append(f"소스 계정 코드 {src_code}가 미매핑 계정 리스트에 없음")

            # 타겟 코드가 표준 라인아이템에 있는지
            target_code = sugg.get("suggested_target_code")
            if (
                target_code
                and standard_codes
                and str(target_code) not in standard_codes
            ):
                errors.append(
                    f"제안된 타겟 코드 {target_code}가 표준 라인아이템에 없음 (할루시네이션)"
                )

        # 계산 시도 검사
        errors.extend(validate_no_calculations(output))

        return errors

    def run(
        self,
        context: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """CoA 매핑 제안을 실행한다.

        BaseAgent.run()으로 LLM 호출 후, 추가 후처리 수행.
        """
        logger.info(
            f"CoA Mapper run started: account_count={len(context.get('unmapped_accounts', []))}"
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

        # 할루시네이션 패턴 검사
        warnings = list(response.warnings)
        if source_data:
            known_codes = source_data.get("standard_codes", set())
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
