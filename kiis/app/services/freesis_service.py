"""FreeSIS (금융투자협회 종합통계 포털) 기관전용 사모펀드 GP 수집 서비스.

FreeSIS에서 수동 다운로드한 기관전용 사모펀드 운용사별 통계 엑셀 파일을
파싱하여 Company 테이블에 동기화한다.

메뉴 경로: 펀드 > 운용사통계 > 기관전용 사모펀드
URL: https://freesis.kofia.or.kr/
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyAlias
from app.utils.entity_resolver import EntityResolver, normalize_company_name
from app.utils.numeric import safe_decimal, safe_int

logger = logging.getLogger(__name__)


@dataclass
class FreeSISGPItem:
    """FreeSIS 기관전용 사모펀드 운용사 데이터."""

    company_name: str
    setting_balance: Decimal | None = None  # 설정잔액 (백만원)
    fund_count: int | None = None  # 펀드수
    fund_inflow: Decimal | None = None  # 자금유입 (백만원)
    fund_outflow: Decimal | None = None  # 자금유출 (백만원)
    reference_date: str | None = None  # 기준일 (YYYY-MM-DD 등)


@dataclass
class FreeSISSyncResult:
    """FreeSIS GP 동기화 결과."""

    total_items: int = 0
    created: int = 0
    updated: int = 0
    matched_existing: int = 0
    errors: list[str] = field(default_factory=list)


class FreeSISService:
    """FreeSIS 기관전용 사모펀드 GP 수집 서비스."""

    # FreeSIS 엑셀 헤더 패턴 (운용사별 설정잔액 등)
    # 실제 헤더는 다운로드 후 확인 필요 — 유연하게 매칭
    _HEADER_PATTERNS: dict[str, list[str]] = {
        "company_name": ["운용사", "운용회사", "회사명", "자산운용사"],
        "setting_balance": ["설정잔액", "설정액", "잔액", "순자산"],
        "fund_count": ["펀드수", "펀드 수", "설정수"],
        "fund_inflow": ["유입", "설정", "자금유입"],
        "fund_outflow": ["유출", "환매", "자금유출"],
    }

    def parse_freesis_excel(
        self,
        file_path: Path,
        reference_date: str | None = None,
    ) -> list[FreeSISGPItem]:
        """FreeSIS에서 다운로드한 기관전용 사모펀드 운용사별 통계 엑셀을 파싱한다.

        Args:
            file_path: 엑셀 파일 경로
            reference_date: 데이터 기준일 (미지정 시 파일명/시트명에서 추출 시도)

        Returns:
            파싱된 GP 목록
        """
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            ws = wb.active
            if ws is None:
                logger.warning("FreeSIS 엑셀: 활성 시트 없음")
                return []
            rows = list(ws.iter_rows(values_only=True))
        finally:
            wb.close()

        if not rows:
            return []

        # 헤더 행 탐색 (첫 5행 내에서 "운용사"/"회사명" 패턴 검색)
        header_row_idx = self._find_header_row(rows)
        if header_row_idx is None:
            logger.warning("FreeSIS 엑셀: 헤더 행을 찾을 수 없음")
            return []

        # 컬럼 매핑
        header = rows[header_row_idx]
        col_map = self._map_columns(header)
        if "company_name" not in col_map:
            logger.warning("FreeSIS 엑셀: '운용사' 컬럼을 찾을 수 없음")
            return []

        # 데이터 행 파싱
        items: list[FreeSISGPItem] = []
        for row in rows[header_row_idx + 1 :]:
            name_idx = col_map["company_name"]
            if name_idx >= len(row):
                continue
            name = row[name_idx]
            if not name or not str(name).strip():
                continue
            name_str = str(name).strip()

            # "합계", "소계", "전체" 등 집계 행 제외
            if name_str in ("합계", "소계", "전체", "총계", "Total", "합 계"):
                continue

            item = FreeSISGPItem(
                company_name=name_str,
                setting_balance=safe_decimal(self._get_cell(row, col_map.get("setting_balance"))),
                fund_count=safe_int(self._get_cell(row, col_map.get("fund_count"))),
                fund_inflow=safe_decimal(self._get_cell(row, col_map.get("fund_inflow"))),
                fund_outflow=safe_decimal(self._get_cell(row, col_map.get("fund_outflow"))),
                reference_date=reference_date,
            )
            items.append(item)

        logger.info("FreeSIS 엑셀 파싱 완료: %d개 GP", len(items))
        return items

    async def sync_pef_gp_from_freesis(
        self,
        db: AsyncSession,
        items: list[FreeSISGPItem],
    ) -> FreeSISSyncResult:
        """파싱된 FreeSIS GP 목록을 Company 테이블에 동기화한다.

        - is_gp = True 설정
        - gp_strategy_tags에 "institutional_pef" 태그 추가
        - EntityResolver로 기존 Company 매칭
        - 매칭 실패 시 신규 Company 생성
        """
        result = FreeSISSyncResult(total_items=len(items))
        resolver = EntityResolver()
        now = datetime.now(UTC)

        for item in items:
            try:
                await self._sync_single_gp(db, resolver, item, now, result)
            except Exception:
                logger.exception("FreeSIS GP 동기화 실패: %s", item.company_name)
                result.errors.append(item.company_name)

        await db.commit()
        logger.info(
            "FreeSIS GP 동기화 완료: 총 %d건, 기존매칭 %d, 신규 %d, 업데이트 %d, 에러 %d",
            result.total_items,
            result.matched_existing,
            result.created,
            result.updated,
            len(result.errors),
        )
        return result

    async def _sync_single_gp(
        self,
        db: AsyncSession,
        resolver: EntityResolver,
        item: FreeSISGPItem,
        now: datetime,
        result: FreeSISSyncResult,
    ) -> None:
        """단일 FreeSIS GP 항목을 Company에 동기화한다."""
        # 1. EntityResolver로 기존 Company 매칭
        match_result = await resolver.resolve(db, item.company_name)
        matched = match_result.get("match")

        if matched:
            company = await self._find_company(db, matched)
            if company:
                self._update_gp_fields(company, item, now)
                result.matched_existing += 1
                result.updated += 1
                return

        # 2. 회사명 직접 매칭 (정확 일치)
        stmt = select(Company).where(func.lower(Company.corp_name) == func.lower(item.company_name))
        db_result = await db.execute(stmt)
        company = db_result.scalar_one_or_none()
        if company:
            self._update_gp_fields(company, item, now)
            result.matched_existing += 1
            result.updated += 1
            return

        # 3. 신규 Company 생성
        company = Company(
            corp_code=None,
            corp_name=item.company_name,
            is_gp=True,
            gp_strategy_tags={"strategies": ["institutional_pef"], "sources": ["freesis"]},
            gp_profile_synced_at=now,
        )
        if item.setting_balance is not None:
            company.gp_aum = item.setting_balance
        if item.fund_count is not None:
            company.gp_fund_count = item.fund_count
        db.add(company)
        await db.flush()
        result.created += 1

        # 정규화 별칭 자동 등록
        normalized = normalize_company_name(item.company_name)
        if normalized and normalized != item.company_name:
            alias = CompanyAlias(
                alias_name=normalized,
                company_id=company.id,
                is_manual=False,
            )
            db.add(alias)

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
    def _update_gp_fields(company: Company, item: FreeSISGPItem, now: datetime) -> None:
        """Company의 GP 프로파일 필드를 FreeSIS 데이터로 업데이트한다."""
        company.is_gp = True

        # 전략 태그에 institutional_pef 및 freesis 소스 추가 (dict 복사로 mutation safety 확보)
        tags = dict(company.gp_strategy_tags or {})
        strategies = list(tags.get("strategies", []))
        if "institutional_pef" not in strategies:
            strategies.append("institutional_pef")
        sources = list(tags.get("sources", []))
        if "freesis" not in sources:
            sources.append("freesis")
        tags["strategies"] = strategies
        tags["sources"] = sources
        company.gp_strategy_tags = tags

        # AUM 업데이트 (FreeSIS 설정잔액은 항상 최신으로 덮어씀)
        if item.setting_balance is not None:
            company.gp_aum = item.setting_balance
        if item.fund_count is not None:
            company.gp_fund_count = item.fund_count

        company.gp_profile_synced_at = now

    def _find_header_row(self, rows: list[tuple]) -> int | None:  # type: ignore[type-arg]
        """헤더 행 인덱스를 찾는다 (첫 10행 내에서)."""
        for idx, row in enumerate(rows[:10]):
            for cell in row:
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                for pattern in self._HEADER_PATTERNS["company_name"]:
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
