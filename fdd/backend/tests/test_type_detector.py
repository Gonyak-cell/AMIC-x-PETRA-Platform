"""Tests for upload type auto-detection (FDD-201)."""

from app.models.upload import UploadType
from app.services.ingestion.type_detector import detect_upload_type, normalize_header


class TestNormalizeHeader:
    def test_korean_account_code(self):
        assert normalize_header("계정코드") == "account_code"

    def test_korean_account_name(self):
        assert normalize_header("계정명") == "account_name"

    def test_korean_debit(self):
        assert normalize_header("차변") == "debit"

    def test_korean_credit(self):
        assert normalize_header("대변") == "credit"

    def test_korean_balance(self):
        assert normalize_header("잔액") == "balance"

    def test_korean_entry_id(self):
        assert normalize_header("전표번호") == "entry_id"

    def test_korean_entry_date(self):
        assert normalize_header("전표일자") == "entry_date"

    def test_korean_description(self):
        assert normalize_header("적요") == "description"

    def test_korean_counterparty(self):
        assert normalize_header("거래처") == "counterparty"

    def test_english_passthrough(self):
        assert normalize_header("debit") == "debit"
        assert normalize_header("credit") == "credit"
        assert normalize_header("amount") == "amount"

    def test_english_with_spaces(self):
        assert normalize_header("account code") == "account_code"
        assert normalize_header("account name") == "account_name"

    def test_whitespace_handling(self):
        assert normalize_header("  계정명  ") == "account_name"

    def test_empty_header(self):
        assert normalize_header("") is None

    def test_unknown_header(self):
        assert normalize_header("unknown_xyz_123") is None


class TestDetectUploadType:
    def test_detect_tb(self, sample_tb_file):
        result = detect_upload_type(sample_tb_file)
        assert result.detected_type == UploadType.TB
        assert result.confidence is not None
        assert result.confidence > 0.3

    def test_detect_gl(self, sample_gl_file):
        result = detect_upload_type(sample_gl_file)
        assert result.detected_type == UploadType.GL
        assert result.confidence is not None
        assert result.confidence > 0.3

    def test_tb_has_expected_headers(self, sample_tb_file):
        result = detect_upload_type(sample_tb_file)
        assert "account_code" in result.normalized_headers
        assert "account_name" in result.normalized_headers

    def test_gl_has_expected_headers(self, sample_gl_file):
        result = detect_upload_type(sample_gl_file)
        assert "entry_id" in result.normalized_headers
        assert "entry_date" in result.normalized_headers
        assert "account_code" in result.normalized_headers

    def test_all_scores_populated(self, sample_tb_file):
        result = detect_upload_type(sample_tb_file)
        assert len(result.all_scores) > 0

    def test_detect_gl_with_preamble_rows(self, tmp_path):
        from openpyxl import Workbook

        path = tmp_path / "uncore_gl.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append([None, None, None, None])
        ws.append([None, None, None, "subtotal"])
        ws.append([None, None, None, None])
        ws.append(
            [
                "회계연월",
                "회계일",
                "구분",
                "계정",
                "계정명",
                "전표번호",
                "비고",
                "차변금액(자국)",
                "대변금액(자국)",
                "거래처명",
                "순번",
            ]
        )
        ws.append(
            [
                "2025-01",
                "2025-01-31",
                "자산",
                "1110104",
                "보통예금",
                "GL-001",
                "입금",
                1000,
                0,
                "거래처",
                1,
            ]
        )
        wb.save(path)

        result = detect_upload_type(str(path))

        assert result.detected_type == UploadType.GL
        assert result.confidence is not None
        assert result.confidence >= 0.8
        assert "account_code" in result.normalized_headers
        assert "entry_date" in result.normalized_headers
