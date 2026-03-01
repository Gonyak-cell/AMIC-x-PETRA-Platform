"""KVIC (한국벤처투자) 모태펀드 자조합 운용사정보 수집 서비스.

공공데이터포털(data.go.kr) 데이터셋 #3060708에서 수동 다운로드한
모태펀드 자조합 운용사정보 CSV/Excel 파일을 파싱하여 Company 테이블에 동기화한다.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import openpyxl
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyAlias
from app.models.gp_fund import KVICFund
from app.utils.entity_resolver import EntityResolver, normalize_company_name
from app.utils.numeric import safe_decimal

logger = logging.getLogger(__name__)


@dataclass
class KVICFundOperator:
    """KVIC 모태펀드 자조합 운용사 데이터."""

    fund_name: str  # 조합명 (없을 수 있음)
    operator_name: str  # 대표운용(영)사명
    operator_type: str = ""  # 운영사구분 (벤처투자회사, 신기술사, LLC 등)
    representative: str = ""  # 대표자
    phone: str = ""  # 연락처
    fund_size: Decimal | None = None  # 조합규모 (백만원)
    established_date: str = ""  # 결성일


@dataclass
class KVICSyncResult:
    """KVIC GP 동기화 결과."""

    total_items: int = 0
    unique_operators: int = 0
    created: int = 0
    updated: int = 0
    matched_existing: int = 0
    errors: list[str] = field(default_factory=list)


class KVICService:
    """KVIC 모태펀드 자조합 운용사정보 수집 서비스."""

    # KVIC CSV/Excel 헤더 패턴 (유연하게 매칭)
    # 실제 파일 헤더: "대표운영사,운영사구분,자조합 규모(백만원)"
    _HEADER_PATTERNS: dict[str, list[str]] = {
        "operator_name": ["대표운영사", "대표운용사", "운영사", "운용사", "운용회사", "GP"],
        "operator_type": ["운영사구분", "운용사구분", "구분"],
        "fund_name": ["조합명", "자조합명", "펀드명"],
        "representative": ["대표자", "대표이사"],
        "phone": ["연락처", "전화번호", "전화"],
        "fund_size": ["자조합 규모", "조합규모", "조합 규모", "펀드규모", "약정규모", "약정총액", "규모"],
        "established_date": ["결성일", "설립일", "결성년도"],
    }

    def parse_kvic_excel(self, file_path: Path) -> list[KVICFundOperator]:
        """KVIC에서 다운로드한 모태펀드 자조합 운용사정보 엑셀을 파싱한다.

        Args:
            file_path: 엑셀 파일 경로

        Returns:
            파싱된 운용사 목록
        """
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            ws = wb.active
            if ws is None:
                logger.warning("KVIC 엑셀: 활성 시트 없음")
                return []
            rows = list(ws.iter_rows(values_only=True))
        finally:
            wb.close()

        if not rows:
            return []

        return self._parse_rows(rows)

    def parse_kvic_csv(self, file_content: bytes) -> list[KVICFundOperator]:
        """KVIC에서 다운로드한 모태펀드 자조합 운용사정보 CSV를 파싱한다.

        Args:
            file_content: CSV 파일 바이트 내용

        Returns:
            파싱된 운용사 목록
        """
        # UTF-8 시도 후 CP949 폴백
        for encoding in ("utf-8-sig", "cp949", "euc-kr"):
            try:
                text = file_content.decode(encoding)
                break
            except (UnicodeDecodeError, ValueError):
                continue
        else:
            logger.warning("KVIC CSV: 인코딩 감지 실패")
            return []

        reader = csv.reader(io.StringIO(text))
        rows = [tuple(row) for row in reader]
        if not rows:
            return []

        return self._parse_rows(rows)

    def _parse_rows(self, rows: list[tuple]) -> list[KVICFundOperator]:  # type: ignore[type-arg]
        """공통 행 파싱 로직."""
        header_row_idx = self._find_header_row(rows)
        if header_row_idx is None:
            logger.warning("KVIC 파일: 헤더 행을 찾을 수 없음")
            return []

        header = rows[header_row_idx]
        col_map = self._map_columns(header)
        if "operator_name" not in col_map:
            logger.warning("KVIC 파일: '운용사' 컬럼을 찾을 수 없음")
            return []

        items: list[KVICFundOperator] = []
        for row in rows[header_row_idx + 1 :]:
            op_idx = col_map["operator_name"]
            if op_idx >= len(row):
                continue
            op_name = row[op_idx]
            if not op_name or not str(op_name).strip():
                continue

            op_name_str = str(op_name).strip()
            if op_name_str in ("합계", "소계", "전체", "총계", "Total"):
                continue

            fund_name = ""
            fn_idx = col_map.get("fund_name")
            if fn_idx is not None and fn_idx < len(row) and row[fn_idx]:
                fund_name = str(row[fn_idx]).strip()

            item = KVICFundOperator(
                fund_name=fund_name,
                operator_name=op_name_str,
                operator_type=self._get_str(row, col_map.get("operator_type")),
                representative=self._get_str(row, col_map.get("representative")),
                phone=self._get_str(row, col_map.get("phone")),
                fund_size=safe_decimal(self._get_cell(row, col_map.get("fund_size"))),
                established_date=self._get_str(row, col_map.get("established_date")),
            )
            items.append(item)

        logger.info("KVIC 파일 파싱 완료: %d건", len(items))
        return items

    async def sync_kvic_gp_data(
        self,
        db: AsyncSession,
        items: list[KVICFundOperator],
    ) -> KVICSyncResult:
        """파싱된 KVIC 운용사 목록을 Company 테이블에 동기화한다.

        - 동일 운용사명이 여러 조합에 등장 → 중복 제거 후 1회만 동기화
        - is_gp = True 설정
        - gp_strategy_tags에 "kvic_fund" 태그 추가
        - EntityResolver로 기존 Company 매칭
        - 매칭 실패 시 신규 Company 생성
        """
        result = KVICSyncResult(total_items=len(items))
        resolver = EntityResolver()
        now = datetime.now(UTC)

        # 운용사별 중복 제거 (가장 큰 fund_size 보존)
        operator_map: dict[str, KVICFundOperator] = {}
        kvic_fund_counts: dict[str, int] = {}
        for item in items:
            name = item.operator_name
            kvic_fund_counts[name] = kvic_fund_counts.get(name, 0) + 1
            existing = operator_map.get(name)
            if existing is None or (
                item.fund_size and (existing.fund_size is None or item.fund_size > existing.fund_size)
            ):
                operator_map[name] = item

        result.unique_operators = len(operator_map)

        # 운용사별 Company 매핑 (자조합 연결용)
        company_map: dict[str, Company] = {}

        for name, item in operator_map.items():
            try:
                await self._sync_single_gp(db, resolver, item, now, kvic_fund_counts.get(name, 1), result, company_map)
            except Exception:
                logger.exception("KVIC GP 동기화 실패: %s", name)
                result.errors.append(name)

        # 개별 자조합 레코드를 kvic_funds 테이블에 저장
        await self._sync_kvic_funds(db, items, company_map, now)

        await db.commit()
        logger.info(
            "KVIC GP 동기화 완료: 총 %d건, 고유 운용사 %d, 기존매칭 %d, 신규 %d, 업데이트 %d, 에러 %d",
            result.total_items,
            result.unique_operators,
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
        item: KVICFundOperator,
        now: datetime,
        kvic_fund_count: int,
        result: KVICSyncResult,
        company_map: dict[str, Company] | None = None,
    ) -> None:
        """단일 KVIC 운용사를 Company에 동기화한다."""
        # 1. EntityResolver로 기존 Company 매칭
        match_result = await resolver.resolve(db, item.operator_name)
        matched = match_result.get("match")

        if matched:
            company = await self._find_company(db, matched)
            if company:
                self._update_gp_fields(company, item, now, kvic_fund_count)
                result.matched_existing += 1
                result.updated += 1
                if company_map is not None:
                    company_map[item.operator_name] = company
                return

        # 2. 회사명 직접 매칭 (정확 일치)
        stmt = select(Company).where(func.lower(Company.corp_name) == func.lower(item.operator_name))
        db_result = await db.execute(stmt)
        company = db_result.scalar_one_or_none()
        if company:
            self._update_gp_fields(company, item, now, kvic_fund_count)
            result.matched_existing += 1
            result.updated += 1
            if company_map is not None:
                company_map[item.operator_name] = company
            return

        # 3. 신규 Company 생성
        company = Company(
            corp_code=None,
            corp_name=item.operator_name,
            is_gp=True,
            phn_no=item.phone or None,
            est_dt=item.established_date or None,
            gp_strategy_tags={
                "strategies": ["kvic_fund"],
                "sources": ["kvic"],
                "kvic_fund_count": kvic_fund_count,
            },
            gp_profile_synced_at=now,
        )
        db.add(company)
        await db.flush()
        result.created += 1
        if company_map is not None:
            company_map[item.operator_name] = company

        # 정규화 별칭 자동 등록
        normalized = normalize_company_name(item.operator_name)
        if normalized and normalized != item.operator_name:
            alias = CompanyAlias(
                alias_name=normalized,
                company_id=company.id,
                is_manual=False,
            )
            db.add(alias)

    @staticmethod
    async def _sync_kvic_funds(
        db: AsyncSession,
        items: list[KVICFundOperator],
        company_map: dict[str, Company],
        now: datetime,
    ) -> None:
        """개별 자조합 레코드를 kvic_funds 테이블에 저장한다.

        Replace 전략: 동기화 대상 GP의 기존 레코드를 삭제 후 재생성.
        """
        # 동기화 대상 GP의 기존 kvic_funds 삭제
        company_ids = [c.id for c in company_map.values()]
        if company_ids:
            from sqlalchemy import delete

            await db.execute(delete(KVICFund).where(KVICFund.company_id.in_(company_ids)))

        # 개별 자조합 레코드 생성
        for item in items:
            company = company_map.get(item.operator_name)
            if not company:
                continue
            if not item.fund_name:
                continue
            fund = KVICFund(
                company_id=company.id,
                fund_name=item.fund_name,
                fund_size=item.fund_size,
                operator_type=item.operator_type,
                representative=item.representative,
                phone=item.phone,
                established_date=item.established_date,
                synced_at=now,
            )
            db.add(fund)

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
    def _update_gp_fields(
        company: Company,
        item: KVICFundOperator,
        now: datetime,
        kvic_fund_count: int,
    ) -> None:
        """Company의 GP 프로파일 필드를 KVIC 데이터로 업데이트한다."""
        company.is_gp = True

        # 전략 태그에 kvic_fund 및 kvic 소스 추가 (dict 복사로 mutation safety 확보)
        tags = dict(company.gp_strategy_tags or {})
        strategies = list(tags.get("strategies", []))
        if "kvic_fund" not in strategies:
            strategies.append("kvic_fund")
        sources = list(tags.get("sources", []))
        if "kvic" not in sources:
            sources.append("kvic")
        tags["strategies"] = strategies
        tags["sources"] = sources
        tags["kvic_fund_count"] = kvic_fund_count
        company.gp_strategy_tags = tags

        # 연락처/설립일 보충 (기존 값이 없는 경우만)
        if item.phone and not company.phn_no:
            company.phn_no = item.phone
        if item.established_date and not company.est_dt:
            company.est_dt = item.established_date

        company.gp_profile_synced_at = now

    def _find_header_row(self, rows: list[tuple]) -> int | None:  # type: ignore[type-arg]
        """헤더 행 인덱스를 찾는다 (첫 10행 내에서)."""
        for idx, row in enumerate(rows[:10]):
            for cell in row:
                if cell is None:
                    continue
                cell_str = str(cell).strip()
                for pattern in self._HEADER_PATTERNS["operator_name"]:
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
