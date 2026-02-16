"""전자공시 Deep Link 서비스

DART/KOFIA 공시 데이터를 동기화하고 원문 Deep Link URL을 생성/관리한다.
"""

import logging
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.disclosure import Disclosure
from app.services.dart_service import DARTService
from app.services.kofia_service import KOFIAService

logger = logging.getLogger(__name__)

# DART Deep Link URL 패턴
DART_VIEWER_BASE = "https://opendart.fss.or.kr/dsaf001/main.do?rcept_no="
DART_PDF_BASE = "https://opendart.fss.or.kr/dsaf001/saveasdocument.do?rcept_no="

# KOFIA Deep Link URL 패턴
KOFIA_DISCLOSURE_BASE = (
    "https://dis.kofia.or.kr/websquare/index.jsp?w2xPath=/wq/fundann/DISFundAnnDetail.xml&lv_annon_id="
)

# 공시 유형 분류 키워드
TYPE_KEYWORDS: dict[str, list[str]] = {
    "annual_report": ["사업보고서"],
    "audit_report": ["감사보고서"],
    "quarterly": ["분기보고서"],
    "semi_annual": ["반기보고서"],
    "material": ["주요사항보고서"],
    "sanction": ["제재", "조치", "과징금"],
}


class DisclosureService:
    """전자공시 Deep Link 서비스 (DART + KOFIA)"""

    def __init__(self) -> None:
        self.dart_service = DARTService()
        self.kofia_service = KOFIAService()

    @staticmethod
    def generate_dart_viewer_url(rcept_no: str) -> str:
        """DART 뷰어 URL을 생성한다.

        Args:
            rcept_no: 접수번호

        Returns:
            DART 뷰어 URL
        """
        return DART_VIEWER_BASE + rcept_no

    @staticmethod
    def generate_dart_pdf_url(rcept_no: str) -> str:
        """DART PDF 다운로드 URL을 생성한다.

        Args:
            rcept_no: 접수번호

        Returns:
            DART PDF URL
        """
        return DART_PDF_BASE + rcept_no

    @staticmethod
    def generate_kofia_url(announcement_id: str) -> str:
        """KOFIA 공시 상세 URL을 생성한다.

        Args:
            announcement_id: KOFIA 공시 고유 ID

        Returns:
            KOFIA 공시 상세 URL
        """
        return KOFIA_DISCLOSURE_BASE + announcement_id

    @staticmethod
    def classify_disclosure_type(report_nm: str) -> str:
        """보고서명을 기반으로 공시 유형을 분류한다.

        Args:
            report_nm: 보고서명

        Returns:
            공시 유형 코드
        """
        for disclosure_type, keywords in TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in report_nm:
                    return disclosure_type
        return "other"

    async def sync_disclosures(
        self,
        db: AsyncSession,
        corp_code: str,
        bgn_de: str | None = None,
        end_de: str | None = None,
    ) -> tuple[int, int]:
        """DART 공시 데이터를 동기화한다.

        Args:
            db: DB 세션
            corp_code: DART 고유번호
            bgn_de: 시작일 (YYYYMMDD)
            end_de: 종료일 (YYYYMMDD)

        Returns:
            (동기화 건수, 스킵 건수)
        """
        # 기업 조회 (company_id 연결용, 없어도 진행)
        company_id: int | None = None
        stmt = select(Company).where(Company.corp_code == corp_code)
        result = await db.execute(stmt)
        company = result.scalar_one_or_none()
        if company:
            company_id = company.id

        # DART 공시 검색
        items, _total_count, _total_page = await self.dart_service.search_disclosures(
            corp_code=corp_code,
            bgn_de=bgn_de,
            end_de=end_de,
        )

        synced_count = 0
        skipped_count = 0

        for item in items:
            # 중복 체크 (rcept_no 기준)
            exists_stmt = select(Disclosure.id).where(Disclosure.rcept_no == item.rcept_no)
            exists_result = await db.execute(exists_stmt)
            if exists_result.scalar_one_or_none() is not None:
                skipped_count += 1
                continue

            # Deep Link URL 생성
            viewer_url = self.generate_dart_viewer_url(item.rcept_no)
            pdf_url = self.generate_dart_pdf_url(item.rcept_no)

            # 공시 유형 분류
            disclosure_type = self.classify_disclosure_type(item.report_nm)

            # Disclosure 레코드 생성
            disclosure = Disclosure(
                company_id=company_id,
                corp_code=item.corp_code or corp_code,
                corp_name=item.corp_name or None,
                corp_cls=item.corp_cls or None,
                report_nm=item.report_nm,
                rcept_no=item.rcept_no,
                rcept_dt=item.rcept_dt or None,
                flr_nm=item.flr_nm or None,
                rm=item.rm or None,
                dart_viewer_url=viewer_url,
                dart_pdf_url=pdf_url,
                disclosure_type=disclosure_type,
                source="dart",
            )
            db.add(disclosure)
            synced_count += 1

        await db.flush()
        return synced_count, skipped_count

    async def sync_kofia_disclosures(
        self,
        db: AsyncSession,
        fund_code: str,
    ) -> tuple[int, int]:
        """KOFIA 펀드 공시 데이터를 동기화한다.

        KOFIA DIS에서 펀드 공시 목록을 조회하고 Deep Link URL을 생성한다.

        Args:
            db: DB 세션
            fund_code: 펀드 코드

        Returns:
            (동기화 건수, 스킵 건수)
        """
        try:
            response = await self.kofia_service._request(
                service_id="BFAnnounce",
                params={"fund_cd": fund_code},
            )
        except Exception:
            logger.exception("KOFIA 공시 조회 실패: fund_code=%s", fund_code)
            return 0, 0

        items = response.get("resultList", response.get("list", []))
        if not items:
            return 0, 0

        synced_count = 0
        skipped_count = 0

        for item in items:
            announcement_id = item.get("annon_id", item.get("annonId", ""))
            report_nm = item.get("annon_title", item.get("title", ""))

            if not announcement_id or not report_nm:
                skipped_count += 1
                continue

            # 중복 체크: KOFIA 공시는 rcept_no 대신 announcement_id 기반 해시 사용
            rcept_no = f"KOFIA-{sha256(announcement_id.encode()).hexdigest()[:16]}"

            exists_stmt = select(Disclosure.id).where(Disclosure.rcept_no == rcept_no)
            exists_result = await db.execute(exists_stmt)
            if exists_result.scalar_one_or_none() is not None:
                skipped_count += 1
                continue

            kofia_url = self.generate_kofia_url(announcement_id)
            disclosure_type = self.classify_disclosure_type(report_nm)
            rcept_dt = item.get("annon_date", item.get("annonDate"))

            disclosure = Disclosure(
                corp_code=fund_code,
                corp_name=item.get("company_nm", item.get("companyNm")),
                report_nm=report_nm,
                rcept_no=rcept_no,
                rcept_dt=rcept_dt,
                flr_nm=item.get("submit_nm", item.get("submitNm")),
                dart_viewer_url=kofia_url,
                kofia_url=kofia_url,
                disclosure_type=disclosure_type,
                source="kofia",
            )
            db.add(disclosure)
            synced_count += 1

        await db.flush()
        return synced_count, skipped_count

    async def get_disclosures(
        self,
        db: AsyncSession,
        corp_code: str,
        disclosure_type: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Disclosure], int]:
        """공시 목록을 페이지네이션으로 조회한다.

        Args:
            db: DB 세션
            corp_code: DART 고유번호
            disclosure_type: 공시 유형 필터 (선택)
            page: 페이지 번호
            size: 페이지 크기

        Returns:
            (공시 목록, 총 건수)
        """
        base_query = select(Disclosure).where(Disclosure.corp_code == corp_code)

        if disclosure_type:
            base_query = base_query.where(Disclosure.disclosure_type == disclosure_type)

        # 총 건수
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 페이지네이션
        query = base_query.order_by(Disclosure.rcept_dt.desc()).offset((page - 1) * size).limit(size)

        result = await db.execute(query)
        disclosures = list(result.scalars().all())

        return disclosures, total

    async def get_deep_link(
        self,
        db: AsyncSession,
        rcept_no: str,
    ) -> Disclosure | None:
        """접수번호로 단일 공시 Deep Link를 조회한다.

        Args:
            db: DB 세션
            rcept_no: 접수번호

        Returns:
            Disclosure 또는 None
        """
        stmt = select(Disclosure).where(Disclosure.rcept_no == rcept_no)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def close(self) -> None:
        """리소스를 정리한다."""
        await self.dart_service.close()
        await self.kofia_service.close()
