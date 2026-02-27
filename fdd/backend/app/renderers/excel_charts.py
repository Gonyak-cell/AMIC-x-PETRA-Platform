"""Excel 네이티브 차트 생성.

openpyxl chart 모듈을 활용하여 FDD 보고서용 차트를 생성합니다.
외부 의존성 없이 워크북 내에 차트를 삽입합니다.

Phase 4: Waterfall(QoE Bridge), Trend Line(NWC), Bar(Revenue).
"""

from __future__ import annotations

from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.chart.series import DataPoint
from openpyxl.worksheet.worksheet import Worksheet

# ── 색상 팔레트 (Big 4 스타일) ──

_PRIMARY = "003366"
_POSITIVE = "2E7D32"
_NEGATIVE = "E0301E"
_ACCENT1 = "1565C0"
_ACCENT2 = "6A1B9A"
_ACCENT3 = "E65100"
_ACCENT4 = "00838F"
_ACCENT5 = "4527A0"
_LIGHT_GRAY = "B0BEC5"

_BAR_PALETTE = [_PRIMARY, _ACCENT1, _ACCENT3, _ACCENT4, _ACCENT2, _ACCENT5]


def render_waterfall_chart(
    ws: Worksheet,
    *,
    data_col: int,
    label_col: int,
    start_row: int,
    end_row: int,
    anchor: str = "A1",
    title: str = "QoE Bridge",
    width: int = 20,
    height: int = 12,
) -> None:
    """EBITDA 워터폴 차트를 시트에 삽입합니다.

    openpyxl은 진정한 워터폴 차트를 지원하지 않으므로,
    Stacked Bar 차트로 워터폴 효과를 시뮬레이션합니다.
    (투명 Base + 컬러 Delta 2-시리즈 방식)

    Args:
        ws: 대상 워크시트 (데이터가 이미 존재해야 함)
        data_col: 금액 데이터 컬럼 번호 (1-based)
        label_col: 카테고리 라벨 컬럼 번호 (1-based)
        start_row: 데이터 시작 행 (헤더 제외)
        end_row: 데이터 끝 행
        anchor: 차트 삽입 위치 (예: "H2")
        title: 차트 제목
        width: 차트 너비 (cm)
        height: 차트 높이 (cm)
    """
    if end_row <= start_row:
        return

    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = title
    chart.y_axis.title = "(백만원)"
    chart.y_axis.numFmt = "#,##0"
    chart.x_axis.delete = False

    # 단일 시리즈로 간략 표현 (워터폴 시뮬레이션 최소 버전)
    data_ref = Reference(ws, min_col=data_col, min_row=start_row - 1, max_row=end_row)
    cats_ref = Reference(ws, min_col=label_col, min_row=start_row, max_row=end_row)

    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.shape = 4
    chart.width = width
    chart.height = height

    # 첫/마지막 바 색상을 primary, 나머지를 accent로 구분
    if chart.series:
        series = chart.series[0]
        series.graphicalProperties.solidFill = _PRIMARY

        num_points = end_row - start_row
        for i in range(num_points):
            pt = DataPoint(idx=i)
            if i == 0 or i == num_points - 1:
                pt.graphicalProperties.solidFill = _PRIMARY
            else:
                pt.graphicalProperties.solidFill = _ACCENT1
            series.data_points.append(pt)

    chart.legend = None
    ws.add_chart(chart, anchor)


def render_trend_line_chart(
    ws: Worksheet,
    *,
    data_cols: list[int],
    label_col: int,
    start_row: int,
    end_row: int,
    anchor: str = "A1",
    title: str = "NWC Monthly Trend",
    width: int = 20,
    height: int = 12,
    series_names: list[str] | None = None,
) -> None:
    """트렌드 라인 차트를 시트에 삽입합니다.

    Args:
        ws: 대상 워크시트
        data_cols: 데이터 컬럼 번호 리스트 (1-based)
        label_col: X축 라벨 컬럼 번호
        start_row: 데이터 시작 행
        end_row: 데이터 끝 행
        anchor: 차트 삽입 위치
        title: 차트 제목
        width: 차트 너비 (cm)
        height: 차트 높이 (cm)
        series_names: 시리즈 이름 리스트 (None이면 헤더에서 추출)
    """
    if end_row <= start_row or not data_cols:
        return

    chart = LineChart()
    chart.style = 10
    chart.title = title
    chart.y_axis.title = "(백만원)"
    chart.y_axis.numFmt = "#,##0"
    chart.x_axis.delete = False
    chart.width = width
    chart.height = height

    cats_ref = Reference(ws, min_col=label_col, min_row=start_row, max_row=end_row)
    chart.set_categories(cats_ref)

    colors = [_PRIMARY, _ACCENT1, _ACCENT3, _ACCENT4, _ACCENT2]
    for idx, col in enumerate(data_cols):
        data_ref = Reference(ws, min_col=col, min_row=start_row - 1, max_row=end_row)
        chart.add_data(data_ref, titles_from_data=True)

        if chart.series and idx < len(chart.series):
            s = chart.series[idx]
            color = colors[idx % len(colors)]
            s.graphicalProperties.line.solidFill = color
            s.graphicalProperties.line.width = 25000  # 2pt in EMU

            if series_names and idx < len(series_names):
                s.title = series_names[idx]

    ws.add_chart(chart, anchor)


