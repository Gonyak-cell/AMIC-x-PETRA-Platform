"""FX Service 테스트 — Sprint 16.

환율 조회, 변환, TB 일괄 환산 테스트.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import FDDError
from app.models.deal import Deal, DealStatus, DealType
from app.models.entity import Entity, EntityType
from app.models.exchange_rate import ExchangeRate, RateType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.services.fx.fx_service import (
    build_fx_converted_tb_map,
    convert_amount,
    get_rate,
)

D = Decimal


def _seed_deal(db: Session) -> Deal:
    deal = Deal(
        name="FX Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        status=DealStatus.ACTIVE,
    )
    db.add(deal)
    db.flush()
    return deal


def _seed_entity(db: Session, deal_id, currency: str = "USD") -> Entity:
    entity = Entity(
        deal_id=deal_id,
        entity_type=EntityType.SUBSIDIARY,
        name=f"Entity {currency}",
        code=f"ENT_{currency}",
        functional_currency=currency,
    )
    db.add(entity)
    db.flush()
    return entity


def _seed_rate(
    db: Session,
    deal_id,
    from_currency: str = "USD",
    to_currency: str = "KRW",
    rate: str = "1300.0000",
    rate_type: RateType = RateType.CLOSING,
    effective_date: date = date(2025, 12, 31),
    period_key: str | None = None,
) -> ExchangeRate:
    fx = ExchangeRate(
        deal_id=deal_id,
        from_currency=from_currency,
        to_currency=to_currency,
        rate_type=rate_type,
        rate=D(rate),
        effective_date=effective_date,
        period_key=period_key,
    )
    db.add(fx)
    db.flush()
    return fx


def _seed_upload(db: Session, deal_id) -> UploadFile:
    upload = UploadFile(
        deal_id=deal_id,
        original_filename="test_tb.xlsx",
        stored_path="/tmp/test_tb.xlsx",
        file_hash="abc123",
        file_size_bytes=1024,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()
    return upload


def _seed_journal_entry(
    db: Session,
    deal_id,
    upload_id,
    account_code: str,
    balance: str,
    currency: str = "USD",
    entity_id=None,
    row_number: int = 1,
) -> JournalEntry:
    je = JournalEntry(
        deal_id=deal_id,
        upload_file_id=upload_id,
        entity_id=entity_id,
        source_type="TB",
        row_number=row_number,
        account_code=account_code,
        account_name=f"Account {account_code}",
        balance=D(balance),
        currency=currency,
    )
    db.add(je)
    db.flush()
    return je


class TestGetRate:
    """get_rate() 테스트."""

    def test_basic_rate_lookup(self, db: Session):
        """기본 환율 조회."""
        deal = _seed_deal(db)
        _seed_rate(db, deal.id, "USD", "KRW", "1300.0000")
        db.commit()

        rate = get_rate(
            db,
            deal.id,
            "USD",
            "KRW",
            RateType.CLOSING,
            effective_date=date(2025, 12, 31),
        )
        assert rate == D("1300.0000")

    def test_same_currency_returns_one(self, db: Session):
        """동일 통화 → 1.0000 (DB 조회 없음)."""
        deal = _seed_deal(db)
        db.commit()

        rate = get_rate(db, deal.id, "KRW", "KRW", RateType.CLOSING)
        assert rate == D("1.0000")

    def test_rate_not_found_raises_fdd_error(self, db: Session):
        """환율 미발견 시 FDDError."""
        deal = _seed_deal(db)
        db.commit()

        with pytest.raises(FDDError) as exc_info:
            get_rate(
                db,
                deal.id,
                "EUR",
                "KRW",
                RateType.CLOSING,
                effective_date=date(2025, 12, 31),
            )
        assert "Exchange rate not found" in exc_info.value.detail

    def test_effective_date_selects_latest(self, db: Session):
        """effective_date 이전 중 최신 환율 선택."""
        deal = _seed_deal(db)
        _seed_rate(
            db, deal.id, "USD", "KRW", "1200.0000", effective_date=date(2025, 6, 30)
        )
        _seed_rate(
            db, deal.id, "USD", "KRW", "1300.0000", effective_date=date(2025, 12, 31)
        )
        db.commit()

        rate = get_rate(
            db,
            deal.id,
            "USD",
            "KRW",
            RateType.CLOSING,
            effective_date=date(2025, 12, 31),
        )
        assert rate == D("1300.0000")

    def test_average_rate_with_period_key(self, db: Session):
        """AVERAGE 환율 + period_key 필터."""
        deal = _seed_deal(db)
        _seed_rate(
            db,
            deal.id,
            "USD",
            "KRW",
            "1250.0000",
            rate_type=RateType.AVERAGE,
            effective_date=date(2025, 1, 31),
            period_key="2025-01",
        )
        db.commit()

        rate = get_rate(
            db,
            deal.id,
            "USD",
            "KRW",
            RateType.AVERAGE,
            period_key="2025-01",
        )
        assert rate == D("1250.0000")


class TestConvertAmount:
    """convert_amount() 테스트 (pure function)."""

    def test_basic_conversion(self):
        """기본 환산: 100 USD * 1300 = 130000 KRW."""
        result = convert_amount(D("100"), D("1300.0000"))
        assert result == D("130000.0000")

    def test_decimal_precision(self):
        """소수점 정밀도: 4자리까지."""
        result = convert_amount(D("100"), D("1300.5678"))
        assert result == D("130056.7800")

    def test_zero_amount(self):
        """0 금액 변환."""
        result = convert_amount(D("0"), D("1300.0000"))
        assert result == D("0.0000")

    def test_negative_amount(self):
        """음수 금액 (credit) 부호 보존."""
        result = convert_amount(D("-50000"), D("1300.0000"))
        assert result == D("-65000000.0000")


class TestBuildFxConvertedTbMap:
    """build_fx_converted_tb_map() 테스트."""

    def test_same_currency_no_conversion(self, db: Session):
        """동일 통화 → 변환 없이 원래 금액."""
        deal = _seed_deal(db)
        upload = _seed_upload(db, deal.id)
        _seed_journal_entry(db, deal.id, upload.id, "1110", "10000000", "KRW")
        db.commit()

        result = build_fx_converted_tb_map(
            db,
            deal.id,
            target_currency="KRW",
        )
        assert result["1110"] == D("10000000")

    def test_currency_conversion(self, db: Session):
        """USD → KRW 변환 적용."""
        deal = _seed_deal(db)
        entity = _seed_entity(db, deal.id, "USD")
        upload = _seed_upload(db, deal.id)
        _seed_rate(db, deal.id, "USD", "KRW", "1300.0000")
        _seed_journal_entry(
            db,
            deal.id,
            upload.id,
            "1110",
            "10000",
            "USD",
            entity_id=entity.id,
        )
        db.commit()

        result = build_fx_converted_tb_map(
            db,
            deal.id,
            target_currency="KRW",
            reference_date=date(2025, 12, 31),
            entity_id=entity.id,
        )
        assert result["1110"] == D("13000000.0000")

    def test_missing_rate_raises_error(self, db: Session):
        """변환 환율 없으면 FDDError."""
        deal = _seed_deal(db)
        upload = _seed_upload(db, deal.id)
        _seed_journal_entry(db, deal.id, upload.id, "1110", "10000", "EUR")
        db.commit()

        with pytest.raises(FDDError):
            build_fx_converted_tb_map(
                db,
                deal.id,
                target_currency="KRW",
                reference_date=date(2025, 12, 31),
            )

    def test_aggregates_multiple_entries(self, db: Session):
        """동일 account_code 복수 항목 합산."""
        deal = _seed_deal(db)
        upload = _seed_upload(db, deal.id)
        _seed_journal_entry(
            db, deal.id, upload.id, "1110", "5000000", "KRW", row_number=1
        )
        _seed_journal_entry(
            db, deal.id, upload.id, "1110", "3000000", "KRW", row_number=2
        )
        db.commit()

        result = build_fx_converted_tb_map(
            db,
            deal.id,
            target_currency="KRW",
        )
        assert result["1110"] == D("8000000")
