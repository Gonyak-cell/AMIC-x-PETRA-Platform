"""Cloudflare Browser Rendering /crawl API 클라이언트.

추가 IB 매체(한경IB, 더벨, 매경IB, 조선비즈 M&A)에서 뉴스 기사를 수집하고
LLM으로 카테고리를 자동 분류하여 deal-mgmt DB에 저장한다.

robots.txt 자동 준수 (Cloudflare 공식 봇 정책).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.models.cf_news_article import CFNewsArticle

logger = logging.getLogger(__name__)

# ── Cloudflare /crawl API 상수 ──────────────────────

_CF_BASE_URL = "https://api.cloudflare.com/client/v4/accounts"
_CRAWL_POLL_INTERVAL = 3.0  # 초
_CRAWL_POLL_MAX = 20  # 최대 20회 × 3초 = 60초 타임아웃
_CRAWL_LOCK_KEY = "cf_crawl_lock"
_CRAWL_LOCK_TTL = 600  # 10분

# ── IB 소스 정의 ──────────────────────────────────────

IB_CF_SOURCES: dict[str, dict[str, Any]] = {
    "hankyung_ib": {
        "display": "한경IB",
        "start_url": "https://www.hankyung.com/economy/ib",
        "max_pages": 5,
    },
    "thebell": {
        "display": "더벨",
        "start_url": "https://www.thebell.co.kr/free/content/List.asp?svccode=00&page=1",
        "max_pages": 5,
    },
    "mk_ib": {
        "display": "매경IB",
        "start_url": "https://www.mk.co.kr/news/stock/ib",
        "max_pages": 5,
    },
    "chosunbiz_ma": {
        "display": "조선비즈 M&A",
        "start_url": "https://biz.chosun.com/topics/ma",
        "max_pages": 5,
    },
}

# ── LLM 분류 프롬프트 ──────────────────────────────────

_CLASSIFY_SYSTEM = """당신은 IB(투자은행) 뉴스 분류 전문가입니다.
주어진 뉴스 기사 제목과 요약을 읽고, 아래 5개 카테고리 중 하나로 분류하세요.

카테고리:
- deal_progress: M&A 딜 진행 상황, 인수합병 소식, 매각/인수 성사
- sourcing_history: 딜 소싱, 투자 이력, 신규 펀드 결성
- investment_style: 투자 전략, 운용 철학, 섹터 선호도
- reputation: GP/운용사 평판, 업계 평가, 트랙레코드
- personnel_evaluation: 운용인력 변동, Key Man 이동, 조직 변화

JSON 형식으로만 응답하세요: {"category": "카테고리명"}
분류 불가 시: {"category": null}"""


def _generate_url_hash(url: str) -> str:
    """URL SHA256 해시 생성."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _extract_title_from_markdown(md: str) -> str:
    """Markdown에서 첫 번째 제목(# 또는 첫 줄)을 추출한다."""
    for line in md.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return re.sub(r"^#+\s*", "", line).strip()
        return line[:200]
    return "제목 없음"


def _extract_lead_from_markdown(md: str, max_len: int = 500) -> str:
    """Markdown에서 lead_text(첫 본문 단락)를 추출한다."""
    lines = md.split("\n")
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if body_lines:
                break
            continue
        if stripped.startswith("#"):
            continue
        body_lines.append(stripped)
    return " ".join(body_lines)[:max_len] if body_lines else ""


