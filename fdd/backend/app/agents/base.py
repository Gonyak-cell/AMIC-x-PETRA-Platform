"""AI Agent 기본 클래스 — Sprint 6 / LLM 연동 Sprint 14.

모든 FDD 에이전트의 기본 인터페이스 및 공통 기능.
Multi-LLM 지원: Anthropic, OpenAI, Google Gemini.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from app.core.logging import get_logger
from app.services.llm import (
    LLMClient,
    create_llm_client,
    get_available_provider,
)
from app.services.llm.routing import FDDModelRouter

logger = get_logger(__name__)

# 프롬프트 및 스키마 디렉토리
PROMPTS_DIR = Path(__file__).parent / "prompts"
SCHEMAS_DIR = Path(__file__).parent / "schemas"


@dataclass
class AgentConfig:
    """에이전트 설정."""

    provider: str = "anthropic"  # LLM 프로바이더: anthropic, openai, gemini
    model: str = ""  # 모델 ID (빈 문자열이면 프로바이더 기본값 사용)
    temperature: float = 0.0  # 금융 분석은 결정론적
    max_tokens: int = 4096  # 최대 출력 토큰
    timeout_seconds: int = 60  # 타임아웃
    max_retries: int = 2  # 재시도 횟수


@dataclass
class AgentResponse:
    """에이전트 응답."""

    success: bool
    result: dict[str, Any] | None = None
    raw_output: str = ""
    token_usage: dict[str, int] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    confidence: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    """에이전트 기본 클래스.

    모든 FDD 에이전트는 이 클래스를 상속받아 구현.
    """

    prompt_version: str = "1.0"
    agent_name: str = "base"

    # 라우터 사용 시 section_id (하위 클래스에서 오버라이드)
    section_id: str = ""

    def __init__(
        self,
        config: AgentConfig | None = None,
        router: FDDModelRouter | None = None,
    ):
        """에이전트 초기화.

        Args:
            config: 에이전트 설정. None이면 기본값 사용.
            router: FDD 모델 라우터. None이면 기존 단일 프로바이더 방식 사용.
        """
        self.config = config or AgentConfig()
        self.router = router
        self._prompt_template: dict[str, Any] | None = None
        self._output_schema: dict[str, Any] | None = None
        self._llm_client: LLMClient | None = None

    def _get_llm_client(self) -> LLMClient | None:
        """LLM 클라이언트를 반환한다. 설정된 프로바이더 우선, 없으면 자동 탐색."""
        if self._llm_client is not None:
            return self._llm_client

        try:
            client = create_llm_client(self.config.provider)
            if client.is_available():
                self._llm_client = client
                return self._llm_client
        except ValueError:
            pass

        # fallback: 사용 가능한 아무 프로바이더
        self._llm_client = get_available_provider()
        return self._llm_client

    @abstractmethod
    def build_prompt(self, context: dict[str, Any]) -> str:
        """컨텍스트를 기반으로 프롬프트를 구성한다.

        Args:
            context: 에이전트에 전달할 컨텍스트 데이터

        Returns:
            구성된 프롬프트 문자열
        """

    @abstractmethod
    def parse_response(self, raw_response: str) -> dict[str, Any]:
        """LLM 응답을 파싱한다.

        Args:
            raw_response: LLM의 원시 응답 문자열

        Returns:
            파싱된 결과 딕셔너리
        """

    def validate_output(
        self,
        output: dict[str, Any],
        source_data: dict[str, Any],
    ) -> list[str]:
        """출력을 검증한다 (Guardrails).

        Args:
            output: 파싱된 LLM 출력
            source_data: 검증용 원본 데이터

        Returns:
            검증 오류 목록 (빈 리스트면 통과)
        """
        # 기본 구현: 하위 클래스에서 오버라이드
        return []

    def load_prompt_template(self) -> dict[str, Any]:
        """YAML 프롬프트 템플릿을 로드한다."""
        if self._prompt_template is not None:
            return self._prompt_template

        prompt_file = (
            PROMPTS_DIR
            / f"{self.agent_name}_v{self.prompt_version.replace('.', '_')}.yaml"
        )

        if not prompt_file.exists():
            logger.warning(
                "Prompt template not found",
                agent=self.agent_name,
                file=str(prompt_file),
            )
            return {}

        with open(prompt_file, encoding="utf-8") as f:
            self._prompt_template = yaml.safe_load(f)

        return self._prompt_template or {}

    def load_output_schema(self) -> dict[str, Any]:
        """JSON 출력 스키마를 로드한다."""
        if self._output_schema is not None:
            return self._output_schema

        schema_file = SCHEMAS_DIR / f"{self.agent_name}_schema.json"

        if not schema_file.exists():
            logger.warning(
                "Output schema not found",
                agent=self.agent_name,
                file=str(schema_file),
            )
            return {}

        with open(schema_file, encoding="utf-8") as f:
            self._output_schema = json.load(f)

        return self._output_schema or {}

    def run(
        self,
        context: dict[str, Any],
        source_data: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """에이전트를 실행한다.

        LLM API 키가 설정되어 있으면 실제 호출, 아니면 placeholder 반환.

        Args:
            context: 프롬프트 구성용 컨텍스트
            source_data: 검증용 원본 데이터

        Returns:
            에이전트 응답
        """
        logger.info(
            "Agent run started",
            extra={"ctx": {"agent": self.agent_name, "version": self.prompt_version}},
        )

        try:
            user_prompt = self.build_prompt(context)
            system_prompt = self.get_system_prompt()
            output_schema = self.load_output_schema()

            # 라우터 사용 시 — 섹션별 최적 프로바이더로 라우팅
            if self.router and self.section_id:
                try:
                    routed_response = self.router.generate(
                        self.section_id,
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        json_schema=output_schema or None,
                        timeout_seconds=self.config.timeout_seconds,
                    )
                    raw_response = routed_response.text
                    token_usage = routed_response.token_usage
                except RuntimeError:
                    # 라우터 폴백도 실패 — 기존 방식으로 전환
                    logger.warning(
                        "Router failed, falling back to direct client",
                        extra={"ctx": {"agent": self.agent_name}},
                    )
                    routed_response = None
                    raw_response = None
                    token_usage = {}

                if raw_response is not None:
                    parsed_result = self.parse_response(raw_response)
                    validation_errors: list[str] = []
                    if source_data:
                        validation_errors = self.validate_output(
                            parsed_result, source_data
                        )
                    return AgentResponse(
                        success=len(validation_errors) == 0,
                        result=parsed_result,
                        raw_output=raw_response,
                        token_usage=token_usage,
                        validation_errors=validation_errors,
                        confidence=Decimal("0"),
                    )

            # 기존 방식: 단일 프로바이더
            llm_client = self._get_llm_client()

            if llm_client is None:
                # LLM 미연동 — placeholder 반환
                logger.warning(
                    "No LLM provider available, returning placeholder",
                    extra={"ctx": {"agent": self.agent_name}},
                )
                return AgentResponse(
                    success=True,
                    result={},
                    raw_output="",
                    confidence=Decimal("0"),
                    warnings=["LLM API 키 미설정 — placeholder 응답"],
                )

            # 실제 LLM 호출 (재시도 포함)
            llm_response = None
            last_error: Exception | None = None
            for attempt in range(self.config.max_retries + 1):
                try:
                    llm_response = llm_client.chat(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=self.config.model or None,
                        temperature=self.config.temperature,
                        max_tokens=self.config.max_tokens,
                        json_schema=output_schema or None,
                        timeout_seconds=self.config.timeout_seconds,
                    )
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"LLM call attempt {attempt + 1} failed",
                        extra={"ctx": {"agent": self.agent_name, "error": str(e)}},
                    )

            if llm_response is None:
                return AgentResponse(
                    success=False,
                    validation_errors=[
                        f"LLM 호출 실패 (재시도 {self.config.max_retries}회): {last_error}"
                    ],
                )

            raw_response = llm_response.content
            parsed_result = self.parse_response(raw_response)

            # 검증
            validation_errors: list[str] = []
            if source_data:
                validation_errors = self.validate_output(parsed_result, source_data)

            return AgentResponse(
                success=len(validation_errors) == 0,
                result=parsed_result,
                raw_output=raw_response,
                token_usage=llm_response.token_usage,
                validation_errors=validation_errors,
                confidence=Decimal("0"),
            )

        except Exception as e:
            logger.error(
                "Agent run failed",
                extra={"ctx": {"agent": self.agent_name, "error": str(e)}},
            )
            return AgentResponse(
                success=False,
                validation_errors=[str(e)],
            )

    def get_system_prompt(self) -> str:
        """시스템 프롬프트를 반환한다."""
        template = self.load_prompt_template()
        return template.get("system_prompt", "")

    def get_user_prompt_template(self) -> str:
        """사용자 프롬프트 템플릿을 반환한다."""
        template = self.load_prompt_template()
        return template.get("user_prompt_template", "")
