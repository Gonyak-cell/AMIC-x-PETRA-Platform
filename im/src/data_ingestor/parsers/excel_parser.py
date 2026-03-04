"""Excel 문서 파서.

openpyxl과 pandas를 사용하여 Excel 파일에서 데이터를 추출합니다.
재무제표, 사업계획서 등의 Excel 문서 처리를 지원합니다.

사용 예시:
    parser = ExcelParser()

    # 전체 파싱
    workbook = await parser.parse("financials.xlsx")

    # 특정 시트 읽기
    df = await parser.read_sheet("data.xlsx", sheet_name="재무제표")

    # 데이터프레임으로 변환
    df = workbook.sheets["Sheet1"].to_dataframe()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.data_ingestor.exceptions import ExcelParserError

if TYPE_CHECKING:
    import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ExcelCell:
    """Excel 셀 데이터."""

    row: int
    """행 번호 (1-indexed)."""

    column: int
    """열 번호 (1-indexed)."""

    value: Any
    """셀 값."""

    formula: str | None = None
    """셀 수식 (있는 경우)."""

    data_type: str = "unknown"
    """데이터 타입 (n=숫자, s=문자열, d=날짜 등)."""

    @property
    def column_letter(self) -> str:
        """열 문자 (A, B, C, ...)."""
        result = ""
        col = self.column
        while col > 0:
            col, remainder = divmod(col - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @property
    def address(self) -> str:
        """셀 주소 (예: A1, B2)."""
        return f"{self.column_letter}{self.row}"

    def as_number(self) -> Decimal | None:
        """숫자로 변환."""
        if self.value is None:
            return None
        try:
            return Decimal(str(self.value).replace(",", ""))
        except Exception:
            return None

    def as_string(self) -> str:
        """문자열로 변환."""
        if self.value is None:
            return ""
        return str(self.value).strip()


@dataclass
class ExcelSheet:
    """Excel 시트."""

    name: str
    """시트 이름."""

    rows: list[list[Any]]
    """행 데이터. 각 행은 셀 값의 리스트."""

    min_row: int = 1
    """데이터가 있는 최소 행 번호."""

    max_row: int = 0
    """데이터가 있는 최대 행 번호."""

    min_col: int = 1
    """데이터가 있는 최소 열 번호."""

    max_col: int = 0
    """데이터가 있는 최대 열 번호."""

    @property
    def row_count(self) -> int:
        """행 개수."""
        return len(self.rows)

    @property
    def column_count(self) -> int:
        """열 개수."""
        if self.rows:
            return max(len(row) for row in self.rows)
        return 0

    @property
    def header(self) -> list[Any]:
        """첫 번째 행 (헤더로 가정)."""
        return self.rows[0] if self.rows else []

    def get_cell(self, row: int, col: int) -> Any:
        """특정 셀 값 조회.

        Args:
            row: 행 번호 (1-indexed).
            col: 열 번호 (1-indexed).

        Returns:
            셀 값 또는 None.
        """
        row_idx = row - self.min_row
        col_idx = col - self.min_col

        if 0 <= row_idx < len(self.rows):
            row_data = self.rows[row_idx]
            if 0 <= col_idx < len(row_data):
                return row_data[col_idx]
        return None

    def to_dict_list(self, header_row: int = 1) -> list[dict[str, Any]]:
        """헤더를 키로 사용하여 딕셔너리 리스트로 변환.

        Args:
            header_row: 헤더 행 번호 (1-indexed).

        Returns:
            헤더를 키로 사용하는 딕셔너리 리스트.
        """
        header_idx = header_row - self.min_row
        if header_idx < 0 or header_idx >= len(self.rows):
            return []

        headers = [
            str(h) if h else f"col_{i}" for i, h in enumerate(self.rows[header_idx])
        ]
        result = []

        for row in self.rows[header_idx + 1 :]:
            record: dict[str, Any] = {}
            for i, value in enumerate(row):
                key = headers[i] if i < len(headers) else f"col_{i}"
                record[key] = value
            result.append(record)

        return result

    def to_dataframe(self, header_row: int = 1) -> pd.DataFrame:
        """pandas DataFrame으로 변환.

        Args:
            header_row: 헤더 행 번호 (1-indexed).

        Returns:
            pandas DataFrame.

        Raises:
            ExcelParserError: pandas가 설치되지 않은 경우.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ExcelParserError(
                file_path="(라이브러리)",
                reason="pandas가 설치되지 않았습니다. pip install pandas",
            ) from e

        header_idx = header_row - self.min_row
        if header_idx < 0 or header_idx >= len(self.rows):
            return pd.DataFrame(self.rows)

        headers = self.rows[header_idx]
        data = self.rows[header_idx + 1 :]
        return pd.DataFrame(data, columns=headers)


