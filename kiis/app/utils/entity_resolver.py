import logging
import re
import unicodedata

from rapidfuzz import fuzz
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import Company, CompanyAlias

logger = logging.getLogger(__name__)

# 기업명 정규화에서 제거할 패턴
CORP_SUFFIXES = re.compile(
    r"(주식회사|㈜|\(주\)|유한회사|유한책임회사|합자회사|합명회사|사단법인|재단법인|특수목적법인|투자조합)"
)
WHITESPACE_RE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """기업명을 정규화한다.

    - 주식회사, ㈜, (주) 등 법인 접미어 제거
    - 앞뒤 공백 제거, 연속 공백 축소
    - 유니코드 NFC 정규화
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFC", name.strip())
    text = CORP_SUFFIXES.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def _decompose_jamo(char: str) -> str:
    """한글 음절을 초성+중성+종성 자모로 분해한다."""
    code = ord(char) - 0xAC00
    if code < 0 or code > 11171:
        return char
    cho = code // 588
    jung = (code % 588) // 28
    jong = code % 28

    cho_list = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
    jung_list = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
    jong_list = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

    result = cho_list[cho] + jung_list[jung]
    if jong != 0:
        result += jong_list[jong]
    return result


def decompose_to_jamo(text: str) -> str:
    """문자열의 한글 음절을 모두 자모로 분해한다."""
    return "".join(_decompose_jamo(c) for c in text)


def calculate_similarity(name1: str, name2: str) -> float:
    """두 기업명 간 유사도를 계산한다 (0.0 ~ 1.0).

    1) 정규화된 이름으로 rapidfuzz ratio
    2) 자모 분해 후 rapidfuzz ratio
    3) 두 값의 가중 평균 (정규화 60%, 자모 40%)
    """
    norm1 = normalize_company_name(name1)
    norm2 = normalize_company_name(name2)

    if not norm1 or not norm2:
        return 0.0

    # 완전 일치
    if norm1 == norm2:
        return 1.0

    # rapidfuzz ratio (0~100 → 0.0~1.0)
    norm_ratio = fuzz.ratio(norm1, norm2) / 100.0

    # 자모 분해 유사도
    jamo1 = decompose_to_jamo(norm1)
    jamo2 = decompose_to_jamo(norm2)
    jamo_ratio = fuzz.ratio(jamo1, jamo2) / 100.0

    return norm_ratio * 0.6 + jamo_ratio * 0.4


class EntityResolver:
    """Entity Resolution 서비스

    기업명 별칭을 정규 기업(Company)에 매핑한다.
    1) 별칭 사전(CompanyAlias) 정확 매칭
    2) Company.corp_name 정규화 매칭
    3) 유사도 기반 후보 추출 (threshold 이상)
    """

    DEFAULT_THRESHOLD = 0.75

    async def resolve(
        self,
        db: AsyncSession,
        name: str,
        threshold: float | None = None,
        max_candidates: int = 5,
    ) -> dict:
        """이름을 정규 기업에 매핑한다.

        Returns:
            {
                "query": 원본 이름,
                "normalized": 정규화된 이름,
                "match": {"corp_code": ..., "corp_name": ..., "similarity": 1.0} or None,
                "candidates": [{"corp_code": ..., "corp_name": ..., "similarity": ...}, ...]
            }
        """
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD

        normalized = normalize_company_name(name)
        result: dict = {
            "query": name,
            "normalized": normalized,
            "match": None,
            "candidates": [],
        }

        if not normalized:
            return result

        # 1) 별칭 사전 정확 매칭
        alias_match = await self._match_by_alias(db, name, normalized)
        if alias_match:
            result["match"] = alias_match
            return result

        # 2) Company.corp_name 정규화 매칭
        exact_match = await self._match_by_corp_name(db, normalized)
        if exact_match:
            result["match"] = exact_match
            return result

        # 3) 유사도 기반 후보 추출
        candidates = await self._find_candidates(db, normalized, threshold, max_candidates)
        result["candidates"] = candidates

        # 최고 유사도가 threshold 이상이면 match로 설정
        if candidates and candidates[0]["similarity"] >= threshold:
            result["match"] = candidates[0]

        return result

    async def _match_by_alias(self, db: AsyncSession, original: str, normalized: str) -> dict | None:
        """별칭 사전에서 정확 매칭을 시도한다."""
        # 원본 이름과 정규화 이름 모두 시도
        for search_name in [original.strip(), normalized]:
            stmt = (
                select(CompanyAlias, Company)
                .join(Company, CompanyAlias.company_id == Company.id)
                .where(func.lower(CompanyAlias.alias_name) == func.lower(search_name))
            )
            result = await db.execute(stmt)
            row = result.first()
            if row:
                alias, company = row
                return {
                    "corp_code": company.corp_code,
                    "corp_name": company.corp_name,
                    "similarity": 1.0,
                    "matched_by": "alias",
                }
        return None

    async def _match_by_corp_name(self, db: AsyncSession, normalized: str) -> dict | None:
        """Company.corp_name 정규화 매칭을 시도한다."""
        # 정규화 이름으로 정식명칭에서 검색
        stmt = select(Company).options(selectinload(Company.aliases))
        result = await db.execute(stmt)
        companies = result.scalars().all()

        for company in companies:
            comp_normalized = normalize_company_name(company.corp_name)
            if comp_normalized == normalized:
                return {
                    "corp_code": company.corp_code,
                    "corp_name": company.corp_name,
                    "similarity": 1.0,
                    "matched_by": "exact",
                }
        return None

    async def _find_candidates(
        self,
        db: AsyncSession,
        normalized: str,
        threshold: float,
        max_candidates: int,
    ) -> list[dict]:
        """유사도 기반으로 후보 기업을 추출한다."""
        stmt = select(Company).options(selectinload(Company.aliases))
        result = await db.execute(stmt)
        companies = result.scalars().all()

        candidates = []
        for company in companies:
            similarity = calculate_similarity(normalized, company.corp_name)
            if similarity >= threshold * 0.8:  # threshold보다 약간 낮은 것도 후보에 포함
                candidates.append(
                    {
                        "corp_code": company.corp_code,
                        "corp_name": company.corp_name,
                        "similarity": round(similarity, 4),
                    }
                )

        # 유사도 내림차순 정렬, 상위 N개
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates[:max_candidates]

    async def add_alias(
        self, db: AsyncSession, alias_name: str, company_id: int, is_manual: bool = True
    ) -> CompanyAlias:
        """별칭을 등록한다."""
        alias = CompanyAlias(
            alias_name=alias_name.strip(),
            company_id=company_id,
            is_manual=is_manual,
        )
        db.add(alias)
        await db.flush()
        await db.commit()
        return alias

    async def get_aliases(self, db: AsyncSession, company_id: int | None = None) -> list[CompanyAlias]:
        """별칭 목록을 조회한다."""
        stmt = select(CompanyAlias).join(Company)
        if company_id is not None:
            stmt = stmt.where(CompanyAlias.company_id == company_id)
        stmt = stmt.order_by(CompanyAlias.alias_name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_alias(self, db: AsyncSession, alias_id: int) -> bool:
        """별칭을 삭제한다."""
        stmt = select(CompanyAlias).where(CompanyAlias.id == alias_id)
        result = await db.execute(stmt)
        alias = result.scalar_one_or_none()
        if alias:
            await db.delete(alias)
            await db.flush()
            await db.commit()
            return True
        return False
