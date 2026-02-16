"""테스트 데이터 팩토리 함수

테스트에서 DB 엔티티를 쉽게 생성하기 위한 팩토리 함수 모음.
각 팩토리는 합리적인 기본값을 사용하며 **kwargs로 오버라이드 가능하다.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.company import Company, CompanyAlias
from app.models.deal import Deal
from app.models.disclosure import Disclosure
from app.models.fund import Fund, FundManager
from app.models.news import NewsArticle
from app.models.reputation import ReputationScore
from app.models.user import User, UserRole
from app.models.watchlist import AlertHistory, AlertType, Watchlist


async def create_test_company(db: AsyncSession, **overrides) -> Company:
    """테스트용 Company를 생성한다."""
    defaults = {
        "corp_code": "00100001",
        "corp_name": "테스트투자파트너스 주식회사",
        "corp_name_eng": "Test Investment Partners Co., Ltd.",
        "stock_name": "테스트투자",
        "stock_code": "000001",
        "ceo_nm": "홍길동",
        "corp_cls": "E",
        "jurir_no": "1101111234567",
        "bizr_no": "1234567890",
        "adres": "서울특별시 강남구 테헤란로 123",
        "hm_url": "https://test-invest.co.kr",
        "induty_code": "64992",
        "est_dt": "20100101",
        "acc_mt": "12",
    }
    defaults.update(overrides)
    company = Company(**defaults)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company


async def create_test_company_alias(db: AsyncSession, **overrides) -> CompanyAlias:
    """테스트용 CompanyAlias를 생성한다."""
    defaults = {
        "alias_name": "테투파",
        "company_id": 1,
        "is_manual": True,
    }
    defaults.update(overrides)
    alias = CompanyAlias(**defaults)
    db.add(alias)
    await db.commit()
    await db.refresh(alias)
    return alias


async def create_test_fund(db: AsyncSession, **overrides) -> Fund:
    """테스트용 Fund를 생성한다."""
    defaults = {
        "fund_code": "FUND-001",
        "fund_name": "테스트 블라인드 1호 펀드",
        "fund_type": "blind",
        "fund_category": "VC",
        "company_name": "테스트투자파트너스",
        "company_code": "COMP-001",
        "total_amount": Decimal("50000000000"),
        "management_fee_rate": Decimal("2.00"),
        "performance_fee_rate": Decimal("20.00"),
        "established_date": datetime(2020, 1, 15).date(),
        "maturity_date": datetime(2030, 1, 15).date(),
        "vintage_year": 2020,
        "is_active": True,
        "is_maturity_alert": False,
        "description": "테스트 펀드입니다.",
    }
    defaults.update(overrides)
    fund = Fund(**defaults)
    db.add(fund)
    await db.commit()
    await db.refresh(fund)
    return fund


async def create_test_fund_manager(db: AsyncSession, **overrides) -> FundManager:
    """테스트용 FundManager를 생성한다."""
    defaults = {
        "fund_id": 1,
        "manager_name": "김테스트",
        "position": "대표이사",
        "role": "펀드매니저",
        "career_years": 15,
        "education": "서울대학교 경영학과",
        "is_active": True,
        "total_deals_involved": 10,
    }
    defaults.update(overrides)
    manager = FundManager(**defaults)
    db.add(manager)
    await db.commit()
    await db.refresh(manager)
    return manager


async def create_test_news(db: AsyncSession, **overrides) -> NewsArticle:
    """테스트용 NewsArticle을 생성한다."""
    url = overrides.get("url", "https://platum.kr/archives/test-article-001")
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    defaults = {
        "title": "테스트투자파트너스, AI 스타트업에 100억원 투자",
        "content": "테스트투자파트너스가 AI 기반 스타트업 테크노바에 100억원 규모의 시리즈A 투자를 단행했다.",
        "summary": "테스트투자파트너스 시리즈A 투자",
        "source": "platum",
        "author": "기자A",
        "published_at": datetime.now(UTC) - timedelta(days=1),
        "url": url,
        "url_hash": url_hash,
        "sentiment_score": 0.5,
        "keywords": '["투자", "AI", "스타트업"]',
    }
    defaults.update(overrides)
    # url이 오버라이드된 경우 url_hash도 재생성
    if "url" in overrides and "url_hash" not in overrides:
        defaults["url_hash"] = hashlib.sha256(defaults["url"].encode("utf-8")).hexdigest()
    article = NewsArticle(**defaults)
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return article


async def create_test_deal(db: AsyncSession, **overrides) -> Deal:
    """테스트용 Deal을 생성한다."""
    defaults = {
        "target_company": "테크노바",
        "amount": Decimal("10000000000"),
        "amount_display": "100억원",
        "round_stage": "series_a",
        "sector": "ai_deeptech",
        "deal_date": datetime(2025, 6, 15).date(),
        "deal_year": 2025,
        "source_type": "news",
        "is_lead_investor": True,
        "description": "AI 스타트업 시리즈A 투자",
    }
    defaults.update(overrides)
    deal = Deal(**defaults)
    db.add(deal)
    await db.commit()
    await db.refresh(deal)
    return deal


async def create_test_user(db: AsyncSession, **overrides) -> User:
    """테스트용 User를 생성한다. password 키가 있으면 해시 처리한다."""
    password = overrides.pop("password", "testpassword123")
    defaults = {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": get_password_hash(password),
        "role": UserRole.VIEWER,
        "is_active": True,
    }
    defaults.update(overrides)
    user = User(**defaults)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_test_reputation(db: AsyncSession, company_id: int, **overrides) -> ReputationScore:
    """테스트용 ReputationScore를 생성한다."""
    defaults = {
        "company_id": company_id,
        "trend_score": Decimal("0.5000"),
        "news_score": Decimal("0.3000"),
        "performance_score": Decimal("0.4000"),
        "total_score": Decimal("0.5000"),
        "status_tag": "stable",
        "scored_at": datetime.now(UTC),
        "news_count": 10,
        "exit_count": 2,
    }
    defaults.update(overrides)
    reputation = ReputationScore(**defaults)
    db.add(reputation)
    await db.commit()
    await db.refresh(reputation)
    return reputation


async def create_test_watchlist(db: AsyncSession, user_id: int, company_id: int, **overrides) -> Watchlist:
    """테스트용 Watchlist를 생성한다."""
    defaults = {
        "user_id": user_id,
        "company_id": company_id,
        "alert_types": '["new_disclosure", "reputation_change"]',
        "is_active": True,
    }
    defaults.update(overrides)
    watchlist = Watchlist(**defaults)
    db.add(watchlist)
    await db.commit()
    await db.refresh(watchlist)
    return watchlist


async def create_test_alert(db: AsyncSession, user_id: int, company_id: int, **overrides) -> AlertHistory:
    """테스트용 AlertHistory를 생성한다."""
    defaults = {
        "user_id": user_id,
        "company_id": company_id,
        "alert_type": AlertType.NEW_DISCLOSURE,
        "title": "새로운 공시가 등록되었습니다",
        "message": "테스트투자파트너스의 사업보고서가 등록되었습니다.",
        "is_read": False,
    }
    defaults.update(overrides)
    alert = AlertHistory(**defaults)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def create_test_disclosure(db: AsyncSession, **overrides) -> Disclosure:
    """테스트용 Disclosure를 생성한다."""
    rcept_no = overrides.get("rcept_no", "20250101000001")
    defaults = {
        "corp_code": "00100001",
        "corp_name": "테스트투자파트너스",
        "report_nm": "사업보고서 (2024.12)",
        "rcept_no": rcept_no,
        "rcept_dt": "20250101",
        "flr_nm": "테스트투자파트너스 주식회사",
        "dart_viewer_url": f"https://opendart.fss.or.kr/dsaf001/main.do?rcept_no={rcept_no}",
        "dart_pdf_url": f"https://opendart.fss.or.kr/dsaf001/saveasdocument.do?rcept_no={rcept_no}",
        "disclosure_type": "annual_report",
        "source": "dart",
    }
    defaults.update(overrides)
    disclosure = Disclosure(**defaults)
    db.add(disclosure)
    await db.commit()
    await db.refresh(disclosure)
    return disclosure
