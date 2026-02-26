"""Stage 5: 관할권 교차 분석 — 크로스보더 M&A 전용.

한국법 LLM + 영미법 LLM을 병렬 실행하여
교차점(양쪽 영향)과 충돌점(상충 요구사항)을 탐지한다.

stage5_jurisdiction=True (기본 OFF, 크로스보더 거래 시만 활성화)
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.ralph.generators.ldd.json_utils import extract_json

logger = logging.getLogger(__name__)


# ── 데이터 클래스 ──────────────────────────────────────────────────

@dataclass
class JurisdictionPoint:
    """관할권 교차/충돌 포인트."""

    point_id: str
    point_type: str  # "cross" (양쪽 영향) | "conflict" (상충)
    korean_aspect: str
    english_aspect: str
    affected_sections: list[str] = field(default_factory=list)
    severity: str = "MEDIUM"  # CRITICAL | HIGH | MEDIUM | LOW
    recommendation: str = ""


@dataclass
class JurisdictionResult:
    """관할권 교차 분석 결과."""

    cross_points: list[JurisdictionPoint] = field(default_factory=list)
    conflict_points: list[JurisdictionPoint] = field(default_factory=list)
    total_points: int = 0


# ── 프롬프트 ──────────────────────────────────────────────────────

KOREAN_LAW_SYSTEM = """\
당신은 한국 M&A 법률 전문가입니다.
상법, 공정거래법, 외국인투자촉진법, 자본시장법 등
한국법 관점에서 거래의 법률 이슈를 분석합니다.

특히 주의할 한국법 쟁점:
- 기업결합신고 (공정거래법 제11조)
- 외국인투자신고 (외투법)
- 주요 인허가 이전/재취득
- 근로관계 승계 (근로기준법)
"""

ENGLISH_LAW_SYSTEM = """\
You are a cross-border M&A legal expert specializing in English/US law.
Analyze the transaction from SPA/APA, Representations & Warranties,
Indemnification, and Conditions Precedent perspectives.

Key areas:
- SPA R&W coverage and limitations
- Indemnification caps and baskets
- Material Adverse Change definitions
- Conditions Precedent requirements
- Post-Closing covenants
"""

JURISDICTION_PROMPT = """\
## 거래 요약

{deal_summary}

## 분석된 주요 조항/이슈

{key_clauses}

## 지침

위 거래에서 {jurisdiction} 관점의 주요 법률 이슈를 분석하세요.

JSON 배열로 반환하세요:
```json
[
  {{
    "point_id": "JP-001",
    "section_type": "CONTRACTS",
    "description": "해당 관할권 관점의 이슈 설명",
    "severity": "CRITICAL | HIGH | MEDIUM | LOW",
    "key_regulation": "관련 법률/규정명",
    "recommendation": "권고사항"
  }}
]
```

JSON만 반환하세요.
"""


# ── 메인 클래스 ──────────────────────────────────────────────────

class JurisdictionAnalyzer:
    """Stage 5: 관할권 교차 분석 (크로스보더 M&A 전용)."""

    def __init__(self, llm_client, router=None) -> None:
        self._llm_client = llm_client
        self._router = router

    async def analyze(
        self,
        key_clauses_summary: str,
        deal_summary: str,
    ) -> JurisdictionResult:
        """한국법 + 영미법 병렬 분석 후 교차점/충돌점을 탐지한다."""
        korean_prompt = JURISDICTION_PROMPT.format(
            deal_summary=deal_summary,
            key_clauses=key_clauses_summary,
            jurisdiction="한국법",
        )
        english_prompt = JURISDICTION_PROMPT.format(
            deal_summary=deal_summary,
            key_clauses=key_clauses_summary,
            jurisdiction="English/US law",
        )

        korean_text, english_text = await asyncio.gather(
            self._call("jurisdiction_korean", KOREAN_LAW_SYSTEM, korean_prompt),
            self._call("jurisdiction_english", ENGLISH_LAW_SYSTEM, english_prompt),
        )

        korean_points = self._parse_points(korean_text, "korean")
        english_points = self._parse_points(english_text, "english")

        cross, conflict = self._find_cross_and_conflicts(korean_points, english_points)

        return JurisdictionResult(
            cross_points=cross,
            conflict_points=conflict,
            total_points=len(cross) + len(conflict),
        )

    async def _call(self, routing_key: str, system: str, user: str) -> str:
        if self._router:
            return await self._router.call_routed(routing_key, system, user)
        return await self._llm_client.call(system, user)

    def _parse_points(self, raw: str, jurisdiction: str) -> list[dict[str, Any]]:
        items = extract_json(raw, context=f"관할권 분석 jurisdiction={jurisdiction}", fallback=[])
        if not isinstance(items, list):
            return []
        for item in items:
            item["_jurisdiction"] = jurisdiction
        return items

    def _find_cross_and_conflicts(
        self,
        korean: list[dict],
        english: list[dict],
    ) -> tuple[list[JurisdictionPoint], list[JurisdictionPoint]]:
        """교차점과 충돌점을 탐지한다."""
        cross_points: list[JurisdictionPoint] = []
        conflict_points: list[JurisdictionPoint] = []
        counter = 0

        for k_item in korean:
            k_section = k_item.get("section_type", "")
            for e_item in english:
                e_section = e_item.get("section_type", "")

                if k_section != e_section:
                    continue

                # 같은 섹션에 대해 양쪽 모두 이슈 제기 → 교차점
                counter += 1
                k_sev = k_item.get("severity", "MEDIUM")
                e_sev = e_item.get("severity", "MEDIUM")

                severity_map = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
                k_val = severity_map.get(k_sev, 2)
                e_val = severity_map.get(e_sev, 2)

                # 심각도 차이 ≥ 2 → 충돌 (관할권 간 상충 가능)
                if abs(k_val - e_val) >= 2:
                    conflict_points.append(JurisdictionPoint(
                        point_id=f"JC-{counter:03d}",
                        point_type="conflict",
                        korean_aspect=k_item.get("description", ""),
                        english_aspect=e_item.get("description", ""),
                        affected_sections=[k_section],
                        severity=max(k_sev, e_sev, key=lambda s: severity_map.get(s, 0)),
                        recommendation=(
                            f"한국법: {k_item.get('recommendation', '')}\n"
                            f"영미법: {e_item.get('recommendation', '')}"
                        ),
                    ))
                else:
                    cross_points.append(JurisdictionPoint(
                        point_id=f"JX-{counter:03d}",
                        point_type="cross",
                        korean_aspect=k_item.get("description", ""),
                        english_aspect=e_item.get("description", ""),
                        affected_sections=[k_section],
                        severity=max(k_sev, e_sev, key=lambda s: severity_map.get(s, 0)),
                        recommendation=(
                            f"한국법: {k_item.get('recommendation', '')}\n"
                            f"영미법: {e_item.get('recommendation', '')}"
                        ),
                    ))

        return cross_points, conflict_points
