"""테스트/로컬 환경 전용 Mock 외부 클라이언트.

프로덕션 환경에서는 절대 로드되지 않는다 (dependencies.py의 환경 분기 참조).
"""

from __future__ import annotations

import uuid


class MockKIISClient:
    """KIIS Mock — 정적 더미 응답 반환."""

    async def search_company(self, name: str) -> list[dict]:
        return [
            {"corp_code": "00000001", "corp_name": f"{name} (Mock)", "stock_code": ""},
        ]

    async def get_company_detail(self, corp_code: str) -> dict:
        return {"corp_code": corp_code, "corp_name": "Mock 기업", "status": "mock"}

    async def get_financial_summary(self, corp_code: str) -> dict:
        return {
            "corp_code": corp_code,
            "revenue": 0,
            "operating_profit": 0,
            "net_income": 0,
            "debt_ratio": 0.0,
        }

    async def search_gps(self, query: str) -> list[dict]:
        return [{"gp_name": f"{query} (Mock)", "gp_code": "MOCK-GP-001"}]

    async def close(self) -> None:
        pass


class MockFDDClient:
    """FDD Mock — 정적 더미 응답 반환."""

    async def create_deal(self, target_name: str, industry: str | None = None) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "target_name": target_name,
            "status": "mock_created",
        }

    async def get_deal_status(self, deal_id: uuid.UUID) -> dict:
        return {"id": str(deal_id), "status": "mock_in_progress"}

    async def get_evidence_export(self, deal_id: uuid.UUID) -> dict:
        return {
            "artifact_type": "FDD_REPORT",
            "external_artifact_ref": f"fdd-{deal_id}",
            "default_workstream": "FDD",
            "records": [
                {
                    "section_type": "WORKING_CAPITAL",
                    "item_id": "NWC-01",
                    "reference_label": "mock_qoe_report.xlsx",
                    "original_name": "mock_qoe_report.xlsx",
                    "primary_workstream": "FDD",
                    "workstream_tags": ["FDD"],
                    "evidence_kind": "FINANCIAL_SUPPORT",
                    "directness": "INDIRECT",
                    "confidence": 0.86,
                    "relevance_score": 0.86,
                    "source_page": "Sheet QoE Row 4",
                    "source_snippet": "Mock NWC adjustment support.",
                    "evidence_locator": {"sheet": "QoE", "row": 4},
                    "used_in_draft": False,
                    "used_in_final": True,
                    "analysis_phase": "FINAL",
                }
            ],
        }

    async def trigger_analysis(self, deal_id: uuid.UUID, analysis_type: str) -> dict:
        return {
            "deal_id": str(deal_id),
            "analysis_type": analysis_type,
            "status": "mock_triggered",
        }


class MockIMClient:
    """IM Mock — 정적 더미 응답 반환."""

    async def create_document(
        self,
        company_name: str,
        project_name: str,
        corp_code: str | None = None,
    ) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "company_name": company_name,
            "status": "mock_created",
        }

    async def get_document_status(self, document_id: uuid.UUID) -> dict:
        return {"id": str(document_id), "status": "mock_generating"}

    async def trigger_generation(self, document_id: uuid.UUID) -> dict:
        return {"id": str(document_id), "status": "mock_regenerating"}
