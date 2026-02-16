"""제재 경중 분류 서비스

DART 제재 내역을 수집하여 경중(주의/경고/위험)과 유형을 자동 분류한다.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.sanction import ClassifiedSanction, SanctionCategory, SanctionSeverity
from app.services.dart_service import DARTService

logger = logging.getLogger(__name__)


class SanctionService:
    """제재 경중 분류 서비스"""

    # 위험(Critical) 키워드: 횡령, 배임, 사기 등 중대 위반
    CRITICAL_KEYWORDS: list[str] = [
        "횡령",
        "배임",
        "사기",
        "부정",
        "허위",
        "위조",
        "조작",
        "불법",
    ]

    # 경고(Warning) 키워드: 위반, 미공시 등 중간 수준
    WARNING_KEYWORDS: list[str] = [
        "위반",
        "위법",
        "미공시",
        "지연공시",
        "미보고",
        "과징금",
    ]

    # 주의(Caution) 키워드: 과태료, 시정명령 등 경미
    CAUTION_KEYWORDS: list[str] = [
        "과태료",
        "시정명령",
        "경고",
        "주의",
        "개선",
        "행정착오",
    ]

    # 유형 분류 키워드
    CATEGORY_KEYWORDS: dict[str, list[str]] = {
        SanctionCategory.FRAUD: ["횡령", "사기", "부정", "허위"],
        SanctionCategory.EMBEZZLEMENT: ["배임", "횡령"],
        SanctionCategory.DISCLOSURE: ["미공시", "지연공시", "미보고", "공시"],
        SanctionCategory.ADMINISTRATIVE: ["과태료", "시정명령", "행정"],
    }

    def __init__(self) -> None:
        self.dart_service = DARTService()

    def classify_severity(self, sanctions_type: str, sanctions_detail: str | None) -> tuple[str, str]:
        """제재 경중을 분류한다.

        키워드 매칭 우선순위: CRITICAL > WARNING > CAUTION.
        매칭되지 않으면 기본 caution으로 분류한다.

        Args:
            sanctions_type: 제재유형
            sanctions_detail: 제재내용

        Returns:
            (경중 등급, 매칭 근거 문자열)
        """
        combined = f"{sanctions_type} {sanctions_detail or ''}"

        # CRITICAL 우선 검사
        matched = [kw for kw in self.CRITICAL_KEYWORDS if kw in combined]
        if matched:
            reason = f"위험 키워드 매칭: {', '.join(matched)}"
            return SanctionSeverity.CRITICAL, reason

        # WARNING 검사
        matched = [kw for kw in self.WARNING_KEYWORDS if kw in combined]
        if matched:
            reason = f"경고 키워드 매칭: {', '.join(matched)}"
            return SanctionSeverity.WARNING, reason

        # CAUTION 검사
        matched = [kw for kw in self.CAUTION_KEYWORDS if kw in combined]
        if matched:
            reason = f"주의 키워드 매칭: {', '.join(matched)}"
            return SanctionSeverity.CAUTION, reason

        # 기본값
        return SanctionSeverity.CAUTION, "키워드 미매칭 (기본 주의)"

    def classify_category(self, sanctions_type: str, sanctions_detail: str | None) -> str:
        """제재 유형을 분류한다.

        CATEGORY_KEYWORDS 매칭 순서대로 첫 매칭 반환.
        매칭되지 않으면 other 반환.

        Args:
            sanctions_type: 제재유형
            sanctions_detail: 제재내용

        Returns:
            유형 분류 코드
        """
        combined = f"{sanctions_type} {sanctions_detail or ''}"

        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in combined:
                    return category

        return SanctionCategory.OTHER

    async def classify_for_company(self, db: AsyncSession, corp_code: str) -> list[ClassifiedSanction]:
        """특정 기업의 DART 제재 내역을 수집하고 분류한다.

        1. 기업 조회
        2. DART API로 제재 내역 조회
        3. 경중/유형 분류
        4. 중복 확인 후 DB 저장

        Args:
            db: DB 세션
            corp_code: DART 고유번호

        Returns:
            새로 분류된 제재 목록
        """
        # 1. 기업 조회
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()

        if not company:
            logger.warning("기업을 찾을 수 없습니다: %s", corp_code)
            return []

        # 2. DART 제재 내역 조회
        sanctions = await self.dart_service.get_sanctions(corp_code)

        if not sanctions:
            logger.info("제재 내역이 없습니다: %s", corp_code)
            return []

        new_records: list[ClassifiedSanction] = []
        now = datetime.now(UTC)

        for item in sanctions:
            # 4. 중복 확인 (corp_code + sanctions_type + sanctions_date)
            dup_stmt = select(ClassifiedSanction).where(
                ClassifiedSanction.corp_code == corp_code,
                ClassifiedSanction.sanctions_type == item.sanctions_type,
                ClassifiedSanction.sanctions_date == item.sanctions_date,
            )
            dup_result = await db.execute(dup_stmt)
            existing = dup_result.scalar_one_or_none()

            if existing:
                logger.debug(
                    "중복 제재 건너뛰기: %s / %s / %s",
                    corp_code,
                    item.sanctions_type,
                    item.sanctions_date,
                )
                continue

            # 3. 분류
            severity, severity_reason = self.classify_severity(item.sanctions_type, item.sanctions_detail)
            category = self.classify_category(item.sanctions_type, item.sanctions_detail)

            record = ClassifiedSanction(
                company_id=company.id,
                corp_code=corp_code,
                sanctions_type=item.sanctions_type,
                sanctions_detail=item.sanctions_detail or None,
                sanctions_date=item.sanctions_date or None,
                sanctions_agency=item.sanctions_agency or None,
                severity=severity,
                severity_reason=severity_reason,
                category=category,
                classified_at=now,
            )
            db.add(record)
            new_records.append(record)

        if new_records:
            await db.flush()
            await db.commit()
            logger.info(
                "제재 분류 완료: %s / %d건",
                corp_code,
                len(new_records),
            )

        return new_records

    async def get_sanctions_by_company(
        self,
        db: AsyncSession,
        corp_code: str,
        severity: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ClassifiedSanction], int]:
        """기업별 분류된 제재 목록을 조회한다.

        Args:
            db: DB 세션
            corp_code: DART 고유번호
            severity: 경중 필터 (선택)
            page: 페이지 번호
            size: 페이지 크기

        Returns:
            (제재 목록, 총 건수)
        """
        base_query = select(ClassifiedSanction).where(ClassifiedSanction.corp_code == corp_code)

        if severity:
            base_query = base_query.where(ClassifiedSanction.severity == severity)

        # 총 건수
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = base_query.order_by(ClassifiedSanction.sanctions_date.desc()).offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        sanctions = list(result.scalars().all())

        return sanctions, total

    async def get_sanction_summary(self, db: AsyncSession, corp_code: str) -> dict:
        """기업별 제재 요약(경중별 건수)을 조회한다.

        Args:
            db: DB 세션
            corp_code: DART 고유번호

        Returns:
            {total, caution_count, warning_count, critical_count}
        """
        query = select(
            func.count(ClassifiedSanction.id).label("total"),
            func.count(
                case(
                    (
                        ClassifiedSanction.severity == SanctionSeverity.CAUTION,
                        ClassifiedSanction.id,
                    ),
                )
            ).label("caution_count"),
            func.count(
                case(
                    (
                        ClassifiedSanction.severity == SanctionSeverity.WARNING,
                        ClassifiedSanction.id,
                    ),
                )
            ).label("warning_count"),
            func.count(
                case(
                    (
                        ClassifiedSanction.severity == SanctionSeverity.CRITICAL,
                        ClassifiedSanction.id,
                    ),
                )
            ).label("critical_count"),
        ).where(ClassifiedSanction.corp_code == corp_code)

        result = await db.execute(query)
        row = result.one()

        return {
            "total": row.total,
            "caution_count": row.caution_count,
            "warning_count": row.warning_count,
            "critical_count": row.critical_count,
        }

    async def close(self) -> None:
        """리소스 정리"""
        await self.dart_service.close()
