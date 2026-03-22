"""외부 서비스 클라이언트 Protocol 정의 — DI 계약.

프로덕션에서는 Real 클라이언트, 테스트에서는 Mock 클라이언트를 주입한다.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable


@runtime_checkable
class KIISClientProtocol(Protocol):
    """KIIS(기업정보 조사 서비스) 클라이언트 계약."""

    async def search_company(self, name: str) -> list[dict]: ...
    async def get_company_detail(self, corp_code: str) -> dict: ...
    async def get_financial_summary(self, corp_code: str) -> dict: ...
    async def search_gps(self, query: str) -> list[dict]: ...
    async def close(self) -> None: ...


@runtime_checkable
class FDDClientProtocol(Protocol):
    """FDD(재무실사) 서비스 클라이언트 계약."""

    async def create_deal(self, target_name: str, industry: str | None = None) -> dict: ...

    async def get_deal_status(self, deal_id: uuid.UUID) -> dict: ...

    async def get_evidence_export(self, deal_id: uuid.UUID) -> dict: ...

    async def trigger_analysis(self, deal_id: uuid.UUID, analysis_type: str) -> dict: ...


@runtime_checkable
class IMClientProtocol(Protocol):
    """IM(투자설명서) 서비스 클라이언트 계약."""

    async def create_document(
        self,
        company_name: str,
        project_name: str,
        corp_code: str | None = None,
    ) -> dict: ...

    async def get_document_status(self, document_id: uuid.UUID) -> dict: ...

    async def trigger_generation(self, document_id: uuid.UUID) -> dict: ...
