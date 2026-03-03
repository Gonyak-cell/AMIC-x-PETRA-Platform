"""R4 리뷰 추가 테스트 — SI 매핑 (R6-TQ-01).

bulk_add_buyers 엔드포인트의 404 경로를 검증한다.
존재하지 않는 txn_id 전달 시 404 반환을 보장하여,
transaction_service.get_transaction 리팩토링 시 회귀를 방지한다.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_bulk_add_buyers_404_unknown_txn(client: AsyncClient) -> None:
    """존재하지 않는 txn_id → 404 반환 (R6-TQ-01).

    si_company_ids는 min_length=1 제약이 있으므로
    더미 UUID 1개를 포함하여 스키마 검증을 통과시킨 뒤
    트랜잭션 조회 단계에서 404가 반환되는지 확인한다.
    """
    fake_txn_id = str(uuid.uuid4())
    dummy_company_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/transactions/{fake_txn_id}/si-mapping/add-buyers",
        json={"si_company_ids": [dummy_company_id]},
    )
    assert resp.status_code == 404
