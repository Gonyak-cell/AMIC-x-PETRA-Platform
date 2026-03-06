"""교차검증 에이전트 — 멀티 LLM 교차검증 시스템.

Writer(기존 분석 에이전트)의 결과를 다른 LLM 프로바이더로 독립 검증하고,
불일치를 deterministic 코드로 탐지한다.

설계 원칙:
- Writer와 Reviewer는 반드시 다른 프로바이더 사용
- BLIND 모드: Reviewer가 Writer 결과를 모른 채 독립 분석
- INFORMED 모드: Reviewer가 Writer 결과를 보고 검증/반박
- 비교는 LLM이 아니라 deterministic 코드로 수행
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from app.agents.base import AgentResponse
from app.core.logging import get_logger
from app.services.llm.client import LLMClient, LLMResponse

logger = get_logger(__name__)

# ── 토큰당 비용 추정 (USD, 1M 토큰 기준) ────────────────────────────────
_COST_PER_1M_TOKENS: dict[str, dict[str, Decimal]] = {
    "anthropic": {"input": Decimal("3.00"), "output": Decimal("15.00")},
    "openai": {"input": Decimal("2.50"), "output": Decimal("10.00")},
    "gemini": {"input": Decimal("0.075"), "output": Decimal("0.30")},
}


class ReviewMode(str, Enum):
    """교차검증 모드."""

    BLIND = "BLIND"
    INFORMED = "INFORMED"


class VerificationStatus(str, Enum):
    """교차검증 실행 상태."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class DisagreementLevel(str, Enum):
    """불일치 심각도."""

    NONE = "NONE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"


@dataclass
class DisagreementItem:
    """개별 불일치 항목."""

    entry_id: str
    field: str
    writer_value: str
    reviewer_value: str
    level: DisagreementLevel
    writer_rationale: str
    reviewer_rationale: str
    writer_confidence: float = 0.0
    reviewer_confidence: float = 0.0
    resolution: str | None = None
    resolved: bool = False
    rule_id: str | None = None


@dataclass
class CrossVerificationResult:
    """교차검증 결과."""

    writer_provider: str
    reviewer_provider: str
    review_mode: ReviewMode
    status: VerificationStatus
    total_items: int
    agreed_items: int
    disagreements: list[DisagreementItem] = field(default_factory=list)
    reviewer_only_items: list[dict[str, Any]] = field(default_factory=list)
    writer_only_items: list[dict[str, Any]] = field(default_factory=list)
    agreement_rate: Decimal = Decimal("0")
    auto_resolved: int = 0
    needs_human_review: int = 0
    total_cost_usd: Decimal = Decimal("0")
    token_usage: dict[str, int] = field(default_factory=dict)


# ── 비교 임계값 ──────────────────────────────────────────────────

# QoE: 심각한 분류 불일치 쌍 (MAJOR로 판정)
_QOE_MAJOR_PAIRS: set[frozenset[str]] = {
    frozenset({"NON_RECURRING", "OPERATING"}),
    frozenset({"NORMALIZATION", "OPERATING"}),
}

# 분석 타입별 금액 임계값
# NWC는 QoE/Debt보다 타이트한 임계값 사용:
#   - NWC Peg은 밸류에이션에 직접 반영되어 소폭 차이도 가격 조정에 영향
#   - QoE 조정항목은 경상/비경상 분류가 핵심이라 금액 허용 범위가 더 넓음
_AMOUNT_THRESHOLDS: dict[str, dict[str, Decimal]] = {
    "qoe": {"moderate": Decimal("0.05"), "major": Decimal("0.15")},
    "nwc": {"moderate": Decimal("0.03"), "major": Decimal("0.10")},
    "debt": {"moderate": Decimal("0.05"), "major": Decimal("0.15")},
}

# 최소 금액 임계값 (원) — 이 금액 미만 불일치는 MINOR 이하로 취급
# 예: Writer=0, Reviewer=10원 → 100% 분산이지만 사소한 불일치
_MATERIALITY_THRESHOLD: Decimal = Decimal("1000000")  # 1백만원


