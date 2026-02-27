"""Guardrails 단위 테스트 — Sprint 6."""

from decimal import Decimal

from app.agents.guardrails import (
    check_hallucination_patterns,
    enforce_confidence_threshold,
    validate_amounts_exist,
    validate_entry_ids_exist,
    validate_no_calculations,
    validate_totals_match,
)

# ── TestValidateAmountsExist ─────────────────────────────


class TestValidateAmountsExist:
    """금액 존재 검증 테스트."""

    def test_valid_amounts_pass(self):
        """소스에 있는 금액은 통과."""
        llm_output = {
            "analysis_results": [
                {"entry_id": "E1", "amount": "1000.00"},
                {"entry_id": "E2", "amount": "2000.00"},
            ]
        }
        source_entries = [
            {"entry_id": "E1", "amount": "1000.00"},
            {"entry_id": "E2", "amount": "2000.00"},
            {"entry_id": "E3", "amount": "3000.00"},
        ]
        errors = validate_amounts_exist(llm_output, source_entries)
        assert errors == []

    def test_invalid_amount_fails(self):
        """소스에 없는 금액은 실패."""
        llm_output = {
            "analysis_results": [
                {"entry_id": "E1", "amount": "9999.00"},  # 소스에 없음
            ]
        }
        source_entries = [
            {"entry_id": "E1", "amount": "1000.00"},
        ]
        errors = validate_amounts_exist(llm_output, source_entries)
        assert len(errors) == 1
        assert "9999.00" in errors[0]
        assert "할루시네이션" in errors[0]

    def test_empty_output_passes(self):
        """빈 출력은 통과."""
        errors = validate_amounts_exist({}, [])
        assert errors == []


# ── TestValidateEntryIdsExist ─────────────────────────────


class TestValidateEntryIdsExist:
    """전표 ID 존재 검증 테스트."""

    def test_valid_ids_pass(self):
        """소스에 있는 ID는 통과."""
        llm_output = {
            "analysis_results": [
                {"entry_id": "GL-001"},
                {"entry_id": "GL-002"},
            ]
        }
        source_entries = [
            {"entry_id": "GL-001"},
            {"entry_id": "GL-002"},
            {"entry_id": "GL-003"},
        ]
        errors = validate_entry_ids_exist(llm_output, source_entries)
        assert errors == []

    def test_invalid_id_fails(self):
        """소스에 없는 ID는 실패."""
        llm_output = {
            "analysis_results": [
                {"entry_id": "GL-999"},  # 소스에 없음
            ]
        }
        source_entries = [
            {"entry_id": "GL-001"},
        ]
        errors = validate_entry_ids_exist(llm_output, source_entries)
        assert len(errors) == 1
        assert "GL-999" in errors[0]

    def test_nested_entry_ids(self):
        """중첩된 entry_id도 검증."""
        llm_output = {
            "results": [
                {"details": {"entry_id": "GL-BAD"}},
            ]
        }
        source_entries = [{"entry_id": "GL-001"}]
        errors = validate_entry_ids_exist(llm_output, source_entries)
        assert len(errors) == 1


# ── TestValidateTotalsMatch ─────────────────────────────


class TestValidateTotalsMatch:
    """합계 일치 검증 테스트."""

    def test_matching_totals_pass(self):
        """일치하는 합계는 통과."""
        errors = validate_totals_match(
            Decimal("1000.00"),
            Decimal("1000.00"),
        )
        assert errors == []

    def test_within_tolerance_pass(self):
        """허용 오차 내 차이는 통과."""
        errors = validate_totals_match(
            Decimal("1000.00"),
            Decimal("1000.005"),
            tolerance=Decimal("0.01"),
        )
        assert errors == []

    def test_exceeds_tolerance_fails(self):
        """허용 오차 초과 차이는 실패."""
        errors = validate_totals_match(
            Decimal("1000.00"),
            Decimal("1100.00"),
        )
        assert len(errors) == 1
        assert "합계 불일치" in errors[0]


# ── TestCheckHallucinationPatterns ────────────────────────


class TestCheckHallucinationPatterns:
    """할루시네이션 패턴 검사 테스트."""

    def test_valid_codes_pass(self):
        """알려진 코드는 통과."""
        llm_output = {
            "mapping_suggestions": [
                {"source_account_code": "54100", "suggested_target_code": "IS-SGA-001"},
            ]
        }
        known_codes = {"54100", "IS-SGA-001", "IS-SGA-002"}
        errors = check_hallucination_patterns(llm_output, known_codes)
        assert errors == []

    def test_unknown_code_fails(self):
        """알 수 없는 코드는 실패."""
        llm_output = {
            "mapping_suggestions": [
                {"suggested_target_code": "IS-FAKE-999"},
            ]
        }
        known_codes = {"IS-SGA-001"}
        errors = check_hallucination_patterns(llm_output, known_codes)
        assert len(errors) == 1
        assert "IS-FAKE-999" in errors[0]
        assert "할루시네이션" in errors[0]


# ── TestEnforceConfidenceThreshold ────────────────────────


class TestEnforceConfidenceThreshold:
    """신뢰도 필터링 테스트."""

    def test_high_confidence_kept(self):
        """높은 신뢰도 항목은 유지."""
        output = {
            "analysis_results": [
                {"entry_id": "E1", "confidence": 0.80},
                {"entry_id": "E2", "confidence": 0.50},
            ]
        }
        filtered = enforce_confidence_threshold(output, min_confidence=Decimal("0.30"))
        assert len(filtered["analysis_results"]) == 2

    def test_low_confidence_filtered(self):
        """낮은 신뢰도 항목은 필터링."""
        output = {
            "analysis_results": [
                {"entry_id": "E1", "confidence": 0.80},
                {"entry_id": "E2", "confidence": 0.10},  # 필터링됨
            ]
        }
        filtered = enforce_confidence_threshold(output, min_confidence=Decimal("0.30"))
        assert len(filtered["analysis_results"]) == 1
        assert filtered["analysis_results"][0]["entry_id"] == "E1"

    def test_mapping_suggestions_filtered(self):
        """매핑 제안도 필터링."""
        output = {
            "mapping_suggestions": [
                {"source_account_code": "A", "confidence": 0.80},
                {"source_account_code": "B", "confidence": 0.20},
            ]
        }
        filtered = enforce_confidence_threshold(output, min_confidence=Decimal("0.30"))
        assert len(filtered["mapping_suggestions"]) == 1


# ── TestValidateNoCalculations ────────────────────────────


class TestValidateNoCalculations:
    """계산 시도 검사 테스트."""

    def test_no_calculation_passes(self):
        """계산 없으면 통과."""
        output = {"analysis_results": [{"rationale": "This is a normal expense."}]}
        errors = validate_no_calculations(output)
        assert errors == []

    def test_calculation_detected(self):
        """계산 키워드 탐지."""
        output = {"summary": "The total is calculated to be 1000."}
        errors = validate_no_calculations(output)
        assert len(errors) == 1
        assert "계산" in errors[0]

    def test_korean_calculation_detected(self):
        """한국어 계산 키워드 탐지."""
        output = {"summary": "계산하면 합계는 1000원입니다."}
        errors = validate_no_calculations(output)
        assert len(errors) == 1
