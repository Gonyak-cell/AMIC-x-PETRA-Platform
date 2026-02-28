"""원문 공시 연결 서비스 테스트."""

import pytest
from sqlalchemy import select

from app.models.deal import Deal
from app.models.disclosure import Disclosure
from app.models.elestock import DartExecutiveHolding
from app.models.holding import DartMajorHolding
from app.services.source_document_service import SourceDocumentService


@pytest.mark.asyncio
async def test_link_all_deals(async_session):
    """Deal의 rcept_no와 Disclosure.rcept_no를 매칭하여 disclosure_id를 설정한다."""
    # Disclosure 생성
    disclosure = Disclosure(
        corp_code="00126380",
        report_nm="사업보고서 (2023.12)",
        rcept_no="20240315000001",
        dart_viewer_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240315000001",
        source="dart",
    )
    async_session.add(disclosure)
    await async_session.flush()

    # Deal 생성 (rcept_no 있지만 disclosure_id 없음)
    deal = Deal(
        target_company="삼성전자",
        deal_type="holding_change",
        source_type="disclosure",
        rcept_no="20240315000001",
    )
    async_session.add(deal)
    await async_session.flush()

    service = SourceDocumentService()
    result = await service.link_all(async_session)

    assert result.deals_linked == 1

    # disclosure_id 설정 확인
    db_result = await async_session.execute(select(Deal).where(Deal.id == deal.id))
    updated_deal = db_result.scalar_one()
    assert updated_deal.disclosure_id == disclosure.id


@pytest.mark.asyncio
async def test_link_all_major_holdings(async_session):
    """DartMajorHolding의 rcept_no를 Disclosure와 매칭한다."""
    disclosure = Disclosure(
        corp_code="00126380",
        report_nm="대량보유상황보고서",
        rcept_no="20240301000001",
        dart_viewer_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240301000001",
        source="dart",
    )
    async_session.add(disclosure)
    await async_session.flush()

    holding = DartMajorHolding(
        rcept_no="20240301000001",
        rcept_dt="20240301",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="한국투자파트너스",
    )
    async_session.add(holding)
    await async_session.flush()

    service = SourceDocumentService()
    result = await service.link_all(async_session)

    assert result.major_holdings_linked == 1

    db_result = await async_session.execute(select(DartMajorHolding).where(DartMajorHolding.id == holding.id))
    updated = db_result.scalar_one()
    assert updated.disclosure_id == disclosure.id


@pytest.mark.asyncio
async def test_link_all_executive_holdings(async_session):
    """DartExecutiveHolding의 rcept_no를 Disclosure와 매칭한다."""
    disclosure = Disclosure(
        corp_code="00126380",
        report_nm="임원·주요주주 소유보고",
        rcept_no="20240601000001",
        dart_viewer_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240601000001",
        source="dart",
    )
    async_session.add(disclosure)
    await async_session.flush()

    holding = DartExecutiveHolding(
        rcept_no="20240601000001",
        rcept_dt="20240601",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="홍길동",
    )
    async_session.add(holding)
    await async_session.flush()

    service = SourceDocumentService()
    result = await service.link_all(async_session)

    assert result.executive_holdings_linked == 1

    db_result = await async_session.execute(select(DartExecutiveHolding).where(DartExecutiveHolding.id == holding.id))
    updated = db_result.scalar_one()
    assert updated.disclosure_id == disclosure.id


@pytest.mark.asyncio
async def test_link_all_no_matching_disclosure(async_session):
    """매칭되는 Disclosure가 없으면 연결하지 않는다."""
    deal = Deal(
        target_company="SK하이닉스",
        deal_type="executive_change",
        source_type="disclosure",
        rcept_no="99999999999999",
    )
    async_session.add(deal)
    await async_session.flush()

    service = SourceDocumentService()
    result = await service.link_all(async_session)

    assert result.deals_linked == 0


@pytest.mark.asyncio
async def test_link_all_skip_already_linked(async_session):
    """이미 disclosure_id가 설정된 레코드는 건너뛴다."""
    disclosure = Disclosure(
        corp_code="00126380",
        report_nm="사업보고서",
        rcept_no="20240315000001",
        dart_viewer_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20240315000001",
        source="dart",
    )
    async_session.add(disclosure)
    await async_session.flush()

    deal = Deal(
        target_company="삼성전자",
        deal_type="holding_change",
        source_type="disclosure",
        rcept_no="20240315000001",
        disclosure_id=disclosure.id,  # 이미 연결됨
    )
    async_session.add(deal)
    await async_session.flush()

    service = SourceDocumentService()
    result = await service.link_all(async_session)

    # 이미 연결되어 있으므로 0
    assert result.deals_linked == 0


@pytest.mark.asyncio
async def test_link_all_combined(async_session):
    """Deal + MajorHolding + ExecutiveHolding 동시 연결 테스트."""
    d1 = Disclosure(
        corp_code="00126380",
        report_nm="공시1",
        rcept_no="R001",
        dart_viewer_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=R001",
        source="dart",
    )
    d2 = Disclosure(
        corp_code="00126380",
        report_nm="공시2",
        rcept_no="R002",
        dart_viewer_url="https://dart.fss.or.kr/dsaf001/main.do?rcpNo=R002",
        source="dart",
    )
    async_session.add_all([d1, d2])
    await async_session.flush()

    deal = Deal(
        target_company="삼성전자",
        rcept_no="R001",
    )
    major = DartMajorHolding(
        rcept_no="R002",
        rcept_dt="20240301",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="테스트GP",
    )
    exec_h = DartExecutiveHolding(
        rcept_no="R001",
        rcept_dt="20240601",
        corp_code="00126380",
        corp_name="삼성전자",
        repror="홍길동",
    )
    async_session.add_all([deal, major, exec_h])
    await async_session.flush()

    service = SourceDocumentService()
    result = await service.link_all(async_session)

    assert result.deals_linked == 1
    assert result.major_holdings_linked == 1
    assert result.executive_holdings_linked == 1