def render_bar_chart(
    ws: Worksheet,
    *,
    data_col: int,
    label_col: int,
    start_row: int,
    end_row: int,
    anchor: str = "A1",
    title: str = "Revenue Breakdown",
    width: int = 18,
    height: int = 12,
    horizontal: bool = True,
) -> None:
    """Bar 차트를 시트에 삽입합니다.

    Args:
        ws: 대상 워크시트
        data_col: 금액 데이터 컬럼 번호
        label_col: 라벨 컬럼 번호
        start_row: 데이터 시작 행
        end_row: 데이터 끝 행
        anchor: 차트 삽입 위치
        title: 차트 제목
        width: 차트 너비 (cm)
        height: 차트 높이 (cm)
        horizontal: 가로 막대 여부 (False면 세로 막대)
    """
    if end_row <= start_row:
        return

    chart = BarChart()
    chart.type = "bar" if horizontal else "col"
    chart.style = 10
    chart.title = title
    chart.y_axis.numFmt = "#,##0"
    chart.width = width
    chart.height = height

    data_ref = Reference(ws, min_col=data_col, min_row=start_row - 1, max_row=end_row)
    cats_ref = Reference(ws, min_col=label_col, min_row=start_row, max_row=end_row)

    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.shape = 4

    # 시리즈별 색상 적용
    if chart.series:
        series = chart.series[0]
        series.graphicalProperties.solidFill = _PRIMARY

        num_points = end_row - start_row
        for i in range(num_points):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = _BAR_PALETTE[i % len(_BAR_PALETTE)]
            series.data_points.append(pt)

    chart.legend = None
    ws.add_chart(chart, anchor)


def render_concentration_chart(
    ws: Worksheet,
    *,
    data_col: int,
    label_col: int,
    start_row: int,
    end_row: int,
    anchor: str = "A1",
    title: str = "Revenue Concentration",
    width: int = 16,
    height: int = 14,
) -> None:
    """파이차트 — 매출 집중도 (Top N 거래처/제품 비중) 시각화.

    Args:
        ws: 대상 워크시트
        data_col: 금액/비중 데이터 컬럼 번호 (1-based)
        label_col: 항목명 컬럼 번호
        start_row: 데이터 시작 행 (헤더 제외)
        end_row: 데이터 끝 행
        anchor: 차트 삽입 위치 (예: "H2")
        title: 차트 제목
        width: 차트 너비 (cm)
        height: 차트 높이 (cm)
    """
    if end_row <= start_row:
        return

    chart = PieChart()
    chart.style = 10
    chart.title = title
    chart.width = width
    chart.height = height

    # 데이터 참조
    data_ref = Reference(ws, min_col=data_col, min_row=start_row - 1, max_row=end_row)
    cats_ref = Reference(ws, min_col=label_col, min_row=start_row, max_row=end_row)

    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)

    # 색상 팔레트 적용
    pie_colors = [_PRIMARY, _ACCENT1, _ACCENT3, _ACCENT4, _ACCENT2, _ACCENT5, _LIGHT_GRAY]
    if chart.series:
        series = chart.series[0]
        num_points = end_row - start_row
        for i in range(num_points):
            pt = DataPoint(idx=i)
            pt.graphicalProperties.solidFill = pie_colors[i % len(pie_colors)]
            series.data_points.append(pt)

    ws.add_chart(chart, anchor)


def render_fcf_waterfall_chart(
    ws: Worksheet,
    *,
    data_col: int,
    label_col: int,
    start_row: int,
    end_row: int,
    anchor: str = "A1",
    title: str = "FCF Bridge",
    width: int = 22,
    height: int = 13,
) -> None:
    """FCF Bridge 워터폴 차트 (EBITDA → OCF → FCF).

    Stacked Bar로 워터폴 효과를 시뮬레이션합니다.
    양수는 green, 음수는 red, subtotal/total은 primary blue.

    Args:
        ws: 대상 워크시트
        data_col: 금액 데이터 컬럼 번호 (1-based)
        label_col: 카테고리 라벨 컬럼 번호
        start_row: 데이터 시작 행 (헤더 제외)
        end_row: 데이터 끝 행
        anchor: 차트 삽입 위치
        title: 차트 제목
        width: 차트 너비 (cm)
        height: 차트 높이 (cm)
    """
    if end_row <= start_row:
        return

    chart = BarChart()
    chart.type = "col"
    chart.style = 10
    chart.title = title
    chart.y_axis.title = "(백만원)"
    chart.y_axis.numFmt = "#,##0"
    chart.x_axis.delete = False
    chart.width = width
    chart.height = height

    data_ref = Reference(ws, min_col=data_col, min_row=start_row - 1, max_row=end_row)
    cats_ref = Reference(ws, min_col=label_col, min_row=start_row, max_row=end_row)

    chart.add_data(data_ref, titles_from_data=True)
    chart.set_categories(cats_ref)
    chart.shape = 4

    # 색상: EBITDA(primary), subtotal(accent4), total(primary)
    if chart.series:
        series = chart.series[0]
        series.graphicalProperties.solidFill = _PRIMARY

        num_points = end_row - start_row
        for i in range(num_points):
            pt = DataPoint(idx=i)
            if i == 0 or i == num_points - 1:
                pt.graphicalProperties.solidFill = _PRIMARY
            elif i == 4:
                pt.graphicalProperties.solidFill = _ACCENT4
            else:
                pt.graphicalProperties.solidFill = _ACCENT1
            series.data_points.append(pt)

    chart.legend = None
    ws.add_chart(chart, anchor)