class CloudflareCrawlService:
    """Cloudflare Browser Rendering /crawl API 기반 IB 매체 수집 서비스."""

    def __init__(self) -> None:
        self._account_id = settings.CLOUDFLARE_ACCOUNT_ID
        self._api_token = settings.CLOUDFLARE_API_TOKEN
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """Cloudflare 인증 정보가 설정되어 있는지."""
        return bool(self._account_id and self._api_token)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=10.0),
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """HTTP 클라이언트를 종료한다."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ── 크롤링 ──────────────────────────────────────────

    async def crawl_source(self, source: str) -> list[dict[str, Any]]:
        """단일 소스에서 Cloudflare /crawl API로 기사를 수집한다.

        Returns:
            [{"title": ..., "lead_text": ..., "markdown": ..., "url": ..., "published_at": None}, ...]
        """
        source_cfg = IB_CF_SOURCES.get(source)
        if not source_cfg:
            logger.warning("알 수 없는 CF 소스: %s", source)
            return []

        if not self.is_configured:
            logger.warning("Cloudflare 인증 정보 미설정, 크롤링 건너뜀: %s", source)
            return []

        client = await self._get_client()
        crawl_url = f"{_CF_BASE_URL}/{self._account_id}/browser-rendering/crawl"

        # 1. 크롤링 작업 제출
        try:
            resp = await client.post(
                crawl_url,
                json={
                    "url": source_cfg["start_url"],
                    "maxPages": source_cfg.get("max_pages", 5),
                    "scrapeOptions": {
                        "formats": ["markdown"],
                    },
                },
            )
            resp.raise_for_status()
            job_data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("CF /crawl 제출 실패 (%s): HTTP %s", source, exc.response.status_code)
            return []
        except Exception as exc:
            logger.warning("CF /crawl 제출 에러 (%s): %s", source, exc)
            return []

        # 응답에서 Job ID 또는 즉시 결과 추출
        result_data = job_data.get("result", job_data)

        # 비동기 Job인 경우 폴링
        job_id = result_data.get("jobId") or result_data.get("id")
        if job_id and result_data.get("status") != "completed":
            result_data = await self._poll_job(client, job_id)
            if not result_data:
                return []

        # 2. 결과 파싱
        return self._parse_crawl_results(result_data, source)

    async def _poll_job(self, client: httpx.AsyncClient, job_id: str) -> dict[str, Any] | None:
        """비동기 Job 완료까지 폴링한다 (최대 60초)."""
        poll_url = f"{_CF_BASE_URL}/{self._account_id}/browser-rendering/crawl/{job_id}"

        for attempt in range(_CRAWL_POLL_MAX):
            await asyncio.sleep(_CRAWL_POLL_INTERVAL)
            try:
                resp = await client.get(poll_url)
                resp.raise_for_status()
                data = resp.json().get("result", resp.json())
                status = data.get("status", "")
                if status == "completed":
                    return data
                if status in ("failed", "error"):
                    logger.warning("CF /crawl Job 실패: %s — %s", job_id, data.get("error", ""))
                    return None
            except Exception as exc:
                logger.debug("CF /crawl 폴링 에러 (attempt %d): %s", attempt + 1, exc)

        logger.warning("CF /crawl Job 폴링 타임아웃: %s", job_id)
        return None

    @staticmethod
    def _parse_crawl_results(data: dict[str, Any], source: str) -> list[dict[str, Any]]:
        """Cloudflare 크롤링 결과에서 기사 목록을 추출한다."""
        articles: list[dict[str, Any]] = []

        # pages 배열 또는 data 배열에서 추출
        pages = data.get("pages") or data.get("data") or []
        if isinstance(pages, dict):
            pages = [pages]

        for page in pages:
            md = page.get("markdown") or page.get("content", "")
            url = page.get("url") or page.get("sourceURL", "")
            if not md or not url:
                continue

            title = _extract_title_from_markdown(md)
            lead_text = _extract_lead_from_markdown(md)

            articles.append(
                {
                    "title": title,
                    "lead_text": lead_text,
                    "markdown": md,
                    "url": url,
                    "source": source,
                    "published_at": None,  # Markdown에서 날짜 추출은 LLM에 위임
                }
            )

        logger.info("CF /crawl 파싱 완료: %s — %d건", source, len(articles))
        return articles

    # ── LLM 분류 ─────────────────────────────────────────

    async def classify_articles(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """RalphLLMClient를 사용하여 기사 카테고리를 자동 분류한다."""
        from app.ralph.llm_client import RalphLLMClient

        llm = RalphLLMClient.from_settings(settings)
        if not llm.is_available:
            logger.warning("LLM 프로바이더 미설정, 분류 건너뜀 (%d건)", len(articles))
            return articles

        for article in articles:
            try:
                user_prompt = f"제목: {article['title']}\n요약: {article.get('lead_text', '')}"
                raw = await llm.call(_CLASSIFY_SYSTEM, user_prompt, max_tokens=100)
                parsed = json.loads(raw.strip().strip("`").removeprefix("json"))
                article["category"] = parsed.get("category")
            except Exception:
                logger.debug("LLM 분류 실패: %s", article.get("title", "")[:60], exc_info=True)
                article["category"] = None
            await asyncio.sleep(0.5)  # LLM rate limit 대비

        return articles

    # ── DB 저장 ──────────────────────────────────────────

    async def save_articles(self, db: AsyncSession, articles: list[dict[str, Any]]) -> dict[str, int]:
        """분류된 기사를 deal-mgmt DB에 저장한다 (중복 제거).

        Returns:
            {"collected": N, "new": M, "duplicates": D}
        """
        if not articles:
            return {"collected": 0, "new": 0, "duplicates": 0}

        # URL 해시 기반 배치 내 중복 제거
        seen: set[str] = set()
        unique: list[dict[str, Any]] = []
        for a in articles:
            url_hash = _generate_url_hash(a["url"])
            if url_hash not in seen:
                seen.add(url_hash)
                a["url_hash"] = url_hash
                unique.append(a)

        # DB 중복 체크
        hashes = [a["url_hash"] for a in unique]
        result = await db.execute(select(CFNewsArticle.url_hash).where(CFNewsArticle.url_hash.in_(hashes)))
        existing = set(result.scalars().all())

        new_count = 0
        for a in unique:
            if a["url_hash"] in existing:
                continue
            row = CFNewsArticle(
                title=a["title"],
                lead_text=a.get("lead_text"),
                markdown_content=a.get("markdown"),
                canonical_url=a["url"],
                url_hash=a["url_hash"],
                source=a["source"],
                category=a.get("category"),
                published_at=a.get("published_at"),
            )
            db.add(row)
            try:
                await db.flush()
                new_count += 1
            except IntegrityError:
                await db.rollback()

        if new_count > 0:
            await db.commit()

        return {
            "collected": len(articles),
            "new": new_count,
            "duplicates": len(existing),
        }

    # ── 전체 수집 파이프라인 ──────────────────────────────

    async def collect_all(
        self,
        db: AsyncSession,
        source_filter: str | None = None,
    ) -> dict[str, dict[str, int]]:
        """전체 또는 특정 CF 소스에서 기사를 수집 → 분류 → 저장한다.

        동시 실행 방지를 위해 Redis Lock을 사용한다.
        """
        # Redis Lock 획득
        redis = get_redis()
        if redis:
            try:
                acquired = await redis.set(_CRAWL_LOCK_KEY, "1", nx=True, ex=_CRAWL_LOCK_TTL)
                if not acquired:
                    logger.info("CF 수집이 이미 진행 중 (Lock 존재)")
                    return {}
            except Exception:
                logger.debug("CF 수집 Lock 획득 실패, Lock 없이 진행", exc_info=True)

        try:
            sources = IB_CF_SOURCES
            if source_filter:
                sources = {k: v for k, v in sources.items() if k == source_filter}

            results: dict[str, dict[str, int]] = {}
            for source_name in sources:
                try:
                    # 1. 크롤링
                    articles = await self.crawl_source(source_name)
                    if not articles:
                        results[source_name] = {"collected": 0, "new": 0, "duplicates": 0}
                        continue

                    # 2. LLM 분류
                    articles = await self.classify_articles(articles)

                    # 3. DB 저장
                    stats = await self.save_articles(db, articles)
                    results[source_name] = stats
                except Exception:
                    logger.exception("CF 수집 실패: %s", source_name)
                    results[source_name] = {"collected": 0, "new": 0, "duplicates": 0}

                await asyncio.sleep(settings.CF_CRAWL_REQUEST_DELAY)

            return results
        finally:
            # Lock 해제
            if redis:
                try:
                    await redis.delete(_CRAWL_LOCK_KEY)
                except Exception:
                    logger.debug("CF 수집 Lock 해제 실패", exc_info=True)
