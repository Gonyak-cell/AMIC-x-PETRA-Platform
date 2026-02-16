"""S1-A-05: DB 통합 테스트 - Company ↔ Fund ↔ REITs 관계 검증"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.company import Company
from app.models.fund import Fund, FundManager
from app.models.news import NewsArticle
from app.models.reits import REITs, REITsAsset

# --- Company CRUD 테스트 ---


async def test_create_company(async_session):
    """Company 모델 생성"""
    company = Company(
        corp_code="00126380",
        corp_name="삼성전자",
        corp_name_eng="SAMSUNG ELECTRONICS CO.,LTD",
        stock_name="삼성전자",
        stock_code="005930",
        ceo_nm="한종희",
        corp_cls="Y",
        jurir_no="1301110006246",
        bizr_no="1248100998",
        adres="경기도 수원시 영통구 삼성로 129 (매탄동)",
        hm_url="https://www.samsung.com",
        induty_code="26110",
        est_dt="19690113",
        acc_mt="12",
    )
    async_session.add(company)
    await async_session.commit()

    result = await async_session.execute(select(Company).where(Company.corp_code == "00126380"))
    saved = result.scalar_one()

    assert saved.corp_name == "삼성전자"
    assert saved.stock_code == "005930"
    assert saved.jurir_no == "1301110006246"
    assert saved.created_at is not None


async def test_company_unique_corp_code(async_session):
    """corp_code 중복 시 에러"""
    company1 = Company(corp_code="00126380", corp_name="삼성전자")
    company2 = Company(corp_code="00126380", corp_name="삼성전자 복제")
    async_session.add(company1)
    await async_session.commit()

    async_session.add(company2)
    with pytest.raises(Exception):
        await async_session.commit()
    await async_session.rollback()


async def test_company_list_query(async_session):
    """Company 목록 조회"""
    companies = [
        Company(corp_code="001", corp_name="A기업"),
        Company(corp_code="002", corp_name="B기업"),
        Company(corp_code="003", corp_name="C기업"),
    ]
    async_session.add_all(companies)
    await async_session.commit()

    result = await async_session.execute(select(Company).order_by(Company.corp_name))
    items = result.scalars().all()
    assert len(items) == 3
    assert items[0].corp_name == "A기업"


# --- Company ↔ Fund 관계 테스트 ---


async def test_company_fund_relationship(async_session):
    """Company ↔ Fund FK 관계"""
    company = Company(corp_code="COM001", corp_name="한국투자파트너스")
    async_session.add(company)
    await async_session.flush()

    fund = Fund(
        fund_code="KR5200001234",
        fund_name="한투파 블라인드 1호",
        fund_type="blind",
        company_name="한국투자파트너스",
        company_id=company.id,
    )
    async_session.add(fund)
    await async_session.commit()

    # Company에서 Fund 조회
    result = await async_session.execute(select(Company).where(Company.corp_code == "COM001"))
    saved_company = result.scalar_one()

    # Fund에서 Company 조회
    result = await async_session.execute(select(Fund).where(Fund.fund_code == "KR5200001234"))
    saved_fund = result.scalar_one()
    assert saved_fund.company_id == saved_company.id


async def test_fund_without_company(async_session):
    """Company 없는 Fund (company_id=None)"""
    fund = Fund(
        fund_code="KR5200009999",
        fund_name="독립 펀드",
        fund_type="blind",
        company_name="미등록 운용사",
    )
    async_session.add(fund)
    await async_session.commit()

    result = await async_session.execute(select(Fund).where(Fund.fund_code == "KR5200009999"))
    saved = result.scalar_one()
    assert saved.company_id is None


# --- Company ↔ REITs 관계 테스트 ---


async def test_company_reits_relationship(async_session):
    """Company ↔ REITs FK 관계"""
    company = Company(corp_code="REITS001", corp_name="한국리츠관리")
    async_session.add(company)
    await async_session.flush()

    reits = REITs(
        reits_code="REITS-001",
        reits_name="한국오피스리츠",
        reits_type="entrusted",
        company_id=company.id,
    )
    async_session.add(reits)
    await async_session.commit()

    result = await async_session.execute(select(REITs).where(REITs.reits_code == "REITS-001"))
    saved_reits = result.scalar_one()
    assert saved_reits.company_id == company.id


# --- Fund ↔ FundManager 관계 테스트 ---


async def test_fund_manager_cascade(async_session):
    """Fund 삭제 시 FundManager cascade 삭제"""
    fund = Fund(
        fund_code="KR-CASCADE",
        fund_name="캐스케이드 테스트 펀드",
        fund_type="blind",
        company_name="테스트운용",
    )
    async_session.add(fund)
    await async_session.flush()

    manager = FundManager(
        fund_id=fund.id,
        manager_name="김테스트",
        position="심사역",
    )
    async_session.add(manager)
    await async_session.commit()

    # Fund 삭제
    await async_session.delete(fund)
    await async_session.commit()

    result = await async_session.execute(select(FundManager))
    assert result.scalars().all() == []


# --- REITs ↔ REITsAsset 관계 테스트 ---


async def test_reits_asset_relationship(async_session):
    """REITs ↔ REITsAsset 관계"""
    reits = REITs(
        reits_code="REITS-ASSET",
        reits_name="자산 테스트 리츠",
        reits_type="self_managed",
    )
    async_session.add(reits)
    await async_session.flush()

    asset = REITsAsset(
        reits_id=reits.id,
        asset_name="강남 오피스빌딩",
        asset_type="office",
        asset_value=Decimal("50000"),
        asset_ratio=Decimal("80.00"),
        location="서울시 강남구",
        acquisition_date=date(2023, 1, 15),
    )
    async_session.add(asset)
    await async_session.commit()

    result = await async_session.execute(select(REITsAsset).where(REITsAsset.reits_id == reits.id))
    saved_asset = result.scalar_one()
    assert saved_asset.asset_name == "강남 오피스빌딩"
    assert saved_asset.asset_type == "office"


# --- NewsArticle 모델 테스트 ---


async def test_create_news_article(async_session):
    """NewsArticle 모델 생성"""
    article = NewsArticle(
        title="스타트업 투자 소식",
        content="스타트업 A가 100억원 투자를 유치했다.",
        source="platum",
        url="https://platum.kr/article/1234",
        url_hash=NewsArticle.generate_url_hash("https://platum.kr/article/1234"),
    )
    async_session.add(article)
    await async_session.commit()

    result = await async_session.execute(select(NewsArticle).where(NewsArticle.source == "platum"))
    saved = result.scalar_one()
    assert saved.title == "스타트업 투자 소식"
    assert len(saved.url_hash) == 64  # SHA256 hex


async def test_news_url_hash_generation():
    """URL 해시 생성 테스트"""
    hash1 = NewsArticle.generate_url_hash("https://example.com/article/1")
    hash2 = NewsArticle.generate_url_hash("https://example.com/article/2")
    hash3 = NewsArticle.generate_url_hash("https://example.com/article/1")

    assert hash1 != hash2
    assert hash1 == hash3
    assert len(hash1) == 64


async def test_news_company_relationship(async_session):
    """NewsArticle ↔ Company FK 관계"""
    company = Company(corp_code="NEWS001", corp_name="뉴스 관련 기업")
    async_session.add(company)
    await async_session.flush()

    article = NewsArticle(
        title="기업 관련 뉴스",
        source="dealsite",
        url="https://dealsite.co.kr/news/1",
        url_hash=NewsArticle.generate_url_hash("https://dealsite.co.kr/news/1"),
        company_id=company.id,
    )
    async_session.add(article)
    await async_session.commit()

    result = await async_session.execute(select(NewsArticle).where(NewsArticle.company_id == company.id))
    saved = result.scalar_one()
    assert saved.title == "기업 관련 뉴스"
