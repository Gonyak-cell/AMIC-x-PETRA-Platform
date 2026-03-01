"""금감원(FSS) 기관전용 사모집합투자기구(PEF) 현황 수집 서비스.

금감원에서 공개한 '기관전용 사모집합투자기구 현황' 엑셀 파일을 파싱하여
PEFFund 테이블에 동기화하고, GP1/GP2/GP3를 Company 테이블에 매핑한다.

파일 헤더: 순번, 설립근거법률, PEF 명칭(약식), 등록일(설립일)*, GP1, GP2, GP3, 총약정액(합계)
단위: 억원
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyAlias
from app.models.gp_fund import PEFFund
from app.utils.entity_resolver import EntityResolver, normalize_company_name
from app.utils.numeric import safe_decimal

logger = logging.getLogger(__name__)


@dataclass
class FSSPEFItem:
    """금감원 PEF 현황 파싱 데이터."""

    pef_name: str
    legal_basis: str = ""
    registration_date: str = ""
    gp1_name: str = ""
    gp2_name: str = ""
    gp3_name: str = ""
    total_commitment: Decimal | None = None  # 억원


@dataclass
class FSSPEFSyncResult:
    """금감원 PEF 동기화 결과."""

    total_items: int = 0
    created: int = 0
    matched_existing: int = 0
    new_companies: int = 0
    errors: list[str] = field(default_factory=list)


class FSSPEFService:
    """금감원 기관전용 사모집합투자기구 현황 파서."""

    # 헤더 패턴 (유연 매칭)
    _HEADER_PATTERNS: dict[str, list[str]] = {
        "pef_name": ["PEF 명칭", "PEF명칭", "명칭", "펀드명"],
        "legal_basis": ["설립근거", "근거법률", "설립근거법률"],
        "registration_date": ["등록일", "설립일"],
        "gp1": ["GP1", "업무집행사원1", "GP 1"],
        "gp2": ["GP2", "업무집행사원2", "GP 2"],
        "gp3": ["GP3", "업무집행사원3", "GP 3"],
        "total_commitment": ["총약정액", "약정액", "약정총액", "합계"],
    }

    def parse_fss_pef_excel(self, file_path: Path) -> list[FSSPEFItem]:
        """금감원 PEF 현황 엑셀을 파싱한다.

        Args:
            file_path: 엑셀 파일 경로

        Returns:
            파싱된 PEF 목록
        """
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            ws = wb.active
            if ws is None:
                logger.warning("FSS PEF 엑셀: 활성 시트 없음")
                return []
            rows = list(ws.iter_rows(values_only=True))
        finally:
            wb.close()

        if not rows:
            return []

        header_row_idx = self._find_header_row(rows)
        if header_row_idx is None:
            logger.warning("FSS PEF 엑셀: 헤더 행을 찾을 수 없음")
            return []

        header = rows[header_row_idx]
        col_map = self._map_columns(header)
        if "pef_name" not in col_map and "gp1" not in col_map:
            logger.warning("FSS PEF 엑셀: 'PEF 명칭' 또는 'GP1' 컬럼을 찾을 수 없음")
            return []

        items: list[FSSPEFItem] = []
        for row in rows[header_row_idx + 1 :]:
            # PEF 명칭 추출
            pef_name = self._get_str(row, col_map.get("pef_name"))
            if not pef_name:
                continue
            if pef_name in ("합계", "소계", "전체", "총계", "Total"):
                continue

            gp1 = self._get_str(row, col_map.get("gp1"))
            if not gp1:
                continue

            item = FSSPEFItem(
                pef_name=pef_name,
                legal_basis=self._get_str(row, col_map.get("legal_basis")),
                registration_date=self._get_str(row, col_map.get("registration_date")),
                gp1_name=gp1,
                gp2_name=self._get_str(row, col_map.get("gp2")),
                gp3_name=self._get_str(row, col_map.get("gp3")),
                total_commitment=safe_decimal(self._get_cell(row, col_map.get("total_commitment"))),
            )
            items.append(item)

        logger.info("FSS PEF 엑셀 파싱 완료: %d건", len(items))
        return items

    async def sync_pef_data(
        self,
        db: AsyncSession,
        items: list[FSSPEFItem],
    ) -> FSSPEFSyncResult:
        """파싱된 PEF 목록을 pef_funds 테이블에 동기화한다.

        GP1/GP2/GP3 회사명을 EntityResolver + 정확 일치로 Company 매칭.
        매칭 실패 시 신규 Company 생성 (is_gp=True).
        """
        result = FSSPEFSyncResult(total_items=len(items))
        resolver = EntityResolver()
        now = datetime.now(UTC)

        # GP 이름 → Company 캐시 (동일 GP가 여러 PEF에 등장)
        gp_cache: dict[str, Company] = {}

        # 기존 pef_funds 전체 삭제 (replace 전략)
        await db.execute(delete(PEFFund))

        for item in items:
            try:
                gp1 = await self._resolve_or_create_gp(db, resolver, item.gp1_name, now, gp_cache, result)
                if not gp1:
                    result.errors.append(item.pef_name)
                    continue

                gp2 = None
                if item.gp2_name:
                    gp2 = await self._resolve_or_create_gp(db, resolver, item.gp2_name, now, gp_cache, result)

                gp3 = None
                if item.gp3_name:
                    gp3 = await self._resolve_or_create_gp(db, resolver, item.gp3_name, now, gp_cache, result)

                pef = PEFFund(
                    pef_name=item.pef_name,
                    legal_basis=item.legal_basis or None,
                    registration_date=item.registration_date or None,
                    total_commitment=item.total_commitment,
                    gp1_company_id=gp1.id,
                    gp2_company_id=gp2.id if gp2 else None,
                    gp3_company_id=gp3.id if gp3 else None,
                    synced_at=now,
                )
                db.add(pef)
                result.created += 1
            except Exception:
                logger.exception("FSS PEF 동기화 실패: %s", item.pef_name)
                result.errors.append(item.pef_name)

        await db.commit()
        logger.info(
            "FSS PEF 동기화 완료: 총 %d건, PEF 생성 %d, GP 신규 %d, 에러 %d",
            result.total_items,
            result.created,
            result.new_companies,
            len(result.errors),
        )
        return result

    async def _resolve_or_create_gp(
        self,
        db: AsyncSession,
        resolver: EntityResolver,
        gp_name: str,
        now: datetime,
        gp_cache: dict[str, Company],
        result: FSSPEFSyncResult,
    ) -> Company | None:
        """GP 이름으로 Company를 조회하거나 신규 생성한다."""
        # 캐시 확인
        if gp_name in gp_cache:
            return gp_cache[gp_name]

        # 1. EntityResolver 매칭
        match_result = await resolver.resolve(db, gp_name)
        matched = match_result.get("match")
        if matched:
            company = await self._find_company(db, matched)
            if company:
                self._update_gp_tags(company, now)
                result.matched_existing += 1
                gp_cache[gp_name] = company
                return company

        # 2. 정확 일치
        stmt = select(Company).where(func.lower(Company.corp_name) == func.lower(gp_name))
        db_result = await db.execute(stmt)
        company = db_result.scalar_one_or_none()
        if company:
            self._update_gp_tags(company, now)
            result.matched_existing += 1
            gp_cache[gp_name] = company
            return company

        # 3. 신규 생성
        company = Company(
            corp_code=None,
            corp_name=gp_name,
            is_gp=True,
            gp_strategy_tags={
                "strategies": ["institutional_pef"],
                "sources": ["fss_pef"],
            },
            gp_profile_synced_at=now,
        )
        db.add(company)
        await db.flush()
        result.new_companies += 1

        # 정규화 별칭 자동 등록
        normalized = normalize_company_name(gp_name)
        if normalized and normalized != gp_name:
            alias = CompanyAlias(
                alias_name=normalized,
                company_id=company.id,
                is_manual=False,
            )
            db.add(alias)

        gp_cache[gp_name] = company
        return company

    @staticmethod
    async def _find_company(db: AsyncSession, matched: dict) -> Company | None:
        """매칭 결과에서 Company를 조회한다."""
        corp_code = matched.get("corp_code")
        if corp_code:
            stmt = select(Company).where(Company.corp_code == corp_code)
        else:
            corp_name = matched.get("corp_name", "")
            stmt = select(Company).where(func.lower(Company.corp_name) == func.lower(corp_name))
        db_result = await db.execute(stmt)
        return db_result.scalar_one_or_none()

    @staticmethod
    def _update_gp_tags(company: Company, now: datetime) -> None:
        """Company의 GP 태그에 fss_pef 소스를 추가한다."""
        company.is_gp = True

        tags = dict(company.gp_strategy_tags or {})
        strategies = list(tags.get("strategies", []))
        if "institutional_pef" not in strategies:
            strategies.append("institutional_pef")
        sources = list(tags.get("sources", []))
        if "fss_pef" not in sources:
            sources.append("fss_pef")
        tags["strategies"] = strategies
        tags["sources"] = sources
        company.gp_strategy_tags = tags
        company.gp_profile_synced_at = now

    def _find_header_row(self, rows: list[tuple]) -> int | None:  # type: ignore[type-arg]
        """헤더 행 인덱스를 찾는다 (첫 10행 내에서)."""
        for idx, row in enumerate(rows[:10]):
            for cell in row:
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                # PEF 명칭 또는 GP1 패턴으로 헤더 행 판별
                for key in ("pef_name", "gp1"):
                    for pattern in self._HEADER_PATTERNS[key]:
                        if pattern in cell_str:
                            return idx
        return None

    def _map_columns(self, header: tuple) -> dict[str, int]:  # type: ignore[type-arg]
        """헤더 행에서 필드별 컬럼 인덱스를 매핑한다."""
        col_map: dict[str, int] = {}
        used_indices: set[int] = set()
        for idx, cell in enumerate(header):
            if cell is None:
                continue
            cell_str = str(cell).strip()
            for field_name, patterns in self._HEADER_PATTERNS.items():
                if field_name in col_map:
                    continue
                if idx in used_indices:
                    continue
                for pattern in patterns:
                    if pattern in cell_str:
                        col_map[field_name] = idx
                        used_indices.add(idx)
                        break
        return col_map

    @staticmethod
    def _get_cell(row: tuple, idx: int | None) -> object:  # type: ignore[type-arg]
        """안전한 셀 값 추출."""
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    @staticmethod
    def _get_str(row: tuple, idx: int | None) -> str:  # type: ignore[type-arg]
        """안전한 문자열 셀 값 추출."""
        if idx is None or idx >= len(row):
            return ""
        val = row[idx]
        return str(val).strip() if val else ""
