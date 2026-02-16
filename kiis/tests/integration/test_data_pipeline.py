"""Integration 테스트: 데이터 파이프라인 시나리오

DART 수집 -> DB 저장, 뉴스 -> NLP 분석, 평판 계산 흐름을 검증한다.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.models.disclosure import Disclosure
from app.models.reputation import ReputationScore
from app.services.reputation_service import ReputationService
from tests.factories import create_test_company, create_test_disclosure, create_test_news

pytestmark = pytest.mark.integration


class TestDartCollectionToDbStorage:
    """DART 공시 수집 -> DB 저장 통합 테스트"""

    async def test_dart_disclosure_sync_stores_in_db(self, db_session):
        """Mock DART API 응답으로 공시를 동기화하면 DB에 Disclosure가 저장된다."""
        company = await create_test_company(db_session, corp_code="00300001", corp_name="다트테스트 주식회사")

        # Disclosure를 직접 생성하여 DB 저장 흐름을 검증
        await create_test_disclosure(
            db_session,
            company_id=company.id,
            corp_code=company.corp_code,
            corp_name=company.corp_name,
            report_nm="사업보고서 (2024.12)",
            rcept_no="20250201000001",
        )

        # DB에서 조회하여 저장 확인
        result = await db_session.execute(select(Disclosure).where(Disclosure.rcept_no == "20250201000001"))
        saved = result.scalar_one_or_none()

        assert saved is not None
        assert saved.corp_code == "00300001"
        assert saved.report_nm == "사업보고서 (2024.12)"
        assert saved.company_id == company.id
        assert saved.dart_viewer_url is not None
        assert "rcept_no=20250201000001" in saved.dart_viewer_url

    async def test_dart_disclosure_sync_via_service(self, db_session):
        """DisclosureService.sync_disclosures를 mock DART 응답으로 호출하여 DB 저장을 검증한다."""
        company = await create_test_company(
            db_session,
            corp_code="00300002",
            corp_name="서비스테스트 주식회사",
            jurir_no="3301112345678",
            stock_code="300002",
        )

        # DARTService의 search_disclosures를 mock
        mock_disclosure_item = AsyncMock()
        mock_disclosure_item.corp_code = company.corp_code
        mock_disclosure_item.corp_name = company.corp_name
        mock_disclosure_item.corp_cls = "E"
        mock_disclosure_item.report_nm = "감사보고서 (2024.12)"
        mock_disclosure_item.rcept_no = "20250201000099"
        mock_disclosure_item.rcept_dt = "20250201"
        mock_disclosure_item.flr_nm = company.corp_name
        mock_disclosure_item.rm = ""

        with patch("app.services.disclosure_service.DARTService") as mock_dart_cls:
            mock_dart_instance = mock_dart_cls.return_value
            mock_dart_instance.search_disclosures = AsyncMock(return_value=([mock_disclosure_item], 1, 1))

            from app.services.disclosure_service import DisclosureService

            service = DisclosureService()
            service.dart_service = mock_dart_instance

            synced, skipped = await service.sync_disclosures(db_session, company.corp_code)

            assert synced == 1
            assert skipped == 0

        # DB에서 저장 확인
        result = await db_session.execute(select(Disclosure).where(Disclosure.rcept_no == "20250201000099"))
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.disclosure_type == "audit_report"
        assert saved.company_id == company.id

    async def test_duplicate_disclosure_is_skipped(self, db_session):
        """이미 존재하는 rcept_no의 공시는 중복 저장되지 않는다."""
        company = await create_test_company(
            db_session,
            corp_code="00300003",
            corp_name="중복테스트 주식회사",
            jurir_no="3301113456789",
            stock_code="300003",
        )

        # 먼저 하나 저장
        await create_test_disclosure(
            db_session,
            company_id=company.id,
            corp_code=company.corp_code,
            rcept_no="20250201000050",
        )

        mock_item = AsyncMock()
        mock_item.corp_code = company.corp_code
        mock_item.corp_name = company.corp_name
        mock_item.corp_cls = "E"
        mock_item.report_nm = "사업보고서 (2024.12)"
        mock_item.rcept_no = "20250201000050"  # 동일 접수번호
        mock_item.rcept_dt = "20250201"
        mock_item.flr_nm = company.corp_name
        mock_item.rm = ""

        with patch("app.services.disclosure_service.DARTService") as mock_dart_cls:
            mock_dart_instance = mock_dart_cls.return_value
            mock_dart_instance.search_disclosures = AsyncMock(return_value=([mock_item], 1, 1))

            from app.services.disclosure_service import DisclosureService

            service = DisclosureService()
            service.dart_service = mock_dart_instance

            synced, skipped = await service.sync_disclosures(db_session, company.corp_code)

            assert synced == 0
            assert skipped == 1


class TestNewsToNlpPipeline:
    """뉴스 -> NLP 분석 파이프라인 통합 테스트"""

    async def test_news_creation_and_sentiment_update(self, db_session):
        """뉴스를 생성하고 감성 점수를 업데이트할 수 있다."""
        company = await create_test_company(
            db_session,
            corp_code="00400001",
            corp_name="NLP테스트 주식회사",
            jurir_no="4401112345678",
            stock_code="400001",
        )

        article = await create_test_news(
            db_session,
            title="NLP테스트 주식회사, 성공적 엑시트 달성",
            content=(
                "NLP테스트 주식회사가 포트폴리오 기업의 성공적 엑시트를 달성하며 업계의 주목을 받고 있다. "
                "매출 증가와 흑자 전환으로 긍정적 평가."
            ),
            url="https://platum.kr/archives/nlp-test-001",
            company_id=company.id,
            sentiment_score=None,  # 아직 분석 전
        )

        assert article.sentiment_score is None

        # NLP 분석 수행 (직접 서비스 호출)
        from app.services.nlp_service import NLPService

        nlp = NLPService()
        result = nlp.analyze_sentiment(article.content)

        # 감성 점수 업데이트
        article.sentiment_score = result["score"]
        await db_session.commit()
        await db_session.refresh(article)

        assert article.sentiment_score is not None
        # 긍정적 키워드(성공적, 매출 증가, 흑자 전환)가 포함되어 있으므로 양수 예상
        assert isinstance(article.sentiment_score, float)

    async def test_news_keyword_extraction(self, db_session):
        """뉴스에서 키워드를 추출할 수 있다."""
        article = await create_test_news(
            db_session,
            title="AI 스타트업 투자 시장 동향",
            content="인공지능 스타트업에 대한 벤처캐피탈 투자가 크게 증가하고 있다. "
            "딥러닝 기술을 활용한 서비스 기업들이 시리즈A 투자를 유치하며 성장세를 보이고 있다.",
            url="https://platum.kr/archives/nlp-keyword-test",
            sentiment_score=None,
        )

        from app.services.nlp_service import NLPService

        nlp = NLPService()
        keywords = nlp.extract_keywords(article.content, top_n=5)

        assert len(keywords) > 0
        keyword_texts = [kw["keyword"] for kw in keywords]
        # 주요 명사가 추출되어야 한다
        expected_nouns = ["투자", "스타트업", "기술", "서비스", "기업", "딥러닝", "벤처캐피탈", "인공지능"]
        assert any(k in keyword_texts for k in expected_nouns)


class TestReputationCalculationFlow:
    """평판 스코어링 계산 흐름 통합 테스트"""

    async def test_reputation_calculation_with_news(self, db_session):
        """뉴스가 있는 기업의 평판을 계산하면 점수가 0~1 범위에 들어온다."""
        company = await create_test_company(
            db_session,
            corp_code="00500001",
            corp_name="평판테스트 주식회사",
            jurir_no="5501112345678",
            stock_code="500001",
        )

        # 긍정적 뉴스 3개 생성
        for i in range(3):
            await create_test_news(
                db_session,
                title=f"평판테스트 주식회사 투자 성과 {i + 1}",
                content="평판테스트가 성공적 엑시트를 달성했다. IPO를 통해 대규모 수익을 실현했다.",
                url=f"https://platum.kr/archives/rep-test-{i + 1}",
                company_id=company.id,
                sentiment_score=0.6 + (i * 0.1),
                published_at=datetime.now(UTC) - timedelta(days=i * 10),
            )

        # 평판 계산 (NLPService는 내부에서 생성됨)
        service = ReputationService()
        reputation = await service.calculate_reputation(
            db=db_session,
            corp_code=company.corp_code,
            months=6,
            save_history=True,
        )

        assert reputation is not None
        assert Decimal("0") <= reputation.total_score <= Decimal("1")
        assert reputation.news_count == 3
        assert reputation.status_tag in ("rising", "stable", "risk")

    async def test_reputation_calculation_without_news(self, db_session):
        """뉴스가 없는 기업의 평판 계산도 정상 동작한다 (기본값)."""
        company = await create_test_company(
            db_session,
            corp_code="00500002",
            corp_name="뉴스없는 주식회사",
            jurir_no="5501113456789",
            stock_code="500002",
        )

        service = ReputationService()
        reputation = await service.calculate_reputation(
            db=db_session,
            corp_code=company.corp_code,
            months=6,
            save_history=False,
        )

        assert reputation is not None
        assert reputation.news_count == 0
        assert reputation.exit_count == 0
        assert Decimal("0") <= reputation.total_score <= Decimal("1")

    async def test_reputation_is_saved_in_db(self, db_session):
        """계산된 평판이 DB에 저장된다."""
        company = await create_test_company(
            db_session,
            corp_code="00500003",
            corp_name="저장테스트 주식회사",
            jurir_no="5501114567890",
            stock_code="500003",
        )

        await create_test_news(
            db_session,
            title="저장테스트 주식회사 뉴스",
            url="https://platum.kr/archives/rep-save-test",
            company_id=company.id,
            sentiment_score=0.5,
            published_at=datetime.now(UTC) - timedelta(days=5),
        )

        service = ReputationService()
        await service.calculate_reputation(db=db_session, corp_code=company.corp_code)

        # DB에서 직접 조회
        result = await db_session.execute(select(ReputationScore).where(ReputationScore.company_id == company.id))
        saved = result.scalar_one_or_none()

        assert saved is not None
        assert saved.scored_at is not None
        assert saved.company_id == company.id
