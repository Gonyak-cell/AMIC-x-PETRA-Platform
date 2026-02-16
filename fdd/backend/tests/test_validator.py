"""Tests for upload schema validation (FDD-202 / FDD-205)."""

from app.models.upload import UploadType, ValidationSeverity
from app.services.ingestion.validator import validate_upload


class TestValidateTB:
    def test_valid_tb_no_errors(self, sample_tb_file):
        errors = validate_upload(sample_tb_file, UploadType.TB)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) == 0

    def test_tb_missing_amounts_error(self, sample_tb_no_amounts):
        errors = validate_upload(sample_tb_no_amounts, UploadType.TB)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) > 0
        error_codes = [e.error_code for e in blocking]
        assert "VAL-002" in error_codes

    def test_tb_string_amounts_warning(self, sample_file_string_amounts):
        errors = validate_upload(sample_file_string_amounts, UploadType.TB)
        warnings = [e for e in errors if e.severity == ValidationSeverity.WARNING]
        assert len(warnings) > 0
        assert any(e.error_code == "VAL-010" for e in warnings)


class TestValidateGL:
    def test_valid_gl_no_blocking_errors(self, sample_gl_file):
        errors = validate_upload(sample_gl_file, UploadType.GL)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) == 0

    def test_gl_missing_required_fields(self, sample_tb_file):
        """TB file used as GL should fail on missing entry_id/entry_date."""
        errors = validate_upload(sample_tb_file, UploadType.GL)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "entry_id" in missing_fields
        assert "entry_date" in missing_fields

    def test_gl_missing_amounts_returns_val003(self, sample_gl_no_amounts_file):
        """GL without debit/credit/amount → VAL-003."""
        errors = validate_upload(sample_gl_no_amounts_file, UploadType.GL)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        error_codes = [e.error_code for e in blocking]
        assert "VAL-003" in error_codes


class TestValidateAR:
    def test_valid_ar_no_blocking_errors(self, sample_ar_file):
        """AR file with counterparty + amount → no blocking errors."""
        errors = validate_upload(sample_ar_file, UploadType.AR)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) == 0

    def test_ar_missing_counterparty(self, sample_tb_file):
        """TB file used as AR → missing 'counterparty' required field."""
        errors = validate_upload(sample_tb_file, UploadType.AR)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "counterparty" in missing_fields


class TestValidateBANK:
    def test_valid_bank_no_blocking_errors(self, sample_bank_file):
        """BANK file with entry_date + amount → no blocking errors."""
        errors = validate_upload(sample_bank_file, UploadType.BANK)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) == 0

    def test_bank_missing_entry_date(self, sample_tb_no_amounts):
        """File without entry_date or amount → VAL-001 for both."""
        errors = validate_upload(sample_tb_no_amounts, UploadType.BANK)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "entry_date" in missing_fields
        assert "amount" in missing_fields


class TestValidateDEBT:
    def test_valid_debt_no_blocking_errors(self, sample_debt_file):
        """DEBT file with amount → no blocking errors."""
        errors = validate_upload(sample_debt_file, UploadType.DEBT)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) == 0


class TestValidateEmptyHeaders:
    def test_empty_headers_returns_val000(self, sample_empty_headers_file):
        """File with empty first row → VAL-000."""
        errors = validate_upload(sample_empty_headers_file, UploadType.TB)
        assert len(errors) > 0
        assert errors[0].error_code == "VAL-000"
        assert errors[0].severity == ValidationSeverity.ERROR


class TestValidateDateWarning:
    def test_unparseable_date_returns_val011(self, sample_file_bad_dates):
        """Date column with unparseable format → VAL-011 warning."""
        errors = validate_upload(sample_file_bad_dates, UploadType.GL)
        warnings = [e for e in errors if e.severity == ValidationSeverity.WARNING]
        assert any(e.error_code == "VAL-011" for e in warnings)


class TestValidateMultipleErrors:
    def test_multiple_errors_same_file(self, sample_tb_no_amounts):
        """File validated as BANK should produce multiple VAL-001 errors."""
        errors = validate_upload(sample_tb_no_amounts, UploadType.BANK)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        # BANK requires entry_date + amount, TB-no-amounts has neither
        assert len(blocking) >= 2
        codes = [e.error_code for e in blocking]
        assert codes.count("VAL-001") >= 2


