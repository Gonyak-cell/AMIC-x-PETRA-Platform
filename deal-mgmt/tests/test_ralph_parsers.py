"""Ralph Loop 파서 + 분류기 단위 테스트."""

from unittest.mock import patch


class TestParsedFile:
    """ParsedFile 데이터 모델 테스트."""

    def test_is_valid_with_text(self):
        from app.ralph.parsers.base import ParsedFile

        pf = ParsedFile(source_path="/test.txt", file_type="txt", text="hello")
        assert pf.is_valid is True

    def test_is_valid_with_error(self):
        from app.ralph.parsers.base import ParsedFile

        pf = ParsedFile(source_path="/test.txt", file_type="txt", parse_error="fail")
        assert pf.is_valid is False

    def test_is_valid_empty(self):
        from app.ralph.parsers.base import ParsedFile

        pf = ParsedFile(source_path="/test.txt", file_type="txt")
        assert pf.is_valid is False

    def test_summary(self):
        from app.ralph.parsers.base import ParsedFile, ParsedTable

        pf = ParsedFile(
            source_path="/test.txt",
            file_type="txt",
            text="A" * 1000,
            tables=[ParsedTable(headers=["col1", "col2"], rows=[["a", "b"]])],
        )
        s = pf.summary(max_chars=100)
        assert len(s) > 0
        assert "표:" in s


class TestParseFile:
    """parse_file 라우팅 테스트."""

    def test_unsupported_extension(self):
        from app.ralph.parsers import parse_file

        result = parse_file("/test.xyz")
        assert result.is_valid is False
        assert "지원하지 않는" in (result.parse_error or "")


class TestFileClassifier:
    """파일 분류기 테스트."""

    def test_classify_by_filename(self):
        from app.ralph.parsers.file_classifier import classify_file

        sections = classify_file("/data/L1_정관/정관_2024.pdf")
        assert "GOVERNANCE" in sections

    def test_classify_by_folder_keyword(self):
        from app.ralph.parsers.file_classifier import classify_file

        sections = classify_file("/project/소송/진행중_민사소송.docx")
        assert "LITIGATION" in sections

    def test_classify_contracts(self):
        from app.ralph.parsers.file_classifier import classify_file

        sections = classify_file("/data/L12_계약서/고객계약_모음.xlsx")
        assert "CONTRACTS" in sections

    def test_classify_tax(self):
        from app.ralph.parsers.file_classifier import classify_file

        sections = classify_file("/data/세무/법인세_신고서.pdf")
        assert "TAX" in sections

    def test_classify_with_parsed_content(self):
        from app.ralph.parsers.base import ParsedFile
        from app.ralph.parsers.file_classifier import classify_file

        parsed = ParsedFile(
            source_path="/unknown/file.pdf",
            file_type="pdf",
            text="본 토지 등기부등본에 의하면 저당권이 설정되어 있으며 부동산 감정 결과 환경오염 이력이 있습니다.",
        )
        sections = classify_file("/unknown/file.pdf", parsed)
        assert "REAL_ESTATE" in sections

    def test_scan_directory_nonexistent(self):
        from app.ralph.parsers.file_classifier import scan_directory

        result = scan_directory("/nonexistent/path/123")
        assert result == []


class TestPdfParser:
    def test_get_pdf_ocr_status_disabled(self, monkeypatch):
        from app.core.config import settings
        from app.ralph.parsers import pdf_parser

        original_enabled = settings.OCR_ENABLED
        try:
            monkeypatch.setattr(settings, "OCR_ENABLED", False)
            pdf_parser._cached_pdf_ocr_status.cache_clear()
            status = pdf_parser.get_pdf_ocr_status()
            assert status["enabled"] is False
            assert status["available"] is False
        finally:
            monkeypatch.setattr(settings, "OCR_ENABLED", original_enabled)
            pdf_parser._cached_pdf_ocr_status.cache_clear()

    def test_parse_pdf_uses_ocr_fallback_when_native_text_is_empty(self):
        from app.ralph.parsers.base import ParsedFile
        from app.ralph.parsers.pdf_parser import parse_pdf

        with (
            patch(
                "app.ralph.parsers.pdf_parser._parse_with_fitz",
                return_value=ParsedFile(source_path="/tmp/test.pdf", file_type="pdf", text="", metadata={"chunks": []}),
            ),
            patch(
                "app.ralph.parsers.pdf_parser._parse_with_pdfplumber",
                return_value=ParsedFile(source_path="/tmp/test.pdf", file_type="pdf", text="", metadata={"chunks": []}),
            ),
            patch(
                "app.ralph.parsers.pdf_parser._parse_with_ocr_if_available",
                return_value=ParsedFile(
                    source_path="/tmp/test.pdf",
                    file_type="pdf",
                    text="[Page 1]\nOCR recovered text",
                    metadata={"chunks": [{"chunk_id": "page-1"}], "ocr_used": True},
                ),
            ),
        ):
            result = parse_pdf("/tmp/test.pdf")

        assert "OCR recovered text" in result.text
        assert result.metadata.get("ocr_used") is True


