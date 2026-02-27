"""GP 로고 크롤링 서비스

운용사(GP) 홈페이지에서 로고 이미지 URL을 추출하여 DB에 저장한다.
3단계 폴백: og:image → link[rel=icon] → Google Favicon API
"""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.utils.http_client import AsyncHTTPClient
from app.utils.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger(__name__)

# 유효한 이미지 Content-Type
_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/svg+xml",
        "image/webp",
        "image/x-icon",
        "image/vnd.microsoft.icon",
    }
)


def _extract_domain(url: str) -> str | None:
    """URL에서 도메인을 추출한다."""
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return parsed.netloc or None
    except Exception:
        return None


def _normalise_homepage(url: str) -> str:
    """홈페이지 URL을 https:// 포함 형태로 정규화한다."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


class LogoService:
    """GP 로고 크롤링 서비스

    Company.hm_url(홈페이지) 기반으로 로고 이미지 URL을 추출한다.
    3단계 폴백: og:image → link[rel~=icon] → Google Favicon API
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.client = AsyncHTTPClient(
            timeout=15.0,
            max_retries=2,
            headers={
                "User-Agent": "KIIS/0.1.0 (GP Logo Collector)",
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "ko-KR,ko;q=0.9",
            },
        )
        self.rate_limiter = TokenBucketRateLimiter(
            per_minute=settings.LOGO_CRAWL_RATE_PER_MINUTE,
            per_day=500,
        )

    async def fetch_logo_url(self, homepage_url: str) -> tuple[str | None, str | None]:
        """홈페이지 URL에서 로고 URL을 추출한다.

        Returns:
            (logo_url, source) 튜플. 실패 시 (None, None).
            source: "og_image" | "meta_icon" | "favicon"
        """
        base_url = _normalise_homepage(homepage_url)
        if not base_url:
            return None, None

        domain = _extract_domain(base_url)
        if not domain:
            return None, None

        # HTML 가져오기
        html = await self._fetch_html(base_url)
        if html:
            soup = BeautifulSoup(html, "html.parser")

            # 1차: og:image 메타 태그
            og_url = self._extract_og_image(soup, base_url)
            if og_url:
                return og_url, "og_image"

            # 2차: link[rel~=icon] (apple-touch-icon 우선)
            icon_url = self._extract_link_icon(soup, base_url)
            if icon_url:
                return icon_url, "meta_icon"

        # 3차: Google Favicon API (폴백)
        favicon_url = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
        return favicon_url, "favicon"

    async def crawl_single(self, company_id: int) -> bool:
        """단일 기업의 로고를 크롤링하여 DB에 저장한다.

        Returns:
            True: 로고 수집 성공, False: 실패
        """
        stmt = select(Company).where(Company.id == company_id)
        result = await self.db.execute(stmt)
        company = result.scalar_one_or_none()
        if not company:
            logger.warning("Company not found: id=%d", company_id)
            return False

        if not company.hm_url:
            logger.info("Company has no homepage URL: %s (id=%d)", company.corp_name, company_id)
            return False

        logo_url, source = await self.fetch_logo_url(company.hm_url)
        if logo_url:
            company.logo_url = logo_url
            company.logo_source = source
            company.logo_fetched_at = datetime.now(UTC)
            await self.db.commit()
            logger.info(
                "Logo fetched: %s → %s (source=%s)",
                company.corp_name,
                logo_url[:80],
                source,
            )
            return True

        logger.info("No logo found for: %s", company.corp_name)
        return False

    async def crawl_batch(
        self,
        *,
        force: bool = False,
        stale_days: int | None = None,
        limit: int = 50,
    ) -> dict[str, int]:
        """일괄 크롤링: hm_url이 있고 logo_url이 없는(또는 stale) 기업 대상.

        Args:
            force: True면 기존 로고가 있어도 재수집
            stale_days: 이 일수 이상 경과한 로고를 재수집 (기본: settings.LOGO_STALE_DAYS)
            limit: 최대 수집 건수

        Returns:
            {"success": N, "failed": M, "skipped": K}
        """
        if stale_days is None:
            stale_days = settings.LOGO_STALE_DAYS

        # 대상 기업 조회
        stmt = select(Company).where(Company.hm_url.isnot(None), Company.hm_url != "")

        if not force:
            stale_cutoff = datetime.now(UTC) - timedelta(days=stale_days)
            stmt = stmt.where(
                (Company.logo_url.is_(None))
                | (Company.logo_fetched_at.is_(None))
                | (Company.logo_fetched_at < stale_cutoff)
            )

        stmt = stmt.order_by(Company.id).limit(limit)
        result = await self.db.execute(stmt)
        companies = list(result.scalars().all())

        stats: dict[str, int] = {"success": 0, "failed": 0, "skipped": 0}

        for company in companies:
            try:
                logo_url, source = await self.fetch_logo_url(company.hm_url)  # type: ignore[arg-type]
                if logo_url:
                    company.logo_url = logo_url
                    company.logo_source = source
                    company.logo_fetched_at = datetime.now(UTC)
                    stats["success"] += 1
                    logger.info("Logo: %s → %s", company.corp_name, source)
                else:
                    stats["failed"] += 1
                    logger.info("No logo: %s", company.corp_name)
            except Exception:
                stats["failed"] += 1
                logger.exception("Logo crawl error: %s", company.corp_name)

            # 크롤링 예의: 요청 간 딜레이
            await asyncio.sleep(settings.LOGO_CRAWL_REQUEST_DELAY)

        await self.db.commit()
        logger.info("Batch crawl done: %s", stats)
        return stats

    async def close(self) -> None:
        """HTTP 클라이언트를 정리한다."""
        await self.client.close()

    # ── Private helpers ──

    async def _fetch_html(self, url: str) -> str | None:
        """Rate limiting이 적용된 HTML 페이지 요청."""
        try:
            await self.rate_limiter.acquire()
            response = await self.client.get(url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "xhtml" not in content_type:
                return None
            return response.text
        except Exception:
            logger.debug("HTML fetch failed: %s", url, exc_info=True)
            return None

    @staticmethod
    def _extract_og_image(soup: BeautifulSoup, base_url: str) -> str | None:
        """og:image 메타 태그에서 이미지 URL을 추출한다."""
        for attr in ("og:image", "twitter:image"):
            tag = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
            if tag and tag.get("content"):
                url = tag["content"].strip()
                if url:
                    return urljoin(base_url, url)
        return None

    @staticmethod
    def _extract_link_icon(soup: BeautifulSoup, base_url: str) -> str | None:
        """link[rel~=icon] 태그에서 아이콘 URL을 추출한다.

        apple-touch-icon을 우선하고, 가장 큰 사이즈를 선택한다.
        """
        candidates: list[tuple[int, str]] = []

        for link in soup.find_all("link", rel=True):
            rels = link["rel"] if isinstance(link["rel"], list) else [link["rel"]]
            href = link.get("href", "").strip()
            if not href:
                continue

            is_icon = any(r in ("icon", "shortcut") for r in rels)
            is_apple = "apple-touch-icon" in rels

            if not (is_icon or is_apple):
                continue

            # 크기 추출 (예: "192x192" → 192)
            sizes = link.get("sizes", "")
            size = 0
            if sizes and "x" in sizes.lower():
                with contextlib.suppress(ValueError):
                    size = int(sizes.lower().split("x")[0])

            # apple-touch-icon에 보너스 (보통 고해상도)
            priority = size + (1000 if is_apple else 0)
            candidates.append((priority, urljoin(base_url, href)))

        if not candidates:
            return None

        # 가장 큰(우선순위 높은) 아이콘 반환
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