class TestValidateAP:
    def test_valid_ap_no_blocking_errors(self, sample_ap_file):
        """AP file with counterparty + amount → no blocking errors."""
        errors = validate_upload(sample_ap_file, UploadType.AP)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        assert len(blocking) == 0

    def test_ap_missing_counterparty_error(self, sample_debt_file):
        """DEBT file used as AP → missing 'counterparty' required field."""
        errors = validate_upload(sample_debt_file, UploadType.AP)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "counterparty" in missing_fields

    def test_ap_missing_amount_error(self, sample_tb_no_amounts):
        """File without 'amount' column used as AP → missing both required fields."""
        errors = validate_upload(sample_tb_no_amounts, UploadType.AP)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "counterparty" in missing_fields
        assert "amount" in missing_fields


class TestValidateLEASE:
    def test_lease_missing_amount_error(self, sample_tb_no_amounts):
        """File without 'amount' column used as LEASE → VAL-001."""
        errors = validate_upload(sample_tb_no_amounts, UploadType.LEASE)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "amount" in missing_fields


class TestValidateTBAmountCombinations:
    def test_tb_debit_only_no_credit_no_balance_fails(self, sample_tb_debit_only_file):
        """TB with debit column only (no credit, no balance) → VAL-002."""
        errors = validate_upload(sample_tb_debit_only_file, UploadType.TB)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        error_codes = [e.error_code for e in blocking]
        assert "VAL-002" in error_codes


class TestValidateGLAmountCombinations:
    def test_gl_debit_only_no_credit_no_amount_fails(self, sample_gl_debit_only_file):
        """GL with debit column only (no credit, no amount) → VAL-003."""
        errors = validate_upload(sample_gl_debit_only_file, UploadType.GL)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        error_codes = [e.error_code for e in blocking]
        assert "VAL-003" in error_codes


class TestValidateCrossTypeErrors:
    def test_debt_file_as_bank_missing_fields(self, sample_debt_file):
        """DEBT file validated as BANK → missing entry_date."""
        errors = validate_upload(sample_debt_file, UploadType.BANK)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "entry_date" in missing_fields

    def test_tb_file_as_debt_missing_amount(self, sample_tb_no_amounts):
        """TB-no-amounts file validated as DEBT → missing 'amount'."""
        errors = validate_upload(sample_tb_no_amounts, UploadType.DEBT)
        blocking = [e for e in errors if e.severity == ValidationSeverity.ERROR]
        missing_fields = [e.field_name for e in blocking if e.error_code == "VAL-001"]
        assert "amount" in missing_fields

    def test_empty_headers_as_gl_returns_val000(self, sample_empty_headers_file):
        """Empty headers validated as GL → VAL-000 (not just TB)."""
        errors = validate_upload(sample_empty_headers_file, UploadType.GL)
        assert len(errors) > 0
        assert errors[0].error_code == "VAL-000"


class TestValidateMoneyFieldEdgeCases:
    def test_money_currency_symbol_warning(self, sample_money_currency_symbol_file):
        """Currency symbols (₩) in money fields → VAL-010 warning."""
        errors = validate_upload(sample_money_currency_symbol_file, UploadType.TB)
        warnings = [e for e in errors if e.severity == ValidationSeverity.WARNING]
        assert any(e.error_code == "VAL-010" for e in warnings)

    def test_money_dash_no_warning(self, sample_money_dash_file):
        """Dash '-' in money fields is treated as zero — no warning."""
        errors = validate_upload(sample_money_dash_file, UploadType.TB)
        warnings = [e for e in errors if e.error_code == "VAL-010"]
        assert len(warnings) == 0

    def test_multiple_money_columns_warned(self, sample_multi_money_string_file):
        """Multiple money columns with strings → VAL-010 for each column."""
        errors = validate_upload(sample_multi_money_string_file, UploadType.TB)
        money_warnings = [e for e in errors if e.error_code == "VAL-010"]
        # Should warn for debit, credit, and balance columns (3 separate warnings)
        warned_fields = {e.field_name for e in money_warnings}
        assert len(warned_fields) >= 2


class TestValidationErrorStructure:
    def test_error_has_all_fields(self, sample_tb_no_amounts):
        errors = validate_upload(sample_tb_no_amounts, UploadType.TB)
        assert len(errors) > 0
        err = errors[0]
        assert err.severity is not None
        assert err.error_code is not None
        assert err.message is not None

    def test_error_has_suggestion(self, sample_tb_no_amounts):
        errors = validate_upload(sample_tb_no_amounts, UploadType.TB)
        for err in errors:
            if err.error_code == "VAL-002":
                assert err.suggestion is not None
