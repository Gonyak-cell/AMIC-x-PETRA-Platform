"""파서 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.data_ingestor.exceptions import ExcelParserError, PDFParserError
from src.data_ingestor.parsers.excel_parser import ExcelParser, ExcelSheet
from src.data_ingestor.parsers.pdf_parser import PDFDocument, PDFPage, PDFParser, PDFTable


class TestPDFTable:
    """PDFTable 데이터클래스 테스트."""

    def test_column_count(self) -> None:
        """열 개수 속성 테스트."""
        table = PDFTable(
            page_number=1,
            rows=[["A", "B", "C"], ["1", "2", "3"]],
        )
        assert table.column_count == 3

    def test_row_count(self) -> None:
        """행 개수 속성 테스트."""
        table = PDFTable(
            page_number=1,
            rows=[["A", "B"], ["1", "2"], ["3", "4"]],
        )
        assert table.row_count == 3

    def test_to_records(self) -> None:
        """레코드 변환 테스트."""
        table = PDFTable(
            page_number=1,
            rows=[["항목", "금액"], ["매출액", "100"], ["영업이익", "50"]],
            header=["항목", "금액"],
        )
        records = table.to_records()

        assert len(records) == 2
        assert records[0] == {"항목": "매출액", "금액": "100"}
        assert records[1] == {"항목": "영업이익", "금액": "50"}


class TestPDFDocument:
    """PDFDocument 데이터클래스 테스트."""

    def test_all_text(self) -> None:
        """전체 텍스트 속성 테스트."""
        doc = PDFDocument(
            path=Path("test.pdf"),
            pages=[
                PDFPage(number=1, text="페이지 1 내용"),
                PDFPage(number=2, text="페이지 2 내용"),
            ],
        )
        assert "페이지 1 내용" in doc.all_text
        assert "페이지 2 내용" in doc.all_text

    def test_get_page(self) -> None:
        """페이지 조회 테스트."""
        doc = PDFDocument(
            path=Path("test.pdf"),
            pages=[
                PDFPage(number=1, text="첫 페이지"),
                PDFPage(number=2, text="두 번째 페이지"),
            ],
        )

        page = doc.get_page(1)
        assert page is not None
        assert page.text == "첫 페이지"

        assert doc.get_page(99) is None


class TestPDFParser:
    """PDFParser 테스트."""

    def test_init_default_values(self) -> None:
        """기본값 초기화 테스트."""
        parser = PDFParser()
        assert parser.default_dpi == 150
        assert parser.table_detection_threshold == 0.5

    def test_init_custom_values(self) -> None:
        """커스텀 값 초기화 테스트."""
        parser = PDFParser(default_dpi=300, table_detection_threshold=0.8)
        assert parser.default_dpi == 300
        assert parser.table_detection_threshold == 0.8

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self) -> None:
        """존재하지 않는 파일 파싱 테스트."""
        parser = PDFParser()

        with pytest.raises(PDFParserError):
            await parser.parse("/nonexistent/file.pdf")


class TestExcelSheet:
    """ExcelSheet 데이터클래스 테스트."""

    def test_row_count(self) -> None:
        """행 개수 테스트."""
        sheet = ExcelSheet(
            name="Sheet1",
            rows=[["A", "B"], ["1", "2"], ["3", "4"]],
        )
        assert sheet.row_count == 3

    def test_column_count(self) -> None:
        """열 개수 테스트."""
        sheet = ExcelSheet(
            name="Sheet1",
            rows=[["A", "B", "C"], ["1", "2", "3"]],
        )
        assert sheet.column_count == 3

    def test_get_cell(self) -> None:
        """셀 조회 테스트."""
        sheet = ExcelSheet(
            name="Sheet1",
            rows=[["A", "B"], ["1", "2"]],
            min_row=1,
            min_col=1,
        )

        assert sheet.get_cell(1, 1) == "A"
        assert sheet.get_cell(2, 2) == "2"
        assert sheet.get_cell(99, 99) is None

    def test_to_dict_list(self) -> None:
        """딕셔너리 리스트 변환 테스트."""
        sheet = ExcelSheet(
            name="Sheet1",
            rows=[["이름", "나이"], ["홍길동", 30], ["김철수", 25]],
            min_row=1,
        )
        records = sheet.to_dict_list()

        assert len(records) == 2
        assert records[0] == {"이름": "홍길동", "나이": 30}


class TestExcelParser:
    """ExcelParser 테스트."""

    def test_init_default_data_only(self) -> None:
        """기본 data_only 옵션 테스트."""
        parser = ExcelParser()
        assert parser.data_only is True

    def test_init_custom_data_only(self) -> None:
        """커스텀 data_only 옵션 테스트."""
        parser = ExcelParser(data_only=False)
        assert parser.data_only is False

    @pytest.mark.asyncio
    async def test_parse_file_not_found(self) -> None:
        """존재하지 않는 파일 파싱 테스트."""
        parser = ExcelParser()

        with pytest.raises(ExcelParserError):
            await parser.parse("/nonexistent/file.xlsx")

    @pytest.mark.asyncio
    async def test_parse_unsupported_format(self) -> None:
        """지원하지 않는 형식 테스트."""
        parser = ExcelParser()

        # 임시 파일 생성
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(ExcelParserError):
                await parser.parse("test.csv")
