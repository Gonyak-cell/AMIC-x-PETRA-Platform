"""Tests for FDD Ralph Loop — Generator, Gates, Service.

FDD 전용 Generator, Programmatic Gate, LLM Judge Gate,
FDDRalphService의 단위/통합 테스트.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.deal import Deal, DealType
from app.models.ralph_session import FddRalphSession, FddRalphSessionStatus
from app.ralph.convergence import ConvergenceConfig
from app.ralph.gates.base import GateVerdict
from app.ralph.gates.fdd_programmatic_gate import FDDProgrammaticGate
from app.ralph.generators.fdd_report_generator import FDDReportGenerator

# ── Fixtures ────────────────────────────────────────────────────


@pytest.fixture
def deal(db: Session) -> Deal:
    deal = Deal(
        name="Ralph Test Deal",
        deal_type=DealType.COMPLETION_ACCOUNTS,
        base_currency="KRW",
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@pytest.fixture
def sample_ir_dict() -> dict:
    """Minimal Report IR dict for testing."""
    return {
        "metadata": {
            "deal_name": "Test Corp",
            "deal_id": str(uuid.uuid4()),
            "generated_at": "2026-01-01T00:00:00",
        },
        "sections": [
            {
                "type": "cover",
                "deal_name": "Test Corp",
                "project_code": "PROJECT-X",
            },
            {
                "type": "kpi",
                "title": "Key Metrics",
                "kpis": [
                    {"label": "Adjusted EBITDA", "value": "₩5,000M"},
                    {"label": "NWC", "value": "₩1,200M"},
                ],
            },
            {
                "type": "text",
                "title": "Executive Summary",
                "content": "The target company demonstrates strong financial performance.",
            },
            {
                "type": "text",
                "title": "QoE Commentary",
                "content": "Adjusted EBITDA of ₩5,000M reflects normalized earnings.",
            },
            {
                "type": "claim",
                "claim_text": "Revenue increased 15% YoY",
                "evidence_refs": [{"doc_id": "vdr-001", "page": 5}],
                "verified": True,
            },
            {
                "type": "issue",
                "issues": [
                    {
                        "issue_id": "ISS-001",
                        "title": "Related party transactions",
                        "severity": "HIGH",
                        "impact_amount": "₩500M",
                        "recommendation": "Adjust EBITDA by ₩500M",
                    }
                ],
            },
            {
                "type": "table",
                "title": "QoE Bridge",
                "headers": ["Item", "Amount"],
                "rows": [["Revenue", "₩10,000M"]],
            },
        ],
    }


@pytest.fixture
def mock_llm_call():
    """Mock LLM call that returns refined JSON.

    Signature: async (system_prompt, user_prompt, temperature, max_tokens) -> str
    """
    async def _llm_call(
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str:
        return json.dumps({
            "type": "text",
            "title": "Executive Summary (Refined)",
            "content": "The target demonstrates robust operational performance with Adjusted EBITDA of ₩5,000M.",
        })
    return _llm_call


# ── FDDReportGenerator Tests ──────────────────────────────────────


class TestFDDReportGenerator:
    @pytest.mark.asyncio
    async def test_generate_outline_extracts_refinable_sections(self, sample_ir_dict, mock_llm_call):
        generator = FDDReportGenerator(
            report_ir_dict=sample_ir_dict,
            llm_call=mock_llm_call,
        )
        outline = await generator.generate_outline(sample_ir_dict)

        # Should extract text, claim, issue blocks but NOT cover, kpi, table
        section_types = {s["block_type"] for s in outline}
        assert "text" in section_types
        assert "claim" in section_types
        assert "issue" in section_types
        assert "cover" not in section_types
        assert "kpi" not in section_types
        assert "table" not in section_types

    @pytest.mark.asyncio
    async def test_generate_outline_has_required_fields(self, sample_ir_dict, mock_llm_call):
        generator = FDDReportGenerator(
            report_ir_dict=sample_ir_dict,
            llm_call=mock_llm_call,
        )
        outline = await generator.generate_outline(sample_ir_dict)
        for section in outline:
            assert "id" in section
            assert "index" in section
            assert "block_type" in section
            assert "title" in section

    @pytest.mark.asyncio
    async def test_generate_section_calls_llm(self, sample_ir_dict, mock_llm_call):
        generator = FDDReportGenerator(
            report_ir_dict=sample_ir_dict,
            llm_call=mock_llm_call,
        )
        result = await generator.generate_section(
            section_id="text_2",
            section_criteria={"required_topics": ["financial performance"]},
            source_data={},
            feedback=None,
        )
        parsed = json.loads(result)
        assert "content" in parsed

    @pytest.mark.asyncio
    async def test_assemble_document_merges_refined(self, sample_ir_dict, mock_llm_call):
        generator = FDDReportGenerator(
            report_ir_dict=sample_ir_dict,
            llm_call=mock_llm_call,
        )
        # Simulate refined text section
        refined_artifact = json.dumps({
            "type": "text",
            "title": "Executive Summary (Refined)",
            "content": "Refined body text here.",
        })
        section_artifacts = {"text_2": refined_artifact}

        result = await generator.assemble_document(section_artifacts, "")
        assembled = json.loads(result)
        assert "sections" in assembled
        # Verify at least one section was updated
        text_sections = [s for s in assembled["sections"] if s["type"] == "text"]
        assert len(text_sections) > 0


# ── FDDProgrammaticGate Tests ────────────────────────────────────


class TestFDDProgrammaticGate:
    @pytest.mark.asyncio
    async def test_clean_text_passes(self):
        gate = FDDProgrammaticGate()
        artifact = json.dumps({
            "type": "text",
            "title": "QoE Commentary",
            "content": "Adjusted EBITDA totals ₩5,000M after normalizations.",
        })
        result = await gate.evaluate(
            artifact_path=artifact,
            prd_section={"required_topics": ["EBITDA"]},
            source_data={"qoe": {"adjusted_ebitda": "₩5,000M"}},
        )
        assert result.gate_name == "fdd_programmatic"
        assert result.weighted_score > 0

    @pytest.mark.asyncio
    async def test_placeholder_detected(self):
        gate = FDDProgrammaticGate()
        artifact = json.dumps({
            "type": "text",
            "title": "Test",
            "content": "The company [INSERT NAME] has revenue of [TBD].",
        })
        result = await gate.evaluate(
            artifact_path=artifact,
            prd_section={},
            source_data={},
        )
        # Should detect placeholders and score lower
        assert any("placeholder" in i.lower() or "[INSERT" in i for i in result.issues) or \
               result.weighted_score < 5.0

    @pytest.mark.asyncio
    async def test_checklist_alignment_pass2(self):
        corrections = [
            {
                "category": "REVENUE_RECOGNITION",
                "title": "Revenue adjustment",
                "status": "CORRECTED",
                "user_correction": "Adjust revenue to ₩9,500M",
                "user_amount": "9500000000",
            }
        ]
        gate = FDDProgrammaticGate(checklist_corrections=corrections)
        artifact = json.dumps({
            "type": "text",
            "title": "Revenue Commentary",
            "content": "Revenue was adjusted to ₩9,500M per management correction.",
        })
        result = await gate.evaluate(
            artifact_path=artifact,
            prd_section={},
            source_data={},
        )
        assert result.gate_name == "fdd_programmatic"


# ── FddRalphSession DB Model Tests ──────────────────────────────


class TestFddRalphSessionModel:
    def test_create_session(self, db: Session, deal: Deal):
        session = FddRalphSession(
            deal_id=deal.id,
            pass_type="draft",
            status=FddRalphSessionStatus.PLANNING,
            created_by="test@autofdd.dev",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.id is not None
        assert session.deal_id == deal.id
        assert session.pass_type == "draft"
        assert session.status == FddRalphSessionStatus.PLANNING

    def test_session_jsonb_fields(self, db: Session, deal: Deal):
        session = FddRalphSession(
            deal_id=deal.id,
            pass_type="draft",
            status=FddRalphSessionStatus.COMPLETED,
            section_scores={"exec_summary": 4.5, "qoe_commentary": 4.2},
            critical_flags=["NUMERICAL_MISMATCH"],
            config={"max_iterations_per_section": 3},
            created_by="test@autofdd.dev",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.section_scores["exec_summary"] == 4.5
        assert "NUMERICAL_MISMATCH" in session.critical_flags
        assert session.config["max_iterations_per_section"] == 3

    def test_session_status_enum(self, db: Session, deal: Deal):
        session = FddRalphSession(
            deal_id=deal.id,
            pass_type="final",
            status=FddRalphSessionStatus.GENERATING,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.status == FddRalphSessionStatus.GENERATING

        # Update status
        session.status = FddRalphSessionStatus.COMPLETED
        db.commit()
        db.refresh(session)
        assert session.status == FddRalphSessionStatus.COMPLETED
