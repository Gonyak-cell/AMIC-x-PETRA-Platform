"""Stage 7: 최종 QA — LDD 보고서 팩트체크.

FDD의 ReportQAAgent 패턴 + LDD 특화 6가지 검증 항목.
분석에 사용하지 않은 제3 프로바이더(Gemini)로 독립 검증.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from app.ralph.generators.ldd.json_utils import extract_json

logger = logging.getLogger(__name__)


# ── 데이터 클래스 ──────────────────────────────────────────────────


@dataclass
class QAIssue:
    """QA에서 발견된 이슈."""

    category: str
    severity: str  # critical | major | minor | info
    location: str  # 섹션/항목 위치
    description: str
    expected: str = ""
    found: str = ""


@dataclass
class LDDQAResult:
    """LDD QA 결과."""

    overall_score: int  # 1-5
    issues: list[QAIssue] = field(default_factory=list)
    passed_checks: list[str] = field(default_factory=list)
    summary: str = ""


# ── 프롬프트 ──────────────────────────────────────────────────────

QA_SYSTEM = """\
당신은 M&A 법률실사(LDD) 보고서 품질 검증 전문가입니다.
완성된 LDD 보고서를 독립적으로 검증하여 오류, 불일치, 누락을 탐지합니다.

6가지 검증 항목:
1. CITATION_ACCURACY: 인용된 조항 번호 ↔ 원본 문서 일치
2. RISK_RECOMMENDATION_ALIGNMENT: 리스크 등급 ↔ 권고사항 논리 일관성
3. COMPLETENESS: 53개 DDRL 항목 중 누락/미분석 항목
4. LEGAL_TERMINOLOGY: 법률 용어 정확성
5. CROSS_REFERENCE: 섹션 간 교차 참조 일관성
6. DEAL_IMPACT_CONSISTENCY: 이슈 심각도 ↔ deal_impact 일관성
"""

QA_PROMPT = """\
## LDD 보고서 데이터

{report_data}

## 검증 지침

위 보고서를 6가지 항목으로 검증하세요.

JSON 형식으로 반환:
```json
{{
  "overall_score": 1-5,
  "issues": [
    {{
      "category": "citation_accuracy | risk_recommendation_alignment | completeness | legal_terminology | cross_reference | deal_impact_consistency",
      "severity": "critical | major | minor | info",
      "location": "섹션/항목 위치",
      "description": "발견된 문제 설명",
      "expected": "기대값 (해당 시)",
      "found": "실제값 (해당 시)"
    }}
  ],
  "passed_checks": ["통과된 검증 항목명"],
  "summary": "종합 평가 (2-3문장)"
}}
```

JSON만 반환하세요.
"""


# ── 메인 클래스 ──────────────────────────────────────────────────


class LDDReportQA:
    """Stage 7: LDD 보고서 최종 QA."""

    def __init__(self, llm_client, router=None) -> None:
        self._llm_client = llm_client
        self._router = router

    async def evaluate(self, report_data: dict[str, Any]) -> LDDQAResult:
        """LDD 보고서를 QA 검증한다."""
        # 보고서 데이터를 텍스트로 직렬화 (토큰 한도 고려)
        report_text = json.dumps(report_data, ensure_ascii=False, indent=2)
        if len(report_text) > 30000:
            report_text = report_text[:30000] + "\n... (이하 생략)"

        prompt = QA_PROMPT.format(report_data=report_text)

        if self._router:
            raw = await self._router.call_routed("final_qa", QA_SYSTEM, prompt)
        else:
            raw = await self._llm_client.call(QA_SYSTEM, prompt)

        return self._parse_result(raw)

    def _parse_result(self, raw: str) -> LDDQAResult:
        data = extract_json(raw, context="LDD QA 결과", fallback=None)
        if data is None:
            return LDDQAResult(
                overall_score=0,
                summary="QA 결과 파싱 실패",
            )

        issues: list[QAIssue] = []
        for issue_data in data.get("issues", []):
            issues.append(
                QAIssue(
                    category=issue_data.get("category", "unknown"),
                    severity=issue_data.get("severity", "info"),
                    location=issue_data.get("location", ""),
                    description=issue_data.get("description", ""),
                    expected=issue_data.get("expected", ""),
                    found=issue_data.get("found", ""),
                )
            )

        score = data.get("overall_score", 0)
        if not isinstance(score, int) or score < 1 or score > 5:
            score = max(1, min(5, int(score) if isinstance(score, (int, float)) else 3))

        return LDDQAResult(
            overall_score=score,
            issues=issues,
            passed_checks=data.get("passed_checks", []),
            summary=data.get("summary", ""),
        )
