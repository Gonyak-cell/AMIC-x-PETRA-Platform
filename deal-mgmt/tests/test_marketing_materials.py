"""마케팅 자료 API 테스트 (TM / DM / IM PPTX)."""

import pytest

from app.core.security import get_jwt_claims
from app.main import app
from tests.conftest import _override_get_jwt_claims, make_claims

SAMPLE_TXN = {
    "name": "마케팅자료 테스트 거래",
    "deal_type": "SE",
    "side": "SELL",
    "target_company_name": "테스트 대상기업",
    "client_name": "테스트 의뢰기업",
    "lead_advisor_email": "test@example.com",
}

TM_BODY = {
    "doc_type": "TM",
    "title": "Project Alpha — Teaser Memo",
    "project_code": "ALPHA",
}

DM_BODY = {
    "doc_type": "DM",
    "title": "Project Alpha — Discussion Memo (가격 협의)",
    "project_code": "ALPHA",
}

IM_BODY = {
    "doc_type": "IM",
    "title": "Project Alpha — Information Memorandum",
    "project_code": "ALPHA",
}

CUSTOM_CONTENT = {
    "project_name": "PROJECT ALPHA",
    "memo_type": "Teaser Memo",
    "date": "March 2026",
    "company_name": "주식회사 페트라브릿지파트너스",
    "disclaimer": "본 자료는 기밀입니다.",
    "contact": "AMIC × PETRA",
    "slides": [
        {
            "layout": "MAIN",
            "title": "Investment Highlights",
            "body": [
                {
                    "type": "bullet",
                    "items": ["강점 1", "강점 2", "강점 3"],
                }
            ],
        }
    ],
}


@pytest.fixture
async def _txn(client):
    """테스트용 거래 생성 — conftest JWT 이메일과 일치."""
    resp = await client.post("/api/v1/transactions", json=SAMPLE_TXN)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