class TestKoreanFinanceDict:
    """한국 재무 용어 파싱 테스트."""

    def test_parse_parenthetical_negative(self):
        from app.ralph.korean_finance_dict import parse_korean_number

        assert parse_korean_number("(500)") == -500.0

    def test_parse_currency(self):
        from app.ralph.korean_finance_dict import parse_korean_number

        assert parse_korean_number("₩1,000") == 1000.0

    def test_parse_percent(self):
        from app.ralph.korean_finance_dict import parse_korean_number

        # 퍼센트는 소수로 변환 (15.5% → 0.155)
        assert parse_korean_number("15.5%") == 0.155

    def test_parse_plain_number(self):
        from app.ralph.korean_finance_dict import parse_korean_number

        assert parse_korean_number("1,234,567") == 1234567.0

    def test_parse_invalid(self):
        from app.ralph.korean_finance_dict import parse_korean_number

        assert parse_korean_number("N/A") is None


class TestPrdManager:
    """PRD 매니저 테스트."""

    def test_load_prd_tm(self):
        from app.ralph.prd_manager import load_prd

        prd = load_prd("TM")
        assert prd["name"] == "Teaser Memo PRD"
        assert "sections" in prd

    def test_load_prd_ldd_full(self):
        from app.ralph.prd_manager import load_prd

        prd = load_prd("ldd_full")
        assert prd["document_type"] == "LDD_FULL"
        assert "GOVERNANCE" in prd["sections"]

    def test_load_prd_nonexistent(self):
        from app.ralph.prd_manager import load_prd

        # 존재하지 않는 PRD는 빈 딕셔너리 반환 (에러 아님)
        prd = load_prd("nonexistent_type_999")
        assert "sections" in prd


class TestConvergence:
    """수렴 조건 판정 테스트 — check_section(section_id, gate_result, tracker) API 사용."""

    def _make_gate_result(self, score: float, critical_flags: list[str] | None = None):
        from app.ralph.gates.base import GateResult, GateVerdict

        verdict = (
            GateVerdict.PASS if score >= 4.0 else (GateVerdict.CONDITIONAL_PASS if score >= 3.0 else GateVerdict.FAIL)
        )
        return GateResult(
            gate_name="test_gate",
            verdict=verdict,
            weighted_score=score,
            critical_flags=critical_flags or [],
        )

    def _make_tracker(self, section_id: str, scores: list[float], total_cost: float = 0.0):
        from app.ralph.progress_tracker import ProgressTracker

        tracker = ProgressTracker()
        for i, score in enumerate(scores):
            gr = self._make_gate_result(score)
            tracker.record(section_id, i + 1, gr)
        tracker._total_cost_usd = total_cost
        return tracker

    def test_passed(self):
        from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig

        checker = ConvergenceChecker(ConvergenceConfig(pass_threshold=4.0))
        gate = self._make_gate_result(4.2)
        tracker = self._make_tracker("sec1", [3.5])
        result = checker.check_section("sec1", gate, tracker)
        assert result.converged is True
        assert result.reason == "passed"

    def test_max_iterations(self):
        from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig

        checker = ConvergenceChecker(ConvergenceConfig(max_iterations_per_section=3))
        gate = self._make_gate_result(2.0)
        tracker = self._make_tracker("sec1", [1.0, 1.5, 2.0])  # 3 iterations recorded
        result = checker.check_section("sec1", gate, tracker)
        assert result.converged is True
        assert result.reason == "max_iterations"

    def test_budget_exceeded(self):
        from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig

        checker = ConvergenceChecker(ConvergenceConfig(max_cost_usd=10.0))
        gate = self._make_gate_result(2.0)
        tracker = self._make_tracker("sec1", [1.5], total_cost=15.0)
        result = checker.check_section("sec1", gate, tracker)
        assert result.converged is True
        assert result.reason == "budget_exceeded"

    def test_critical_flag(self):
        from app.ralph.convergence import ConvergenceChecker

        checker = ConvergenceChecker()
        gate = self._make_gate_result(4.5, critical_flags=["deal breaker"])
        tracker = self._make_tracker("sec1", [])
        result = checker.check_section("sec1", gate, tracker)
        assert result.converged is True
        assert result.reason == "critical_flag"

    def test_diminishing_returns(self):
        from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig

        checker = ConvergenceChecker(ConvergenceConfig(improvement_threshold=0.5))
        gate = self._make_gate_result(3.5)
        tracker = self._make_tracker("sec1", [3.2, 3.4])  # improvement = 0.2 < 0.5
        result = checker.check_section("sec1", gate, tracker)
        assert result.converged is True
        assert result.reason == "diminishing_returns"

    def test_continue(self):
        from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig

        checker = ConvergenceChecker(ConvergenceConfig(pass_threshold=4.0, max_iterations_per_section=5))
        gate = self._make_gate_result(3.0)
        tracker = self._make_tracker("sec1", [2.0])  # 1 iteration, big improvement
        result = checker.check_section("sec1", gate, tracker)
        assert result.converged is False
