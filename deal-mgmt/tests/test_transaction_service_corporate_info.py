from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionSide
from app.models.transaction import Transaction
from app.schemas.transaction import TransactionUpdate
from app.services.transaction_service import update_transaction

pytestmark = pytest.mark.anyio


async def _make_txn(async_session: AsyncSession) -> Transaction:
    txn = Transaction(
        name="Project Guided",
        code_name=f"SE26-TST-{uuid.uuid4().hex[:4].upper()}",
        side=TransactionSide.SELL,
        target_company_name="Target Co",
        client_name="Client Co",
        lead_advisor_email="lead@amic.kr",
    )
    async_session.add(txn)
    await async_session.flush()
    await async_session.commit()
    await async_session.refresh(txn)
    return txn


async def test_update_transaction_merges_allowed_corporate_info_fields(
    async_session: AsyncSession,
) -> None:
    txn = await _make_txn(async_session)
    txn.corporate_info = {"company_name": "Existing Co"}
    await async_session.commit()

    updated = await update_transaction(
        async_session,
        txn.id,
        TransactionUpdate(
            corporate_info={
                "representative_name": "홍길동",
                "business_registration_number": "123-45-67890",
            }
        ),
    )

    assert updated.corporate_info == {
        "company_name": "Existing Co",
        "representative_name": "홍길동",
        "business_registration_number": "123-45-67890",
    }


async def test_update_transaction_keeps_existing_ocr_only_fields(
    async_session: AsyncSession,
) -> None:
    txn = await _make_txn(async_session)
    txn.corporate_info = {
        "company_name": "Target Co",
        "capital_amount": 500000000,
        "directors": [{"name": "홍길동", "position": "대표이사"}],
    }
    await async_session.commit()

    updated = await update_transaction(
        async_session,
        txn.id,
        TransactionUpdate(
            corporate_info={
                "representative_name": "신규 대표",
            }
        ),
    )

    assert updated.corporate_info["capital_amount"] == 500000000
    assert updated.corporate_info["directors"] == [{"name": "홍길동", "position": "대표이사"}]
    assert updated.corporate_info["representative_name"] == "신규 대표"


async def test_update_transaction_removes_blank_or_null_corporate_info_fields(
    async_session: AsyncSession,
) -> None:
    txn = await _make_txn(async_session)
    txn.corporate_info = {
        "company_name": "Target Co",
        "representative_name": "홍길동",
        "business_type": "서비스업",
    }
    await async_session.commit()

    updated = await update_transaction(
        async_session,
        txn.id,
        TransactionUpdate(
            corporate_info={
                "representative_name": "",
                "business_type": None,
            }
        ),
    )

    assert updated.corporate_info == {
        "company_name": "Target Co",
    }


async def test_update_transaction_can_clear_corporate_info_entirely(
    async_session: AsyncSession,
) -> None:
    txn = await _make_txn(async_session)
    txn.corporate_info = {
        "company_name": "Target Co",
        "representative_name": "홍길동",
    }
    await async_session.commit()

    updated = await update_transaction(
        async_session,
        txn.id,
        TransactionUpdate(corporate_info=None),
    )

    assert updated.corporate_info is None