class CrossVerificationAgent:
    """멀티 LLM 교차검증 에이전트.

    BaseAgent를 상속하지 않는다.
    Writer 에이전트의 결과를 받아서 다른 프로바이더의 Reviewer 결과와
    deterministic 코드로 비교하는 오케스트레이터 역할.
    """

    def __init__(
        self,
        writer_provider: str,
        reviewer_provider: str,
        reviewer_client: LLMClient,
        review_mode: ReviewMode = ReviewMode.BLIND,
        analysis_type: str = "qoe",
        max_cost_usd: Decimal = Decimal("10.00"),
    ) -> None:
        """교차검증 에이전트를 초기화한다.

        Args:
            writer_provider: Writer 에이전트의 프로바이더 이름
            reviewer_provider: Reviewer의 프로바이더 이름
            reviewer_client: Reviewer LLM 클라이언트
            review_mode: 검증 모드 (BLIND 또는 INFORMED)
            analysis_type: 분석 유형 (qoe, nwc, debt)
            max_cost_usd: 최대 비용 한도 (USD)
        """
        if writer_provider == reviewer_provider:
            logger.warning(
                "Writer와 Reviewer가 동일 프로바이더 — 교차검증 의미 없음",
                extra={"ctx": {"provider": writer_provider}},
            )

        self.writer_provider = writer_provider
        self.reviewer_provider = reviewer_provider
        self.reviewer_client = reviewer_client
        self.review_mode = review_mode
        self.analysis_type = analysis_type
        self.max_cost_usd = max_cost_usd
        self._accumulated_cost = Decimal("0")

    def run_cross_verification(
        self,
        writer_result: AgentResponse,
        source_data: dict[str, Any],
        context: dict[str, Any],
    ) -> CrossVerificationResult:
        """교차검증을 실행한다.

        Args:
            writer_result: Writer 에이전트의 응답
            source_data: 원본 데이터 (GL 전표 등)
            context: 프롬프트 구성용 컨텍스트

        Returns:
            CrossVerificationResult
        """
        # Writer 결과가 없거나 실패한 경우
        if not writer_result.success or not writer_result.result:
            logger.warning("Writer 결과 없음 — 교차검증 건너뜀")
            return CrossVerificationResult(
                writer_provider=self.writer_provider,
                reviewer_provider=self.reviewer_provider,
                review_mode=self.review_mode,
                status=VerificationStatus.SKIPPED,
                total_items=0,
                agreed_items=0,
                agreement_rate=Decimal("1.0"),
            )

        writer_items = writer_result.result.get("analysis_results", [])
        if not writer_items:
            logger.info("Writer 분석 결과 항목 0개 — 교차검증 건너뜀")
            return CrossVerificationResult(
                writer_provider=self.writer_provider,
                reviewer_provider=self.reviewer_provider,
                review_mode=self.review_mode,
                status=VerificationStatus.SKIPPED,
                total_items=0,
                agreed_items=0,
                agreement_rate=Decimal("1.0"),
            )

        # 비용 사전 체크
        if self._accumulated_cost >= self.max_cost_usd:
            logger.warning(
                "비용 한도 초과 — 교차검증 건너뜀",
                extra={
                    "ctx": {
                        "cost": str(self._accumulated_cost),
                        "limit": str(self.max_cost_usd),
                    }
                },
            )
            return CrossVerificationResult(
                writer_provider=self.writer_provider,
                reviewer_provider=self.reviewer_provider,
                review_mode=self.review_mode,
                status=VerificationStatus.SKIPPED,
                total_items=len(writer_items),
                agreed_items=0,
                agreement_rate=Decimal("0"),
            )

        # Reviewer 프롬프트 구성 및 호출
        try:
            system_prompt, user_prompt = self._build_reviewer_prompt(
                context,
                writer_result,
                self.review_mode,
            )
            reviewer_items = self._call_reviewer(system_prompt, user_prompt)
        except Exception as e:
            logger.error(
                "Reviewer 호출 실패",
                extra={"ctx": {"error": str(e), "provider": self.reviewer_provider}},
            )
            return CrossVerificationResult(
                writer_provider=self.writer_provider,
                reviewer_provider=self.reviewer_provider,
                review_mode=self.review_mode,
                status=VerificationStatus.FAILED,
                total_items=len(writer_items),
                agreed_items=0,
                agreement_rate=Decimal("0"),
                token_usage={"error": 1},
            )

        # deterministic 비교
        disagreements, reviewer_only, writer_only = self._compare_results(
            writer_items,
            reviewer_items,
            self.analysis_type,
        )

        # 자동 해결
        resolved_disagreements = self._auto_resolve(disagreements, source_data)

        auto_resolved = sum(1 for d in resolved_disagreements if d.resolved)
        needs_human = sum(1 for d in resolved_disagreements if not d.resolved)
        agreed = len(writer_items) - len(disagreements) - len(writer_only)
        total = max(len(writer_items), len(reviewer_items))

        agreement_rate = (
            Decimal(str(agreed)) / Decimal(str(total)) if total > 0 else Decimal("1.0")
        )

        return CrossVerificationResult(
            writer_provider=self.writer_provider,
            reviewer_provider=self.reviewer_provider,
            review_mode=self.review_mode,
            status=VerificationStatus.COMPLETED,
            total_items=total,
            agreed_items=agreed,
            disagreements=resolved_disagreements,
            reviewer_only_items=reviewer_only,
            writer_only_items=writer_only,
            agreement_rate=agreement_rate.quantize(Decimal("0.0001")),
            auto_resolved=auto_resolved,
            needs_human_review=needs_human,
            total_cost_usd=self._accumulated_cost,
            token_usage={},
        )

    def _build_reviewer_prompt(
        self,
        context: dict[str, Any],
        writer_result: AgentResponse,
        review_mode: ReviewMode,
    ) -> tuple[str, str]:
        """Reviewer 프롬프트를 구성한다.

        Args:
            context: 원본 컨텍스트 (deal_name, gl_entries 등)
            writer_result: Writer 에이전트의 응답
            review_mode: BLIND 또는 INFORMED

        Returns:
            (system_prompt, user_prompt) 튜플
        """
        analysis_labels = {
            "qoe": "QoE (Quality of Earnings)",
            "nwc": "NWC (Net Working Capital)",
            "debt": "Net Debt",
        }
        analysis_label = analysis_labels.get(
            self.analysis_type, self.analysis_type.upper()
        )

        if review_mode == ReviewMode.BLIND:
            system_prompt = (
                f"You are an independent {analysis_label} reviewer for Financial Due Diligence.\n"
                "Classify the provided GL entries independently based on the source data.\n"
                "Output JSON with an 'analysis_results' array matching the standard output schema.\n"
                "Each item must have: entry_id, assessment, rationale, confidence (0.0-1.0), "
                "recommended_action.\n"
                "Focus on precision: only flag items where you have clear evidence from the "
                "source data. Do not speculate or flag items based on general suspicion."
            )
        else:
            system_prompt = (
                f"You are a senior {analysis_label} reviewer for Financial Due Diligence.\n"
                "A junior analyst has classified the provided GL entries.\n"
                "Your task:\n"
                "1. Verify each classification independently\n"
                "2. Challenge disagreements only with specific counter-evidence\n"
                "3. Identify entries the junior analyst may have missed\n"
                "Output JSON with an 'analysis_results' array.\n"
                "Each item must have: entry_id, assessment, rationale, confidence (0.0-1.0), "
                "recommended_action.\n"
                "Prioritize precision over recall — only disagree when you have clear evidence."
            )

        # User prompt: 동일한 소스 데이터
        entries = context.get("gl_entries", [])
        candidates = context.get("adjustment_candidates", [])
        deal_name = context.get("deal_name", "Unknown Deal")

        user_parts = [
            f"## Deal: {deal_name}",
            f"## Analysis Type: {analysis_label}",
            f"## GL Entries ({len(entries)} items):",
            json.dumps(entries[:50], ensure_ascii=False, indent=2),
        ]

        if candidates:
            user_parts.extend(
                [
                    f"\n## Adjustment Candidates ({len(candidates)} items):",
                    json.dumps(candidates, ensure_ascii=False, indent=2),
                ]
            )

        # INFORMED 모드에서만 Writer 결과 추가
        if review_mode == ReviewMode.INFORMED and writer_result.result:
            user_parts.extend(
                [
                    "\n## Junior Analyst's Classification (for review):",
                    json.dumps(
                        writer_result.result.get("analysis_results", []),
                        ensure_ascii=False,
                        indent=2,
                    ),
                ]
            )

        user_prompt = "\n".join(user_parts)
        return system_prompt, user_prompt

    def _call_reviewer(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> list[dict[str, Any]]:
        """Reviewer LLM을 호출하고 결과를 파싱한다.

        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트

        Returns:
            Reviewer의 analysis_results 리스트
        """
        response: LLMResponse = self.reviewer_client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.0,
            max_tokens=4096,
            json_schema={
                "type": "object",
                "properties": {"analysis_results": {"type": "array"}},
            },
            timeout_seconds=60,
        )

        # 비용 누적
        self._accumulated_cost += self._estimate_cost(response.token_usage)

        # JSON 파싱 — 정규식으로 코드블록 내 JSON 추출 (중첩 ``` 안전)
        raw = response.content
        try:
            parsed = _extract_json(raw)
            return parsed.get("analysis_results", [])

        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            logger.error(f"Reviewer 응답 파싱 실패: {e}")
            return []

    def _compare_results(
        self,
        writer_items: list[dict[str, Any]],
        reviewer_items: list[dict[str, Any]],
        analysis_type: str,
    ) -> tuple[list[DisagreementItem], list[dict[str, Any]], list[dict[str, Any]]]:
        """Writer와 Reviewer 결과를 deterministic 코드로 비교한다.

        Args:
            writer_items: Writer의 analysis_results
            reviewer_items: Reviewer의 analysis_results
            analysis_type: qoe, nwc, debt

        Returns:
            (disagreements, reviewer_only_items, writer_only_items)
        """
        # entry_id 기반 매핑
        writer_map = {item.get("entry_id", ""): item for item in writer_items}
        reviewer_map = {item.get("entry_id", ""): item for item in reviewer_items}

        writer_ids = set(writer_map.keys())
        reviewer_ids = set(reviewer_map.keys())

        # 한쪽에만 있는 항목
        writer_only_ids = writer_ids - reviewer_ids
        reviewer_only_ids = reviewer_ids - writer_ids
        common_ids = writer_ids & reviewer_ids

        writer_only = [writer_map[eid] for eid in writer_only_ids if eid]
        reviewer_only = [reviewer_map[eid] for eid in reviewer_only_ids if eid]

        # 공통 항목 비교
        disagreements: list[DisagreementItem] = []

        for entry_id in common_ids:
            if not entry_id:
                continue
            w = writer_map[entry_id]
            r = reviewer_map[entry_id]

            items = self._compare_single_item(entry_id, w, r, analysis_type)
            disagreements.extend(items)

        return disagreements, reviewer_only, writer_only

    def _compare_single_item(
        self,
        entry_id: str,
        writer: dict[str, Any],
        reviewer: dict[str, Any],
        analysis_type: str,
    ) -> list[DisagreementItem]:
        """단일 항목을 비교한다."""
        disagreements: list[DisagreementItem] = []

        if analysis_type == "qoe":
            disagreements.extend(self._compare_qoe_item(entry_id, writer, reviewer))
        elif analysis_type == "nwc":
            disagreements.extend(self._compare_nwc_item(entry_id, writer, reviewer))
        elif analysis_type == "debt":
            disagreements.extend(self._compare_debt_item(entry_id, writer, reviewer))

        return disagreements

    def _compare_qoe_item(
        self,
        entry_id: str,
        writer: dict[str, Any],
        reviewer: dict[str, Any],
    ) -> list[DisagreementItem]:
        """QoE 항목을 비교한다."""
        disagreements: list[DisagreementItem] = []

        w_assessment = str(writer.get("assessment", "")).upper()
        r_assessment = str(reviewer.get("assessment", "")).upper()

        # Assessment 불일치
        if w_assessment != r_assessment:
            pair = frozenset({w_assessment, r_assessment})
            level = (
                DisagreementLevel.MAJOR
                if pair in _QOE_MAJOR_PAIRS
                else DisagreementLevel.MODERATE
            )
            disagreements.append(
                DisagreementItem(
                    entry_id=entry_id,
                    field="assessment",
                    writer_value=w_assessment,
                    reviewer_value=r_assessment,
                    level=level,
                    writer_rationale=writer.get("rationale", ""),
                    reviewer_rationale=reviewer.get("rationale", ""),
                    writer_confidence=float(writer.get("confidence", 0)),
                    reviewer_confidence=float(reviewer.get("confidence", 0)),
                )
            )

        # 금액 불일치
        amount_disagreement = self._compare_amount(
            entry_id,
            writer,
            reviewer,
            "qoe",
        )
        if amount_disagreement:
            disagreements.append(amount_disagreement)

        return disagreements

    def _compare_nwc_item(
        self,
        entry_id: str,
        writer: dict[str, Any],
        reviewer: dict[str, Any],
    ) -> list[DisagreementItem]:
        """NWC 항목을 비교한다."""
        disagreements: list[DisagreementItem] = []

        w_class = str(writer.get("classification", "")).upper()
        r_class = str(reviewer.get("classification", "")).upper()

        if w_class != r_class:
            disagreements.append(
                DisagreementItem(
                    entry_id=entry_id,
                    field="classification",
                    writer_value=w_class,
                    reviewer_value=r_class,
                    level=DisagreementLevel.MODERATE,
                    writer_rationale=writer.get("rationale", ""),
                    reviewer_rationale=reviewer.get("rationale", ""),
                    writer_confidence=float(writer.get("confidence", 0)),
                    reviewer_confidence=float(reviewer.get("confidence", 0)),
                )
            )

        amount_disagreement = self._compare_amount(
            entry_id,
            writer,
            reviewer,
            "nwc",
        )
        if amount_disagreement:
            disagreements.append(amount_disagreement)

        return disagreements

    def _compare_debt_item(
        self,
        entry_id: str,
        writer: dict[str, Any],
        reviewer: dict[str, Any],
    ) -> list[DisagreementItem]:
        """Net Debt 항목을 비교한다."""
        disagreements: list[DisagreementItem] = []

        w_debt_like = writer.get("debt_like")
        r_debt_like = reviewer.get("debt_like")

        if (
            w_debt_like is not None
            and r_debt_like is not None
            and w_debt_like != r_debt_like
        ):
            disagreements.append(
                DisagreementItem(
                    entry_id=entry_id,
                    field="debt_like",
                    writer_value=str(w_debt_like),
                    reviewer_value=str(r_debt_like),
                    level=DisagreementLevel.MAJOR,
                    writer_rationale=writer.get("rationale", ""),
                    reviewer_rationale=reviewer.get("rationale", ""),
                    writer_confidence=float(writer.get("confidence", 0)),
                    reviewer_confidence=float(reviewer.get("confidence", 0)),
                )
            )

        amount_disagreement = self._compare_amount(
            entry_id,
            writer,
            reviewer,
            "debt",
        )
        if amount_disagreement:
            disagreements.append(amount_disagreement)

        return disagreements

    def _compare_amount(
        self,
        entry_id: str,
        writer: dict[str, Any],
        reviewer: dict[str, Any],
        analysis_type: str,
    ) -> DisagreementItem | None:
        """금액을 비교한다."""
        w_amount = self._to_decimal(
            writer.get("amount") or writer.get("adjusted_amount")
        )
        r_amount = self._to_decimal(
            reviewer.get("amount") or reviewer.get("adjusted_amount")
        )

        if w_amount is None or r_amount is None:
            return None
        if w_amount == Decimal("0") and r_amount == Decimal("0"):
            return None

        # 금액 차이의 절대값이 materiality threshold 미만이면 무시
        absolute_diff = abs(w_amount - r_amount)
        if absolute_diff < _MATERIALITY_THRESHOLD:
            return None

        # 분산 계산
        base = max(abs(w_amount), abs(r_amount))
        if base == Decimal("0"):
            return None

        variance = absolute_diff / base
        thresholds = _AMOUNT_THRESHOLDS.get(analysis_type, _AMOUNT_THRESHOLDS["qoe"])

        if variance >= thresholds["major"]:
            level = DisagreementLevel.MAJOR
        elif variance >= thresholds["moderate"]:
            level = DisagreementLevel.MODERATE
        else:
            return None  # 임계값 미만 — 불일치 아님

        return DisagreementItem(
            entry_id=entry_id,
            field="amount",
            writer_value=str(w_amount),
            reviewer_value=str(r_amount),
            level=level,
            writer_rationale=writer.get("rationale", ""),
            reviewer_rationale=reviewer.get("rationale", ""),
        )

    def _auto_resolve(
        self,
        disagreements: list[DisagreementItem],
        source_data: dict[str, Any],
    ) -> list[DisagreementItem]:
        """불일치를 자동 해결한다.

        규칙:
        1. 한쪽이 UNCLEAR이고 다른 쪽이 명확 → 명확한 쪽 채택
        2. 금액 MINOR이고 한쪽이 원본과 정확히 일치 → 일치하는 쪽 채택
        3. 양쪽 confidence 차이 0.4+ → 높은 쪽 채택
        4. 그 외 → 미해결 (needs_human_review)
        """
        # 원본 데이터 맵 구성
        source_entries = source_data.get("gl_entries", [])
        source_map: dict[str, dict[str, Any]] = {
            entry.get("entry_id", ""): entry for entry in source_entries
        }

        for d in disagreements:
            # 규칙 1: UNCLEAR 해결
            if d.field == "assessment":
                if d.writer_value == "UNCLEAR" and d.reviewer_value != "UNCLEAR":
                    d.resolution = (
                        f"Reviewer 분류 채택 ({d.reviewer_value}): Writer가 UNCLEAR"
                    )
                    d.resolved = True
                    d.rule_id = "RULE_UNCLEAR"
                    continue
                if d.reviewer_value == "UNCLEAR" and d.writer_value != "UNCLEAR":
                    d.resolution = (
                        f"Writer 분류 채택 ({d.writer_value}): Reviewer가 UNCLEAR"
                    )
                    d.resolved = True
                    d.rule_id = "RULE_UNCLEAR"
                    continue

            # 규칙 2: 금액이 MINOR 이하이고 원본과 일치
            if d.field == "amount" and d.level in (
                DisagreementLevel.MINOR,
                DisagreementLevel.MODERATE,
            ):
                source_entry = source_map.get(d.entry_id, {})
                source_amount = self._to_decimal(
                    source_entry.get("amount") or source_entry.get("adjusted_amount"),
                )
                if source_amount is not None:
                    w = self._to_decimal(d.writer_value)
                    r = self._to_decimal(d.reviewer_value)
                    if w == source_amount:
                        d.resolution = (
                            f"Writer 금액 채택: 원본과 정확히 일치 ({source_amount})"
                        )
                        d.resolved = True
                        d.rule_id = "RULE_SOURCE_MATCH"
                        continue
                    if r == source_amount:
                        d.resolution = (
                            f"Reviewer 금액 채택: 원본과 정확히 일치 ({source_amount})"
                        )
                        d.resolved = True
                        d.rule_id = "RULE_SOURCE_MATCH"
                        continue

            # 규칙 3: confidence 차이 0.4+ → 높은 쪽 채택
            if d.writer_confidence > 0 and d.reviewer_confidence > 0:
                diff = abs(d.writer_confidence - d.reviewer_confidence)
                if diff >= 0.4:
                    if d.writer_confidence > d.reviewer_confidence:
                        d.resolution = (
                            f"Writer 채택 (confidence {d.writer_confidence:.2f} vs "
                            f"{d.reviewer_confidence:.2f}, 차이 {diff:.2f})"
                        )
                    else:
                        d.resolution = (
                            f"Reviewer 채택 (confidence {d.reviewer_confidence:.2f} vs "
                            f"{d.writer_confidence:.2f}, 차이 {diff:.2f})"
                        )
                    d.resolved = True
                    d.rule_id = "RULE_CONFIDENCE"

        return disagreements

    def _estimate_cost(self, token_usage: dict[str, int]) -> Decimal:
        """토큰 사용량에서 비용을 추정한다."""
        rates = _COST_PER_1M_TOKENS.get(
            self.reviewer_provider, _COST_PER_1M_TOKENS["gemini"]
        )
        input_tokens = Decimal(str(token_usage.get("input_tokens", 0)))
        output_tokens = Decimal(str(token_usage.get("output_tokens", 0)))

        cost = input_tokens * rates["input"] / Decimal(
            "1000000"
        ) + output_tokens * rates["output"] / Decimal("1000000")
        return cost.quantize(Decimal("0.000001"))

    @staticmethod
    def _to_decimal(value: Any) -> Decimal | None:
        """값을 Decimal로 변환한다."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None


# ── JSON 파싱 유틸리티 ──────────────────────────────────────────

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)


def _extract_json(raw: str) -> dict[str, Any]:
    """LLM 응답에서 JSON을 안전하게 추출한다.

    1. 코드블록 (```json ... ```) 내 JSON을 정규식으로 추출
    2. 코드블록이 없으면 전체 문자열을 JSON으로 파싱
    3. 여러 코드블록이 있으면 첫 번째 유효한 JSON 사용

    Raises:
        ValueError: JSON을 추출할 수 없을 때
    """
    # 1차: 코드블록 내 JSON 추출
    matches = _JSON_BLOCK_RE.findall(raw)
    for match in matches:
        try:
            return json.loads(match.strip())
        except json.JSONDecodeError:
            continue

    # 2차: 전체 문자열을 JSON으로 시도
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass

    raise ValueError(f"JSON 추출 실패: 응답 길이={len(raw)}")
