"""전자공시 Deep Link 서비스 테스트"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.disclosure import Disclosure
from app.services.disclosure_service import (
    DART_PDF_BASE,
    DART_VIEWER_BASE,
    KOFIA_DISCLOSURE_BASE,
    DisclosureService,
)


@pytest.fixture
def disclosure_service() -> DisclosureService:
    """공시 서비스 인스턴스 (DART 호출 없이 로직만 테스트)"""
    return DisclosureService()


@pytest.fixture
async def sample_company(async_session: AsyncSession) -> Company:
    """테스트용 기업"""
    company = Company(
        corp_code="00100001",
        corp_name="한국투자파트너스 주식회사",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
async def sample_disclosures(async_session: AsyncSession, sample_company: Company) -> list[Disclosure]:
    """테스트용 공시 데이터"""
    disclosures = [
        Disclosure(
            company_id=sample_company.id,
            corp_code=sample_company.corp_code,
            corp_name=sample_company.corp_name,
            report_nm="사업보고서 (2024.12)",
            rcept_no="20250301000001",
            rcept_dt="20250301",
            flr_nm="한국투자파트너스",
            dart_viewer_url=DART_VIEWER_BASE + "20250301000001",
            dart_pdf_url=DART_PDF_BASE + "20250301000001",
            disclosure_type="annual_report",
            source="dart",
        ),
        Disclosure(
            company_id=sample_company.id,
            corp_code=sample_company.corp_code,
            corp_name=sample_company.corp_name,
            report_nm="감사보고서 (2024.12)",
            rcept_no="20250315000002",
            rcept_dt="20250315",
            flr_nm="한국투자파트너스",
            dart_viewer_url=DART_VIEWER_BASE + "20250315000002",
            dart_pdf_url=DART_PDF_BASE + "20250315000002",
            disclosure_type="audit_report",
            source="dart",
        ),
        Disclosure(
            company_id=sample_company.id,
            corp_code=sample_company.corp_code,
            corp_name=sample_company.corp_name,
            report_nm="분기보고서 (2025.03)",
            rcept_no="20250515000003",
            rcept_dt="20250515",
            flr_nm="한국투자파트너스",
            dart_viewer_url=DART_VIEWER_BASE + "20250515000003",
            dart_pdf_url=DART_PDF_BASE + "20250515000003",
            disclosure_type="quarterly",
            source="dart",
        ),
    ]
    async_session.add_all(disclosures)
    await async_session.flush()
    return disclosures


class TestGenerateUrls:
    """URL 생성 테스트"""

    def test_viewer_url(self):
        """DART 뷰어 URL 생성"""
        url = DisclosureService.generate_dart_viewer_url("20240101000001")
        assert url == "https://opendart.fss.or.kr/dsaf001/main.do?rcept_no=20240101000001"

    def test_pdf_url(self):
        """DART PDF URL 생성"""
        url = DisclosureService.generate_dart_pdf_url("20240101000001")
        assert url == "https://opendart.fss.or.kr/dsaf001/saveasdocument.do?rcept_no=20240101000001"

    def test_kofia_url(self):
        """KOFIA 공시 URL 생성"""
        url = DisclosureService.generate_kofia_url("ANN20250101001")
        assert url == KOFIA_DISCLOSURE_BASE + "ANN20250101001"

    def test_kofia_url_empty(self):
        """빈 ID로 KOFIA URL 생성"""
        url = DisclosureService.generate_kofia_url("")
        assert url == KOFIA_DISCLOSURE_BASE


class TestClassifyType:
    """공시 유형 분류 테스트"""

    def test_annual_report(self):
        """사업보고서 분류"""
        result = DisclosureService.classify_disclosure_type("사업보고서 (2024.12)")
        assert result == "annual_report"

    def test_audit_report(self):
        """감사보고서 분류"""
        result = DisclosureService.classify_disclosure_type("[감사보고서] 제출")
        assert result == "audit_report"

    def test_quarterly(self):
        """분기보고서 분류"""
        result = DisclosureService.classify_disclosure_type("분기보고서 (2025.03)")
        assert result == "quarterly"

    def test_semi_annual(self):
        """반기보고서 분류"""
        result = DisclosureService.classify_disclosure_type("반기보고서 (2025.06)")
        assert result == "semi_annual"

    def test_sanction(self):
        """제재 관련 분류"""
        result = DisclosureService.classify_disclosure_type("제재 조치 결과 통보")
        assert result == "sanction"

    def test_default_other(self):
        """기타 분류 (매칭 키워드 없음)"""
        result = DisclosureService.classify_disclosure_type("임원 변경 공시")
        assert result == "other"


class TestSyncDisclosures:
    """공시 동기화 테스트"""

    async def test_sync_new_disclosures(
        self,
        async_session: AsyncSession,
        sample_company: Company,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """DART에서 신규 공시 동기화"""
        from unittest.mock import AsyncMock

        from app.schemas.dart import DisclosureItem

        # DART 응답 모킹
        mock_items = [
            DisclosureItem(
                corp_code="00100001",
                corp_name="한국투자파트너스 주식회사",
                corp_cls="E",
                report_nm="사업보고서 (2024.12)",
                rcept_no="20250401000001",
                flr_nm="한국투자파트너스",
                rcept_dt="20250401",
                rm="",
            ),
            DisclosureItem(
                corp_code="00100001",
                corp_name="한국투자파트너스 주식회사",
                corp_cls="E",
                report_nm="감사보고서 (2024.12)",
                rcept_no="20250401000002",
                flr_nm="한국투자파트너스",
                rcept_dt="20250401",
                rm="",
            ),
        ]

        service = DisclosureService()
        service.dart_service.search_disclosures = AsyncMock(return_value=(mock_items, 2, 1))

        synced, skipped = await service.sync_disclosures(
            db=async_session,
            corp_code="00100001",
        )

        assert synced == 2
        assert skipped == 0

        # DB에 저장된 레코드 확인
        from sqlalchemy import select

        stmt = select(Disclosure).where(Disclosure.corp_code == "00100001")
        result = await async_session.execute(stmt)
        disclosures = list(result.scalars().all())

        assert len(disclosures) == 2

        # URL 형식 확인
        for d in disclosures:
            assert d.dart_viewer_url.startswith(DART_VIEWER_BASE)
            assert d.dart_pdf_url.startswith(DART_PDF_BASE)
            assert d.company_id == sample_company.id

        # 유형 분류 확인
        types = {d.rcept_no: d.disclosure_type for d in disclosures}
        assert types["20250401000001"] == "annual_report"
        assert types["20250401000002"] == "audit_report"

    async def test_skip_existing(
        self,
        async_session: AsyncSession,
        sample_company: Company,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """이미 존재하는 공시는 스킵"""
        from unittest.mock import AsyncMock

        from app.schemas.dart import DisclosureItem

        # 먼저 하나를 DB에 저장
        existing = Disclosure(
            company_id=sample_company.id,
            corp_code="00100001",
            corp_name="한국투자파트너스 주식회사",
            report_nm="사업보고서 (2024.12)",
            rcept_no="20250501000001",
            rcept_dt="20250501",
            dart_viewer_url=DART_VIEWER_BASE + "20250501000001",
            dart_pdf_url=DART_PDF_BASE + "20250501000001",
            disclosure_type="annual_report",
            source="dart",
        )
        async_session.add(existing)
        await async_session.flush()

        # 같은 rcept_no를 포함하는 DART 응답 모킹
        mock_items = [
            DisclosureItem(
                corp_code="00100001",
                corp_name="한국투자파트너스 주식회사",
                corp_cls="E",
                report_nm="사업보고서 (2024.12)",
                rcept_no="20250501000001",  # 이미 존재
                flr_nm="한국투자파트너스",
                rcept_dt="20250501",
                rm="",
            ),
            DisclosureItem(
                corp_code="00100001",
                corp_name="한국투자파트너스 주식회사",
                corp_cls="E",
                report_nm="분기보고서 (2025.03)",
                rcept_no="20250501000002",  # 신규
                flr_nm="한국투자파트너스",
                rcept_dt="20250501",
                rm="",
            ),
        ]

        service = DisclosureService()
        service.dart_service.search_disclosures = AsyncMock(return_value=(mock_items, 2, 1))

        synced, skipped = await service.sync_disclosures(
            db=async_session,
            corp_code="00100001",
        )

        assert synced == 1
        assert skipped == 1


class TestGetDisclosures:
    """공시 조회 테스트"""

    async def test_paginated_list(
        self,
        async_session: AsyncSession,
        sample_company: Company,
        sample_disclosures: list[Disclosure],
    ):
        """페이지네이션 조회"""
        service = DisclosureService()

        disclosures, total = await service.get_disclosures(
            db=async_session,
            corp_code=sample_company.corp_code,
            page=1,
            size=2,
        )

        assert total == 3
        assert len(disclosures) == 2

    async def test_filter_by_type(
        self,
        async_session: AsyncSession,
        sample_company: Company,
        sample_disclosures: list[Disclosure],
    ):
        """공시 유형 필터"""
        service = DisclosureService()

        disclosures, total = await service.get_disclosures(
            db=async_session,
            corp_code=sample_company.corp_code,
            disclosure_type="annual_report",
        )

        assert total == 1
        assert disclosures[0].disclosure_type == "annual_report"
        assert disclosures[0].report_nm == "사업보고서 (2024.12)"


class TestGetDeepLink:
    """Deep Link 조회 테스트"""

    async def test_found(
        self,
        async_session: AsyncSession,
        sample_disclosures: list[Disclosure],
    ):
        """존재하는 접수번호로 조회"""
        service = DisclosureService()

        disclosure = await service.get_deep_link(
            db=async_session,
            rcept_no="20250301000001",
        )

        assert disclosure is not None
        assert disclosure.rcept_no == "20250301000001"
        assert disclosure.dart_viewer_url == DART_VIEWER_BASE + "20250301000001"
        assert disclosure.dart_pdf_url == DART_PDF_BASE + "20250301000001"

    async def test_not_found(
        self,
        async_session: AsyncSession,
    ):
        """존재하지 않는 접수번호 조회"""
        service = DisclosureService()

        disclosure = await service.get_deep_link(
            db=async_session,
            rcept_no="99999999999999",
        )

        assert disclosure is None


class TestSyncKofiaDisclosures:
    """KOFIA 공시 동기화 테스트"""

    async def test_sync_kofia_new(self, async_session: AsyncSession):
        """KOFIA에서 신규 펀드 공시 동기화"""
        from unittest.mock import AsyncMock

        mock_response = {
            "resultList": [
                {
                    "annon_id": "ANN20250601001",
                    "annon_title": "사업보고서 (2024.12)",
                    "annon_date": "20250601",
                    "company_nm": "한국투자신탁운용",
                    "submit_nm": "한국투자신탁운용",
                },
                {
                    "annon_id": "ANN20250601002",
                    "annon_title": "감사보고서 (2024.12)",
                    "annon_date": "20250601",
                    "company_nm": "한국투자신탁운용",
                    "submit_nm": "한국투자신탁운용",
                },
            ],
        }

        service = DisclosureService()
        service.kofia_service._request = AsyncMock(return_value=mock_response)

        synced, skipped = await service.sync_kofia_disclosures(
            db=async_session,
            fund_code="KR5100001234",
        )

        assert synced == 2
        assert skipped == 0

        # DB 저장 확인
        from sqlalchemy import select

        stmt = select(Disclosure).where(Disclosure.source == "kofia")
        result = await async_session.execute(stmt)
        disclosures = list(result.scalars().all())

        assert len(disclosures) == 2
        for d in disclosures:
            assert d.kofia_url is not None
            assert d.kofia_url.startswith(KOFIA_DISCLOSURE_BASE)
            assert d.source == "kofia"
            assert d.corp_code == "KR5100001234"

    async def test_sync_kofia_skip_existing(self, async_session: AsyncSession):
        """이미 동기화된 KOFIA 공시는 스킵"""
        from hashlib import sha256
        from unittest.mock import AsyncMock

        # 동일 announcement_id로 기존 레코드 생성
        ann_id = "ANN20250601001"
        rcept_no = f"KOFIA-{sha256(ann_id.encode()).hexdigest()[:16]}"
        existing = Disclosure(
            corp_code="KR5100001234",
            report_nm="사업보고서 (2024.12)",
            rcept_no=rcept_no,
            dart_viewer_url=KOFIA_DISCLOSURE_BASE + ann_id,
            kofia_url=KOFIA_DISCLOSURE_BASE + ann_id,
            source="kofia",
        )
        async_session.add(existing)
        await async_session.flush()

        mock_response = {
            "resultList": [
                {
                    "annon_id": ann_id,
                    "annon_title": "사업보고서 (2024.12)",
                    "annon_date": "20250601",
                    "company_nm": "한국투자신탁운용",
                },
            ],
        }

        service = DisclosureService()
        service.kofia_service._request = AsyncMock(return_value=mock_response)

        synced, skipped = await service.sync_kofia_disclosures(
            db=async_session,
            fund_code="KR5100001234",
        )

        assert synced == 0
        assert skipped == 1

    async def test_sync_kofia_empty_response(self, async_session: AsyncSession):
        """KOFIA API가 빈 결과를 반환할 때"""
        from unittest.mock import AsyncMock

        service = DisclosureService()
        service.kofia_service._request = AsyncMock(return_value={"resultList": []})

        synced, skipped = await service.sync_kofia_disclosures(
            db=async_session,
            fund_code="KR5100009999",
        )

        assert synced == 0
        assert skipped == 0

    async def test_sync_kofia_api_failure(self, async_session: AsyncSession):
        """KOFIA API 호출 실패 시 (0, 0) 반환"""
        from unittest.mock import AsyncMock

        service = DisclosureService()
        service.kofia_service._request = AsyncMock(side_effect=Exception("Connection error"))

        synced, skipped = await service.sync_kofia_disclosures(
            db=async_session,
            fund_code="KR5100009999",
        )

        assert synced == 0
        assert skipped == 0
