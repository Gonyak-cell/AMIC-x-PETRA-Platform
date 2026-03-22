from __future__ import annotations

import uuid

from app.models.deal import Deal, DealType
from app.models.evidence import EvidenceLink, SourceType
from app.models.upload import UploadFile


def test_evidence_export_returns_normalized_records(client, db):
    deal = Deal(
        name="FDD Export Test",
        target_company_name="Target Co",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        created_by="system",
    )
    db.add(deal)
    db.flush()

    upload = UploadFile(
        deal_id=deal.id,
        original_filename="Revenue Bridge.xlsx",
        stored_path="uploads/revenue-bridge.xlsx",
        file_hash="abc123",
        file_size_bytes=1024,
        uploaded_by="system",
    )
    db.add(upload)
    db.flush()

    target_id = uuid.uuid4()
    db.add(
        EvidenceLink(
            deal_id=deal.id,
            target_type="qoe_calculation",
            target_id=target_id,
            source_type=SourceType.FILE,
            source_id=str(upload.id),
            source_detail={
                "sheet": "Bridge",
                "row": 12,
                "chunk_id": "bridge-r12",
            },
            transaction_id="txn-1",
            engine_version="0.15.1",
        )
    )
    db.commit()

    response = client.get(f"/api/v1/deals/{deal.id}/evidence-export")

    assert response.status_code == 200
    payload = response.json()
    assert payload["artifact_type"] == "FDD_REPORT"
    assert payload["default_workstream"] == "FDD"
    assert payload["external_artifact_ref"] == f"fdd-deal-{deal.id}"
    assert payload["artifact_id"] is None
    assert len(payload["records"]) == 1

    record = payload["records"][0]
    assert record["workstream"] == "FDD"
    assert record["section_type"] == "QOE"
    assert record["item_id"] == str(target_id)
    assert record["original_name"] == "Revenue Bridge.xlsx"
    assert record["evidence_kind"] == "uploaded_file"
    assert record["directness"] == "DIRECT"
    assert record["source_page"] == "Bridge:12"
    assert record["analysis_phase"] == "DRAFT"
    assert record["chunk_id"] == "bridge-r12"
