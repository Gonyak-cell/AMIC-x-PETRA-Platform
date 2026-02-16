"""제재 경중 분류 서비스 테스트"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.sanction import SanctionCategory, SanctionSeverity
from app.schemas.dart import SanctionItem
from app.services.sanction_service import SanctionService


@pytest.fixture
def sanction_service() -> SanctionService:
    """제재 서비스 인스턴스 (DART 서비스 모킹)"""
    service = SanctionService()
    service.dart_service = AsyncMock()
    return service


@pytest.fixture
async def sample_company(async_session: AsyncSession) -> Company:
    """테스트용 기업"""
    company = Company(
        corp_code="00100001",
        corp_name="테스트기업 주식회사",
        corp_cls="E",
    )
    async_session.add(company)
    await async_session.flush()
    return company


@pytest.fixture
def sample_dart_sanctions() -> list[SanctionItem]:
    """테스트용 DART 제재 항목"""
    return [
        SanctionItem(
            corp_code="00100001",
            corp_name="테스트기업 주식회사",
            sanctions_type="과징금 부과",
            sanctions_detail="자본시장법 위반으로 과징금 부과",
            sanctions_date="20240315",
            sanctions_agency="금융감독원",
        ),
        SanctionItem(
            corp_code="00100001",
            corp_name="테스트기업 주식회사",
            sanctions_type="임원 해임",
            sanctions_detail="대표이사 횡령 혐의로 해임",
            sanctions_date="20240520",
            sanctions_agency="금융위원회",
        ),
        SanctionItem(
            corp_code="00100001",
            corp_name="테스트기업 주식회사",
            sanctions_type="과태료",
            sanctions_detail="사업보고서 제출 지연에 따른 과태료",
            sanctions_date="20240101",
            sanctions_agency="금융감독원",
        ),
    ]


class TestClassifySeverity:
    """제재 경중 분류 테스트"""

    def test_critical_embezzlement(self, sanction_service: SanctionService):
        """횡령 키워드 → critical"""
        severity, reason = sanction_service.classify_severity("임원 해임", "대표이사 횡령 혐의")
        assert severity == SanctionSeverity.CRITICAL
        assert "횡령" in reason

    def test_critical_fraud(self, sanction_service: SanctionService):
        """사기 키워드 → critical"""
        severity, reason = sanction_service.classify_severity("사기 혐의", "투자금 사기")
        assert severity == SanctionSeverity.CRITICAL
        assert "사기" in reason

    def test_warning_undisclosed(self, sanction_service: SanctionService):
        """미공시 키워드 → warning"""
        severity, reason = sanction_service.classify_severity("미공시", "주요사항보고서 미공시")
        assert severity == SanctionSeverity.WARNING
        assert "미공시" in reason

    def test_warning_violation(self, sanction_service: SanctionService):
        """위반 키워드 → warning"""
        severity, reason = sanction_service.classify_severity("과징금 부과", "자본시장법 위반으로 과징금 부과")
        assert severity == SanctionSeverity.WARNING
        assert "위반" in reason

    def test_caution_fine(self, sanction_service: SanctionService):
        """과태료 키워드 → caution"""
        severity, reason = sanction_service.classify_severity("과태료", "경미한 행정 절차상 과태료 부과")
        assert severity == SanctionSeverity.CAUTION
        assert "과태료" in reason

    def test_caution_correction_order(self, sanction_service: SanctionService):
        """시정명령 키워드 → caution"""
        severity, reason = sanction_service.classify_severity("시정명령", "내부 통제 개선 시정명령")
        assert severity == SanctionSeverity.CAUTION
        assert "시정명령" in reason

    def test_default_caution(self, sanction_service: SanctionService):
        """키워드 미매칭 → 기본 caution"""
        severity, reason = sanction_service.classify_severity("기타 조치", "특이 사항 없음")
        assert severity == SanctionSeverity.CAUTION
        assert "기본" in reason

    def test_priority_critical_over_warning(self, sanction_service: SanctionService):
        """위반 + 횡령 동시 포함 → critical 우선"""
        severity, reason = sanction_service.classify_severity("법령 위반", "자금 횡령에 의한 자본시장법 위반")
        assert severity == SanctionSeverity.CRITICAL
        assert "횡령" in reason

    def test_priority_critical_over_caution(self, sanction_service: SanctionService):
        """과태료 + 배임 동시 포함 → critical 우선"""
        severity, reason = sanction_service.classify_severity("과태료 부과", "배임 행위 관련 과태료")
        assert severity == SanctionSeverity.CRITICAL
        assert "배임" in reason


class TestClassifyCategory:
    """제재 유형 분류 테스트"""

    def test_fraud_category(self, sanction_service: SanctionService):
        """사기 키워드 → fraud"""
        category = sanction_service.classify_category("사기 행위", "투자금 사기")
        assert category == SanctionCategory.FRAUD

    def test_embezzlement_category(self, sanction_service: SanctionService):
        """배임 키워드 → embezzlement"""
        category = sanction_service.classify_category("배임 혐의", "업무상 배임")
        assert category == SanctionCategory.EMBEZZLEMENT

    def test_disclosure_category(self, sanction_service: SanctionService):
        """미공시 키워드 → disclosure"""
        category = sanction_service.classify_category("미공시", "주요사항보고서 미공시")
        assert category == SanctionCategory.DISCLOSURE

    def test_administrative_category(self, sanction_service: SanctionService):
        """과태료 키워드 → administrative"""
        category = sanction_service.classify_category("과태료", "행정 절차 위반")
        assert category == SanctionCategory.ADMINISTRATIVE

    def test_default_other(self, sanction_service: SanctionService):
        """키워드 미매칭 → other"""
        category = sanction_service.classify_category("기타 조치", "특이 사항 없음")
        assert category == SanctionCategory.OTHER


class TestClassifyForCompany:
    """기업별 제재 분류 테스트"""

    async def test_classify_and_store(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
        sample_dart_sanctions: list[SanctionItem],
    ):
        """DART 제재 수집, 분류, DB 저장 확인"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=sample_dart_sanctions)

        records = await sanction_service.classify_for_company(db=async_session, corp_code=sample_company.corp_code)

        assert len(records) == 3

        # 각 레코드의 분류 결과 확인
        severities = {r.sanctions_type: r.severity for r in records}
        assert severities["임원 해임"] == SanctionSeverity.CRITICAL  # 횡령
        assert severities["과징금 부과"] == SanctionSeverity.WARNING  # 위반
        assert severities["과태료"] == SanctionSeverity.CAUTION  # 과태료

        # DB에 저장되었는지 확인
        for r in records:
            assert r.id is not None
            assert r.company_id == sample_company.id
            assert r.classified_at is not None

    async def test_skip_duplicates(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
        sample_dart_sanctions: list[SanctionItem],
    ):
        """동일 제재를 두 번 분류해도 중복 생성되지 않음"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=sample_dart_sanctions)

        # 첫 번째 분류
        first_records = await sanction_service.classify_for_company(
            db=async_session, corp_code=sample_company.corp_code
        )
        assert len(first_records) == 3

        # 두 번째 분류 (동일 데이터)
        second_records = await sanction_service.classify_for_company(
            db=async_session, corp_code=sample_company.corp_code
        )
        assert len(second_records) == 0  # 중복이므로 새 레코드 없음

    async def test_classify_no_company(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
    ):
        """존재하지 않는 기업 → 빈 목록 반환"""
        records = await sanction_service.classify_for_company(db=async_session, corp_code="99999999")
        assert len(records) == 0

    async def test_classify_no_sanctions(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
    ):
        """DART 제재 내역 없음 → 빈 목록 반환"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=[])

        records = await sanction_service.classify_for_company(db=async_session, corp_code=sample_company.corp_code)
        assert len(records) == 0


