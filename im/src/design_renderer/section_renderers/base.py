"""섹션 렌더러 추상 기반 클래스.

모든 섹션 렌더러는 BaseSectionRenderer를 상속하며,
render_html() + render_pptx() 듀얼 메서드를 구현한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.design_renderer.design_tokens import IMDesignTokens
from src.design_renderer.im_document import IMDocumentData


class RendererError(Exception):
    """렌더러 관련 예외 기반 클래스."""


class RendererNotFoundError(RendererError):
    """미등록 섹션 렌더러 접근 시 발생."""


class BaseSectionRenderer(ABC):
    """섹션 렌더러 추상 기반 클래스.

    각 렌더러는 section_id 클래스 변수로 고유 섹션 ID를 선언하고,
    render_html()과 render_pptx()를 구현한다.

    Attributes:
        section_id: SECTION_IDS 중 하나에 해당하는 고유 섹션 식별자.
    """

    section_id: str

    @abstractmethod
    def render_html(
        self,
        data: IMDocumentData,
        *,
        tokens: IMDesignTokens | None = None,
    ) -> list[str]:
        """HTML 슬라이드 렌더링.

        Args:
            data: IM 문서 통합 데이터.
            tokens: 디자인 토큰. None이면 DEFAULT_TOKENS 사용.

        Returns:
            <div class="slide">...</div> HTML 문자열 리스트.
            다중 슬라이드가 필요한 경우 여러 항목 반환.
        """

    @abstractmethod
    def render_pptx(
        self,
        factory: Any,
        data: IMDocumentData,
        *,
        prs: Any,
        tokens: IMDesignTokens | None = None,
    ) -> list[Any]:
        """PPTX 슬라이드 렌더링.

        Args:
            factory: SlideFactory 인스턴스.
            data: IM 문서 통합 데이터.
            prs: python-pptx Presentation 객체.
            tokens: 디자인 토큰. None이면 DEFAULT_TOKENS 사용.

        Returns:
            생성된 Slide 객체 리스트.
        """
