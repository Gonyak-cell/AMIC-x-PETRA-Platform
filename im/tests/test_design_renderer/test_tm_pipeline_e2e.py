"""Phase 5 검증 테스트 (2/2) — tm_pipeline E2E (15 tests).

JSON → DocumentRenderingSpec → IMDocumentData → PPTX 전체 흐름을 검증한다.
기존 test_tm_pipeline.py(렌더러 메커닉스)와 비중복 — 여기서는 JSON 파이프라인을 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.design_renderer.tm_pipeline.schema import DocumentRenderingSpec
from src.design_renderer.tm_pipeline.orchestrator import (
    render_from_json,
)
from src.design_renderer.tm_pipeline.validators import (
    AntiHallucinationValidator,
)
from src.design_renderer.im_document import IMStyle

# ── 경로 상수 ─────────────────────────────────────────────────────────────────

SAMPLE_SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "sample_specs"

SAMPLE_IM_JSON = SAMPLE_SPECS_DIR / "sample_im_full.json"
SAMPLE_TM_JSON = SAMPLE_SPECS_DIR / "sample_tm_spicy.json"
SAMPLE_DM_JSON = SAMPLE_SPECS_DIR / "sample_dm_internal.json"


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────


def _load_spec(json_path: Path) -> DocumentRenderingSpec:
    """JSON 파일 → DocumentRenderingSpec 로드."""
    raw = json_path.read_text(encoding="utf-8")
    return DocumentRenderingSpec.model_validate_json(raw)


# ══════════════════════════════════════════════════════════════════════════════
# TestDocumentRenderingSpec (5)
# ══════════════════════════════════════════════════════════════════════════════


class TestDocumentRenderingSpec:
    """DocumentRenderingSpec 스키마 검증."""

    def test_schema_parses_sample_im_json(self) -> None:
        """sample_im_full.json → model_validate_json() 성공."""
        if not SAMPLE_IM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_IM_JSON}")
        spec = _load_spec(SAMPLE_IM_JSON)
        assert spec.document_type == "IM"
        assert spec.project_name == "Project NEXUS"

    def test_schema_parses_sample_tm_json(self) -> None:
        """sample_tm_spicy.json 파싱 성공."""
        if not SAMPLE_TM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_TM_JSON}")
        spec = _load_spec(SAMPLE_TM_JSON)
        assert spec.document_type == "TM"

    def test_schema_parses_sample_dm_json(self) -> None:
        """sample_dm_internal.json 파싱 성공."""
        if not SAMPLE_DM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_DM_JSON}")
        spec = _load_spec(SAMPLE_DM_JSON)
        assert spec.document_type == "DM"

    def test_schema_to_im_document_data_roundtrip(self) -> None:
        """spec → to_im_document_data() → 올바른 im_style."""
        if not SAMPLE_TM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_TM_JSON}")
        spec = _load_spec(SAMPLE_TM_JSON)
        data = spec.to_im_document_data()
        assert data.im_style == IMStyle.TEASER
        assert data.project_name == spec.project_name

    def test_schema_rejects_invalid_json(self) -> None:
        """필수 필드 누락 JSON → ValidationError."""
        invalid_json = '{"document_type": "INVALID", "project_name": "Test", "company_name_kr": "테스트"}'
        with pytest.raises(Exception, match="허용되지 않음|validation error"):
            DocumentRenderingSpec.model_validate_json(invalid_json)


# ══════════════════════════════════════════════════════════════════════════════
# TestJsonToPptxPipeline (5)
# ══════════════════════════════════════════════════════════════════════════════


class TestJsonToPptxPipeline:
    """JSON → PPTX 파이프라인 통합 테스트."""

    def test_orchestrator_im_full_generates_pptx(self, tmp_path: Path) -> None:
        """IM JSON → PPTX bytes > 0."""
        if not SAMPLE_IM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_IM_JSON}")
        out = tmp_path / "test_im.pptx"
        result = render_from_json(SAMPLE_IM_JSON, out)
        assert result.success is True, f"실패: {result.errors}"
        assert out.exists(), "PPTX 파일 미생성"
        assert out.stat().st_size > 0, "PPTX 파일 크기 0"

    def test_orchestrator_tm_generates_pptx(self, tmp_path: Path) -> None:
        """TM JSON → PPTX 성공."""
        if not SAMPLE_TM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_TM_JSON}")
        out = tmp_path / "test_tm.pptx"
        result = render_from_json(SAMPLE_TM_JSON, out)
        assert result.success is True, f"실패: {result.errors}"
        assert out.exists()

    def test_orchestrator_dm_generates_pptx(self, tmp_path: Path) -> None:
        """DM JSON → PPTX 성공."""
        if not SAMPLE_DM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_DM_JSON}")
        out = tmp_path / "test_dm.pptx"
        result = render_from_json(SAMPLE_DM_JSON, out)
        assert result.success is True, f"실패: {result.errors}"
        assert out.exists()

    def test_pipeline_result_has_manifest(self, tmp_path: Path) -> None:
        """PipelineOutput에 GenerationManifest 포함."""
        if not SAMPLE_TM_JSON.exists():
            pytest.skip(f"샘플 파일 없음: {SAMPLE_TM_JSON}")
        out = tmp_path / "test_manifest.pptx"
        result = render_from_json(SAMPLE_TM_JSON, out)
        assert result.manifest is not None, "manifest가 None"
        assert len(result.manifest.entries) > 0, "manifest entries 비어있음"

    def test_pipeline_error_handling_malformed_json(self, tmp_path: Path) -> None:
        """잘못된 JSON → 명확한 에러 (unhandled exception 아님)."""
        bad_json = tmp_path / "bad.json"
        bad_json.write_text('{"invalid": true}', encoding="utf-8")
        out = tmp_path / "should_not_exist.pptx"
        result = render_from_json(bad_json, out)
        assert result.success is False, "잘못된 JSON인데 성공 반환"
        assert len(result.errors) > 0, "에러 메시지 없음"


# ══════════════════════════════════════════════════════════════════════════════
# TestAntiHallucinationValidators (5)
# ══════════════════════════════════════════════════════════════════════════════


class TestAntiHallucinationValidators:
    """Anti-Hallucination 검증기 테스트."""

    def test_arithmetic_check_revenue_sum_equals_segments(self) -> None:
        """세그먼트 매출 합 ≠ 총 매출 시 검출."""
        from src.design_renderer.im_document import (
            FinancialStatements,
            IMDocumentData,
            SegmentRevenue,
        )

        data = IMDocumentData(
            financial_statements=FinancialStatements(revenue={"2024": 100_000}),
            segment_revenue=SegmentRevenue(
                segments={
                    "A": {"2024": 60_000},
                    "B": {"2024": 30_000},
                    # 합 90,000 ≠ 100,000 → 이슈 발생 기대
                }
            ),
        )
        validator = AntiHallucinationValidator(data)
        result = validator.run_all()
        arith_issues = [i for i in result.issues if i.check_type == "arithmetic"]
        assert len(arith_issues) >= 1, "산술 불일치 미검출"

    def test_arithmetic_check_passes_consistent_data(self) -> None:
        """일관된 데이터 → 산술 검증 통과."""
        from src.design_renderer.im_document import (
            FinancialStatements,
            IMDocumentData,
            SegmentRevenue,
        )

        data = IMDocumentData(
            financial_statements=FinancialStatements(revenue={"2024": 100_000}),
            segment_revenue=SegmentRevenue(
                segments={
                    "A": {"2024": 60_000},
                    "B": {"2024": 40_000},
                    # 합 100,000 == 100,000
                }
            ),
        )
        validator = AntiHallucinationValidator(data)
        result = validator.run_all()
        arith_issues = [i for i in result.issues if i.check_type == "arithmetic"]
        assert len(arith_issues) == 0, f"불필요한 산술 이슈: {arith_issues}"

    def test_source_verification_rejects_empty_citations(self) -> None:
        """수치 주장 + 출처 없음 → 플래그."""
        from src.design_renderer.im_document import (
            FinancialStatements,
            IMDocumentData,
        )

        data = IMDocumentData(
            financial_statements=FinancialStatements(revenue={"2024": 100_000}),
            source_citations={},  # 출처 없음
        )
        validator = AntiHallucinationValidator(data)
        result = validator.run_all()
        source_issues = [i for i in result.issues if i.check_type == "source"]
        assert len(source_issues) >= 1, "출처 누락 미검출"

    def test_source_verification_passes_with_citations(self) -> None:
        """출처 있는 데이터 → 검증 통과."""
        from src.design_renderer.im_document import (
            FinancialStatements,
            IMDocumentData,
            SourceCitation,
        )

        data = IMDocumentData(
            financial_statements=FinancialStatements(revenue={"2024": 100_000}),
            source_citations={
                "financial_analysis": [
                    SourceCitation(source_name="DART", access_date="2026-01")
                ]
            },
        )
        validator = AntiHallucinationValidator(data)
        result = validator.run_all()
        source_issues = [i for i in result.issues if i.check_type == "source"]
        assert len(source_issues) == 0, f"불필요한 출처 이슈: {source_issues}"

    def test_validator_chain_runs_all_checks(self) -> None:
        """전체 검증기 순차 실행, 결과 합산."""
        from src.design_renderer.sample_data.im_full import get_full_im_data

        data = get_full_im_data()
        validator = AntiHallucinationValidator(data)
        result = validator.run_all()
        assert result.checks_run >= 3, (
            f"검증 {result.checks_run}회 실행 (3회 이상 기대)"
        )
        # IM 풀 데이터는 일관적이므로 에러 없어야 함
        assert result.passed is True, (
            f"IM 풀 데이터 검증 실패: {[i.message for i in result.issues]}"
        )
