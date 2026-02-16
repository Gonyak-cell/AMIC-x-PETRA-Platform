"""Playwright 기반 웹 크롤링 엔진.

JavaScript 렌더링이 필요한 동적 웹 페이지를 크롤링하기 위한
Playwright 래퍼를 제공합니다.

사용 예시:
    async with PlaywrightEngine() as engine:
        # HTML 가져오기
        html = await engine.get_page_content("https://example.com")

        # 스크린샷 캡처
        screenshot = await engine.capture_screenshot("https://example.com")

        # JavaScript 실행 후 결과 가져오기
        data = await engine.evaluate_script("https://example.com", "document.title")
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.data_ingestor.exceptions import (
    ContentExtractionError,
    CrawlerBlockedError,
    CrawlerNetworkError,
    CrawlerTimeoutError,
    PageRenderError,
)

if TYPE_CHECKING:
    from playwright.async_api import Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)


@dataclass
class CrawlerConfig:
    """크롤러 설정."""

    headless: bool = True
    """헤드리스 모드 여부."""

    timeout: float = 30.0
    """페이지 로드 타임아웃 (초)."""

    wait_for_network_idle: bool = True
    """네트워크 유휴 상태까지 대기 여부."""

    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    """User-Agent 문자열."""

    viewport_width: int = 1920
    """뷰포트 너비."""

    viewport_height: int = 1080
    """뷰포트 높이."""

    locale: str = "ko-KR"
    """로케일 설정."""

    timezone: str = "Asia/Seoul"
    """타임존 설정."""

    block_images: bool = False
    """이미지 로딩 차단 여부 (속도 향상용)."""

    block_fonts: bool = False
    """폰트 로딩 차단 여부."""

    extra_headers: dict[str, str] = field(default_factory=dict)
    """추가 HTTP 헤더."""


@dataclass
class PageResult:
    """페이지 크롤링 결과."""

    url: str
    """최종 URL (리다이렉트 후)."""

    html: str
    """HTML 콘텐츠."""

    title: str
    """페이지 제목."""

    status: int
    """HTTP 상태 코드."""

    headers: dict[str, str] = field(default_factory=dict)
    """응답 헤더."""

    cookies: list[dict[str, Any]] = field(default_factory=list)
    """쿠키 목록."""

    load_time_ms: float = 0.0
    """페이지 로드 시간 (밀리초)."""


class PlaywrightEngine:
    """Playwright 기반 웹 크롤링 엔진.

    JavaScript 렌더링, 페이지 상호작용, 스크린샷 캡처 등을
    지원하는 고급 크롤링 기능을 제공합니다.

    Attributes:
        config: 크롤러 설정.

    Example:
        >>> async with PlaywrightEngine() as engine:
        ...     result = await engine.get_page("https://example.com")
        ...     print(f"Title: {result.title}")
        ...     print(f"Load time: {result.load_time_ms:.0f}ms")
    """

    def __init__(self, config: CrawlerConfig | None = None) -> None:
        """PlaywrightEngine 초기화.

        Args:
            config: 크롤러 설정. None이면 기본값 사용.
        """
        self.config = config or CrawlerConfig()
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> PlaywrightEngine:
        """비동기 컨텍스트 매니저 진입."""
        await self._ensure_browser()
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: Any) -> None:
        """비동기 컨텍스트 매니저 종료."""
        await self.close()

    async def _ensure_browser(self) -> BrowserContext:
        """브라우저와 컨텍스트가 초기화되었는지 확인."""
        if self._context is not None:
            return self._context

        try:
            from playwright.async_api import async_playwright
        except ImportError as e:
            raise CrawlerNetworkError(
                message="Playwright가 설치되지 않았습니다.",
                details={
                    "install": "pip install playwright && playwright install chromium",
                },
            ) from e

        try:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.config.headless,
            )

            # 브라우저 컨텍스트 생성
            self._context = await self._browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                },
                user_agent=self.config.user_agent,
                locale=self.config.locale,
                timezone_id=self.config.timezone,
                extra_http_headers=self.config.extra_headers or {},
            )

            # 리소스 차단 설정
            if self.config.block_images or self.config.block_fonts:
                await self._context.route(
                    "**/*",
                    lambda route: self._handle_route(route),
                )

            return self._context

        except Exception as e:
            raise CrawlerNetworkError(
                message=f"브라우저 초기화 실패: {e}",
                details={"error": str(e)},
            ) from e

    async def _handle_route(self, route: Any) -> None:
        """리소스 요청 라우팅 핸들러."""
        request = route.request
        resource_type = request.resource_type

        if self.config.block_images and resource_type == "image":
            await route.abort()
            return

        if self.config.block_fonts and resource_type == "font":
            await route.abort()
            return

        await route.continue_()

    async def close(self) -> None:
        """브라우저 연결 종료."""
        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @property
    def is_connected(self) -> bool:
        """브라우저가 연결되어 있는지 확인."""
        return self._browser is not None and self._browser.is_connected()

    async def get_page(
        self,
        url: str,
        *,
        wait_until: str = "networkidle",
        wait_for_selector: str | None = None,
        timeout: float | None = None,
    ) -> PageResult:
        """URL의 페이지를 가져옵니다.

        Args:
            url: 크롤링할 URL.
            wait_until: 페이지 로드 대기 조건 ("load", "domcontentloaded", "networkidle").
            wait_for_selector: 특정 요소가 나타날 때까지 대기.
            timeout: 타임아웃 (초). None이면 설정값 사용.

        Returns:
            PageResult: 페이지 크롤링 결과.

        Raises:
            CrawlerTimeoutError: 타임아웃 초과.
            CrawlerBlockedError: 접근이 차단됨.
            PageRenderError: 페이지 렌더링 실패.
        """
        context = await self._ensure_browser()
        page: Page | None = None
        timeout_ms = int((timeout or self.config.timeout) * 1000)

        try:
            import time
            start_time = time.monotonic()

            page = await context.new_page()

            # 페이지 로드
            response = await page.goto(
                url,
                wait_until=wait_until,  # type: ignore
                timeout=timeout_ms,
            )

            if response is None:
                raise PageRenderError(
                    message="페이지 응답을 받지 못했습니다.",
                    details={"url": url},
                )

            # 추가 대기
            if wait_for_selector:
                await page.wait_for_selector(
                    wait_for_selector,
                    timeout=timeout_ms,
                )

            # 결과 수집
            end_time = time.monotonic()
            load_time_ms = (end_time - start_time) * 1000

            # 차단 감지
            status = response.status
            if status in (403, 429):
                raise CrawlerBlockedError(
                    message=f"접근이 차단되었습니다: HTTP {status}",
                    details={"url": url, "status": status},
                )

            html = await page.content()
            title = await page.title()
            cookies = await context.cookies(url)

            return PageResult(
                url=page.url,
                html=html,
                title=title,
                status=status,
                headers=dict(response.headers),
                cookies=cookies,
                load_time_ms=load_time_ms,
            )

        except asyncio.TimeoutError as e:
            raise CrawlerTimeoutError(
                message=f"페이지 로드 타임아웃: {url}",
                details={"url": url, "timeout": timeout or self.config.timeout},
            ) from e

        except CrawlerBlockedError:
            raise

        except Exception as e:
            if "net::ERR_" in str(e):
                raise CrawlerNetworkError(
                    message=f"네트워크 오류: {e}",
                    details={"url": url},
                ) from e

            raise PageRenderError(
                message=f"페이지 렌더링 실패: {e}",
                details={"url": url},
            ) from e

        finally:
            if page:
                await page.close()

    async def get_page_content(
        self,
        url: str,
        *,
        wait_until: str = "networkidle",
        timeout: float | None = None,
    ) -> str:
        """URL의 HTML 콘텐츠만 가져옵니다.

        Args:
            url: 크롤링할 URL.
            wait_until: 페이지 로드 대기 조건.
            timeout: 타임아웃 (초).

        Returns:
            HTML 콘텐츠 문자열.
        """
        result = await self.get_page(url, wait_until=wait_until, timeout=timeout)
        return result.html

    async def evaluate_script(
        self,
        url: str,
        script: str,
        *,
        wait_until: str = "networkidle",
        timeout: float | None = None,
    ) -> Any:
        """페이지에서 JavaScript를 실행하고 결과를 반환합니다.

        Args:
            url: 크롤링할 URL.
            script: 실행할 JavaScript 코드.
            wait_until: 페이지 로드 대기 조건.
            timeout: 타임아웃 (초).

        Returns:
            JavaScript 실행 결과.

        Example:
            >>> result = await engine.evaluate_script(
            ...     "https://example.com",
            ...     "document.querySelectorAll('a').length"
            ... )
        """
        context = await self._ensure_browser()
        page: Page | None = None
        timeout_ms = int((timeout or self.config.timeout) * 1000)

        try:
            page = await context.new_page()
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)  # type: ignore
            return await page.evaluate(script)

        finally:
            if page:
                await page.close()

    async def capture_screenshot(
        self,
        url: str,
        *,
        path: str | Path | None = None,
        full_page: bool = False,
        wait_until: str = "networkidle",
        timeout: float | None = None,
    ) -> bytes:
        """페이지 스크린샷을 캡처합니다.

        Args:
            url: 크롤링할 URL.
            path: 저장 경로. None이면 바이트로만 반환.
            full_page: 전체 페이지 캡처 여부.
            wait_until: 페이지 로드 대기 조건.
            timeout: 타임아웃 (초).

        Returns:
            PNG 이미지 바이트.
        """
        context = await self._ensure_browser()
        page: Page | None = None
        timeout_ms = int((timeout or self.config.timeout) * 1000)

        try:
            page = await context.new_page()
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)  # type: ignore

            screenshot = await page.screenshot(
                path=str(path) if path else None,
                full_page=full_page,
                type="png",
            )
            return screenshot

        finally:
            if page:
                await page.close()

    async def extract_text(
        self,
        url: str,
        selector: str = "body",
        *,
        wait_until: str = "networkidle",
        timeout: float | None = None,
    ) -> str:
        """페이지에서 텍스트를 추출합니다.

        Args:
            url: 크롤링할 URL.
            selector: CSS 선택자.
            wait_until: 페이지 로드 대기 조건.
            timeout: 타임아웃 (초).

        Returns:
            추출된 텍스트.
        """
        context = await self._ensure_browser()
        page: Page | None = None
        timeout_ms = int((timeout or self.config.timeout) * 1000)

        try:
            page = await context.new_page()
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)  # type: ignore

            element = await page.query_selector(selector)
            if element is None:
                raise ContentExtractionError(
                    message=f"요소를 찾을 수 없습니다: {selector}",
                    details={"url": url, "selector": selector},
                )

            text = await element.inner_text()
            return text.strip()

        finally:
            if page:
                await page.close()

    async def extract_links(
        self,
        url: str,
        selector: str = "a",
        *,
        wait_until: str = "networkidle",
        timeout: float | None = None,
    ) -> list[dict[str, str]]:
        """페이지에서 링크를 추출합니다.

        Args:
            url: 크롤링할 URL.
            selector: 링크 요소의 CSS 선택자.
            wait_until: 페이지 로드 대기 조건.
            timeout: 타임아웃 (초).

        Returns:
            링크 정보 리스트 (href, text 포함).
        """
        script = f"""
        Array.from(document.querySelectorAll('{selector}')).map(a => ({{
            href: a.href,
            text: a.innerText.trim()
        }}))
        """
        return await self.evaluate_script(url, script, wait_until=wait_until, timeout=timeout)

    async def fill_form(
        self,
        url: str,
        form_data: dict[str, str],
        submit_selector: str | None = None,
        *,
        wait_until: str = "networkidle",
        timeout: float | None = None,
    ) -> PageResult:
        """폼을 작성하고 제출합니다.

        Args:
            url: 폼이 있는 URL.
            form_data: 필드명 → 값 매핑.
            submit_selector: 제출 버튼 선택자. None이면 제출하지 않음.
            wait_until: 페이지 로드 대기 조건.
            timeout: 타임아웃 (초).

        Returns:
            제출 후 페이지 결과.
        """
        context = await self._ensure_browser()
        page: Page | None = None
        timeout_ms = int((timeout or self.config.timeout) * 1000)

        try:
            import time
            start_time = time.monotonic()

            page = await context.new_page()
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)  # type: ignore

            # 폼 필드 채우기
            for field, value in form_data.items():
                await page.fill(f"[name='{field}']", value)

            # 제출
            if submit_selector:
                await page.click(submit_selector)
                await page.wait_for_load_state(wait_until)  # type: ignore

            end_time = time.monotonic()

            return PageResult(
                url=page.url,
                html=await page.content(),
                title=await page.title(),
                status=200,
                load_time_ms=(end_time - start_time) * 1000,
            )

        finally:
            if page:
                await page.close()
