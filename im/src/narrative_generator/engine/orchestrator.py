"""NarrativeOrchestrator — 내러티브 생성 통합 파이프라인 (T-N13).

> 마지막 수정: 2026-02-11 21:38:33

FinancialProcessor 패턴을 따라 sub-component를 초기화하고,
번호 매긴 단계로 내러티브를 생성한다.

Multi-Model Routing 지원: OpenAI, Anthropic Claude, Google Gemini를
섹션별로 라우팅하여 최적의 모델에 배정한다.

파이프라인:
  1. 데이터 준비: IMDocumentData에서 섹션별 데이터 추출
  2. RAG 검색: 관련 컨텍스트 검색 (선택적)
  3. 프롬프트 조립: system + user 프롬프트 구성
  4. LLM 호출: ModelRouter로 섹션별 프로바이더 선택 → 텍스트 생성
  5. 구조화 파싱: 수치 클레임 추출
  6. Fact Check: 수치 정합성 검증
  7. 일관성 검사 + 신뢰도 평가
  8. 결과 조합: NarrativeResult

사용 예시::

    from src.narrative_generator.engine.orchestrator import NarrativeOrchestrator

    orchestrator = NarrativeOrchestrator()
    result = orchestrator.generate(im_data, industry="tech")
    im_data.narratives = result.narratives  # Design Renderer에 공급
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from src.api.core.log_decorators import log_error_with_input
from src.design_renderer.im_document import IMDocumentData
from src.narrative_generator.config import NarrativeConfig, get_config
from src.narrative_generator.engine.structured_output import (
    SectionNarrative,
    parse_narrative_response,
)
from src.narrative_generator.engine.token_budget import TokenBudgetManager
from src.narrative_generator.engine.model_router import ModelRouter
from src.narrative_generator.engine.router_factory import create_model_router
from src.narrative_generator.exceptions import (
    LLMAPIError,
    LLMError,
    NarrativeGeneratorError,
)
from src.narrative_generator.fact_checker.confidence import (
    ConfidenceResult,
    ConfidenceScorer,
)
from src.narrative_generator.fact_checker.consistency import (
    ConsistencyChecker,
    ConsistencyReport,
)
from src.narrative_generator.fact_checker.validator import (
    FactCheckReport,
    FactValidator,
)
from src.narrative_generator.prompts import (
    create_default_registry,
    get_industry_variant,
)
from src.narrative_generator.prompts.base import PromptRegistry
from src.narrative_generator.prompts.slot_fill import SlotFillPromptBuilder
from src.narrative_generator.rag.retriever import ContextRetriever, RetrievedContext
from src.narrative_generator.templates.registry import TemplateRegistry
from src.narrative_generator.templates.renderer import TemplateRenderer
from src.narrative_generator.engine.slot_parser import SlotResponseParser

logger = logging.getLogger(__name__)

# 내러티브가 필요 없는 섹션
_SKIP_SECTIONS = {"cover", "disclaimer", "toc_divider"}


# ---------------------------------------------------------------------------
# 결과 데이터클래스
# ---------------------------------------------------------------------------


@dataclass
class CostTracker:
    """멀티 프로바이더 LLM 비용 추적기.

    Attributes:
        max_cost_usd: 문서당 최대 비용 한도 (USD).
        accumulated_cost: 누적 비용.
        usage_by_provider: 프로바이더별 토큰 사용량.
    """

    max_cost_usd: float = 1.0
    accumulated_cost: float = 0.0
    usage_by_provider: dict[str, dict[str, int]] = field(default_factory=dict)

    # 1K 토큰당 비용 (USD, 2026-02 기준)
    COST_PER_1K: dict[str, dict[str, float]] = field(default_factory=lambda: {
        "openai": {"input": 0.0025, "output": 0.01},
        "anthropic": {"input": 0.003, "output": 0.015},
        "google": {"input": 0.0001, "output": 0.0004},
    })

    def add_usage(self, provider: str, usage: dict[str, int] | None) -> None:
        """토큰 사용량을 기록하고 비용을 누적한다."""
        if not usage:
            return
        rates = self.COST_PER_1K.get(provider, self.COST_PER_1K["openai"])
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        cost = (
            prompt_tokens / 1000 * rates["input"]
            + completion_tokens / 1000 * rates["output"]
        )
        self.accumulated_cost += cost

        # 프로바이더별 집계
        if provider not in self.usage_by_provider:
            self.usage_by_provider[provider] = {"prompt_tokens": 0, "completion_tokens": 0}
        self.usage_by_provider[provider]["prompt_tokens"] += prompt_tokens
        self.usage_by_provider[provider]["completion_tokens"] += completion_tokens

    @property
    def is_over_budget(self) -> bool:
        return self.accumulated_cost > self.max_cost_usd


@dataclass
class NarrativeResult:
    """내러티브 생성 결과.

    Attributes:
        narratives: {section_id: narrative_text} 딕셔너리.
        section_narratives: 구조화된 SectionNarrative 리스트.
        fact_check_reports: 섹션별 팩트 체크 보고서.
        confidence_scores: 섹션별 신뢰도 결과.
        consistency_report: 내러티브 간 일관성 보고서.
        warnings: 처리 중 경고 메시지.
        cost_tracker: 비용 추적 정보.
    """

    narratives: dict[str, str] = field(default_factory=dict)
    section_narratives: dict[str, SectionNarrative] = field(default_factory=dict)
    fact_check_reports: dict[str, FactCheckReport] = field(default_factory=dict)
    confidence_scores: dict[str, ConfidenceResult] = field(default_factory=dict)
    consistency_report: Optional[ConsistencyReport] = None
    warnings: list[str] = field(default_factory=list)
    cost_tracker: Optional[CostTracker] = None


# ---------------------------------------------------------------------------
# NarrativeOrchestrator
# ---------------------------------------------------------------------------


class NarrativeOrchestrator:
    """내러티브 생성 통합 파이프라인.

    Args:
        config: NarrativeConfig. None이면 get_config() 사용.
        registry: PromptRegistry. None이면 기본 레지스트리 사용.
        retriever: ContextRetriever. None이면 RAG 미사용.
        llm_client: LLM 클라이언트 (테스트용 주입). None이면 자동 생성.
        model_router: ModelRouter (멀티 프로바이더 라우팅). None이면 자동 판단.
    """

    def __init__(
        self,
        config: NarrativeConfig | None = None,
        registry: PromptRegistry | None = None,
        retriever: ContextRetriever | None = None,
        llm_client: Any | None = None,
        model_router: ModelRouter | None = None,
        template_registry: TemplateRegistry | None = None,
    ) -> None:
        self._config = config or get_config()
        self._registry = registry or create_default_registry()
        self._retriever = retriever
        self._token_manager = TokenBudgetManager()
        self._fact_validator = FactValidator()
        self._consistency_checker = ConsistencyChecker()
        self._confidence_scorer = ConfidenceScorer(
            threshold=self._config.confidence_threshold,
        )

        # 템플릿 시스템 (슬롯 채우기 방식)
        self._template_registry: TemplateRegistry | None = None
        self._template_renderer: TemplateRenderer | None = None
        self._slot_fill_builder: SlotFillPromptBuilder | None = None
        self._slot_parser: SlotResponseParser | None = None

        if template_registry is not None:
            self._template_registry = template_registry
            self._template_renderer = TemplateRenderer()
            self._slot_fill_builder = SlotFillPromptBuilder()
            self._slot_parser = SlotResponseParser()
        elif self._config.template_enabled:
            template_dir = self._config.template_dir
            if not template_dir:
                # 기본 경로: 패키지 내 templates/ 디렉터리
                from pathlib import Path
                template_dir = str(
                    Path(__file__).resolve().parent.parent / "templates"
                )
            self._template_registry = TemplateRegistry(template_dir)
            self._template_renderer = TemplateRenderer()
            self._slot_fill_builder = SlotFillPromptBuilder()
            self._slot_parser = SlotResponseParser()

        # LLM 라우팅 설정
        if model_router is not None:
            # 새로운 multi-model 라우터
            self._model_router: ModelRouter | None = model_router
            self._llm_client = None
        elif llm_client is not None:
            # 기존 방식: 직접 주입된 클라이언트 (테스트/레거시 호환)
            self._model_router = None
            self._llm_client = llm_client
        else:
            # 기본: config에 따라 라우터 또는 단일 클라이언트 생성
            if self._config.has_anthropic or self._config.has_google:
                self._model_router = create_model_router(self._config)
                self._llm_client = None
            else:
                self._model_router = None
                self._llm_client = self._create_llm_client()

    @log_error_with_input
    def generate(
        self,
        data: IMDocumentData,
        *,
        industry: str = "",
        sections: list[str] | None = None,
        feedback_hints: dict[str, list[str]] | None = None,
    ) -> NarrativeResult:
        """전체 IM 내러티브를 생성한다.

        Args:
            data: IM 문서 통합 데이터.
            industry: 산업 분류 ("tech", "healthcare", "manufacturing",
                      "financial_services"). 빈 문자열이면 일반.
            sections: 생성할 섹션 ID 리스트. None이면 data의 활성 섹션 전체.
            feedback_hints: Ralph Loop 이전 평가 피드백.
                ``{section_id: ["피드백1", "피드백2"]}`` 형태.
                해당 섹션 프롬프트 끝에 피드백 블록이 추가된다.

        Returns:
            NarrativeResult.
        """
        cost_tracker = CostTracker()
        result = NarrativeResult(cost_tracker=cost_tracker)

        # 활성 섹션 결정
        active_sections = sections or data.get_active_sections()
        target_sections = [
            s for s in active_sections if s not in _SKIP_SECTIONS and self._registry.has(s)
        ]

        logger.info(
            "내러티브 생성 시작: %d개 섹션, industry='%s'",
            len(target_sections),
            industry,
        )

        # 산업별 컨텍스트
        industry_context = ""
        variant = get_industry_variant(industry) if industry else None
        if variant:
            industry_context = variant.format_context()

        # --- 각 섹션 생성 ---
        for section_id in target_sections:
            # 비용 한도 초과 검사
            if cost_tracker.is_over_budget:
                result.warnings.append(
                    f"비용 한도 초과 (${cost_tracker.accumulated_cost:.4f} / "
                    f"${cost_tracker.max_cost_usd:.2f}). "
                    f"'{section_id}'부터 생성 중단."
                )
                logger.warning(
                    "비용 한도 초과: $%.4f / $%.2f",
                    cost_tracker.accumulated_cost,
                    cost_tracker.max_cost_usd,
                )
                break

            try:
                section_feedback = (feedback_hints or {}).get(section_id)
                section_narrative = self._generate_section(
                    section_id=section_id,
                    data=data,
                    industry=industry,
                    industry_context=industry_context,
                    cost_tracker=cost_tracker,
                    feedback=section_feedback,
                )

                # 토큰 예산 검사 & 자르기
                budget_check = self._token_manager.check_budget(section_id, section_narrative.text)
                if not budget_check.within_budget:
                    section_narrative = SectionNarrative(
                        section_id=section_id,
                        text=self._token_manager.truncate_to_budget(
                            section_narrative.text,
                            budget_check.budget,
                        ),
                        key_claims=section_narrative.key_claims,
                        metadata=section_narrative.metadata,
                    )
                    result.warnings.append(
                        f"토큰 예산 초과로 자름: section='{section_id}', "
                        f"예산={budget_check.budget}, 실제={budget_check.actual}"
                    )

                result.narratives[section_id] = section_narrative.text
                result.section_narratives[section_id] = section_narrative

                # --- Fact Check ---
                if self._config.fact_check_enabled:
                    fact_report = self._fact_validator.validate(section_narrative, data)
                    result.fact_check_reports[section_id] = fact_report

                    # 신뢰도 평가
                    confidence = self._confidence_scorer.score(section_narrative, fact_report)
                    result.confidence_scores[section_id] = confidence

                    if not confidence.is_confident:
                        result.warnings.append(
                            f"신뢰도 미달: section='{section_id}', "
                            f"점수={confidence.overall_score:.2f}"
                        )

            except NarrativeGeneratorError as exc:
                logger.warning("섹션 '%s' 내러티브 생성 실패: %s", section_id, exc)
                result.warnings.append(f"섹션 '{section_id}' 생성 실패: {exc.message}")
            except Exception as exc:
                logger.error("섹션 '%s' 예기치 않은 오류: %s", section_id, exc)
                result.warnings.append(f"섹션 '{section_id}' 오류: {exc}")

        # --- 일관성 검사 ---
        if result.section_narratives and self._config.fact_check_enabled:
            result.consistency_report = self._consistency_checker.check(result.section_narratives)
            if not result.consistency_report.is_consistent:
                result.warnings.extend(result.consistency_report.warnings)

        logger.info(
            "내러티브 생성 완료: %d/%d 섹션 성공, %d 경고, 비용=$%.4f",
            len(result.narratives),
            len(target_sections),
            len(result.warnings),
            cost_tracker.accumulated_cost,
        )

        return result

    def generate_section(
        self,
        section_id: str,
        data: IMDocumentData,
        *,
        industry: str = "",
    ) -> SectionNarrative:
        """단일 섹션의 내러티브를 생성한다.

        Args:
            section_id: 섹션 식별자.
            data: IM 문서 통합 데이터.
            industry: 산업 분류.

        Returns:
            SectionNarrative.
        """
        industry_context = ""
        variant = get_industry_variant(industry) if industry else None
        if variant:
            industry_context = variant.format_context()

        return self._generate_section(
            section_id=section_id,
            data=data,
            industry=industry,
            industry_context=industry_context,
        )

    # -----------------------------------------------------------------------
    # 내부 메서드
    # -----------------------------------------------------------------------

    def _generate_section(
        self,
        section_id: str,
        data: IMDocumentData,
        industry: str,
        industry_context: str,
        cost_tracker: CostTracker | None = None,
        feedback: list[str] | None = None,
    ) -> SectionNarrative:
        """단일 섹션 내러티브 생성 (내부 구현).

        템플릿이 있으면 슬롯 채우기 방식, 없으면 기존 자유 생성 방식.
        """
        # 템플릿 분기: 템플릿이 있으면 슬롯 채우기
        if (
            self._template_registry is not None
            and self._template_registry.has(section_id)
        ):
            return self._generate_section_template(
                section_id=section_id,
                data=data,
                industry=industry,
                industry_context=industry_context,
                cost_tracker=cost_tracker,
            )

        # 기존 자유 생성 방식 (레거시)
        return self._generate_section_legacy(
            section_id=section_id,
            data=data,
            industry=industry,
            industry_context=industry_context,
            cost_tracker=cost_tracker,
            feedback=feedback,
        )

    def _generate_section_legacy(
        self,
        section_id: str,
        data: IMDocumentData,
        industry: str,
        industry_context: str,
        cost_tracker: CostTracker | None = None,
        feedback: list[str] | None = None,
    ) -> SectionNarrative:
        """기존 자유 생성 방식 (레거시).

        Steps:
        1. 프롬프트 조회
        2. RAG 컨텍스트 검색 (선택적)
        3. 시스템/유저 프롬프트 조립 (+ 피드백 주입)
        4. LLM 호출
        5. 응답 파싱
        """
        # 1. 프롬프트 조회
        prompt = self._registry.get(section_id)

        # 2. RAG 컨텍스트 검색
        context: list[RetrievedContext] = []
        if self._retriever:
            try:
                query = self._build_rag_query(section_id, data)
                context = self._retriever.retrieve(
                    query,
                    section_id=section_id,
                    industry=industry,
                    namespace=data.corp_code or "",
                )
            except Exception as exc:
                logger.warning(
                    "RAG 검색 실패 (graceful degradation): section='%s', error=%s",
                    section_id,
                    exc,
                )

        # 3. 프롬프트 조립
        system_prompt = prompt.build_system_prompt(industry_context=industry_context)
        user_prompt = prompt.build_user_prompt(data, context)

        # 3-1. Ralph Loop 피드백 주입
        if feedback:
            feedback_block = "\n\n---\n이전 평가 피드백 (반드시 반영하세요):\n"
            for i, hint in enumerate(feedback, 1):
                feedback_block += f"  {i}. {hint}\n"
            user_prompt += feedback_block

        # 4. LLM 호출
        raw_response = self._call_llm(
            system_prompt, user_prompt,
            section_id=section_id, industry=industry,
            cost_tracker=cost_tracker,
        )

        # 5. 응답 파싱
        return parse_narrative_response(raw_response, section_id)

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        section_id: str = "",
        industry: str = "",
        cost_tracker: CostTracker | None = None,
    ) -> str:
        """LLM API를 호출하여 텍스트를 생성한다.

        multi-model 라우터가 설정되어 있으면 섹션에 따라 프로바이더를 선택하고,
        없으면 기존 단일 클라이언트를 사용한다.
        """
        if self._model_router is not None:
            response = self._model_router.generate(
                section_id=section_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                industry=industry,
                temperature=self._config.narrative_temperature,
                max_tokens=self._config.narrative_max_tokens,
            )
            logger.debug(
                "LLM 호출 완료: section='%s', provider=%s, model=%s",
                section_id,
                response.provider.value,
                response.model,
            )
            if cost_tracker is not None:
                cost_tracker.add_usage(response.provider.value, response.usage)
            return response.text

        # 기존 단일 클라이언트 경로 (레거시 호환)
        try:
            response = self._llm_client.chat.completions.create(
                model=self._config.narrative_model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self._config.narrative_temperature,
                max_tokens=self._config.narrative_max_tokens,
            )
            content = response.choices[0].message.content
            return content or ""
        except Exception as exc:
            raise LLMAPIError(
                provider="openai",
                original_error=str(exc),
            ) from exc

    def _create_llm_client(self) -> Any:
        """OpenAI LLM 클라이언트를 생성한다."""
        if not self._config.has_openai:
            logger.warning("OpenAI API 키 미설정 — LLM 호출 불가")
            return _NullLLMClient()

        try:
            from openai import OpenAI

            return OpenAI(api_key=self._config.openai_api_key)
        except ImportError:
            logger.warning("openai 패키지 미설치 — LLM 호출 불가")
            return _NullLLMClient()

    def _generate_section_template(
        self,
        section_id: str,
        data: IMDocumentData,
        industry: str,
        industry_context: str,
        cost_tracker: CostTracker | None = None,
    ) -> SectionNarrative:
        """템플릿 기반 슬롯 채우기 방식으로 내러티브를 생성한다.

        Steps:
        1. 템플릿 로드 (산업별 오버라이드 포함)
        2. L3 슬롯 확인
        3. L3 슬롯이 있으면 LLM 호출 (슬롯 채우기 프롬프트)
        4. TemplateRenderer로 L1/L2/L3/L4 조합
        5. SectionNarrative 반환
        """
        assert self._template_registry is not None
        assert self._template_renderer is not None
        assert self._slot_fill_builder is not None
        assert self._slot_parser is not None

        # 1. 템플릿 로드
        template = self._template_registry.get(section_id, industry=industry)
        if template is None:
            raise LLMError(f"템플릿 로드 실패: section={section_id}")

        # 2. L3 슬롯 확인
        l3_slots = template.l3_slots
        llm_slots: dict[str, str] = {}

        # 3. L3 슬롯이 있으면 LLM 호출
        if l3_slots:
            system_prompt = self._slot_fill_builder.build_system_prompt(
                industry_context=industry_context,
            )
            user_prompt = self._slot_fill_builder.build_user_prompt(
                template, data, industry_context=industry_context,
            )

            raw_response = self._call_llm(
                system_prompt,
                user_prompt,
                section_id=section_id,
                industry=industry,
                cost_tracker=cost_tracker,
            )

            expected = list(l3_slots.keys())
            llm_slots = self._slot_parser.parse(raw_response, expected)

            # 파싱 실패한 슬롯 경고
            missing = set(expected) - set(llm_slots.keys())
            if missing:
                logger.warning(
                    "슬롯 파싱 일부 실패: section=%s, missing=%s",
                    section_id,
                    missing,
                )

        # 4. 렌더링
        base_blocks = self._template_registry.base_blocks
        rendered_text = self._template_renderer.render(
            template=template,
            data=data,
            llm_slots=llm_slots,
            industry=industry,
            base_blocks=base_blocks,
        )

        # 5. SectionNarrative 반환
        return SectionNarrative(
            section_id=section_id,
            text=rendered_text,
            key_claims=[],
            metadata={"mode": "template", "l3_slots_filled": len(llm_slots)},
        )

    @staticmethod
    def _build_rag_query(section_id: str, data: IMDocumentData) -> str:
        """RAG 검색용 쿼리를 구성한다."""
        parts = [data.company_name_kr, section_id]

        if section_id == "financial_analysis" and data.financial_statements.revenue:
            latest_year = (
                data.financial_statements.years[-1] if data.financial_statements.years else ""
            )
            if latest_year:
                parts.append(f"{latest_year}년 재무 실적")

        if section_id == "market_overview" and data.market_data:
            if data.market_data.industry_trends:
                parts.append(data.market_data.industry_trends[0])

        return " ".join(parts)


# ---------------------------------------------------------------------------
# Null Object (LLM 미사용 시)
# ---------------------------------------------------------------------------


class _NullLLMClient:
    """LLM API 키가 없을 때 사용하는 Null Object.

    싱글턴 인스턴스를 사용하여 불필요한 객체 생성을 방지한다.
    """

    def __init__(self) -> None:
        self._chat = _NullChat()

    @property
    def chat(self) -> "_NullChat":
        return self._chat


class _NullChat:
    def __init__(self) -> None:
        self._completions = _NullCompletions()

    @property
    def completions(self) -> "_NullCompletions":
        return self._completions


class _NullCompletions:
    def create(self, **kwargs: Any) -> "_NullResponse":
        logger.warning("LLM 클라이언트 미설정 — 빈 응답 반환")
        return _NullResponse()


class _NullResponse:
    def __init__(self) -> None:
        self.choices = [_NullChoice()]


class _NullChoice:
    def __init__(self) -> None:
        self.message = _NullMessage()


class _NullMessage:
    content: str = ""
