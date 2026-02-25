"""심사역 추적 서비스

Key Man(심사역)의 소속 변경을 감지하고 프로필을 관리한다.
"""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.deal import Deal
from app.models.fund import Fund, FundManager
from app.models.manager import ManagerMovement, MovementType

logger = logging.getLogger(__name__)


class ManagerService:
    """심사역 추적 서비스"""

    def __init__(self) -> None:
        pass

    async def detect_movements(self, db: AsyncSession) -> list[ManagerMovement]:
        """FundManager 레코드를 스캔하여 이동 이벤트를 감지한다.

        1. resigned_date가 설정되고 is_active=False인 매니저 → 사임 이벤트
        2. is_active=True이며 아직 appointment 이벤트가 없는 매니저 → 신규 임명

        Args:
            db: DB 세션

        Returns:
            새로 감지된 이동 이력 목록
        """
        new_movements: list[ManagerMovement] = []
        now = datetime.now(UTC)

        # 1. 사임 감지: resigned_date가 설정된 매니저 중 이미 기록되지 않은 건
        resigned_stmt = select(FundManager).where(
            FundManager.resigned_date.isnot(None),
            FundManager.is_active.is_(False),
        )
        resigned_result = await db.execute(resigned_stmt)
        resigned_managers = list(resigned_result.scalars().all())

        for manager in resigned_managers:
            # 이미 동일 이동이 기록되었는지 확인
            existing_stmt = select(ManagerMovement).where(
                ManagerMovement.manager_name == manager.manager_name,
                ManagerMovement.from_fund_id == manager.fund_id,
                ManagerMovement.movement_type == MovementType.RESIGNATION,
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                continue

            # 펀드 → 기업 정보 조회
            fund_stmt = select(Fund).where(Fund.id == manager.fund_id)
            fund_result = await db.execute(fund_stmt)
            fund = fund_result.scalar_one_or_none()

            from_company_id = fund.company_id if fund else None
            from_company_name = fund.company_name if fund else None

            movement = ManagerMovement(
                manager_name=manager.manager_name,
                from_company_id=from_company_id,
                from_company_name=from_company_name,
                from_fund_id=manager.fund_id,
                to_company_id=None,
                to_company_name=None,
                to_fund_id=None,
                movement_type=MovementType.RESIGNATION,
                detected_at=now,
                source="kofia",
                notes=f"사임일: {manager.resigned_date}",
            )
            db.add(movement)
            new_movements.append(movement)

        # 2. 신규 임명 감지: is_active=True인 매니저 중 appointment 기록이 없는 건
        active_stmt = select(FundManager).where(FundManager.is_active.is_(True))
        active_result = await db.execute(active_stmt)
        active_managers = list(active_result.scalars().all())

        for manager in active_managers:
            existing_stmt = select(ManagerMovement).where(
                ManagerMovement.manager_name == manager.manager_name,
                ManagerMovement.to_fund_id == manager.fund_id,
                ManagerMovement.movement_type == MovementType.APPOINTMENT,
            )
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()

            if existing:
                continue

            # 펀드 → 기업 정보 조회
            fund_stmt = select(Fund).where(Fund.id == manager.fund_id)
            fund_result = await db.execute(fund_stmt)
            fund = fund_result.scalar_one_or_none()

            to_company_id = fund.company_id if fund else None
            to_company_name = fund.company_name if fund else None

            # 동일 이름의 사임 이력이 있으면 이직(transfer)으로 분류
            resignation_stmt = select(ManagerMovement).where(
                ManagerMovement.manager_name == manager.manager_name,
                ManagerMovement.movement_type == MovementType.RESIGNATION,
            )
            resignation_result = await db.execute(resignation_stmt)
            prev_resignation = resignation_result.scalars().first()

            if prev_resignation:
                # 이전 사임 이력 → 이직으로 기록
                movement = ManagerMovement(
                    manager_name=manager.manager_name,
                    from_company_id=prev_resignation.from_company_id,
                    from_company_name=prev_resignation.from_company_name,
                    from_fund_id=prev_resignation.from_fund_id,
                    to_company_id=to_company_id,
                    to_company_name=to_company_name,
                    to_fund_id=manager.fund_id,
                    movement_type=MovementType.TRANSFER,
                    detected_at=now,
                    source="kofia",
                    notes=f"임명일: {manager.appointed_date}",
                )
            else:
                movement = ManagerMovement(
                    manager_name=manager.manager_name,
                    from_company_id=None,
                    from_company_name=None,
                    from_fund_id=None,
                    to_company_id=to_company_id,
                    to_company_name=to_company_name,
                    to_fund_id=manager.fund_id,
                    movement_type=MovementType.APPOINTMENT,
                    detected_at=now,
                    source="kofia",
                    notes=f"임명일: {manager.appointed_date}",
                )

            db.add(movement)
            new_movements.append(movement)

        await db.flush()
        await db.commit()
        return new_movements

    async def get_manager_profile(self, db: AsyncSession, manager_name: str) -> dict:
        """심사역 프로필을 조회한다.

        FundManager 레코드, 이동 이력, 관련 딜 정보를 통합한다.

        Args:
            db: DB 세션
            manager_name: 심사역 이름

        Returns:
            프로필 딕셔너리
        """
        # FundManager 레코드 조회
        fm_stmt = (
            select(FundManager)
            .where(FundManager.manager_name == manager_name)
            .order_by(FundManager.appointed_date.desc())
        )
        fm_result = await db.execute(fm_stmt)
        fund_managers = list(fm_result.scalars().all())

        if not fund_managers:
            return {
                "manager_name": manager_name,
                "current_company": None,
                "current_fund": None,
                "specialty_sectors": [],
                "career_years": None,
                "total_deals_involved": 0,
                "movements": [],
                "deals": [],
            }

        # 현재 소속 (활성 상태)
        current_fm = next((fm for fm in fund_managers if fm.is_active), None)
        current_company = None
        current_fund = None
        career_years = None
        total_deals = 0
        specialty_sectors: list[str] = []

        # 현재 소속 펀드 1회만 조회 (N+1 방지)
        current_fund_obj: Fund | None = None
        if current_fm:
            fund_stmt = select(Fund).where(Fund.id == current_fm.fund_id)
            fund_result = await db.execute(fund_stmt)
            current_fund_obj = fund_result.scalar_one_or_none()

            if current_fund_obj:
                current_fund = current_fund_obj.fund_name
                current_company = current_fund_obj.company_name

            career_years = current_fm.career_years
            total_deals = current_fm.total_deals_involved

            # 전문 섹터 파싱
            if current_fm.specialty_sectors:
                try:
                    specialty_sectors = json.loads(current_fm.specialty_sectors)
                except (json.JSONDecodeError, TypeError):
                    specialty_sectors = []

        # 경력 년수: 가장 큰 값 사용
        if career_years is None:
            career_values = [fm.career_years for fm in fund_managers if fm.career_years]
            career_years = max(career_values) if career_values else None

        # 관여 딜 수 합산
        total_deals = sum(fm.total_deals_involved for fm in fund_managers)

        # 이동 이력 조회
        movements_stmt = (
            select(ManagerMovement)
            .where(ManagerMovement.manager_name == manager_name)
            .order_by(ManagerMovement.detected_at.desc())
        )
        movements_result = await db.execute(movements_stmt)
        movements = list(movements_result.scalars().all())

        # 관련 딜 조회 (이미 조회한 current_fund_obj 재사용)
        deals: list[Deal] = []
        if current_fund_obj and current_fund_obj.company_id:
            deals_stmt = (
                select(Deal).where(Deal.company_id == current_fund_obj.company_id).order_by(Deal.deal_date.desc()).limit(20)
            )
            deals_result = await db.execute(deals_stmt)
            deals = list(deals_result.scalars().all())

        return {
            "manager_name": manager_name,
            "current_company": current_company,
            "current_fund": current_fund,
            "specialty_sectors": specialty_sectors,
            "career_years": career_years,
            "total_deals_involved": total_deals,
            "movements": movements,
            "deals": deals,
        }

    async def get_movements(
        self,
        db: AsyncSession,
        manager_name: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ManagerMovement], int]:
        """심사역 이동 이력을 페이지네이션으로 조회한다.

        Args:
            db: DB 세션
            manager_name: 심사역 이름 필터 (선택)
            page: 페이지 번호
            size: 페이지 크기

        Returns:
            (이동 이력 목록, 총 건수)
        """
        base_query = select(ManagerMovement)

        if manager_name:
            base_query = base_query.where(ManagerMovement.manager_name == manager_name)

        # 총 건수
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = base_query.order_by(ManagerMovement.detected_at.desc()).offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        movements = list(result.scalars().all())

        return movements, total

    async def get_movements_by_company(
        self,
        db: AsyncSession,
        corp_code: str,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ManagerMovement], int]:
        """특정 기업과 관련된 심사역 이동 이력을 조회한다.

        from_company 또는 to_company가 해당 기업인 이동을 모두 포함한다.

        Args:
            db: DB 세션
            corp_code: DART 고유번호
            page: 페이지 번호
            size: 페이지 크기

        Returns:
            (이동 이력 목록, 총 건수)
        """
        # 기업 조회
        company_stmt = select(Company).where(Company.corp_code == corp_code)
        company_result = await db.execute(company_stmt)
        company = company_result.scalar_one_or_none()

        if not company:
            return [], 0

        base_query = select(ManagerMovement).where(
            or_(
                ManagerMovement.from_company_id == company.id,
                ManagerMovement.to_company_id == company.id,
            )
        )

        # 총 건수
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = base_query.order_by(ManagerMovement.detected_at.desc()).offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        movements = list(result.scalars().all())

        return movements, total
