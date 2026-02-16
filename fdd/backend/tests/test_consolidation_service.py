"""Consolidation Service 테스트 — Sprint 16.

멀티 엔티티 연결 분석 오케스트레이션 테스트 (DB 의존).
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models.account_mapping import (
    AccountMapping,
    MappingConfidence,
    MappingStatus,
)
from app.models.deal import Deal, DealStatus, DealType
from app.models.entity import Entity, EntityType
from app.models.exchange_rate import ExchangeRate, RateType
from app.models.journal_entry import JournalEntry
from app.models.upload import IngestionStatus, UploadFile, UploadType
from app.seeds.standard_coa_v1 import seed_standard_line_items
from app.services.consolidation.consolidation_service import run_consolidation

D = Decimal


@pytest.fixture(autouse=True)
def seed_coa(db: Session):
    """표준 라인아이템 시드."""
    seed_standard_line_items(db)


def _seed_deal(db: Session, base_currency: str = "KRW") -> Deal:
    deal = Deal(
        name="Consolidation Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency=base_currency,
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        status=DealStatus.ACTIVE,
    )
    db.add(deal)
    db.flush()
    return deal


def _seed_entity(
    db: Session,
    deal_id,
    entity_type: EntityType = EntityType.TARGET,
    code: str = "TARGET",
    currency: str = "KRW",
    ownership_pct: str = "100.0000",
    parent_id=None,
) -> Entity:
    entity = Entity(
        deal_id=deal_id,
        parent_entity_id=parent_id,
        entity_type=entity_type,
        name=f"Entity {code}",
        code=code,
        functional_currency=currency,
        ownership_pct=D(ownership_pct),
    )
    db.add(entity)
    db.flush()
    return entity


def _seed_upload(db: Session, deal_id) -> UploadFile:
    upload = UploadFile(
        deal_id=deal_id,
        original_filename="test_tb.xlsx",
        stored_path="/tmp/test_tb.xlsx",
        file_hash="hash123",
        file_size_bytes=1024,
        detected_type=UploadType.TB,
        confirmed_type=UploadType.TB,
        status=IngestionStatus.COMPLETED,
    )
    db.add(upload)
    db.flush()
    return upload


def _seed_tb_entry(
    db: Session,
    deal_id,
    upload_id,
    account_code: str,
    account_name: str,
    balance: str,
    currency: str = "KRW",
    entity_id=None,
    row_number: int = 1,
):
    je = JournalEntry(
        deal_id=deal_id,
        upload_file_id=upload_id,
        entity_id=entity_id,
        source_type="TB",
        row_number=row_number,
        account_code=account_code,
        account_name=account_name,
        balance=D(balance),
        currency=currency,
    )
    db.add(je)
    db.flush()
    return je


def _seed_mapping(
    db: Session,
    deal_id,
    source_code: str,
    source_name: str,
    target_code: str,
    affected_amount: str = "0",
):
    mapping = AccountMapping(
        deal_id=deal_id,
        source_account_code=source_code,
        source_account_name=source_name,
        target_line_item_code=target_code,
        status=MappingStatus.APPROVED,
        confidence=MappingConfidence.HIGH,
        affected_amount=D(affected_amount),
    )
    db.add(mapping)
    db.flush()
    return mapping


class TestRunConsolidation:
    """run_consolidation() 서비스 테스트."""

    def test_single_entity_target_only(self, db: Session):
        """단일 엔티티(TARGET) — subtotals == consolidated."""
        deal = _seed_deal(db)
        target = _seed_entity(db, deal.id)
        upload = _seed_upload(db, deal.id)

        _seed_tb_entry(
            db, deal.id, upload.id, "4100", "매출", "-50000000", entity_id=target.id
        )
        _seed_mapping(db, deal.id, "4100", "매출", "IS-REV-001")
        db.commit()

        result, evidence = run_consolidation(db, deal.id)

        assert "REVENUE" in result.consolidated_totals
        assert result.consolidated_totals["REVENUE"] == D("-50000000")
        assert result.minority_interest == D("0")
        assert len(evidence) >= 1

    def test_two_entities_same_currency(self, db: Session):
        """2개 엔티티, 동일 통화 (KRW) — FX 변환 없이 합산."""
        deal = _seed_deal(db)
        target = _seed_entity(db, deal.id, EntityType.TARGET, "TARGET", "KRW")
        sub1 = _seed_entity(
            db, deal.id, EntityType.SUBSIDIARY, "SUB1", "KRW", parent_id=target.id
        )
        upload = _seed_upload(db, deal.id)

        _seed_tb_entry(
            db,
            deal.id,
            upload.id,
            "4100",
            "매출",
            "-30000000",
            entity_id=target.id,
            row_number=1,
        )
        _seed_tb_entry(
            db,
            deal.id,
            upload.id,
            "4100",
            "매출",
            "-20000000",
            entity_id=sub1.id,
            row_number=2,
        )
        _seed_mapping(db, deal.id, "4100", "매출", "IS-REV-001")
        db.commit()

        result, _ = run_consolidation(db, deal.id)

        assert result.consolidated_totals["REVENUE"] == D("-50000000")
        assert "TARGET" in result.entity_subtotals
        assert "SUB1" in result.entity_subtotals

    def test_two_entities_different_currency(self, db: Session):
        """2개 엔티티 다른 통화 (KRW + USD) → FX 변환 적용."""
        deal = _seed_deal(db, base_currency="KRW")
        target = _seed_entity(db, deal.id, EntityType.TARGET, "TARGET", "KRW")
        sub_usd = _seed_entity(
            db, deal.id, EntityType.SUBSIDIARY, "SUB_USD", "USD", parent_id=target.id
        )
        upload = _seed_upload(db, deal.id)

        # TARGET: KRW 30M
        _seed_tb_entry(
            db, deal.id, upload.id, "4100", "매출", "-30000000", "KRW", target.id, 1
        )
        # SUB_USD: USD 10,000
        _seed_tb_entry(
            db, deal.id, upload.id, "4100", "Revenue", "-10000", "USD", sub_usd.id, 2
        )

        _seed_mapping(db, deal.id, "4100", "매출", "IS-REV-001")

        # FX rate: USD → KRW = 1300
        db.add(
            ExchangeRate(
                deal_id=deal.id,
                from_currency="USD",
                to_currency="KRW",
                rate_type=RateType.CLOSING,
                rate=D("1300.0000"),
                effective_date=date(2025, 12, 31),
            )
        )
        db.commit()

        result, _ = run_consolidation(db, deal.id)

        # TARGET: -30000000 + SUB_USD: -10000 * 1300 = -13000000
        # total = -43000000
        assert result.consolidated_totals["REVENUE"] == D("-43000000.0000")

    def test_with_ic_pairs(self, db: Session):
        """IC pairs 적용 → elimination_total > 0."""
        deal = _seed_deal(db)
        target = _seed_entity(db, deal.id, EntityType.TARGET, "TARGET", "KRW")
        sub1 = _seed_entity(
            db, deal.id, EntityType.SUBSIDIARY, "SUB1", "KRW", parent_id=target.id
        )
        upload = _seed_upload(db, deal.id)

        _seed_tb_entry(
            db,
            deal.id,
            upload.id,
            "1130",
            "매출채권",
            "10000000",
            entity_id=target.id,
            row_number=1,
        )
        _seed_tb_entry(
            db,
            deal.id,
            upload.id,
            "2110",
            "매입채무",
            "10000000",
            entity_id=sub1.id,
            row_number=2,
        )
        _seed_mapping(db, deal.id, "1130", "매출채권", "BS-AR-001")
        _seed_mapping(db, deal.id, "2110", "매입채무", "BS-AP-001")
        db.commit()

        ic_pairs = [("TARGET", "SUB1", "AR", D("5000000"))]
        result, _ = run_consolidation(db, deal.id, ic_pairs)

        assert result.elimination_total == D("5000000")
        assert len(result.eliminations) == 1

    def test_minority_interest(self, db: Session):
        """80% ownership → 소수지분 계산."""
        deal = _seed_deal(db)
        target = _seed_entity(db, deal.id, EntityType.TARGET, "TARGET", "KRW")
        sub1 = _seed_entity(
            db,
            deal.id,
            EntityType.SUBSIDIARY,
            "SUB1",
            "KRW",
            "80.0000",
            parent_id=target.id,
        )
        upload = _seed_upload(db, deal.id)

        _seed_tb_entry(
            db, deal.id, upload.id, "4100", "매출", "-100000000", entity_id=sub1.id
        )
        _seed_mapping(db, deal.id, "4100", "매출", "IS-REV-001")
        db.commit()

        result, _ = run_consolidation(db, deal.id)

        # MI = (-100000000) * (100-80)/100 = -20000000
        assert result.minority_interest == D("-20000000.0000")
        assert len(result.warnings) >= 1

    def test_deal_not_found_raises(self, db: Session):
        """Deal 미발견 → ValueError."""
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="Deal not found"):
            run_consolidation(db, fake_id)

    def test_no_entities_raises(self, db: Session):
        """엔티티 없음 → ValueError."""
        deal = _seed_deal(db)
        db.commit()

        with pytest.raises(ValueError, match="No active entities"):
            run_consolidation(db, deal.id)

    def test_consolidated_entity_type_excluded(self, db: Session):
        """CONSOLIDATED 타입 엔티티 제외."""
        deal = _seed_deal(db)
        target = _seed_entity(db, deal.id, EntityType.TARGET, "TARGET", "KRW")
        _seed_entity(db, deal.id, EntityType.CONSOLIDATED, "CONSOL", "KRW")
        upload = _seed_upload(db, deal.id)

        _seed_tb_entry(
            db, deal.id, upload.id, "4100", "매출", "-10000000", entity_id=target.id
        )
        _seed_mapping(db, deal.id, "4100", "매출", "IS-REV-001")
        db.commit()

        result, _ = run_consolidation(db, deal.id)

        # CONSOLIDATED entity should NOT appear in subtotals
        assert "CONSOL" not in result.entity_subtotals
        assert "TARGET" in result.entity_subtotals
