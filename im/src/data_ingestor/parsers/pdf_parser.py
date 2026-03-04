"""PDF 문서 파서.

PyMuPDF를 사용하여 PDF 문서에서 텍스트와 테이블을 추출합니다.
재무제표, 사업보고서 등의 PDF 문서 처리를 지원합니다.

사용 예시:
    pdf_parser = PDFParser()

    # 텍스트 추출
    text = await pdf_parser.extract_text("report.pdf")

    # 테이블 추출
    tables = await pdf_parser.extract_tables("financials.pdf")

    # 메타데이터 조회
    metadata = await pdf_parser.get_metadata("document.pdf")
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.data_ingestor.exceptions import PDFParserError, TableExtractionError

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


@dataclass
class PDFTable:
    """PDF에서 추출된 테이블."""

    page_number: int
    """테이블이 있는 페이지 번호 (1-indexed)."""

    rows: list[list[str]]
    """테이블 행 데이터. 각 행은 셀 값의 리스트."""

    bbox: tuple[float, float, float, float] | None = None
    """테이블 경계 박스 (x0, y0, x1, y1)."""

    header: list[str] = field(default_factory=list)
    """테이블 헤더 (첫 번째 행으로 추정)."""

    @property
    def column_count(self) -> int:
        """테이블의 열 개수."""
        if self.rows:
            return max(len(row) for row in self.rows)
        return 0

    @property
    def row_count(self) -> int:
        """테이블의 행 개수."""
        return len(self.rows)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "page_number": self.page_number,
            "rows": self.rows,
            "bbox": self.bbox,
            "header": self.header,
            "column_count": self.column_count,
            "row_count": self.row_count,
        }

    def to_records(self) -> list[dict[str, str]]:
        """헤더를 키로 사용하여 레코드 리스트로 변환.

        Returns:
            헤더를 키로 사용하는 딕셔너리 리스트.

        Example:
            >>> table.header = ["항목", "금액"]
            >>> table.rows = [["항목", "금액"], ["매출액", "100"]]
            >>> table.to_records()
            [{"항목": "매출액", "금액": "100"}]
        """
        if not self.header or len(self.rows) <= 1:
            return []

        records = []
        for row in self.rows[1:]:  # 헤더 제외
            record = {}
            for i, cell in enumerate(row):
                if i < len(self.header):
                    record[self.header[i]] = cell
            records.append(record)
        return records


@dataclass
class PDFPage:
    """PDF 페이지 정보."""

    number: int
    """페이지 번호 (1-indexed)."""

    text: str
    """페이지 텍스트 내용."""

    tables: list[PDFTable] = field(default_factory=list)
    """페이지 내 테이블 목록."""

    width: float = 0.0
    """페이지 너비 (포인트)."""

    height: float = 0.0
    """페이지 높이 (포인트)."""


@dataclass
class PDFDocument:
    """파싱된 PDF 문서."""

    path: Path
    """원본 파일 경로."""

    pages: list[PDFPage] = field(default_factory=list)
    """페이지 목록."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """문서 메타데이터."""

    @property
    def page_count(self) -> int:
        """총 페이지 수."""
        return len(self.pages)

    @property
    def all_text(self) -> str:
        """모든 페이지의 텍스트를 합친 결과."""
        return "\n\n".join(page.text for page in self.pages)

    @property
    def all_tables(self) -> list[PDFTable]:
        """모든 페이지의 테이블을 합친 결과."""
        tables = []
        for page in self.pages:
            tables.extend(page.tables)
        return tables

    def get_page(self, number: int) -> PDFPage | None:
        """특정 페이지 조회.

        Args:
            number: 페이지 번호 (1-indexed).

        Returns:
            해당 페이지 또는 None.
        """
        for page in self.pages:
            if page.number == number:
                return page
        return None


class PDFParser:
    """PDF 문서 파서.

    PyMuPDF(fitz)를 사용하여 PDF에서 텍스트와 테이블을 추출합니다.
    비동기 API를 제공하지만, 내부적으로는 동기 라이브러리를 사용합니다.

    Attributes:
        default_dpi: 이미지 추출 시 기본 DPI.
        table_detection_threshold: 테이블 감지 임계값.

    Example:
        >>> parser = PDFParser()
        >>> doc = await parser.parse("report.pdf")
        >>> print(f"페이지 수: {doc.page_count}")
        >>> for table in doc.all_tables:
        ...     print(f"테이블 ({table.row_count}x{table.column_count})")
    """

    def __init__(
        self,
        *,
        default_dpi: int = 150,
        table_detection_threshold: float = 0.5,
    ) -> None:
        """PDFParser 초기화.

        Args:
            default_dpi: 이미지 추출 시 기본 해상도.
            table_detection_threshold: 테이블 감지 민감도 (0.0~1.0).
        """
        self.default_dpi = default_dpi
        self.table_detection_threshold = table_detection_threshold
        self._fitz: Any = None

    def _ensure_fitz(self) -> Any:
        """PyMuPDF 라이브러리 로드."""
        if self._fitz is None:
            try:
                import fitz

                self._fitz = fitz
            except ImportError as e:
                raise PDFParserError(
                    file_path="(라이브러리)",
                    reason="PyMuPDF(fitz)가 설치되지 않았습니다. pip install pymupdf",
                ) from e
        return self._fitz

    async def parse(
        self,
        file_path: str | Path,
        *,
        pages: Sequence[int] | None = None,
        extract_tables: bool = True,
        password: str | None = None,
    ) -> PDFDocument:
        """PDF 문서를 파싱합니다.

        Args:
            file_path: PDF 파일 경로.
            pages: 파싱할 페이지 번호 리스트 (1-indexed). None이면 전체.
            extract_tables: 테이블 추출 여부.
            password: 암호화된 PDF의 비밀번호.

        Returns:
            파싱된 PDFDocument.

        Raises:
            PDFParserError: 파일을 열 수 없거나 파싱 실패.
        """
        path = Path(file_path)
        if not path.exists():
            raise PDFParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        # 동기 작업을 스레드풀에서 실행
        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._parse_sync,
            path,
            pages,
            extract_tables,
            password,
        )

    def _parse_sync(
        self,
        path: Path,
        pages: Sequence[int] | None,
        extract_tables: bool,
        password: str | None,
    ) -> PDFDocument:
        """동기 PDF 파싱."""
        fitz = self._ensure_fitz()

        try:
            doc = fitz.open(str(path))
        except Exception as e:
            raise PDFParserError(
                file_path=str(path),
                reason=f"PDF 파일을 열 수 없습니다: {e}",
            ) from e

        try:
            # 암호화된 문서 처리
            if doc.is_encrypted:
                if password:
                    if not doc.authenticate(password):
                        raise PDFParserError(
                            file_path=str(path),
                            reason="잘못된 비밀번호입니다",
                        )
                else:
                    raise PDFParserError(
                        file_path=str(path),
                        reason="암호화된 PDF입니다. 비밀번호를 입력하세요",
                    )

            # 메타데이터 추출
            metadata = dict(doc.metadata) if doc.metadata else {}

            # 페이지 처리
            pdf_pages: list[PDFPage] = []
            page_numbers = pages if pages else range(1, doc.page_count + 1)

            for page_num in page_numbers:
                if page_num < 1 or page_num > doc.page_count:
                    continue

                page = doc.load_page(page_num - 1)  # 0-indexed

                # 텍스트 추출
                text = page.get_text("text")

                # 테이블 추출
                tables: list[PDFTable] = []
                if extract_tables:
                    tables = self._extract_tables_from_page(page, page_num)

                pdf_pages.append(
                    PDFPage(
                        number=page_num,
                        text=text,
                        tables=tables,
                        width=page.rect.width,
                        height=page.rect.height,
                    )
                )

            return PDFDocument(
                path=path,
                pages=pdf_pages,
                metadata=metadata,
            )

        finally:
            doc.close()

    def _extract_tables_from_page(
        self,
        page: Any,
        page_number: int,
    ) -> list[PDFTable]:
        """페이지에서 테이블을 추출합니다.

        PyMuPDF의 텍스트 블록을 분석하여 테이블 구조를 추론합니다.
        """
        tables: list[PDFTable] = []

        try:
            # PyMuPDF의 테이블 감지 기능 사용 (fitz 1.18.0+)
            # 없으면 텍스트 기반 추론으로 폴백
            if hasattr(page, "find_tables"):
                found_tables = page.find_tables()
                for table in found_tables:
                    if hasattr(table, "extract"):
                        rows = table.extract()
                        if rows:
                            # 빈 셀 정리
                            cleaned_rows = [
                                [cell if cell else "" for cell in row] for row in rows
                            ]
                            header = cleaned_rows[0] if cleaned_rows else []

                            pdf_table = PDFTable(
                                page_number=page_number,
                                rows=cleaned_rows,
                                header=header,
                                bbox=table.bbox if hasattr(table, "bbox") else None,
                            )
                            tables.append(pdf_table)
            else:
                # 폴백: 텍스트 블록 기반 테이블 추론
                tables = self._infer_tables_from_text(page, page_number)

        except Exception as e:
            logger.warning("테이블 추출 실패 (페이지 %d): %s", page_number, e)

        return tables

    def _infer_tables_from_text(
        self,
        page: Any,
        page_number: int,
    ) -> list[PDFTable]:
        """텍스트 블록에서 테이블 구조를 추론합니다.

        탭/공백으로 구분된 열과 줄바꿈으로 구분된 행을 감지합니다.
        """
        tables: list[PDFTable] = []
        text = page.get_text("text")

        # 줄 단위로 분리
        lines = text.split("\n")

        # 연속된 구조화된 줄 그룹 찾기
        current_table_rows: list[list[str]] = []
        prev_col_count = 0

        for line in lines:
            line = line.strip()
            if not line:
                # 빈 줄이면 현재 테이블 종료
                if len(current_table_rows) >= 2:  # 최소 2행
                    tables.append(
                        PDFTable(
                            page_number=page_number,
                            rows=current_table_rows,
                            header=current_table_rows[0] if current_table_rows else [],
                        )
                    )
                current_table_rows = []
                prev_col_count = 0
                continue

            # 탭 또는 다중 공백으로 분리
            cells = re.split(r"\t|  +", line)
            cells = [c.strip() for c in cells if c.strip()]

            col_count = len(cells)

            # 열 개수가 일정하면 테이블로 간주
            if col_count >= 2:
                if prev_col_count == 0 or col_count == prev_col_count:
                    current_table_rows.append(cells)
                    prev_col_count = col_count
                else:
                    # 열 개수가 바뀌면 새 테이블 시작
                    if len(current_table_rows) >= 2:
                        tables.append(
                            PDFTable(
                                page_number=page_number,
                                rows=current_table_rows,
                                header=current_table_rows[0],
                            )
                        )
                    current_table_rows = [cells]
                    prev_col_count = col_count

        # 마지막 테이블 처리
        if len(current_table_rows) >= 2:
            tables.append(
                PDFTable(
                    page_number=page_number,
                    rows=current_table_rows,
                    header=current_table_rows[0],
                )
            )

        return tables

    async def extract_text(
        self,
        file_path: str | Path,
        *,
        pages: Sequence[int] | None = None,
        password: str | None = None,
    ) -> str:
        """PDF에서 텍스트만 추출합니다.

        Args:
            file_path: PDF 파일 경로.
            pages: 추출할 페이지 번호 리스트 (1-indexed).
            password: 암호화된 PDF의 비밀번호.

        Returns:
            추출된 텍스트.
        """
        doc = await self.parse(
            file_path,
            pages=pages,
            extract_tables=False,
            password=password,
        )
        return doc.all_text

    async def extract_tables(
        self,
        file_path: str | Path,
        *,
        pages: Sequence[int] | None = None,
        password: str | None = None,
    ) -> list[PDFTable]:
        """PDF에서 테이블만 추출합니다.

        Args:
            file_path: PDF 파일 경로.
            pages: 추출할 페이지 번호 리스트 (1-indexed).
            password: 암호화된 PDF의 비밀번호.

        Returns:
            추출된 테이블 리스트.

        Raises:
            TableExtractionError: 테이블 추출 실패.
        """
        try:
            doc = await self.parse(
                file_path,
                pages=pages,
                extract_tables=True,
                password=password,
            )
            return doc.all_tables
        except PDFParserError:
            raise
        except Exception as e:
            raise TableExtractionError(
                message=f"테이블 추출 실패: {e}",
                details={"path": str(file_path)},
            ) from e

    async def get_metadata(
        self,
        file_path: str | Path,
        password: str | None = None,
    ) -> dict[str, Any]:
        """PDF 메타데이터를 조회합니다.

        Args:
            file_path: PDF 파일 경로.
            password: 암호화된 PDF의 비밀번호.

        Returns:
            메타데이터 딕셔너리 (title, author, subject, creator 등).
        """
        path = Path(file_path)
        if not path.exists():
            raise PDFParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        fitz = self._ensure_fitz()

        def _get_metadata_sync() -> dict[str, Any]:
            doc = fitz.open(str(path))
            try:
                if doc.is_encrypted and password:
                    doc.authenticate(password)
                return dict(doc.metadata) if doc.metadata else {}
            finally:
                doc.close()

        return await asyncio.get_event_loop().run_in_executor(None, _get_metadata_sync)

    async def get_page_count(
        self,
        file_path: str | Path,
        password: str | None = None,
    ) -> int:
        """PDF 페이지 수를 조회합니다.

        Args:
            file_path: PDF 파일 경로.
            password: 암호화된 PDF의 비밀번호.

        Returns:
            총 페이지 수.
        """
        path = Path(file_path)
        if not path.exists():
            raise PDFParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        fitz = self._ensure_fitz()

        def _get_page_count_sync() -> int:
            doc = fitz.open(str(path))
            try:
                if doc.is_encrypted and password:
                    doc.authenticate(password)
                return doc.page_count
            finally:
                doc.close()

        return await asyncio.get_event_loop().run_in_executor(
            None, _get_page_count_sync
        )
