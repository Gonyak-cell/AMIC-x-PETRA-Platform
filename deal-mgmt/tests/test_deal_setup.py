"""AI 딜 셋업 confirm — bootstrap(Closing Checklist + VDR 폴더) 회귀 테스트."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.closing_checklist import ClosingChecklist
from app.models.vdr_folder import VdrFolder
from app.services.transaction_service import _STANDARD_CLOSING_ITEMS

pytestmark = pytest.mark.asyncio

_CONFIRM_BODY = {
    "transaction": {
        "name": "AI 딜 셋업 테스트",
        "deal_type": "SE",
        "side": "SELL",
        "target_company_name": "대상기업",
        "client_name": "의뢰기업",
    },
    "dd_checklist": [
        {"workstream": "FDD_FINANCIAL_STATEMENTS", "title": "재무 DD 항목"},
    ],
    "timeline": [
        {"event_type": "MILESTONE", "title": "착수", "event_date": "2026-04-01"},
    ],
    "buyer_candidates": [
        {"company_name": "매수후보사"},
    ],
    "lead_advisor_email": "advisor@example.com",
}


class TestDealSetupBootstrap:
    """confirm 후 Closing Checklist + VDR 기본 폴더 자동 생성 검증."""

    async def test_confirm_creates_closing_checklist(self, client: AsyncClient, async_session: AsyncSession) -> None:
        """confirm 시 표준 Closing Checklist 항목이 자동 생성된다."""
        resp = await client.post(
            "/api/v1/transactions/ai-setup/confirm",
            json=_CONFIRM_BODY,
        )
        assert resp.status_code == 201
        txn_id = uuid.UUID(resp.json()["transaction_id"])

        result = await async_session.execute(select(func.count()).where(ClosingChecklist.transaction_id == txn_id))
        count = result.scalar()
        assert count == len(_STANDARD_CLOSING_ITEMS)

    async def test_confirm_creates_vdr_default_folders(self, client: AsyncClient, async_session: AsyncSession) -> None:
        """confirm 시 VDR 기본 폴더 12개가 자동 생성된다."""
        resp = await client.post(
            "/api/v1/transactions/ai-setup/confirm",
            json=_CONFIRM_BODY,
        )
        assert resp.status_code == 201
        txn_id = uuid.UUID(resp.json()["transaction_id"])

        result = await async_session.execute(select(func.count()).where(VdrFolder.transaction_id == txn_id))
        count = result.scalar()
        assert count == 12

    async def test_confirm_returns_correct_counts(self, client: AsyncClient) -> None:
        """confirm 응답에 dd_checklist_count, timeline_count, buyer_count가 정확하다."""
        resp = await client.post(
            "/api/v1/transactions/ai-setup/confirm",
            json=_CONFIRM_BODY,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["dd_checklist_count"] == 1
        assert data["timeline_count"] == 1
        assert data["buyer_count"] == 1
