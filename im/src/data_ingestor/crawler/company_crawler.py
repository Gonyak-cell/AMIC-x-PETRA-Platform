"""기업 웹사이트 크롤러.

기업 홈페이지에서 회사 소개, 제품/서비스, IR 정보 등을 수집합니다.

사용 예시:
    crawler = CompanyCrawler()

    # 기업 정보 추출
    info = await crawler.extract_company_info("https://www.samsung.com")

    # IR 페이지 크롤링
    ir_data = await crawler.crawl_ir_page("https://www.company.com/ir")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from src.data_ingestor.crawler.playwright_engine import CrawlerConfig, PlaywrightEngine

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class CompanyWebInfo:
    """기업 웹사이트에서 추출한 정보."""

    url: str
    """웹사이트 URL."""

    name: str = ""
    """회사명."""

    description: str = ""
    """회사 소개."""

    vision: str = ""
    """비전/미션."""

    history: list[dict[str, str]] = field(default_factory=list)
    """연혁 (year, event)."""

    products: list[dict[str, str]] = field(default_factory=list)
    """제품/서비스 (name, description)."""

    executives: list[dict[str, str]] = field(default_factory=list)
    """경영진 (name, title)."""

    locations: list[dict[str, str]] = field(default_factory=list)
    """사업장 위치 (name, address)."""

    contact: dict[str, str] = field(default_factory=dict)
    """연락처 (phone, email, fax)."""

    social_links: dict[str, str] = field(default_factory=dict)
    """소셜 미디어 링크."""

    ir_url: str = ""
    """IR 페이지 URL."""

    careers_url: str = ""
    """채용 페이지 URL."""

    logo_url: str = ""
    """로고 이미지 URL."""

    brand_colors: list[str] = field(default_factory=list)
    """브랜드 컬러 (HEX)."""

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "url": self.url,
            "name": self.name,
            "description": self.description,
            "vision": self.vision,
            "history": self.history,
            "products": self.products,
            "executives": self.executives,
            "locations": self.locations,
            "contact": self.contact,
            "social_links": self.social_links,
            "ir_url": self.ir_url,
            "careers_url": self.careers_url,
            "logo_url": self.logo_url,
            "brand_colors": self.brand_colors,
        }


@dataclass
class IRDocument:
    """IR 문서 정보."""

    title: str
    """문서 제목."""

    url: str
    """다운로드 URL."""

    doc_type: str = ""
    """문서 유형 (annual_report, earnings, presentation 등)."""

    date: str = ""
    """게시 날짜."""

    file_type: str = ""
    """파일 형식 (pdf, xlsx 등)."""


class CompanyCrawler:
    """기업 웹사이트 크롤러.

    기업 홈페이지에서 회사 정보, 제품/서비스, IR 정보 등을
    자동으로 추출합니다.

    Attributes:
        engine: Playwright 엔진 인스턴스.

    Example:
        >>> crawler = CompanyCrawler()
        >>> info = await crawler.extract_company_info("https://www.samsung.com")
        >>> print(f"회사명: {info.name}")
        >>> print(f"소개: {info.description}")
    """

    # 일반적인 페이지 패턴
    ABOUT_PATTERNS = [
        "/about",
        "/company",
        "/about-us",
        "/aboutus",
        "/corporate",
        "/introduction",
        "/who-we-are",
        "/profile",
        "/회사소개",
        "/기업소개",
    ]

    IR_PATTERNS = [
        "/ir",
        "/investor",
        "/investors",
        "/investor-relations",
        "/financial",
        "/earnings",
        "/finance",
        "/투자정보",
        "/IR",
    ]

    CAREERS_PATTERNS = [
        "/careers",
        "/jobs",
        "/career",
        "/hiring",
        "/work-with-us",
        "/채용",
        "/인재채용",
        "/recruit",
    ]

    def __init__(
        self,
        *,
        headless: bool = True,
        timeout: float = 30.0,
        engine: PlaywrightEngine | None = None,
    ) -> None:
        """CompanyCrawler 초기화.

        Args:
            headless: 헤드리스 모드 여부.
            timeout: 크롤링 타임아웃 (초).
            engine: 기존 PlaywrightEngine 인스턴스. None이면 새로 생성.
        """
        self._engine = engine
        self._own_engine = engine is None
        self._config = CrawlerConfig(
            headless=headless,
            timeout=timeout,
        )

    async def _ensure_engine(self) -> PlaywrightEngine:
        """엔진이 초기화되었는지 확인."""
        if self._engine is None:
            self._engine = PlaywrightEngine(self._config)
            await self._engine._ensure_browser()
        return self._engine

    async def close(self) -> None:
        """리소스 정리."""
        if self._own_engine and self._engine is not None:
            await self._engine.close()
            self._engine = None

    async def extract_company_info(
        self,
        url: str,
        *,
        crawl_subpages: bool = True,
        timeout: float | None = None,
    ) -> CompanyWebInfo:
        """기업 웹사이트에서 정보를 추출합니다.

        Args:
            url: 기업 웹사이트 URL.
            crawl_subpages: About, IR 등 하위 페이지도 크롤링할지 여부.
            timeout: 타임아웃 (초).

        Returns:
            추출된 기업 정보.
        """
        engine = await self._ensure_engine()
        info = CompanyWebInfo(url=url)

        try:
            # 메인 페이지 크롤링
            await engine.get_page(url, timeout=timeout)

            # 기본 정보 추출
            info.name = await self._extract_company_name(engine, url)
            info.logo_url = await self._extract_logo_url(engine, url)
            info.contact = await self._extract_contact(engine, url)
            info.social_links = await self._extract_social_links(engine, url)

            # 중요 페이지 URL 찾기
            links = await engine.extract_links(url)
            info.ir_url = self._find_page_url(links, self.IR_PATTERNS, url)
            info.careers_url = self._find_page_url(links, self.CAREERS_PATTERNS, url)
            about_url = self._find_page_url(links, self.ABOUT_PATTERNS, url)

            # 하위 페이지 크롤링
            if crawl_subpages:
                if about_url:
                    about_info = await self._crawl_about_page(
                        engine, about_url, timeout
                    )
                    info.description = about_info.get("description", "")
                    info.vision = about_info.get("vision", "")
                    info.history = about_info.get("history", [])
                    info.executives = about_info.get("executives", [])

        except Exception as e:
            logger.warning("기업 정보 추출 실패: %s - %s", url, e)

        return info

    async def _extract_company_name(
        self,
        engine: PlaywrightEngine,
        url: str,
    ) -> str:
        """회사명을 추출합니다."""
        script = """
        (() => {
            // 메타 태그에서 찾기
            const ogSiteName = document.querySelector('meta[property="og:site_name"]');
            if (ogSiteName) return ogSiteName.content;

            // title에서 추출
            const title = document.title;
            if (title) {
                // 일반적인 구분자로 분리
                const parts = title.split(/[|\-–—:]/).map(s => s.trim());
                return parts[0] || title;
            }

            return '';
        })()
        """
        try:
            return await engine.evaluate_script(url, script)
        except Exception:
            return ""

    async def _extract_logo_url(
        self,
        engine: PlaywrightEngine,
        url: str,
    ) -> str:
        """로고 URL을 추출합니다."""
        script = """
        (() => {
            // 일반적인 로고 선택자들
            const selectors = [
                'header img[class*="logo"]',
                'header img[alt*="logo"]',
                '.logo img',
                '#logo img',
                'a[class*="logo"] img',
                'img[class*="logo"]',
                'link[rel="icon"]',
            ];

            for (const selector of selectors) {
                const el = document.querySelector(selector);
                if (el) {
                    return el.src || el.href || '';
                }
            }

            return '';
        })()
        """
        try:
            logo_url = await engine.evaluate_script(url, script)
            if logo_url:
                return urljoin(url, logo_url)
        except Exception:
            pass
        return ""

    async def _extract_contact(
        self,
        engine: PlaywrightEngine,
        url: str,
    ) -> dict[str, str]:
        """연락처 정보를 추출합니다."""
        script = """
        (() => {
            const contact = {};
            const text = document.body.innerText;

            // 전화번호 패턴
            const phoneMatch = text.match(/(?:TEL|전화|대표전화)[:\s]*([0-9\-\(\)\s]{10,})/i);
            if (phoneMatch) contact.phone = phoneMatch[1].trim();

            // 팩스 패턴
            const faxMatch = text.match(/(?:FAX|팩스)[:\s]*([0-9\-\(\)\s]{10,})/i);
            if (faxMatch) contact.fax = faxMatch[1].trim();

            // 이메일 패턴
            const emailMatch = text.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
            if (emailMatch) contact.email = emailMatch[1];

            return contact;
        })()
        """
        try:
            return await engine.evaluate_script(url, script)
        except Exception:
            return {}

    async def _extract_social_links(
        self,
        engine: PlaywrightEngine,
        url: str,
    ) -> dict[str, str]:
        """소셜 미디어 링크를 추출합니다."""
        script = """
        (() => {
            const social = {};
            const links = document.querySelectorAll('a[href]');

            const patterns = {
                facebook: /facebook\\.com/,
                twitter: /twitter\\.com|x\\.com/,
                instagram: /instagram\\.com/,
                youtube: /youtube\\.com/,
                linkedin: /linkedin\\.com/,
                blog: /blog\\./,
            };

            links.forEach(link => {
                for (const [name, pattern] of Object.entries(patterns)) {
                    if (pattern.test(link.href) && !social[name]) {
                        social[name] = link.href;
                    }
                }
            });

            return social;
        })()
        """
        try:
            return await engine.evaluate_script(url, script)
        except Exception:
            return {}

    def _find_page_url(
        self,
        links: list[dict[str, str]],
        patterns: list[str],
        base_url: str,
    ) -> str:
        """링크 목록에서 특정 패턴의 페이지 URL을 찾습니다."""
        for link in links:
            href = link.get("href", "").lower()
            for pattern in patterns:
                if pattern.lower() in href:
                    return urljoin(base_url, link.get("href", ""))
        return ""

    async def _crawl_about_page(
        self,
        engine: PlaywrightEngine,
        url: str,
        timeout: float | None,
    ) -> dict[str, Any]:
        """회사 소개 페이지를 크롤링합니다."""
        result: dict[str, Any] = {
            "description": "",
            "vision": "",
            "history": [],
            "executives": [],
        }

        try:
            await engine.get_page(url, timeout=timeout)

            # 회사 소개 추출
            script = """
            (() => {
                const result = { description: '', vision: '' };

                // 회사 소개
                const descSelectors = [
                    '.about-description', '.company-intro', '.about-content',
                    '.introduction', '#about', '.overview',
                ];
                for (const sel of descSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.length > 50) {
                        result.description = el.innerText.trim();
                        break;
                    }
                }

                // 비전/미션
                const visionSelectors = [
                    '.vision', '.mission', '.philosophy',
                    '[class*="vision"]', '[class*="mission"]',
                ];
                for (const sel of visionSelectors) {
                    const el = document.querySelector(sel);
                    if (el && el.innerText.length > 20) {
                        result.vision = el.innerText.trim();
                        break;
                    }
                }

                // 폴백: 첫 번째 큰 텍스트 블록
                if (!result.description) {
                    const paragraphs = document.querySelectorAll('p');
                    for (const p of paragraphs) {
                        if (p.innerText.length > 100) {
                            result.description = p.innerText.trim();
                            break;
                        }
                    }
                }

                return result;
            })()
            """
            about_data = await engine.evaluate_script(url, script)
            result["description"] = about_data.get("description", "")
            result["vision"] = about_data.get("vision", "")

        except Exception as e:
            logger.warning("회사 소개 페이지 크롤링 실패: %s", e)

        return result

    async def crawl_ir_page(
        self,
        url: str,
        *,
        timeout: float | None = None,
    ) -> list[IRDocument]:
        """IR 페이지에서 문서 목록을 추출합니다.

        Args:
            url: IR 페이지 URL.
            timeout: 타임아웃 (초).

        Returns:
            IR 문서 리스트.
        """
        engine = await self._ensure_engine()
        documents: list[IRDocument] = []

        try:
            await engine.get_page(url, timeout=timeout)

            script = """
            (() => {
                const docs = [];
                const links = document.querySelectorAll('a[href]');

                links.forEach(link => {
                    const href = link.href.toLowerCase();
                    const text = link.innerText.trim();

                    // PDF 또는 문서 파일 링크
                    if (href.endsWith('.pdf') || href.endsWith('.xlsx') ||
                        href.endsWith('.xls') || href.includes('/download')) {

                        let docType = 'other';
                        const textLower = text.toLowerCase();

                        if (textLower.includes('annual') || textLower.includes('사업보고서')) {
                            docType = 'annual_report';
                        } else if (textLower.includes('earning') || textLower.includes('실적')) {
                            docType = 'earnings';
                        } else if (textLower.includes('presentation') || textLower.includes('발표자료')) {
                            docType = 'presentation';
                        } else if (textLower.includes('financial') || textLower.includes('재무')) {
                            docType = 'financial';
                        }

                        docs.push({
                            title: text || 'Unknown',
                            url: link.href,
                            doc_type: docType,
                            file_type: href.split('.').pop() || ''
                        });
                    }
                });

                return docs;
            })()
            """
            raw_docs = await engine.evaluate_script(url, script)

            for doc in raw_docs:
                documents.append(
                    IRDocument(
                        title=doc.get("title", ""),
                        url=doc.get("url", ""),
                        doc_type=doc.get("doc_type", ""),
                        file_type=doc.get("file_type", ""),
                    )
                )

        except Exception as e:
            logger.warning("IR 페이지 크롤링 실패: %s", e)

        return documents

    async def extract_brand_colors(
        self,
        url: str,
        *,
        timeout: float | None = None,
    ) -> list[str]:
        """웹사이트에서 브랜드 컬러를 추출합니다.

        Args:
            url: 웹사이트 URL.
            timeout: 타임아웃 (초).

        Returns:
            HEX 컬러 코드 리스트.
        """
        engine = await self._ensure_engine()

        script = """
        (() => {
            const colors = new Set();

            // CSS 변수에서 추출
            const root = getComputedStyle(document.documentElement);
            const cssVars = [
                '--primary-color', '--brand-color', '--main-color',
                '--accent-color', '--theme-color',
            ];
            for (const v of cssVars) {
                const color = root.getPropertyValue(v);
                if (color) colors.add(color.trim());
            }

            // 헤더/로고 영역의 배경색
            const headerSelectors = ['header', '.header', '#header', 'nav', '.nav'];
            for (const sel of headerSelectors) {
                const el = document.querySelector(sel);
                if (el) {
                    const bg = getComputedStyle(el).backgroundColor;
                    if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
                        colors.add(bg);
                    }
                }
            }

            // 버튼 색상
            const buttons = document.querySelectorAll('button, .btn, [class*="button"]');
            buttons.forEach(btn => {
                const bg = getComputedStyle(btn).backgroundColor;
                if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
                    colors.add(bg);
                }
            });

            // RGB to HEX 변환
            function rgbToHex(rgb) {
                const match = rgb.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
                if (match) {
                    const r = parseInt(match[1]).toString(16).padStart(2, '0');
                    const g = parseInt(match[2]).toString(16).padStart(2, '0');
                    const b = parseInt(match[3]).toString(16).padStart(2, '0');
                    return `#${r}${g}${b}`;
                }
                return rgb.startsWith('#') ? rgb : null;
            }

            return Array.from(colors)
                .map(c => rgbToHex(c))
                .filter(c => c && c !== '#ffffff' && c !== '#000000')
                .slice(0, 5);
        })()
        """

        try:
            await engine.get_page(url, timeout=timeout)
            return await engine.evaluate_script(url, script)
        except Exception as e:
            logger.warning("브랜드 컬러 추출 실패: %s", e)
            return []

    async def crawl_products(
        self,
        url: str,
        *,
        timeout: float | None = None,
    ) -> list[dict[str, str]]:
        """제품/서비스 정보를 크롤링합니다.

        Args:
            url: 제품 페이지 URL.
            timeout: 타임아웃 (초).

        Returns:
            제품 정보 리스트 (name, description, url).
        """
        engine = await self._ensure_engine()
        products: list[dict[str, str]] = []

        try:
            await engine.get_page(url, timeout=timeout)

            script = """
            (() => {
                const products = [];

                // 제품 카드/항목 찾기
                const cardSelectors = [
                    '.product-item', '.product-card', '.service-item',
                    '[class*="product"]', '[class*="service"]',
                    'article', '.card',
                ];

                for (const selector of cardSelectors) {
                    const items = document.querySelectorAll(selector);
                    if (items.length > 0 && items.length < 50) {
                        items.forEach(item => {
                            const titleEl = item.querySelector('h2, h3, h4, .title, .name');
                            const descEl = item.querySelector('p, .description, .desc');
                            const linkEl = item.querySelector('a');

                            if (titleEl) {
                                products.push({
                                    name: titleEl.innerText.trim(),
                                    description: descEl ? descEl.innerText.trim() : '',
                                    url: linkEl ? linkEl.href : '',
                                });
                            }
                        });
                        break;
                    }
                }

                return products.slice(0, 20);
            })()
            """
            products = await engine.evaluate_script(url, script)

        except Exception as e:
            logger.warning("제품 정보 크롤링 실패: %s", e)

        return products