class TestGetSanctionsByCompany:
    """기업별 제재 조회 테스트"""

    async def test_get_all(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
        sample_dart_sanctions: list[SanctionItem],
    ):
        """전체 목록 조회"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=sample_dart_sanctions)
        await sanction_service.classify_for_company(db=async_session, corp_code=sample_company.corp_code)

        sanctions, total = await sanction_service.get_sanctions_by_company(
            db=async_session, corp_code=sample_company.corp_code
        )

        assert total == 3
        assert len(sanctions) == 3

    async def test_filter_by_severity(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
        sample_dart_sanctions: list[SanctionItem],
    ):
        """경중 필터 조회"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=sample_dart_sanctions)
        await sanction_service.classify_for_company(db=async_session, corp_code=sample_company.corp_code)

        sanctions, total = await sanction_service.get_sanctions_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
            severity=SanctionSeverity.CRITICAL,
        )

        assert total == 1
        assert sanctions[0].severity == SanctionSeverity.CRITICAL

    async def test_pagination(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
        sample_dart_sanctions: list[SanctionItem],
    ):
        """페이지네이션"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=sample_dart_sanctions)
        await sanction_service.classify_for_company(db=async_session, corp_code=sample_company.corp_code)

        sanctions, total = await sanction_service.get_sanctions_by_company(
            db=async_session,
            corp_code=sample_company.corp_code,
            page=1,
            size=2,
        )

        assert total == 3
        assert len(sanctions) == 2


class TestSanctionSummary:
    """제재 요약 테스트"""

    async def test_summary_counts(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
        sample_company: Company,
        sample_dart_sanctions: list[SanctionItem],
    ):
        """경중별 건수 집계 확인"""
        sanction_service.dart_service.get_sanctions = AsyncMock(return_value=sample_dart_sanctions)
        await sanction_service.classify_for_company(db=async_session, corp_code=sample_company.corp_code)

        summary = await sanction_service.get_sanction_summary(db=async_session, corp_code=sample_company.corp_code)

        assert summary["total"] == 3
        assert summary["critical_count"] == 1  # 횡령
        assert summary["warning_count"] == 1  # 위반
        assert summary["caution_count"] == 1  # 과태료

    async def test_summary_empty(
        self,
        async_session: AsyncSession,
        sanction_service: SanctionService,
    ):
        """제재 없는 기업의 요약"""
        summary = await sanction_service.get_sanction_summary(db=async_session, corp_code="99999999")

        assert summary["total"] == 0
        assert summary["caution_count"] == 0
        assert summary["warning_count"] == 0
        assert summary["critical_count"] == 0
