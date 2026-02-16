"""Evidence Index 테스트 — FDD-1401."""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.deal import Deal, DealType
from app.models.evidence import EvidenceLink, SourceType
from app.services.evidence.index_builder import (
    build_evidence_index,
    get_evidence_coverage_stats,
    map_evidence_to_report_sections,
)


def _create_deal(db: Session) -> Deal:
    deal = Deal(
        name="Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
        reference_date=date(2025, 12, 31),
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
    )
    db.add(deal)
    db.flush()
    return deal


def _create_evidence_links(db: Session, deal_id: uuid.UUID, count: int = 3):
    for i in range(count):
        link = EvidenceLink(
            deal_id=deal_id,
            target_type="qoe_adjustment" if i % 2 == 0 else "nwc_item",
            target_id=uuid.uuid4(),
            source_type=SourceType.TB if i % 2 == 0 else SourceType.GL,
            source_id=f"src-{i}",
        )
        db.add(link)
    db.commit()


def test_build_evidence_index_empty(db: Session):
    deal = _create_deal(db)
    db.commit()
    index = build_evidence_index(db, deal.id)
    assert index.total_count == 0
    assert index.entries == []


def test_build_evidence_index(db: Session):
    deal = _create_deal(db)
    db.commit()
    _create_evidence_links(db, deal.id, 5)

    index = build_evidence_index(db, deal.id)
    assert index.total_count == 5
    assert index.deal_id == str(deal.id)
    assert "TB" in index.by_source_type or "GL" in index.by_source_type
    assert (
        "qoe_adjustment" in index.by_target_type or "nwc_item" in index.by_target_type
    )


def test_build_evidence_index_by_source_type(db: Session):
    deal = _create_deal(db)
    db.commit()
    _create_evidence_links(db, deal.id, 4)

    index = build_evidence_index(db, deal.id)
    total_by_source = sum(index.by_source_type.values())
    assert total_by_source == index.total_count


def test_map_evidence_to_sections(db: Session):
    deal = _create_deal(db)
    db.commit()
    _create_evidence_links(db, deal.id, 4)

    index = build_evidence_index(db, deal.id)
    mapping = {"qoe_adjustment": "section-qoe", "nwc_item": "section-nwc"}
    mapped = map_evidence_to_report_sections(index, mapping)

    for entry in mapped.entries:
        if entry.target_type in mapping:
            assert len(entry.referenced_in) > 0
            assert entry.referenced_in[0].section_id == mapping[entry.target_type]


def test_evidence_coverage_stats(db: Session):
    deal = _create_deal(db)
    db.commit()
    _create_evidence_links(db, deal.id, 6)

    stats = get_evidence_coverage_stats(db, deal.id)
    assert stats["total_evidence_links"] == 6
    assert "by_target_type" in stats
    assert "by_source_type" in stats


def test_evidence_coverage_empty(db: Session):
    deal = _create_deal(db)
    db.commit()
    stats = get_evidence_coverage_stats(db, deal.id)
    assert stats["total_evidence_links"] == 0


def test_evidence_index_api(client, db):
    deal = _create_deal(db)
    db.commit()
    _create_evidence_links(db, deal.id, 3)

    resp = client.get(f"/api/v1/deals/{deal.id}/evidence-index")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 3
    assert len(data["entries"]) == 3


def test_evidence_coverage_api(client, db):
    deal = _create_deal(db)
    db.commit()

    resp = client.get(f"/api/v1/deals/{deal.id}/evidence-coverage")
    assert resp.status_code == 200
    assert resp.json()["total_evidence_links"] == 0