async def _other_txn(client):
    """격리 테스트용 두 번째 거래."""
    resp = await client.post(
        "/api/v1/transactions",
        json={
            **SAMPLE_TXN,
            "name": "격리 테스트 거래",
            "deal_type": "SE",
            "lead_advisor_email": "test@example.com",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _set_claims(*, role: str, email: str) -> None:
    async def _override():
        return make_claims(role=role, email=email)

    app.dependency_overrides[get_jwt_claims] = _override


def _restore_claims() -> None:
    app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims


@pytest.mark.asyncio
async def test_list_marketing_materials_empty(client, _txn):
    """빈 마케팅 자료 목록 조회."""
    txn_id = _txn["id"]
    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_preview_marketing_material_source_routing_empty(client, _txn):
    """VDR 臾몄꽌媛 ?놁쑝硫?留덉????먮즺 source preview媛 鍮?寃곌낵瑜?諛섑솚?쒕떎."""
    txn_id = _txn["id"]
    resp = await client.get(
        f"/api/v1/transactions/{txn_id}/marketing-materials/source-routing-preview",
        params={"doc_type": "IM"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["target_workstreams"] == ["COMMON", "VALUATION", "FDD"]
    assert data["summary"]["total_documents"] == 0
    assert data["summary"]["included_for_marketing_material"] == 0
    assert data["summary"]["excluded_from_marketing_material"] == 0
    assert data["documents"] == []


@pytest.mark.asyncio
async def test_list_marketing_materials_allows_internal_workspace_user(client, _txn):
    """리드 어드바이저가 아닌 내부 사용자도 워크스페이스 기준으로 조회 가능해야 한다."""
    txn_id = _txn["id"]
    _set_claims(role="ANALYST", email="teammate@amic.kr")
    try:
        resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials")
    finally:
        _restore_claims()

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_tm(client, _txn):
    """TM 생성 — GENERATING 상태로 즉시 반환."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "TM"
    assert data["title"] == TM_BODY["title"]
    assert data["project_code"] == "ALPHA"
    assert data["status"] == "GENERATING"
    assert data["transaction_id"] == txn_id


@pytest.mark.asyncio
async def test_create_dm(client, _txn):
    """DM 생성."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=DM_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "DM"


@pytest.mark.asyncio
async def test_create_im(client, _txn):
    """IM 생성."""
    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=IM_BODY,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "IM"


@pytest.mark.asyncio
async def test_create_tm_marks_material_failed_when_task_queue_is_unavailable(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from app.tasks import marketing_tasks

    def _raise_queue_error(*args, **kwargs):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(marketing_tasks.generate_pptx_task, "delay", _raise_queue_error)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "TM"
    assert data["status"] == "FAILED"
    assert "작업 큐" in data["error_message"]


@pytest.mark.asyncio
async def test_upload_tm_creates_material_and_bound_attachment(
    client,
    _txn,
    async_session,
):
    import uuid

    from sqlalchemy import select

    from app.models.attachment import Attachment
    from app.models.marketing_material import MarketingMaterial

    txn_id = _txn["id"]
    pdf_bytes = b"%PDF-1.4\nuploaded teaser\n"

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Uploaded teaser memo",
            "distributed_to": "Buyer A",
            "distributed_at": "2026-03-01T09:00:00+09:00",
        },
        files={"file": ("uploaded-tm.pdf", pdf_bytes, "application/pdf")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "TM"
    assert data["source_mode"] == "UPLOADED"
    assert data["status"] == "READY"
    assert data["attachment_id"] is not None

    material_result = await async_session.execute(
        select(MarketingMaterial).where(MarketingMaterial.id == uuid.UUID(data["id"]))
    )
    material = material_result.scalar_one()
    assert material.attachment_id is not None

    attachment_result = await async_session.execute(select(Attachment).where(Attachment.id == material.attachment_id))
    attachment = attachment_result.scalar_one()
    assert attachment.entity_type == "MARKETING_MATERIAL"
    assert attachment.entity_id == str(material.id)


@pytest.mark.asyncio
async def test_upload_tm_allows_multi_dot_filename(
    client,
    _txn,
):
    txn_id = _txn["id"]
    pdf_bytes = b"%PDF-1.4\nuploaded teaser\n"

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Uploaded teaser memo",
        },
        files={"file": ("uploaded.tm.v1.pdf", pdf_bytes, "application/pdf")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "TM"
    assert data["file_name"] == "uploaded.tm.v1.pdf"


@pytest.mark.asyncio
async def test_upload_tm_truncates_overlong_filename_for_legacy_backend_limits(
    client,
    _txn,
    async_session,
):
    import uuid
    from pathlib import Path

    from sqlalchemy import select

    from app.models.attachment import Attachment
    from app.services import marketing_material_service

    txn_id = _txn["id"]
    pdf_bytes = b"%PDF-1.4\nuploaded teaser\n"
    original_name = f"{'a' * 280}.pdf"

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Uploaded teaser memo",
        },
        files={"file": (original_name, pdf_bytes, "application/pdf")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["file_name"].endswith(".pdf")
    assert len(data["file_name"]) <= marketing_material_service.LEGACY_COMPAT_ATTACHMENT_FILE_NAME_MAX_LEN
    assert data["file_name"] != original_name
    assert (
        len(Path(data["file_path"]).name.encode()) <= marketing_material_service.ATTACHMENT_STORAGE_BASENAME_MAX_BYTES
    )

    attachment_result = await async_session.execute(
        select(Attachment).where(Attachment.id == uuid.UUID(data["attachment_id"]))
    )
    attachment = attachment_result.scalar_one()
    assert attachment.file_name == data["file_name"]


@pytest.mark.asyncio
async def test_upload_tm_rejects_disallowed_final_extension_in_multi_dot_filename(
    client,
    _txn,
):
    txn_id = _txn["id"]

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Uploaded teaser memo",
        },
        files={
            "file": (
                "uploaded.tm.v1.pdf.exe",
                b"MZ fake executable content",
                "application/octet-stream",
            )
        },
    )

    assert resp.status_code == 400
    assert "Unsupported file type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_tm_rolls_back_when_material_finalize_fails(
    client,
    _txn,
    async_session,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy import select

    from app.models.attachment import Attachment
    from app.models.marketing_material import MarketingMaterial
    from app.services import marketing_material_service

    def _raise_finalize(*args, **kwargs):
        raise RuntimeError("finalize failed")

    monkeypatch.setattr(
        marketing_material_service,
        "_apply_uploaded_material_fields",
        _raise_finalize,
    )

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Broken teaser memo",
        },
        files={"file": ("broken-teaser.pdf", b"%PDF-1.4\nbroken teaser\n", "application/pdf")},
    )

    assert resp.status_code == 500
    assert "material_finalize" in resp.json()["detail"]

    material_result = await async_session.execute(
        select(MarketingMaterial).where(MarketingMaterial.title == "Broken teaser memo")
    )
    assert material_result.scalars().first() is None

    attachment_result = await async_session.execute(
        select(Attachment).where(Attachment.file_name == "broken-teaser.pdf")
    )
    assert attachment_result.scalars().first() is None


@pytest.mark.asyncio
async def test_upload_tm_reports_stale_local_sqlite_schema_with_restart_hint(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    import sqlite3

    from sqlalchemy.exc import OperationalError

    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    async def _flush_with_stale_attachment_schema(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise OperationalError(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                sqlite3.OperationalError("table attachments has no column named processing_status"),
            )
        return await original_flush(self, *args, **kwargs)

    stale_db_url = f"sqlite+aiosqlite:///{(tmp_path / 'deal_mgmt_dev.db').as_posix()}"
    monkeypatch.setattr(marketing_material_service.settings, "DATABASE_URL", stale_db_url)
    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_stale_attachment_schema)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Uploaded teaser memo",
        },
        files={"file": ("uploaded-tm.pdf", b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "attachment_db_flush" in detail
    assert "Local SQLite dev database is stale" in detail
    assert "run_dev_server.py" in detail
    assert resp.headers["x-request-id"] in detail


@pytest.mark.asyncio
async def test_upload_tm_retries_after_backend_attachment_schema_repair(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import ProgrammingError

    from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult
    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    class _FakeOrigError(Exception):
        sqlstate = "42703"

        def __str__(self):
            return 'column "vdr_document_id" of relation "attachments" does not exist'

    async def _flush_with_single_schema_failure(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise ProgrammingError(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                _FakeOrigError(),
            )
        return await original_flush(self, *args, **kwargs)

    async def _repair_schema(**kwargs):
        return AttachmentUploadSchemaRepairResult(
            issues=(
                AttachmentUploadSchemaIssue(
                    table="attachments",
                    column="vdr_document_id",
                    reason="missing_column",
                    repairable=True,
                ),
            ),
            repaired=True,
            repair_attempted=True,
        )

    monkeypatch.setattr(
        marketing_material_service.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )
    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_single_schema_failure)
    monkeypatch.setattr(marketing_material_service, "repair_attachment_upload_schema_if_needed", _repair_schema)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Recovered teaser memo",
        },
        files={"file": ("recovered-tm.pdf", b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Recovered teaser memo"
    assert data["source_mode"] == "UPLOADED"


@pytest.mark.asyncio
async def test_upload_tm_reports_backend_migration_hint_when_attachment_schema_repair_fails(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import ProgrammingError

    from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult
    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    class _FakeOrigError(Exception):
        sqlstate = "42703"

        def __str__(self):
            return 'column "vdr_document_id" of relation "attachments" does not exist'

    async def _flush_with_persistent_schema_failure(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise ProgrammingError(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                _FakeOrigError(),
            )
        return await original_flush(self, *args, **kwargs)

    async def _repair_schema(**kwargs):
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
            repair_attempted=True,
        )

    monkeypatch.setattr(
        marketing_material_service.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )
    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_persistent_schema_failure)
    monkeypatch.setattr(marketing_material_service, "repair_attachment_upload_schema_if_needed", _repair_schema)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Broken teaser memo",
        },
        files={"file": ("broken-tm.pdf", b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "attachment_db_flush" in detail
    assert "alembic upgrade head" in detail
    assert "attachments.vdr_document_id" in detail
    assert resp.headers["x-request-id"] in detail


@pytest.mark.asyncio
async def test_upload_tm_retries_after_backend_attachment_entity_id_type_repair(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import ProgrammingError

    from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult
    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    class _FakeOrigError(Exception):
        sqlstate = "42804"

        def __str__(self):
            return 'column "entity_id" is of type uuid but expression is of type character varying'

    async def _flush_with_entity_id_type_failure(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise ProgrammingError(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                _FakeOrigError(),
            )
        return await original_flush(self, *args, **kwargs)

    async def _repair_schema(**kwargs):
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
            repaired=True,
            repair_attempted=True,
        )

    monkeypatch.setattr(
        marketing_material_service.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )
    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_entity_id_type_failure)
    monkeypatch.setattr(marketing_material_service, "repair_attachment_upload_schema_if_needed", _repair_schema)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Recovered teaser memo",
        },
        files={"file": ("recovered-tm.pdf", b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Recovered teaser memo"
    assert data["source_mode"] == "UPLOADED"


@pytest.mark.asyncio
async def test_upload_tm_reports_backend_entity_id_type_migration_hint_when_repair_fails(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import ProgrammingError

    from app.core.local_dev_schema_guard import AttachmentUploadSchemaIssue, AttachmentUploadSchemaRepairResult
    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    class _FakeOrigError(Exception):
        sqlstate = "42804"

        def __str__(self):
            return 'column "entity_id" is of type uuid but expression is of type character varying'

    async def _flush_with_entity_id_type_failure(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise ProgrammingError(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                _FakeOrigError(),
            )
        return await original_flush(self, *args, **kwargs)

    async def _repair_schema(**kwargs):
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
            repair_attempted=True,
        )

    monkeypatch.setattr(
        marketing_material_service.settings,
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost:5432/deal_mgmt",
    )
    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_entity_id_type_failure)
    monkeypatch.setattr(marketing_material_service, "repair_attachment_upload_schema_if_needed", _repair_schema)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Broken teaser memo",
        },
        files={"file": ("broken-tm.pdf", b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "attachment_db_flush" in detail
    assert "alembic upgrade head" in detail
    assert "attachments.entity_id" in detail
    assert "incompatible database type" in detail
    assert "Expected VARCHAR(50)." in detail
    assert resp.headers["x-request-id"] in detail


@pytest.mark.asyncio
async def test_upload_tm_reports_backend_length_limit_hint_for_attachment_value_overflow(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import DataError

    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    class _FakeOrigError(Exception):
        sqlstate = "22001"

        def __str__(self):
            return "value too long for type character varying(60)"

    async def _flush_with_legacy_length_overflow(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise DataError(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                _FakeOrigError(),
            )
        return await original_flush(self, *args, **kwargs)

    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_legacy_length_overflow)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Broken teaser memo",
        },
        files={"file": ((f"{'b' * 100}.pdf"), b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "attachment_db_flush" in detail
    assert "Uploaded file name exceeded backend length limits." in detail
    assert "Backend limit is 60 characters." in detail
    assert "Shorten the file name and retry." in detail
    assert resp.headers["x-request-id"] in detail


@pytest.mark.asyncio
async def test_upload_tm_reports_backend_length_limit_hint_for_asyncpg_dbapi_overflow(
    client,
    _txn,
    monkeypatch: pytest.MonkeyPatch,
):
    from sqlalchemy.exc import DBAPIError

    from app.services import marketing_material_service

    original_flush = marketing_material_service.AsyncSession.flush
    flush_calls = 0

    _FakeAsyncpgDbapiError = type(
        "Error",
        (Exception,),
        {
            "sqlstate": "22001",
            "__str__": lambda self: "value too long for type character varying(60)",
        },
    )

    async def _flush_with_asyncpg_length_overflow(self, *args, **kwargs):
        nonlocal flush_calls
        flush_calls += 1
        if flush_calls == 2:
            raise DBAPIError.instance(
                "INSERT INTO attachments (...) VALUES (...)",
                {},
                _FakeAsyncpgDbapiError(),
                Exception,
            )
        return await original_flush(self, *args, **kwargs)

    monkeypatch.setattr(marketing_material_service.AsyncSession, "flush", _flush_with_asyncpg_length_overflow)

    txn_id = _txn["id"]
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials/uploaded",
        data={
            "doc_type": "TM",
            "title": "Broken teaser memo",
        },
        files={"file": ((f"{'c' * 100}.pdf"), b"%PDF-1.4\nuploaded teaser\n", "application/pdf")},
    )

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "attachment_db_flush" in detail
    assert "Uploaded file name exceeded backend length limits." in detail
    assert "Backend limit is 60 characters." in detail
    assert "Shorten the file name and retry." in detail
    assert resp.headers["x-request-id"] in detail


@pytest.mark.asyncio
async def test_create_uploaded_tm_registers_attachment_without_queue(
    client,
    _txn,
    async_session,
    monkeypatch: pytest.MonkeyPatch,
):
    import uuid
    from pathlib import Path

    from app.models.attachment import Attachment
    from app.tasks import marketing_tasks

    def _raise_if_called(*args, **kwargs):
        raise AssertionError("queue should not be used for uploaded marketing materials")

    monkeypatch.setattr(marketing_tasks.generate_pptx_task, "delay", _raise_if_called)

    txn_id = _txn["id"]
    pdf_bytes = b"%PDF-1.4\nuploaded teaser\n"
    upload_dir = Path(__file__).resolve().parents[1] / "uploads" / "attachments"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{uuid.uuid4()}_uploaded-tm.pdf"
    file_path.write_bytes(pdf_bytes)

    attachment = Attachment(
        transaction_id=uuid.UUID(txn_id),
        entity_type="MARKETING_MATERIAL",
        entity_id=None,
        file_path=str(file_path),
        file_name="uploaded-tm.pdf",
        file_size_bytes=len(pdf_bytes),
        mime_type="application/pdf",
        uploaded_by_email="test@example.com",
    )
    async_session.add(attachment)
    await async_session.commit()
    await async_session.refresh(attachment)

    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json={
            **TM_BODY,
            "title": "Uploaded teaser memo",
            "attachment_id": str(attachment.id),
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["doc_type"] == "TM"
    assert data["status"] == "READY"
    assert data["source_mode"] == "UPLOADED"
    assert data["attachment_id"] == str(attachment.id)
    assert data["file_name"] == "uploaded-tm.pdf"
    assert data["quality_status"] == "SKIPPED"


@pytest.mark.asyncio
async def test_create_with_custom_content(client, _txn):
    """커스텀 콘텐츠 파라미터로 TM 생성."""
    txn_id = _txn["id"]
    body = {**TM_BODY, "parameters": CUSTOM_CONTENT}
    resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=body,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["parameters"] is not None


@pytest.mark.asyncio
async def test_get_marketing_material(client, _txn):
    """단건 조회."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == mat_id


@pytest.mark.asyncio
async def test_get_marketing_material_not_found(client, _txn):
    """존재하지 않는 자료 조회 — 404."""
    txn_id = _txn["id"]
    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_marketing_materials(client, _txn):
    """생성 후 목록 조회."""
    txn_id = _txn["id"]
    await client.post(f"/api/v1/transactions/{txn_id}/marketing-materials", json=TM_BODY)
    await client.post(f"/api/v1/transactions/{txn_id}/marketing-materials", json=DM_BODY)

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2


@pytest.mark.asyncio
async def test_update_distribution(client, _txn, async_session):
    """배포 대상 목록 업데이트 — READY 상태 + 파일 존재 시에만 허용."""
    from app.models.enums import MarketingDocStatus
    from app.models.marketing_material import MarketingMaterial

    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    # GENERATING → READY + 실제 임시 파일 생성 (배포 사전조건 충족)
    import tempfile
    import uuid

    from sqlalchemy import select

    with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as tmp:
        tmp.write(b"fake-pptx-content")

    result = await async_session.execute(select(MarketingMaterial).where(MarketingMaterial.id == uuid.UUID(mat_id)))
    mat = result.scalar_one()
    mat.status = MarketingDocStatus.READY
    mat.file_path = tmp.name
    mat.file_name = "test_memo.pptx"
    mat.file_size_bytes = 1024
    mat.quality_status = "PASS"
    await async_session.commit()

    dist_body = {
        "distributed_to": ["A투자사", "B펀드", "c@example.com"],
        "distributed_at": "2026-03-01T09:00:00+09:00",
    }
    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/distribute",
        json=dist_body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["distributed_to"]) == set(dist_body["distributed_to"])
    assert data["distributed_at"] == dist_body["distributed_at"]


@pytest.mark.asyncio
async def test_update_distribution_not_ready(client, _txn):
    """READY 아닌 상태에서 배포 시도 → 404."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    dist_body = {
        "distributed_to": ["A투자사"],
        "distributed_at": "2026-03-01T09:00:00+09:00",
    }
    resp = await client.put(
        f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/distribute",
        json=dist_body,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_marketing_material(client, _txn):
    """자료 삭제 — 204."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_download_not_ready(client, _txn):
    """GENERATING 상태 자료 다운로드 시도 — 409."""
    txn_id = _txn["id"]
    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/download")
    # GENERATING 상태이므로 409
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_download_uploaded_marketing_material(client, _txn, async_session):
    """업로드형 마케팅자료는 attachment 원본 PDF를 내려준다."""
    import uuid
    from pathlib import Path

    from app.models.attachment import Attachment
    from app.models.enums import MarketingDocStatus, MarketingDocType
    from app.models.marketing_material import MarketingMaterial

    txn_id = _txn["id"]
    pdf_bytes = b"%PDF-1.4\nuploaded marketing material\n"
    upload_dir = Path(__file__).resolve().parents[1] / "uploads" / "attachments"
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{uuid.uuid4()}_uploaded-im.pdf"
    file_path.write_bytes(pdf_bytes)

    attachment = Attachment(
        transaction_id=uuid.UUID(txn_id),
        entity_type="MARKETING_MATERIAL",
        entity_id="IM",
        file_path=str(file_path),
        file_name="uploaded-im.pdf",
        file_size_bytes=len(pdf_bytes),
        mime_type="application/pdf",
        uploaded_by_email="test@example.com",
    )
    async_session.add(attachment)
    await async_session.flush()

    material = MarketingMaterial(
        transaction_id=uuid.UUID(txn_id),
        doc_type=MarketingDocType.IM,
        title="Uploaded IM",
        status=MarketingDocStatus.READY,
        source_mode="UPLOADED",
        attachment_id=attachment.id,
        file_path=str(file_path),
        file_name="uploaded-im.pdf",
        file_size_bytes=len(pdf_bytes),
        quality_status="SKIPPED",
    )
    async_session.add(material)
    await async_session.commit()

    resp = await client.get(f"/api/v1/transactions/{txn_id}/marketing-materials/{material.id}/download")
    assert resp.status_code == 200
    assert resp.content == pdf_bytes
    assert resp.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_cross_transaction_isolation(client, _txn, _other_txn):
    """다른 거래의 자료는 접근 불가 — 404."""
    txn_id = _txn["id"]
    other_txn_id = _other_txn["id"]

    create_resp = await client.post(
        f"/api/v1/transactions/{txn_id}/marketing-materials",
        json=TM_BODY,
    )
    mat_id = create_resp.json()["id"]

    # 다른 거래 ID로 접근
    resp = await client.get(f"/api/v1/transactions/{other_txn_id}/marketing-materials/{mat_id}")
    assert resp.status_code == 404
