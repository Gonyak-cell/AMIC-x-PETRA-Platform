"""레포트 QA 에이전트 — 완성된 레포트 IR을 독립 LLM으로 팩트체크.

분석/서술에 사용하지 않은 프로바이더(Gemini)를 사용하여
수치 정확성, 논리 일관성, 교차 참조, 완전성, 용어 정확성을 검증한다.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import BaseAgent
from app.core.logging import get_logger

logger = get_logger(__name__)


class ReportQAAgent(BaseAgent):
    """레포트 QA 에이전트.

    section_id = "report_qa" → Gemini로 라우팅.
    분석(OpenAI)과 서술(Anthropic) 모두에 사용하지 않은 프로바이더로 팩트체크.
    """

    prompt_version = "1.0"
    agent_name = "report_qa"
    section_id = "report_qa"

    def build_prompt(self, context: dict[str, Any]) -> str:
        """QA 프롬프트를 구성한다.

        Args:
            context: 다음 키 포함
                - deal_name: 딜 이름
                - report_ir_json: 레포트 IR JSON 문자열
                - qoe_summary: QoE 분석 요약 (dict | None)
                - nwc_summary: NWC 분석 요약 (dict | None)
                - debt_summary: Net Debt 분석 요약 (dict | None)

        Returns:
            구성된 프롬프트
        """
        template = self.load_prompt_template()
        user_template = template.get("user_prompt_template", "")

        if user_template:
            return user_template.format(
                deal_name=context.get("deal_name", "Unknown Deal"),
                report_ir_json=context.get("report_ir_json", "{}"),
                qoe_summary_json=json.dumps(
                    context.get("qoe_summary") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
                nwc_summary_json=json.dumps(
                    context.get("nwc_summary") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
                debt_summary_json=json.dumps(
                    context.get("debt_summary") or {},
                    ensure_ascii=False,
                    indent=2,
                ),
            )

        # 템플릿 파일이 없을 때 fallback
        parts = [
            f"## Deal: {context.get('deal_name', 'Unknown Deal')}",
            "\n## Report IR (to verify):",
            context.get("report_ir_json", "{}"),
            "\n## Source Analysis Data:",
            f"### QoE Summary:\n{json.dumps(context.get('qoe_summary') or {}, ensure_ascii=False, indent=2)}",
            f"### NWC Summary:\n{json.dumps(context.get('nwc_summary') or {}, ensure_ascii=False, indent=2)}",
            f"### Net Debt Summary:\n{json.dumps(context.get('debt_summary') or {}, ensure_ascii=False, indent=2)}",
        ]
        return "\n".join(parts)

    def parse_response(self, raw_response: str) -> dict[str, Any]:
        """QA 결과를 파싱한다.

        Expected:
        {
          "overall_score": 4,
          "issues": [{ "severity", "category", "location", "description", "expected", "found" }],
          "passed_checks": ["cross_reference", "terminology"],
          "summary": "..."
        }
        """
        try:
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
            if "overall_score" not in parsed:
                parsed["overall_score"] = 0
            if "issues" not in parsed:
                parsed["issues"] = []
            if "passed_checks" not in parsed:
                parsed["passed_checks"] = []
            if "summary" not in parsed:
                parsed["summary"] = ""

            return parsed

        except json.JSONDecodeError as e:
            logger.error(f"Report QA 응답 파싱 실패: {e}")
            return {
                "overall_score": 0,
                "issues": [],
                "passed_checks": [],
                "summary": f"JSON 파싱 실패: {e!s}",
            }

    def validate_output(
        self,
        output: dict[str, Any],
        source_data: dict[str, Any],
    ) -> list[str]:
        """QA 결과를 검증한다.

        Args:
            output: 파싱된 QA 결과
            source_data: 검증용 원본 데이터

        Returns:
            검증 오류 목록
        """
        errors: list[str] = []

        # overall_score 범위 검증
        score = output.get("overall_score", 0)
        if not isinstance(score, (int, float)) or score < 1 or score > 5:
            errors.append(f"overall_score 범위 오류: {score} (1-5 필요)")

        # issues 구조 검증
        valid_severities = {"critical", "major", "minor", "info"}
        valid_categories = {
            "number_accuracy",
            "logical_consistency",
            "cross_reference",
            "completeness",
            "terminology",
        }

        for i, issue in enumerate(output.get("issues", [])):
            if not isinstance(issue, dict):
                errors.append(f"issues[{i}]: dict가 아님")
                continue
            if "location" not in issue:
                errors.append(f"issues[{i}]: 'location' 필드 누락")
            if "description" not in issue:
                errors.append(f"issues[{i}]: 'description' 필드 누락")
            if issue.get("severity") and issue["severity"] not in valid_severities:
                errors.append(
                    f"issues[{i}]: 유효하지 않은 severity '{issue['severity']}'"
                )
            if issue.get("category") and issue["category"] not in valid_categories:
                errors.append(
                    f"issues[{i}]: 유효하지 않은 category '{issue['category']}'"
                )

        return errors
