"""Health check endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "deal-mgmt"
    assert data["migration_ok"] is True
    assert data["migration"]["ok"] is True
    assert data["migration"]["managed"] is False
    assert "ocr" in data
    assert "available" in data["ocr"]
    assert data["attachment_upload_schema_ok"] is True
    assert data["attachment_upload_schema"]["ok"] is True
    assert data["attachment_upload_schema"]["issues"] == []


@pytest.mark.asyncio
async def test_health_check_reports_degraded_attachment_upload_schema(client, monkeypatch: pytest.MonkeyPatch):
    from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult

    async def _probe_schema(**kwargs):
        return AttachmentUploadSchemaRepairResult(
            issues=(
                AttachmentUploadSchemaIssue(
                    table="attachments",
                    column="vdr_document_id",
                    reason="missing_column",
                    repairable=True,
                ),
            ),
            repaired=False,
            repair_attempted=False,
        )

    monkeypatch.setattr("app.core.local_dev_schema_guard.probe_attachment_upload_schema", _probe_schema)

    resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["migration_ok"] is False
    assert data["attachment_upload_schema_ok"] is False
    assert data["attachment_upload_schema"]["ok"] is False
    assert data["attachment_upload_schema"]["issues"] == [
        {
            "table": "attachments",
            "column": "vdr_document_id",
            "reason": "missing_column",
            "repairable": True,
        }
    ]


@pytest.mark.asyncio
async def test_health_check_reports_degraded_attachment_upload_schema_type_issue(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult

    async def _probe_schema(**kwargs):
        return AttachmentUploadSchemaRepairResult(
            issues=(
                AttachmentUploadSchemaIssue(
                    table="attachments",
                    column="entity_id",
                    reason="incompatible_type",
                    repairable=True,
                    expected_type="VARCHAR(50)",
                    actual_type="UUID",
                ),
            ),
            repaired=False,
            repair_attempted=False,
        )

    monkeypatch.setattr("app.core.local_dev_schema_guard.probe_attachment_upload_schema", _probe_schema)

    resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["migration_ok"] is False
    assert data["attachment_upload_schema_ok"] is False
    assert data["attachment_upload_schema"]["ok"] is False
    assert data["attachment_upload_schema"]["issues"] == [
        {
            "table": "attachments",
            "column": "entity_id",
            "reason": "incompatible_type",
            "repairable": True,
            "expected_type": "VARCHAR(50)",
            "actual_type": "UUID",
        }
    ]


@pytest.mark.asyncio
async def test_health_check_reports_degraded_migration_head_mismatch(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.core.attachment_upload_runtime_diagnostics import AttachmentUploadMigrationState

    async def _probe_migration(**kwargs):
        return AttachmentUploadMigrationState(
            ok=False,
            expected_heads=("095",),
            current_heads=("094",),
            managed=True,
        )

    monkeypatch.setattr(
        "app.core.attachment_upload_runtime_diagnostics.probe_attachment_upload_migration_state",
        _probe_migration,
    )

    resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["migration_ok"] is False
    assert data["migration"] == {
        "ok": False,
        "managed": True,
        "expected_heads": ["095"],
        "current_heads": ["094"],
    }