@dataclass
class ExcelWorkbook:
    """파싱된 Excel 워크북."""

    path: Path
    """원본 파일 경로."""

    sheets: dict[str, ExcelSheet] = field(default_factory=dict)
    """시트 이름 → ExcelSheet 매핑."""

    properties: dict[str, Any] = field(default_factory=dict)
    """워크북 속성 (author, created 등)."""

    @property
    def sheet_names(self) -> list[str]:
        """시트 이름 목록."""
        return list(self.sheets.keys())

    @property
    def sheet_count(self) -> int:
        """시트 개수."""
        return len(self.sheets)

    def get_sheet(self, name: str) -> ExcelSheet | None:
        """시트 이름으로 조회."""
        return self.sheets.get(name)

    def get_sheet_by_index(self, index: int) -> ExcelSheet | None:
        """인덱스로 시트 조회.

        Args:
            index: 시트 인덱스 (0-indexed).

        Returns:
            해당 시트 또는 None.
        """
        if 0 <= index < len(self.sheets):
            return list(self.sheets.values())[index]
        return None


class ExcelParser:
    """Excel 파일 파서.

    openpyxl을 사용하여 .xlsx 파일을 파싱하고,
    xlrd를 사용하여 .xls 파일을 파싱합니다.

    Attributes:
        data_only: True면 수식 대신 계산된 값을 읽음.

    Example:
        >>> parser = ExcelParser(data_only=True)
        >>> workbook = await parser.parse("financials.xlsx")
        >>> sheet = workbook.get_sheet("재무제표")
        >>> df = sheet.to_dataframe()
    """

    def __init__(self, *, data_only: bool = True) -> None:
        """ExcelParser 초기화.

        Args:
            data_only: True면 수식 대신 계산된 값을 읽음.
        """
        self.data_only = data_only
        self._openpyxl: Any = None

    def _ensure_openpyxl(self) -> Any:
        """openpyxl 라이브러리 로드."""
        if self._openpyxl is None:
            try:
                import openpyxl

                self._openpyxl = openpyxl
            except ImportError as e:
                raise ExcelParserError(
                    file_path="(라이브러리)",
                    reason="openpyxl이 설치되지 않았습니다. pip install openpyxl",
                ) from e
        return self._openpyxl

    async def parse(
        self,
        file_path: str | Path,
        *,
        sheets: list[str] | None = None,
        password: str | None = None,
    ) -> ExcelWorkbook:
        """Excel 파일을 파싱합니다.

        Args:
            file_path: Excel 파일 경로 (.xlsx, .xlsm).
            sheets: 파싱할 시트 이름 리스트. None이면 전체.
            password: 암호화된 파일의 비밀번호.

        Returns:
            파싱된 ExcelWorkbook.

        Raises:
            ExcelParserError: 파일을 열 수 없거나 파싱 실패.
        """
        path = Path(file_path)
        if not path.exists():
            raise ExcelParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        # 확장자 확인
        suffix = path.suffix.lower()
        if suffix not in (".xlsx", ".xlsm", ".xltx", ".xltm"):
            raise ExcelParserError(
                file_path=str(path),
                reason=f"지원하지 않는 파일 형식입니다: {suffix}",
            )

        return await asyncio.get_event_loop().run_in_executor(
            None,
            self._parse_sync,
            path,
            sheets,
            password,
        )

    def _parse_sync(
        self,
        path: Path,
        sheets: list[str] | None,
        password: str | None,
    ) -> ExcelWorkbook:
        """동기 Excel 파싱."""
        openpyxl = self._ensure_openpyxl()

        try:
            wb = openpyxl.load_workbook(
                str(path),
                data_only=self.data_only,
                read_only=True,
            )
        except Exception as e:
            raise ExcelParserError(
                file_path=str(path),
                reason=f"Excel 파일을 열 수 없습니다: {e}",
            ) from e

        try:
            # 워크북 속성
            properties: dict[str, Any] = {}
            if wb.properties:
                properties = {
                    "title": wb.properties.title,
                    "creator": wb.properties.creator,
                    "created": wb.properties.created,
                    "modified": wb.properties.modified,
                    "lastModifiedBy": wb.properties.lastModifiedBy,
                }

            # 시트 파싱
            parsed_sheets: dict[str, ExcelSheet] = {}
            target_sheets = sheets if sheets else wb.sheetnames

            for sheet_name in target_sheets:
                if sheet_name not in wb.sheetnames:
                    logger.warning("시트를 찾을 수 없습니다: %s", sheet_name)
                    continue

                ws = wb[sheet_name]

                # 행 데이터 추출
                rows: list[list[Any]] = []
                for row in ws.iter_rows():
                    row_data = [self._convert_cell_value(cell.value) for cell in row]
                    rows.append(row_data)

                parsed_sheets[sheet_name] = ExcelSheet(
                    name=sheet_name,
                    rows=rows,
                    min_row=ws.min_row or 1,
                    max_row=ws.max_row or 0,
                    min_col=ws.min_column or 1,
                    max_col=ws.max_column or 0,
                )

            return ExcelWorkbook(
                path=path,
                sheets=parsed_sheets,
                properties=properties,
            )

        finally:
            wb.close()

    def _convert_cell_value(self, value: Any) -> Any:
        """셀 값을 Python 타입으로 변환."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            return value.strip()
        return value

    async def read_sheet(
        self,
        file_path: str | Path,
        *,
        sheet_name: str | None = None,
        sheet_index: int = 0,
        header_row: int = 1,
    ) -> pd.DataFrame:
        """특정 시트를 DataFrame으로 읽습니다.

        Args:
            file_path: Excel 파일 경로.
            sheet_name: 시트 이름. None이면 sheet_index 사용.
            sheet_index: 시트 인덱스 (0-indexed).
            header_row: 헤더 행 번호 (1-indexed).

        Returns:
            pandas DataFrame.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ExcelParserError(
                file_path="(라이브러리)",
                reason="pandas가 설치되지 않았습니다. pip install pandas",
            ) from e

        path = Path(file_path)
        if not path.exists():
            raise ExcelParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        def _read_sync() -> pd.DataFrame:
            return pd.read_excel(
                str(path),
                sheet_name=sheet_name if sheet_name else sheet_index,
                header=header_row - 1,  # pandas는 0-indexed
            )

        return await asyncio.get_event_loop().run_in_executor(None, _read_sync)

    async def read_all_sheets(
        self,
        file_path: str | Path,
        *,
        header_row: int = 1,
    ) -> dict[str, pd.DataFrame]:
        """모든 시트를 DataFrame으로 읽습니다.

        Args:
            file_path: Excel 파일 경로.
            header_row: 헤더 행 번호 (1-indexed).

        Returns:
            시트 이름 → DataFrame 딕셔너리.
        """
        try:
            import pandas as pd
        except ImportError as e:
            raise ExcelParserError(
                file_path="(라이브러리)",
                reason="pandas가 설치되지 않았습니다. pip install pandas",
            ) from e

        path = Path(file_path)
        if not path.exists():
            raise ExcelParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        def _read_all_sync() -> dict[str, pd.DataFrame]:
            return pd.read_excel(
                str(path),
                sheet_name=None,  # 모든 시트
                header=header_row - 1,
            )

        return await asyncio.get_event_loop().run_in_executor(None, _read_all_sync)

    async def get_sheet_names(self, file_path: str | Path) -> list[str]:
        """시트 이름 목록을 조회합니다.

        Args:
            file_path: Excel 파일 경로.

        Returns:
            시트 이름 리스트.
        """
        openpyxl = self._ensure_openpyxl()
        path = Path(file_path)

        if not path.exists():
            raise ExcelParserError(
                file_path=str(path),
                reason="파일을 찾을 수 없습니다",
            )

        def _get_names_sync() -> list[str]:
            wb = openpyxl.load_workbook(str(path), read_only=True)
            try:
                return wb.sheetnames
            finally:
                wb.close()

        return await asyncio.get_event_loop().run_in_executor(None, _get_names_sync)

    async def validate_financial_data(
        self,
        workbook: ExcelWorkbook,
        *,
        required_columns: list[str] | None = None,
        sheet_name: str | None = None,
    ) -> list[str]:
        """재무 데이터 유효성을 검증합니다.

        Args:
            workbook: 검증할 워크북.
            required_columns: 필수 열 이름 리스트.
            sheet_name: 검증할 시트 이름. None이면 첫 번째 시트.

        Returns:
            검증 오류 메시지 리스트 (비어 있으면 성공).
        """
        errors: list[str] = []

        # 시트 선택
        if sheet_name:
            sheet = workbook.get_sheet(sheet_name)
            if not sheet:
                errors.append(f"시트를 찾을 수 없습니다: {sheet_name}")
                return errors
        else:
            sheet = workbook.get_sheet_by_index(0)
            if not sheet:
                errors.append("워크북에 시트가 없습니다.")
                return errors

        # 데이터 존재 확인
        if not sheet.rows:
            errors.append(f"시트 '{sheet.name}'에 데이터가 없습니다.")
            return errors

        # 필수 열 확인
        if required_columns:
            header = [str(h).strip() for h in sheet.header if h]
            for col in required_columns:
                if col not in header:
                    errors.append(f"필수 열이 없습니다: {col}")

        # 숫자 데이터 검증 (간단한 검사)
        for row_idx, row in enumerate(sheet.rows[1:], start=2):
            for col_idx, value in enumerate(row):
                # 빈 셀 건너뛰기
                if value is None or value == "":
                    continue

                # 숫자처럼 보이는데 변환 불가능한 경우
                if (
                    isinstance(value, str)
                    and value.replace(",", "")
                    .replace("-", "")
                    .replace(".", "")
                    .isdigit()
                ):
                    try:
                        float(value.replace(",", ""))
                    except ValueError:
                        col_letter = (
                            chr(65 + col_idx) if col_idx < 26 else f"col{col_idx}"
                        )
                        errors.append(
                            f"잘못된 숫자 형식: {col_letter}{row_idx} = '{value}'"
                        )

        return errors
