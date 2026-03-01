"""CLIENT 역할 RBAC 테스트 + remove_buyer CASCADE 감사 추적 테스트.

CLIENT 역할:
- 자기 딜 GET → 200
- 남의 딜 GET → 403
- 쓰기(POST/PATCH/DELETE) → 403

CASCADE 감사 추적:
- remove_buyer 시 마케팅 로그/컨소시엄 매핑 건수가 notes에 기록되는지 검증
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, insert
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

from app.core.database import get_db
from app.core.security import JWTClaims, get_jwt_claims
from app.main import app
from app.models import Base
from app.models.deal_client import DealClient

# ── Test DB engine ─────────────────────────────────────────

_test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False,
    poolclass=StaticPool,
)

_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@event.listens_for(_test_engine.sync_engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ── Claims ────────────────────────────────────────────────

CLIENT_CLAIMS = JWTClaims(
    user_id="client-user-id",
    email="client@investor.com",
    role="CLIENT",
)

ADMIN_CLAIMS = JWTClaims(
    user_id="admin-user-id",
    email="admin@amic.kr",
    role="ADMIN",
)

SAMPLE_TXN = {
    "name": "프로젝트 클라이언트",
    "code_name": "CLIENT-001",
    "side": "SELL",
    "target_company_name": "대상기업",
    "client_name": "의뢰기업",
    "lead_advisor_email": "advisor@example.com",
}


# ── Claims 전환 ───────────────────────────────────────────

_current_claims = ADMIN_CLAIMS


def _set_claims(claims: JWTClaims) -> None:
    """테스트 중 JWT claims를 전환한다."""
    global _current_claims
    _current_claims = claims


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


async def _override_get_jwt_claims() -> JWTClaims:
    return _current_claims


# ── Fixtures ─────────────────────────────────────────────


@pytest.fixture(autouse=True)
async def setup_database():
    """DB 테이블 생성/삭제 + 의존성 오버라이드."""
    _set_claims(ADMIN_CLAIMS)

    original_db = app.dependency_overrides.get(get_db)
    original_auth = app.dependency_overrides.get(get_jwt_claims)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_jwt_claims] = _override_get_jwt_claims

    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # 원복
    if original_db is not None:
        app.dependency_overrides[get_db] = original_db
    else:
        app.dependency_overrides.pop(get_db, None)
    if original_auth is not None:
        app.dependency_overrides[get_jwt_claims] = original_auth
    else:
        app.dependency_overrides.pop(get_jwt_claims, None)


@pytest.fixture
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP 클라이언트 — claims 전환은 _set_claims()로."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def async_session() -> AsyncGenerator[AsyncSession, None]:
    async with _test_session_factory() as session:
        yield session


# ── 헬퍼 ─────────────────────────────────────────────────


async def _create_txn(client: AsyncClient, **overrides) -> str:
    body = {**SAMPLE_TXN, **overrides}
    resp = await client.post("/api/v1/transactions", json=body)
    assert resp.status_code == 201
    return resp.json()["id"]


async def _add_buyer(client: AsyncClient, txn_id: str, **overrides) -> dict:
    body = {"company_name": "기본기업", "buyer_type": "STRATEGIC", **overrides}
    resp = await client.post(f"/api/v1/transactions/{txn_id}/buyers", json=body)
    assert resp.status_code == 201
    return resp.json()


async def _grant_deal_access(
    session: AsyncSession,
    txn_id: str,
    email: str,
) -> None:
    """DealClient 매핑을 생성하여 CLIENT 역할의 딜 접근 권한을 부여."""
    await session.execute(
        insert(DealClient).values(
            id=uuid.uuid4(),
            transaction_id=uuid.UUID(txn_id),
            email=email,
            display_name="테스트 클라이언트",
        )
    )
    await session.commit()


# ═════════════════════════════════════════════════════════
# CLIENT 역할 RBAC 테스트
# ═════════════════════════════════════════════════════════


class TestClientReadAccess:
    """CLIENT 역할의 읽기 접근 테스트."""

    async def test_client_can_read_own_deal_buyers(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 자기 딜의 매수자 목록을 조회할 수 있다."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        await _add_buyer(http_client, txn_id, company_name="A사")

        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.get(
            f"/api/v1/transactions/{txn_id}/buyers",
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    async def test_client_can_read_own_deal_consortium(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 자기 딜의 컨소시엄 매핑을 조회할 수 있다."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        lead = await _add_buyer(http_client, txn_id, company_name="리드")
        co = await _add_buyer(http_client, txn_id, company_name="코인")
        await http_client.post(
            f"/api/v1/transactions/{txn_id}/consortium/",
            json={
                "lead_buyer_id": lead["id"],
                "co_investor_buyer_id": co["id"],
            },
        )

        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.get(
            f"/api/v1/transactions/{txn_id}/consortium/",
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestClientDealIsolation:
    """CLIENT가 다른 딜에 접근하지 못하는지 검증."""

    async def test_client_blocked_from_other_deal(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 접근 권한 없는 딜에 403을 받는다."""
        _set_claims(ADMIN_CLAIMS)
        txn_own = await _create_txn(http_client, code_name="OWN-001")
        txn_other = await _create_txn(http_client, code_name="OTHER-001")

        await _grant_deal_access(async_session, txn_own, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.get(
            f"/api/v1/transactions/{txn_other}/buyers",
        )
        assert resp.status_code == 403

    async def test_client_blocked_from_other_deal_consortium(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 접근 권한 없는 딜의 컨소시엄에 403을 받는다."""
        _set_claims(ADMIN_CLAIMS)
        txn_own = await _create_txn(http_client, code_name="OWN-002")
        txn_other = await _create_txn(http_client, code_name="OTHER-002")

        await _grant_deal_access(async_session, txn_own, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.get(
            f"/api/v1/transactions/{txn_other}/consortium/",
        )
        assert resp.status_code == 403


class TestClientWriteBlocked:
    """CLIENT의 모든 쓰기 작업이 차단되는지 검증."""

    async def test_client_cannot_create_buyer(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 매수자를 생성할 수 없다 (403)."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.post(
            f"/api/v1/transactions/{txn_id}/buyers",
            json={"company_name": "신규기업", "buyer_type": "STRATEGIC"},
        )
        assert resp.status_code == 403

    async def test_client_cannot_update_buyer(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 매수자를 수정할 수 없다 (403)."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(http_client, txn_id)
        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
            json={"notes": "수정 시도"},
        )
        assert resp.status_code == 403

    async def test_client_cannot_delete_buyer(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 매수자를 삭제할 수 없다 (403)."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(http_client, txn_id)
        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.delete(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        )
        assert resp.status_code == 403

    async def test_client_cannot_create_consortium(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 컨소시엄 매핑을 생성할 수 없다 (403)."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        lead = await _add_buyer(http_client, txn_id, company_name="리드")
        co = await _add_buyer(http_client, txn_id, company_name="코인")
        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.post(
            f"/api/v1/transactions/{txn_id}/consortium/",
            json={
                "lead_buyer_id": lead["id"],
                "co_investor_buyer_id": co["id"],
            },
        )
        assert resp.status_code == 403

    async def test_client_cannot_create_marketing_log(
        self,
        http_client: AsyncClient,
        async_session: AsyncSession,
    ) -> None:
        """CLIENT가 마케팅 로그를 생성할 수 없다 (403)."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(http_client, txn_id)
        await _grant_deal_access(async_session, txn_id, CLIENT_CLAIMS.email)

        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.post(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
            json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
        )
        assert resp.status_code == 403

    async def test_client_cannot_access_audit_logs(
        self,
        http_client: AsyncClient,
    ) -> None:
        """CLIENT가 감사 로그에 접근할 수 없다 (403)."""
        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.get("/api/v1/audit-logs")
        assert resp.status_code == 403

    async def test_client_cannot_export_audit_logs(
        self,
        http_client: AsyncClient,
    ) -> None:
        """CLIENT가 감사 로그 CSV 내보내기에 접근할 수 없다 (403)."""
        _set_claims(CLIENT_CLAIMS)
        resp = await http_client.get("/api/v1/audit-logs/export")
        assert resp.status_code == 403


# ═════════════════════════════════════════════════════════
# remove_buyer CASCADE 감사 추적 테스트
# ═════════════════════════════════════════════════════════


class TestCascadeAuditTrail:
    """remove_buyer CASCADE 삭제 시 감사 로그의 notes 검증."""

    async def test_remove_buyer_cascade_notes(
        self,
        http_client: AsyncClient,
    ) -> None:
        """매수자 삭제 시 감사 로그에 CASCADE 삭제 건수가 기록된다."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(http_client, txn_id, company_name="삭제대상")
        co = await _add_buyer(http_client, txn_id, company_name="공동투자")

        # 마케팅 로그 2건 생성
        await http_client.post(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
            json={"stage": "IDENTIFIED", "log_date": "2026-03-01"},
        )
        await http_client.post(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}/marketing-logs",
            json={"stage": "EMAIL_SENT", "log_date": "2026-03-05"},
        )

        # 컨소시엄 매핑 1건 생성 (buyer가 lead)
        await http_client.post(
            f"/api/v1/transactions/{txn_id}/consortium/",
            json={
                "lead_buyer_id": buyer["id"],
                "co_investor_buyer_id": co["id"],
            },
        )

        # 매수자 삭제
        resp = await http_client.delete(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        )
        assert resp.status_code == 204

        # 감사 로그에서 CASCADE notes 검증
        audit_resp = await http_client.get(
            "/api/v1/audit-logs",
            params={"entity_type": "BuyerCandidate", "action": "DELETE"},
        )
        assert audit_resp.status_code == 200
        items = audit_resp.json()["items"]
        assert len(items) >= 1

        delete_log = items[0]
        notes = delete_log["notes"]
        assert notes is not None
        assert "마케팅 로그 2건" in notes
        assert "컨소시엄 매핑 1건" in notes

    async def test_remove_buyer_old_value_fields(
        self,
        http_client: AsyncClient,
    ) -> None:
        """매수자 삭제 시 감사 로그 old_value에 핵심 필드가 포함된다."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(
            http_client,
            txn_id,
            company_name="감사추적기업",
            buyer_type="FINANCIAL_SPONSOR",
        )
        # tier/status 업데이트
        await http_client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
            json={"tier": "TIER_1", "status": "NDA_SENT"},
        )

        # 삭제
        resp = await http_client.delete(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        )
        assert resp.status_code == 204

        # 감사 로그 old_value 검증
        audit_resp = await http_client.get(
            "/api/v1/audit-logs",
            params={"entity_type": "BuyerCandidate", "action": "DELETE"},
        )
        items = audit_resp.json()["items"]
        assert len(items) >= 1
        old_value = items[0]["old_value"]
        assert old_value is not None
        assert old_value["company_name"] == "감사추적기업"
        assert old_value["tier"] == "TIER_1"
        assert old_value["status"] == "NDA_SENT"
        assert old_value["buyer_type"] == "FINANCIAL_SPONSOR"
        assert "deal_role" in old_value
        assert "contact_name" in old_value
        assert "corp_code" in old_value

    async def test_remove_buyer_cascade_notes_zero(
        self,
        http_client: AsyncClient,
    ) -> None:
        """관련 데이터가 없는 매수자 삭제 시 0건으로 기록된다."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(http_client, txn_id, company_name="단독삭제")

        resp = await http_client.delete(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
        )
        assert resp.status_code == 204

        audit_resp = await http_client.get(
            "/api/v1/audit-logs",
            params={"entity_type": "BuyerCandidate", "action": "DELETE"},
        )
        items = audit_resp.json()["items"]
        assert len(items) >= 1

        notes = items[0]["notes"]
        assert "마케팅 로그 0건" in notes
        assert "컨소시엄 매핑 0건" in notes


# ═════════════════════════════════════════════════════════
# 감사 로그 CSV 내보내기 테스트
# ═════════════════════════════════════════════════════════


class TestAuditCsvExport:
    """감사 로그 CSV 내보내기 컬럼/직렬화 검증."""

    async def test_csv_export_8_columns(
        self,
        http_client: AsyncClient,
    ) -> None:
        """CSV 내보내기가 8개 컬럼 헤더를 포함한다."""
        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        await _add_buyer(http_client, txn_id)

        resp = await http_client.get("/api/v1/audit-logs/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]

        content = resp.content.decode("utf-8-sig")
        lines = content.strip().split("\r\n")
        header = lines[0]
        assert "Timestamp" in header
        assert "Old Value" in header
        assert "New Value" in header
        assert "Notes" in header

        import csv as csv_mod
        import io

        reader = csv_mod.reader(io.StringIO(content))
        header_row = next(reader)
        assert len(header_row) == 8

    async def test_csv_export_old_new_value_json(
        self,
        http_client: AsyncClient,
    ) -> None:
        """UPDATE 후 CSV Old Value/New Value가 유효한 JSON이다."""
        import csv as csv_mod
        import io
        import json

        _set_claims(ADMIN_CLAIMS)
        txn_id = await _create_txn(http_client)
        buyer = await _add_buyer(http_client, txn_id, company_name="CSV검증")

        # UPDATE로 old_value/new_value 생성
        await http_client.patch(
            f"/api/v1/transactions/{txn_id}/buyers/{buyer['id']}",
            json={"status": "NDA_SENT"},
        )

        resp = await http_client.get(
            "/api/v1/audit-logs/export",
            params={"entity_type": "BuyerCandidate", "action": "UPDATE"},
        )
        assert resp.status_code == 200
        content = resp.content.decode("utf-8-sig")

        reader = csv_mod.reader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) >= 2  # 헤더 + 데이터

        data_row = rows[1]
        # Old Value (index 5), New Value (index 6) — 유효 JSON인지 확인
        old_val = json.loads(data_row[5])
        new_val = json.loads(data_row[6])
        assert "status" in old_val or "status" in new_val
