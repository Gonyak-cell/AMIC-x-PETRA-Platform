"""문서 파싱 패키지.

PDF, Excel 등 다양한 문서 형식에서 데이터를 추출하는 파서들을 제공합니다.

Usage::
    from src.data_ingestor.parsers import PDFParser, ExcelParser

    # PDF 파싱
    pdf_parser = PDFParser()
    tables = await pdf_parser.extract_tables("report.pdf")

    # Excel 파싱
    excel_parser = ExcelParser()
    data = await excel_parser.parse("financials.xlsx")
"""

from src.data_ingestor.parsers.excel_parser import ExcelParser
from src.data_ingestor.parsers.pdf_parser import PDFParser

__all__ = [
    "ExcelParser",
    "PDFParser",
]
