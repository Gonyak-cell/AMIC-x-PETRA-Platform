"""위즈코어 FDD Working Paper 로컬 생성 스크립트.

실사자료 폴더의 Excel 파일을 직접 파싱하여 DB 없이
Phase 1~5 엔진 → Report IR → Excel WP를 생성한다.

Usage:
    cd fdd/backend
    python -m scripts.generate_wp_local \
        --input-dir "C:\\...\\FDD" \
        --output ./generated/WizCore_FDD_WP.xlsx \
        --deal-name "위즈코어"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

# ── sys.path 설정 (fdd/backend를 기준으로) ─────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── 상수 ─────────────────────────────────────────────────
ZERO = Decimal("0")
Q4 = Decimal("0.0001")
_ONE_MILLION = Decimal("1000000")
_HUNDRED = Decimal("100")
_365 = Decimal("365")
_270 = Decimal("270")  # FY24.9M = 9개월

# ── 유틸리티 ───────────────────────────────────────────────


def _q(v: Decimal) -> Decimal:
    return v.quantize(Q4)


def _safe_decimal(value: object) -> Decimal:
    """안전한 Decimal 변환 (None/빈문자열 → 0)."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    s = str(value).strip().replace(",", "").replace(" ", "")
    if not s or s == "-":
        return ZERO
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return ZERO


def _to_millions(val: Decimal) -> Decimal:
    """원 단위 → 백만원 단위 변환."""
    if val == ZERO:
        return ZERO
    return _q(val / _ONE_MILLION)


def _fmt(amount: Decimal) -> str:
    """백만원 단위 금액 포맷."""
    if amount == ZERO:
        return ""
    return f"{amount:,.0f}"


def _pct(num: Decimal, den: Decimal) -> str:
    """비율 포맷 (분모=0이면 빈 문자열)."""
    if den == ZERO:
        return ""
    return f"{float(num / den * _HUNDRED):.1f}%"


def _p(msg: str) -> None:
    """Windows cp949 safe print."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", errors="replace").decode())


# ═══════════════════════════════════════════════════════════
# 품질 게이트 헬퍼
# ═══════════════════════════════════════════════════════════


def _run_gate_sync(
    gate: Any,
    artifact_json: str,
    prd_section: dict[str, Any],
    source_data: dict[str, Any] | None = None,
) -> Any:
    """async 게이트를 sync 환경에서 실행."""
    return asyncio.run(gate.evaluate(artifact_json, prd_section, source_data))


def _block_to_json(block: Any) -> str:
    """Report IR 블록 → JSON 문자열 (Programmatic Gate 입력용)."""
    if hasattr(block, "rows"):
        rows = block.rows
        title = getattr(block, "title", "")
        return json.dumps(
            {
                "type": "table",
                "title": title,
                "content": title,
                "rows": rows[:20],  # 토큰 절약: 상위 20행
            },
            ensure_ascii=False,
            default=str,
        )
    if hasattr(block, "issues"):
        return json.dumps(
            {
                "type": "issue",
                "issues": getattr(block, "issues", [])[:10],
                "content": str(getattr(block, "title", "")),
            },
            ensure_ascii=False,
            default=str,
        )
    return json.dumps(
        {"type": "unknown", "content": str(block)[:500]}, ensure_ascii=False
    )


def _block_to_dict(block: Any) -> dict[str, Any]:
    """Report IR 블록 → dict (validation.py 입력용)."""
    result: dict[str, Any] = {"title": getattr(block, "title", "")}
    if hasattr(block, "rows"):
        result["rows"] = block.rows
    if hasattr(block, "footer_rows"):
        result["footer_rows"] = block.footer_rows
    return result


# Guardrail 경고 수집용 (모듈 레벨)
_guardrail_warnings: list[str] = []


# ═══════════════════════════════════════════════════════════
# 파서 1: 재무제표 (33. 2024년 9월기준 재무제표.xlsx)
# ═══════════════════════════════════════════════════════════


def parse_financial_statements(input_dir: Path) -> dict[str, Any]:
    """재무상태표 + 손익계산서 파싱 (원 단위 → 백만원 변환).

    Returns:
        {"bs": {period: {항목: Decimal(백만원)}}, "is": {period: {항목: Decimal(백만원)}}}
    """
    candidates = list(input_dir.glob("*재무제표*.xlsx"))
    if not candidates:
        print("  [SKIP] No financial statements file")
        return {"bs": {}, "is": {}}

    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)

    result: dict[str, Any] = {"bs": {}, "is": {}}

    def _parse_sheet(
        ws: Any, period_labels: list[str]
    ) -> dict[str, dict[str, Decimal]]:
        """BS/IS 공통 파싱 — B/C, D/E coalesce 후 백만원 변환."""
        data: dict[str, dict[str, Decimal]] = {lbl: {} for lbl in period_labels}
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx <= 6:
                continue
            if not row or not row[0]:
                continue
            account_name = str(row[0]).strip()
            if not account_name or "표시과목" in account_name:
                continue
            cells = list(row) + [None] * 5
            cur = _safe_decimal(cells[1]) or _safe_decimal(cells[2])
            pri = _safe_decimal(cells[3]) or _safe_decimal(cells[4])
            data[period_labels[0]][account_name] = _to_millions(cur)
            data[period_labels[1]][account_name] = _to_millions(pri)
        return data

    if "재무상태표" in wb.sheetnames:
        result["bs"] = _parse_sheet(wb["재무상태표"], ["FY24.9M", "FY23"])
    if "손익계산서" in wb.sheetnames:
        result["is"] = _parse_sheet(wb["손익계산서"], ["FY24.9M", "FY23"])

    wb.close()
    return result


# ═══════════════════════════════════════════════════════════
# 파서 2: 사업부 매출이익 (12-1. 사업부 매출이익현황)
# ═══════════════════════════════════════════════════════════


def parse_business_unit_pl(input_dir: Path) -> dict[str, dict[str, Decimal]]:
    """사업부별 매출이익현황 → 연도별 {항목: 금액(백만원)}.

    Returns:
        {"FY2022": {"매출액": Decimal("22695"), ...}, "FY2023": {...}, ...}
    """
    candidates = list(input_dir.glob("*사업부*매출이익*.xlsx"))
    if not candidates:
        print("  [SKIP] No BU P&L file")
        return {}

    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return {}

    data: dict[str, dict[str, Decimal]] = {}
    period_cols: dict[int, str] = {}

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row is None:
            continue
        row_strs = [str(c).strip() if c else "" for c in row]

        if row_idx <= 3:
            for col_idx, cell_str in enumerate(row_strs):
                if "년" in cell_str and any(
                    y in cell_str for y in ["2022", "2023", "2024", "2025"]
                ):
                    label = cell_str.replace("년", "").strip()
                    if " " in label:
                        parts = label.split()
                        label = f"FY{parts[0]}.{parts[1]}"
                    else:
                        label = f"FY{label}"
                    period_cols[col_idx] = label
                    data[label] = {}
            continue

        if not period_cols:
            continue

        item_name = ""
        for ci in range(min(3, len(row_strs))):
            if row_strs[ci]:
                item_name = row_strs[ci]
                break
        if not item_name or item_name in ("단위", ""):
            continue

        for col_idx, label in period_cols.items():
            if col_idx < len(row):
                val = _safe_decimal(row[col_idx])
                if val != ZERO:
                    data[label][item_name] = val

    wb.close()
    return data


# ═══════════════════════════════════════════════════════════
# 파서 3: 고객사별 매출 (10 위즈코어_고객사별)
# ═══════════════════════════════════════════════════════════


def parse_customer_revenue(input_dir: Path) -> list[dict[str, Any]]:
    """고객사별 매출 → Revenue 엔진 입력 (원 단위 그대로, 엔진이 처리)."""
    candidates = list(input_dir.glob("*고객사별*.xlsx"))
    if not candidates:
        print("  [SKIP] No customer revenue file")
        return []

    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)
    entries: list[dict[str, Any]] = []

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        year_str = ""
        for ch in sheet_name:
            if ch.isdigit():
                year_str += ch
        if not year_str:
            continue
        period = f"FY{year_str[:4]}"
        if "3Q" in sheet_name or "3q" in sheet_name:
            period += ".3Q"

        header_map: dict[str, int] = {}
        data_start = 1

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row is None:
                continue
            row_strs = [str(c).strip().lower() if c else "" for c in row]
            if any(k in "".join(row_strs) for k in ["고객사", "매출금액", "매출월"]):
                for ci, h in enumerate(row_strs):
                    if "고객" in h:
                        header_map["customer"] = ci
                    elif "제품" in h:
                        header_map["product"] = ci
                    elif "매출금액" in h or "금액" in h:
                        header_map["amount"] = ci
                    elif "매출월" in h or "월" in h:
                        header_map["month"] = ci
                    elif "사업" in h or "판매" in h or "구분" in h:
                        header_map["segment"] = ci
                data_start = row_idx + 1
                break

        if "amount" not in header_map:
            continue

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx < data_start or row is None:
                continue
            amount = _safe_decimal(
                row[header_map["amount"]] if header_map["amount"] < len(row) else None
            )
            if amount == ZERO:
                continue

            customer = ""
            if "customer" in header_map and header_map["customer"] < len(row):
                customer = str(row[header_map["customer"]] or "").strip()
            segment = ""
            if "segment" in header_map and header_map["segment"] < len(row):
                segment = str(row[header_map["segment"]] or "").strip()
            product = ""
            if "product" in header_map and header_map["product"] < len(row):
                product = str(row[header_map["product"]] or "").strip()

            # "Unknown" 대신 fallback 체인
            cust_name = customer or segment or f"미분류({sheet_name})"
            prod_name = product or segment or f"미분류({sheet_name})"
            # "합계" 행 필터
            if any(k in cust_name for k in ["합계", "소계", "총계"]):
                continue

            month_str = ""
            if "month" in header_map and header_map["month"] < len(row):
                raw = row[header_map["month"]]
                if isinstance(raw, (datetime, date)):
                    month_str = raw.strftime("%Y-%m")
                elif raw:
                    month_str = str(raw).strip()[:7]

            entries.append(
                {
                    "customer_name": cust_name,
                    "product_name": prod_name,
                    "period": period,
                    "month": month_str,
                    "amount": str(amount),
                }
            )

    wb.close()
    print(f"    -> {len(entries)} revenue entries loaded")
    return entries


# ═══════════════════════════════════════════════════════════
# 파서 4: 매입원장 (13. 매입원장_고객사별 제품별 현황)
# ═══════════════════════════════════════════════════════════


def parse_purchase_ledger(input_dir: Path) -> list[dict[str, Any]]:
    """매입원장 총괄표 → Cost 엔진 입력."""
    candidates = list(input_dir.glob("*매입원장*.xlsx"))
    if not candidates:
        print("  [SKIP] No purchase ledger file")
        return []

    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)
    entries: list[dict[str, Any]] = []

    for sheet_name in wb.sheetnames:
        if "총괄표" not in sheet_name:
            continue
        ws = wb[sheet_name]
        year_str = ""
        for ch in sheet_name:
            if ch.isdigit():
                year_str += ch
        period = f"FY{year_str[:4]}" if year_str else "Unknown"
        if "3Q" in sheet_name or "3q" in sheet_name:
            period += ".3Q"

        header_map: dict[str, int] = {}
        data_start = 1

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row is None:
                continue
            row_strs = [str(c).strip().lower() if c else "" for c in row]
            joined = "".join(row_strs)
            if "매출금액" in joined or ("고객사" in joined and "금액" in joined):
                for ci, h in enumerate(row_strs):
                    if "고객" in h:
                        header_map["customer"] = ci
                    elif "제품" in h:
                        header_map["product"] = ci
                    elif "사업" in h or "형태" in h:
                        header_map["segment"] = ci
                    elif "매출금액" in h:
                        header_map["revenue"] = ci
                    elif "매입금액" in h:
                        header_map["cost"] = ci
                    elif "매출이익" in h and "율" not in h:
                        header_map["margin"] = ci
                    elif "이익율" in h or "이익률" in h:
                        header_map["margin_pct"] = ci
                data_start = row_idx + 1
                break

        if "revenue" not in header_map:
            continue

        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx < data_start or row is None:
                continue

            def _get(key: str) -> Any:
                idx = header_map.get(key)
                if idx is None or idx >= len(row):
                    return None
                return row[idx]

            revenue = _safe_decimal(_get("revenue"))
            cost = _safe_decimal(_get("cost"))
            if revenue == ZERO and cost == ZERO:
                continue
            cust = str(_get("customer") or "").strip()
            if any(k in cust for k in ["합계", "소계", "총계"]):
                continue

            entries.append(
                {
                    "customer": cust,
                    "product": str(_get("product") or "").strip(),
                    "segment": str(_get("segment") or "").strip(),
                    "period": period,
                    "revenue": str(revenue),
                    "cost": str(cost),
                    "margin": str(_safe_decimal(_get("margin"))),
                }
            )

    wb.close()
    print(f"    -> {len(entries)} purchase entries loaded")
    return entries


# ═══════════════════════════════════════════════════════════
# 파서 5: 차입금 현황표
# ═══════════════════════════════════════════════════════════


def parse_debt_schedule(input_dir: Path) -> list[dict[str, Any]]:
    """차입금 건별 내역 (원 단위 → 백만원 변환)."""
    debt_dir = input_dir / "26. 장단기차입금"
    candidates = list(debt_dir.glob("*차입금*현황*.xlsx")) if debt_dir.exists() else []
    if not candidates:
        candidates = list(input_dir.glob("**/차입금*현황*.xlsx"))
    if not candidates:
        print("  [SKIP] No debt schedule file")
        return []

    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return []

    items: list[dict[str, Any]] = []
    header_map: dict[str, int] = {}
    data_start = 1

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row is None:
            continue
        row_strs = [str(c).strip().lower() if c else "" for c in row]
        joined = "".join(row_strs)
        if "대출은행" in joined or ("구분" in joined and "잔액" in joined):
            for ci, h in enumerate(row_strs):
                if "은행" in h or "대출은행" in h:
                    header_map["bank"] = ci
                elif h == "구분":
                    header_map["type"] = ci
                elif "내용" in h or "상품" in h:
                    header_map["description"] = ci
                elif "이율" in h or "이 율" in h or "금리" in h:
                    header_map["rate"] = ci
                elif "잔액" in h:
                    header_map["balance"] = ci
                elif "만기" in h:
                    header_map["maturity"] = ci
                elif "최초차입금액" in h or "차입금액" in h:
                    header_map["original"] = ci
            data_start = row_idx + 1
            break

    if not header_map:
        wb.close()
        return []

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
        if row_idx < data_start or row is None:
            continue
        if len(row) < 3:
            continue

        def _get(key: str) -> Any:
            idx = header_map.get(key)
            if idx is None or idx >= len(row):
                return None
            return row[idx]

        balance = _safe_decimal(_get("balance"))
        if balance == ZERO:
            continue
        bank = str(_get("bank") or "").strip()
        if not bank:
            continue
        first_cell = str(row[0]).strip() if row[0] else ""
        if any(k in first_cell for k in ["합계", "소계"]):
            continue

        rate_raw = _get("rate")
        rate_str = ""
        rate_dec = ZERO
        if rate_raw is not None:
            rate_dec = _safe_decimal(rate_raw)
            if rate_dec != ZERO:
                rate_str = (
                    f"{float(rate_dec) * 100:.2f}%" if rate_dec < 1 else f"{rate_dec}%"
                )

        maturity_raw = _get("maturity")
        maturity_str = ""
        if isinstance(maturity_raw, (date, datetime)):
            maturity_str = maturity_raw.strftime("%Y-%m-%d")
        elif maturity_raw:
            maturity_str = str(maturity_raw).strip()

        balance_m = _to_millions(balance)
        items.append(
            {
                "item": f"{bank} - {str(_get('description') or str(_get('type') or '')).strip()}",
                "type": "debt",
                "balance": _fmt(balance_m),
                "adjustment": "",
                "adjusted": _fmt(balance_m),
                "rate": rate_str,
                "maturity": maturity_str,
                "_balance_dec": balance_m,
                "_rate_dec": rate_dec,
            }
        )

    wb.close()
    print(f"    -> {len(items)} debt items loaded")
    return items


# ═══════════════════════════════════════════════════════════
# 파서 6: 유형자산 감가상각비명세서
# ═══════════════════════════════════════════════════════════


def parse_fixed_assets(input_dir: Path) -> dict[str, dict[str, Decimal]]:
    """연도별 유형자산 합계 (원 단위 → 백만원)."""
    asset_dir = input_dir / "21. 유무형자산"
    candidates = (
        list(asset_dir.glob("*유형자산*감가상각*.xlsx")) if asset_dir.exists() else []
    )
    if not candidates:
        candidates = list(input_dir.glob("**/유형자산*감가상각*.xlsx"))
    if not candidates:
        print("  [SKIP] No fixed asset file")
        return {}

    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)
    result: dict[str, dict[str, Decimal]] = {}

    for sheet_name in wb.sheetnames:
        year_str = ""
        for ch in sheet_name:
            if ch.isdigit():
                year_str += ch
        if not year_str or len(year_str) < 4:
            continue
        period = f"FY{year_str[:4]}"
        ws = wb[sheet_name]
        totals = {
            "취득원가": ZERO,
            "감가상각누계": ZERO,
            "미상각잔액": ZERO,
            "당기상각비": ZERO,
        }

        for row in ws.iter_rows(values_only=True):
            if not row or not row[0]:
                continue
            if "합계" in str(row[0]).strip() or str(row[0]).strip() == "계":
                if len(row) >= 13:
                    totals["취득원가"] = _to_millions(_safe_decimal(row[2]))
                    totals["감가상각누계"] = _to_millions(_safe_decimal(row[11]))
                    totals["미상각잔액"] = _to_millions(_safe_decimal(row[12]))
                    totals["당기상각비"] = _to_millions(_safe_decimal(row[10]))

        result[period] = totals

    wb.close()
    return result


# ═══════════════════════════════════════════════════════════
# 파서 7: 현금 및 현금성자산
# ═══════════════════════════════════════════════════════════


def parse_cash(input_dir: Path) -> Decimal:
    """현금및현금성자산 합계 (백만원)."""
    candidates = list(input_dir.glob("*현금*현금성자산*.xlsx"))
    if not candidates:
        return ZERO
    path = candidates[0]
    print(f"  [PARSE] {path.name}")
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        wb.close()
        return ZERO
    total = ZERO
    for row in ws.iter_rows(values_only=True):
        if not row or not row[0]:
            continue
        if "합계" in str(row[0]).strip():
            for cell in row[1:]:
                val = _safe_decimal(cell)
                if val != ZERO:
                    total += val
    wb.close()
    return _to_millions(total)


# ═══════════════════════════════════════════════════════════
# 규칙 기반 코멘터리 엔진
# ═══════════════════════════════════════════════════════════


class RuleBasedCommentary:
    """데이터에서 자동으로 분석적 코멘터리를 생성한다."""

    def for_multiperiod_is(
        self,
        bu_pl: dict[str, dict[str, Decimal]],
    ) -> list[str]:
        """다기간 IS 코멘터리 (bullet points)."""
        bullets: list[str] = []
        periods = sorted(bu_pl.keys())
        if len(periods) < 2:
            return bullets

        for i in range(1, len(periods)):
            prev_p, curr_p = periods[i - 1], periods[i]
            prev_rev = bu_pl[prev_p].get("매출액", ZERO)
            curr_rev = bu_pl[curr_p].get("매출액", ZERO)
            if prev_rev != ZERO and curr_rev != ZERO:
                yoy = float((curr_rev - prev_rev) / prev_rev * _HUNDRED)
                direction = "증가" if yoy > 0 else "감소"
                bullets.append(
                    f"{curr_p} 매출 {abs(yoy):.1f}% {direction} ({_fmt(prev_rev)}M -> {_fmt(curr_rev)}M)"
                )

        # 마진 추이
        for p in periods:
            rev = bu_pl[p].get("매출액", ZERO)
            gp = bu_pl[p].get("매출이익", bu_pl[p].get("매출총이익", ZERO))
            if rev != ZERO and gp != ZERO:
                margin = float(gp / rev * _HUNDRED)
                bullets.append(f"{p} GP 마진 {margin:.1f}% (매출총이익 {_fmt(gp)}M)")

        # CAGR
        if len(periods) >= 3:
            first_rev = bu_pl[periods[0]].get("매출액", ZERO)
            last_rev = bu_pl[periods[-2]].get("매출액", ZERO)  # 3Q 제외, 직전 전체연도
            if first_rev > ZERO and last_rev > ZERO:
                n = len(periods) - 2
                if n > 0:
                    cagr = float((float(last_rev / first_rev) ** (1.0 / n) - 1) * 100)
                    bullets.append(
                        f"매출 CAGR ({periods[0]}~{periods[-2]}): {cagr:.1f}%"
                    )

        return bullets

    def for_revenue_concentration(
        self,
        hhi: Decimal,
        top5_share: Decimal,
        top1_name: str,
        top1_share: Decimal,
    ) -> list[str]:
        """매출 집중도 코멘터리."""
        bullets: list[str] = []
        if hhi > Decimal("2500"):
            bullets.append(f"고집중 시장 (HHI: {hhi:,.0f}) -- 특정 거래처 의존도 높음")
        elif hhi > Decimal("1500"):
            bullets.append(f"중집중 시장 (HHI: {hhi:,.0f})")
        else:
            bullets.append(f"분산 시장 (HHI: {hhi:,.0f})")

        if top1_share > Decimal("30"):
            bullets.append(
                f"최대 거래처 '{top1_name}' 비중 {top1_share:.1f}% -- Key-man risk 존재"
            )

        if top5_share > Decimal("70"):
            bullets.append(f"Top 5 거래처 비중 {top5_share:.1f}% -- 거래처 다변화 필요")

        return bullets

    def for_debt_schedule(
        self,
        debt_items: list[dict[str, Any]],
        cash: Decimal,
        ebitda: Decimal,
    ) -> list[str]:
        """차입금 분석 코멘터리."""
        bullets: list[str] = []
        total = sum(d.get("_balance_dec", ZERO) for d in debt_items)
        if total == ZERO:
            return bullets

        bullets.append(
            f"총 차입금 {_fmt(total)}M, 현금 {_fmt(cash)}M, Net Debt {_fmt(total - cash)}M"
        )

        # 가중평균 금리
        weighted_rate = ZERO
        for d in debt_items:
            bal = d.get("_balance_dec", ZERO)
            rate = d.get("_rate_dec", ZERO)
            if bal > ZERO and rate > ZERO:
                weighted_rate += bal * rate
        if total > ZERO and weighted_rate > ZERO:
            avg_rate = float(weighted_rate / total * _HUNDRED)
            bullets.append(f"가중평균 금리 {avg_rate:.2f}%")

        # Net Debt / EBITDA
        net_debt = total - cash
        if ebitda > ZERO:
            ratio = float(net_debt / ebitda)
            level = "양호" if ratio < 2 else ("주의" if ratio < 4 else "고레버리지")
            bullets.append(f"Net Debt/EBITDA {ratio:.1f}x -- {level}")

        # 만기 분석
        near_term = ZERO
        today = date.today()
        for d in debt_items:
            mat = d.get("maturity", "")
            if mat:
                try:
                    mat_date = datetime.strptime(mat, "%Y-%m-%d").date()
                    if (mat_date - today).days <= 365:
                        near_term += d.get("_balance_dec", ZERO)
                except ValueError:
                    pass
        if total > ZERO and near_term > ZERO:
            pct = float(near_term / total * _HUNDRED)
            bullets.append(
                f"12개월 내 만기 도래 {_fmt(near_term)}M ({pct:.0f}%) -- 차환 계획 확인 필요"
            )

        return bullets

    def for_nwc(
        self,
        nwc_data: dict[str, Any],
    ) -> list[str]:
        """NWC 코멘터리."""
        bullets: list[str] = []
        td = nwc_data.get("turnover_days", {})

        ar_days = td.get("ar_days", ZERO)
        inv_days = td.get("inventory_days", ZERO)
        ap_days = td.get("ap_days", ZERO)
        ccc = ar_days + inv_days - ap_days

        if ar_days > Decimal("60"):
            bullets.append(
                f"매출채권 회전일수 {ar_days:.0f}일 -- 업종 평균(45-60일) 대비 지연"
            )
        elif ar_days > ZERO:
            bullets.append(f"매출채권 회전일수 {ar_days:.0f}일")

        if inv_days > Decimal("90"):
            bullets.append(f"재고자산 회전일수 {inv_days:.0f}일 -- 재고 관리 점검 필요")
        elif inv_days > ZERO:
            bullets.append(f"재고자산 회전일수 {inv_days:.0f}일")

        if ap_days > ZERO:
            bullets.append(f"매입채무 회전일수 {ap_days:.0f}일")

        if ccc > ZERO:
            level = (
                "양호"
                if ccc < Decimal("60")
                else ("관리 필요" if ccc < Decimal("90") else "개선 시급")
            )
            bullets.append(f"Cash Conversion Cycle {ccc:.0f}일 -- {level}")

        return bullets

    def for_issues(
        self,
        bu_pl: dict[str, dict[str, Decimal]],
        hhi: Decimal,
        nwc_data: dict[str, Any],
        debt_items: list[dict],
        cash: Decimal,
        fs_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """자동 이슈 탐지 → IssueBlock 입력."""
        issues: list[dict[str, Any]] = []

        # 1. 영업적자 확인 (매출총이익 또는 영업이익 적자)
        for p, items in bu_pl.items():
            rev = items.get("매출액", ZERO)
            gp = items.get("매출이익", items.get("매출총이익", ZERO))
            if rev > ZERO and gp < ZERO:
                issues.append(
                    {
                        "title": f"{p} 매출총이익 적자",
                        "severity": "HIGH",
                        "category": "Profitability",
                        "description": f"{p} 매출총이익 적자 ({_fmt(gp)}M). 원가율 점검 필요.",
                        "status": "Open",
                    }
                )
            # GP 마진 급락 (전년 대비 -5%p 이상)
            if rev > ZERO and gp > ZERO:
                gp_margin = float(gp / rev * _HUNDRED)
                if gp_margin < 25:
                    issues.append(
                        {
                            "title": f"{p} GP 마진 악화",
                            "severity": "MEDIUM",
                            "category": "Profitability",
                            "description": f"{p} 매출총이익률 {gp_margin:.1f}%. 원가율 상승 추세 점검 필요.",
                            "status": "Open",
                        }
                    )

        # FY24.9M 재무제표 영업손실 확인
        is_fy24 = fs_data.get("is", {}).get("FY24.9M", {})
        for k, v in is_fy24.items():
            if "영업" in k and "손" in k and v < ZERO:
                issues.append(
                    {
                        "title": "FY24.9M 영업적자 (재무제표 기준)",
                        "severity": "HIGH",
                        "category": "Profitability",
                        "description": f"영업손실 {_fmt(abs(v))}M. 판관비 > 매출총이익.",
                        "status": "Open",
                    }
                )
                break
            if "영업" in k and "이익" in k and v < ZERO:
                issues.append(
                    {
                        "title": "FY24.9M 영업적자 (재무제표 기준)",
                        "severity": "HIGH",
                        "category": "Profitability",
                        "description": f"영업손실 {_fmt(abs(v))}M.",
                        "status": "Open",
                    }
                )
                break

        # 2. 매출 집중도
        if hhi > Decimal("2500"):
            issues.append(
                {
                    "title": "매출 고집중 (HHI > 2,500)",
                    "severity": "MEDIUM",
                    "category": "Revenue Risk",
                    "description": f"HHI {hhi:,.0f}. 특정 거래처 의존도 높아 거래처 이탈 시 매출 급감 리스크.",
                    "status": "Open",
                }
            )

        # 3. NWC
        td = nwc_data.get("turnover_days", {})
        if td.get("ar_days", ZERO) > Decimal("90"):
            issues.append(
                {
                    "title": "매출채권 회전 지연",
                    "severity": "MEDIUM",
                    "category": "Working Capital",
                    "description": f"AR Days {td['ar_days']:.0f}일. 대손 리스크 점검 필요.",
                    "status": "Open",
                }
            )

        # 4. 차입금 만기 집중
        total_debt = sum(d.get("_balance_dec", ZERO) for d in debt_items)
        if total_debt > ZERO:
            net_debt = total_debt - cash
            # 국고보조금 의존도 (FS에서 확인)
            for k, v in is_fy24.items():
                if "국고" in k or "보조금" in k:
                    if v > ZERO:
                        issues.append(
                            {
                                "title": "국고보조금 의존",
                                "severity": "MEDIUM",
                                "category": "Earnings Quality",
                                "description": f"국고보조금 {_fmt(v)}M -- Normalized EBITDA에서 제외 검토 필요.",
                                "status": "Open",
                            }
                        )
                    break

        return issues


# ═══════════════════════════════════════════════════════════
# LLM 코멘터리 오버레이 (Phase 4)
# ═══════════════════════════════════════════════════════════

_LLM_SYSTEM_PROMPT = """당신은 PE(사모펀드) 재무실사(FDD) 전문 분석가입니다.
Big 4 회계법인 수준의 분석 보고서를 작성합니다.

작성 원칙:
1. 한국어로 작성. 금액 단위는 백만원(M). 천 단위 구분자 사용.
2. 숫자를 단순 반복하지 말고, **원인 → 영향 → 시사점** 구조로 분석.
3. PE 투자자 관점: 밸류에이션 영향, EBITDA 조정 필요 항목, Deal Breaker 여부를 명시.
4. 구체적 수치를 인용하되, 반드시 YoY/QoQ 변동률과 함께 제시.
5. 추측 금지 — 데이터에 근거한 분석만 수행. "추정" 시에는 명확히 표시.
6. 각 불릿은 최소 2문장 이상으로 구체적 분석을 포함.
7. 전문 용어 사용: Adjusted EBITDA, Quality of Earnings, Normalized, Run-rate 등.
8. 마크다운 서식 사용: **굵게**, - 불릿, ### 소제목."""


class LLMCommentaryOverlay:
    """LLM으로 규칙 기반 코멘터리를 보강한다.

    규칙 코멘터리가 "무엇이 변했는지"를 설명하면,
    LLM은 "왜 변했고, 시사점은 무엇인지"를 추가한다.
    Guardrails로 할루시네이션/백분율/방향 불일치를 검증한다.
    """

    def __init__(
        self,
        router: Any,
        known_values: dict[str, str] | None = None,
        known_pcts: dict[str, str] | None = None,
        known_trends: dict[str, str] | None = None,
    ) -> None:
        self._router = router
        self._known_values = known_values or {}
        self._known_pcts = known_pcts or {}
        self._known_trends = known_trends or {}

    # 연도/기간 패턴 — false positive 방지
    _YEAR_PATTERN = re.compile(r"(19|20)\d{2}")  # 1900~2099

    def _validate_with_guardrails(self, text: str, section_id: str) -> str:
        """LLM 출력에 guardrails 검증을 적용한다.

        연도(2020~2029), 기간명(FY2024 등), 일수(365 등)는 false positive 제외.
        """
        global _guardrail_warnings
        try:
            from app.agents.guardrails import (
                validate_narrative_claims,
                validate_percentage_claims,
                validate_trend_direction,
            )

            # 1. 금액 할루시네이션 (연도/기간 필터링)
            if self._known_values:
                warnings = validate_narrative_claims(text, self._known_values)
                for w in warnings:
                    # false positive 필터: 연도(2020-2029), 일수(365, 270 등)
                    if self._is_false_positive(w):
                        continue
                    _p(f"      [GUARDRAIL] {section_id}: {w}")
                    _guardrail_warnings.append(f"[{section_id}] {w}")

            # 2. 백분율 오차
            if self._known_pcts:
                pct_warnings = validate_percentage_claims(text, self._known_pcts)
                for w in pct_warnings:
                    _p(f"      [GUARDRAIL] {section_id}: {w}")
                    _guardrail_warnings.append(f"[{section_id}] {w}")

            # 3. 방향 불일치
            if self._known_trends:
                trend_warnings = validate_trend_direction(text, self._known_trends)
                for w in trend_warnings:
                    _p(f"      [GUARDRAIL] {section_id}: {w}")
                    _guardrail_warnings.append(f"[{section_id}] {w}")

        except ImportError:
            pass  # guardrails 모듈 없으면 스킵

        return text

    @staticmethod
    def _is_false_positive(warning: str) -> bool:
        """Guardrail 경고가 false positive인지 판단한다."""
        import re

        # 경고 메시지에서 숫자 추출
        num_match = re.search(r"'([\d,]+\.?\d*)'", warning)
        if not num_match:
            return False
        num_str = num_match.group(1).replace(",", "")
        try:
            num_val = int(float(num_str))
        except (ValueError, OverflowError):
            return False

        # 연도 범위 (2000~2099)
        if 2000 <= num_val <= 2099:
            return True
        # 일수 상수 (365, 270, 180, 360 등)
        if num_val in {365, 270, 180, 360, 90, 120, 150, 240, 300, 100}:
            return True
        # 기간 표현 (9M = FY24.9M에서 추출된 24 등)
        if num_val < 200:
            return False  # 200 미만은 guardrails가 이미 필터하므로 여기 안 옴
        return False

    def _call(self, section_id: str, user_prompt: str, max_tokens: int = 1024) -> str:
        """LLM 호출 → guardrails 검증. 실패 시 폴백."""
        text = ""

        # 1차: 라우터 기본 경로
        try:
            resp = self._router.generate(
                section_id=section_id,
                system_prompt=_LLM_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,
                max_tokens=max_tokens,
                timeout_seconds=45,
            )
            _p(
                f"      [LLM] {section_id}: {resp.provider}/{resp.model} ({resp.token_usage})"
            )
            text = resp.text.strip()
        except Exception as e:
            _p(f"      [LLM] {section_id} primary failed: {e}")

        # 2차: 직접 프로바이더 폴백 (라우터가 API 에러 시 폴백 안 하므로)
        if not text:
            for name, client in self._router._providers.items():
                if not client.is_available():
                    continue
                try:
                    resp = client.chat(
                        system_prompt=_LLM_SYSTEM_PROMPT,
                        user_prompt=user_prompt,
                        temperature=0.2,
                        max_tokens=max_tokens,
                        timeout_seconds=45,
                    )
                    if resp.content and resp.content.strip():
                        _p(f"      [LLM] {section_id}: fallback to {name}/{resp.model}")
                        text = resp.content.strip()
                        break
                except Exception as fallback_err:
                    _p(
                        f"      [LLM] {section_id} fallback {name} failed: {str(fallback_err)[:100]}"
                    )
                    continue

        if not text:
            _p(f"      [LLM FAIL] {section_id}: all providers exhausted")
            return ""

        # Guardrails 검증
        return self._validate_with_guardrails(text, section_id)

    def enhance_is(
        self,
        bu_pl: dict[str, dict[str, Decimal]],
        rule_commentary: list[str],
    ) -> str:
        """IS 분석 보강 — Quality of Earnings 관점."""
        periods = sorted(bu_pl.keys())
        data_lines = []
        prev_rev, prev_gp, prev_op = ZERO, ZERO, ZERO
        for p in periods:
            items = bu_pl[p]
            rev = items.get("매출액", ZERO)
            cogs = items.get("매출원가", ZERO)
            gp = items.get("매출이익", items.get("매출총이익", ZERO))
            op = items.get("영업이익", ZERO)
            sga = items.get("판매비와관리비", items.get("판관비", ZERO))
            gp_margin = float(gp / rev * 100) if rev else 0
            op_margin = float(op / rev * 100) if rev else 0
            yoy_rev = (
                f" (YoY {float((rev - prev_rev) / prev_rev * 100):+.1f}%)"
                if prev_rev > ZERO
                else ""
            )
            data_lines.append(
                f"| {p} | {_fmt(rev)}M{yoy_rev} | {_fmt(cogs)}M | {_fmt(gp)}M ({gp_margin:.1f}%) | "
                f"{_fmt(sga)}M | {_fmt(op)}M ({op_margin:.1f}%) |"
            )
            prev_rev, prev_gp, prev_op = rev, gp, op

        prompt = (
            "# 손익계산서 심층 분석 (Quality of Earnings)\n\n"
            "## 다기간 손익 데이터\n"
            "| 기간 | 매출 | 매출원가 | 매출총이익 (GP%) | 판관비 | 영업이익 (OP%) |\n"
            "|------|------|----------|-----------------|--------|---------------|\n"
            + "\n".join(data_lines)
            + "\n\n## 규칙 기반 분석 결과 (자동 탐지)\n"
            + "\n".join(f"- {b}" for b in rule_commentary)
            + "\n\n## 분석 요구사항\n\n"
            "아래 4가지 관점에서 **각 3~5문장**으로 분석하세요:\n\n"
            "### 1. 매출 성장성 분석\n"
            "- 매출 YoY 변동의 핵심 드라이버 (가격 vs 물량 추정)\n"
            "- 성장의 지속 가능성 평가 (organic vs inorganic)\n\n"
            "### 2. 마진 구조 분석\n"
            "- GP 마진 변동 요인 (원가율 변화, 제품 믹스, 원재료 가격)\n"
            "- 판관비 효율성 (매출 대비 비율 추이, 고정비/변동비 구조)\n\n"
            "### 3. Earnings Quality 이슈\n"
            "- 비경상/일회성 항목 식별 (Normalized EBITDA 조정 후보)\n"
            "- 수익 인식 시점 관련 리스크\n\n"
            "### 4. PE 투자 시사점\n"
            "- EBITDA 멀티플 적용 시 조정 필요 항목\n"
            "- 인수 후 마진 개선 기회 (cost synergy 영역)\n"
        )
        return self._call("qoe_analysis_narrative", prompt, max_tokens=2048)

    def enhance_revenue(
        self,
        hhi: Decimal,
        top5_share: Decimal,
        top1_name: str,
        top1_share: Decimal,
        rule_commentary: list[str],
    ) -> str:
        """매출 집중도 분석 보강 — Customer Concentration Risk."""
        hhi_level = (
            "고집중 (High)"
            if hhi > 2500
            else "중집중 (Moderate)"
            if hhi > 1500
            else "분산 (Low)"
        )
        prompt = (
            "# Customer Concentration Risk Analysis\n\n"
            "## 매출 집중도 지표\n"
            f"- **HHI**: {hhi:,.0f} → {hhi_level}\n"
            f"- **Top 1 거래처**: {top1_name} ({top1_share:.1f}%)\n"
            f"- **Top 5 거래처 합산**: {top5_share:.1f}%\n\n"
            "## 규칙 기반 분석 결과\n"
            + "\n".join(f"- {b}" for b in rule_commentary)
            + "\n\n## 분석 요구사항\n\n"
            "아래 4가지 관점에서 **각 2~4문장**으로 분석하세요:\n\n"
            "### 1. 집중 리스크 심각도 평가\n"
            f"- HHI {hhi:,.0f}의 의미와 동종 업계 대비 수준\n"
            f"- Top 1 거래처({top1_name}) {top1_share:.1f}% 의존의 사업 연속성 리스크\n\n"
            "### 2. 거래처 관계 안정성\n"
            "- 장기 계약 vs 스팟 거래 구조 추정\n"
            "- Key-man dependency 및 전환 비용 분석\n\n"
            "### 3. 밸류에이션 영향\n"
            "- 매출 집중도가 EBITDA 멀티플에 미치는 할인 효과\n"
            "- 인수 후 고객 이탈 시 매출 하락 시나리오\n\n"
            "### 4. 매출 다변화 전략\n"
            "- 신규 거래처 확보 가능성 및 업종 다각화 방안\n"
            "- 인수자 관점에서 Cross-selling 기회\n"
        )
        return self._call("revenue_concentration_narrative", prompt, max_tokens=2048)

    def enhance_nwc(self, nwc_data: dict[str, Any], rule_commentary: list[str]) -> str:
        """NWC 분석 보강 — Working Capital & Cash Conversion."""
        td = nwc_data.get("turnover_days", {})
        ar_days = td.get("ar_days", 0)
        inv_days = td.get("inventory_days", 0)
        ap_days = td.get("ap_days", 0)
        ccc = ar_days + inv_days - ap_days

        # NWC 항목 상세
        nwc_items = nwc_data.get("items", [])
        item_lines = []
        for item in nwc_items[:10]:
            if isinstance(item, dict):
                item_lines.append(
                    f"- {item.get('label', item.get('name', '?'))}: {_fmt(item.get('amount', ZERO))}M"
                )

        prompt = (
            "# Net Working Capital 심층 분석\n\n"
            "## 운전자본 회전 지표\n"
            f"| 지표 | 값 | 평가 |\n"
            f"|------|----|------|\n"
            f"| AR Days (매출채권 회전일수) | {ar_days:.0f}일 | {'⚠ 장기' if ar_days > 60 else '양호'} |\n"
            f"| Inventory Days (재고 회전일수) | {inv_days:.0f}일 | {'⚠ 장기' if inv_days > 90 else '양호'} |\n"
            f"| AP Days (매입채무 회전일수) | {ap_days:.0f}일 | - |\n"
            f"| **CCC (Cash Conversion Cycle)** | **{ccc:.0f}일** | {'⚠ 비효율' if ccc > 90 else '양호'} |\n\n"
            + (
                "## NWC 구성 항목\n" + "\n".join(item_lines) + "\n\n"
                if item_lines
                else ""
            )
            + "## 규칙 기반 분석 결과\n"
            + "\n".join(f"- {b}" for b in rule_commentary)
            + "\n\n## 분석 요구사항\n\n"
            "아래 4가지 관점에서 **각 2~4문장**으로 분석하세요:\n\n"
            "### 1. 매출채권 분석\n"
            f"- AR Days {ar_days:.0f}일의 의미 (업종 평균 대비)\n"
            "- 대손 위험 평가, 장기 미수금 비중 추정\n\n"
            "### 2. Cash Conversion Cycle 분석\n"
            f"- CCC {ccc:.0f}일 → 영업현금 창출 효율성 평가\n"
            "- 인수 후 CCC 개선 시 현금 유입 효과 추정\n\n"
            "### 3. NWC 변동 및 Debt-like Item\n"
            "- 계절성/분기별 변동 패턴 추정\n"
            "- Normalized NWC 산정 시 조정 필요 항목\n\n"
            "### 4. 인수 후 개선 기회\n"
            "- 매출채권 회수 가속화 방안\n"
            "- 공급자 결제 조건 재협상 가능성\n"
        )
        return self._call("nwc_analysis_narrative", prompt, max_tokens=2048)

    def enhance_debt(
        self,
        debt_items: list[dict],
        cash: Decimal,
        ebitda: Decimal,
        rule_commentary: list[str],
    ) -> str:
        """차입금 분석 보강 — Debt & Leverage Analysis."""
        total_debt = sum(d.get("_balance_dec", ZERO) for d in debt_items)
        net_debt = total_debt - cash
        leverage = float(net_debt / ebitda) if ebitda > ZERO else 0

        debt_table = []
        for d in debt_items:
            bal = d.get("_balance_dec", ZERO)
            share = float(bal / total_debt * 100) if total_debt > ZERO else 0
            debt_table.append(
                f"| {d.get('lender', '?')} | {_fmt(bal)}M | {share:.1f}% | "
                f"{d.get('_rate_dec', ZERO):.1f}% | {d.get('maturity', 'N/A')} |"
            )

        prompt = (
            "# Debt Schedule & Leverage Analysis\n\n"
            "## 차입금 구조 요약\n"
            f"- **총 차입금**: {_fmt(total_debt)}M\n"
            f"- **현금**: {_fmt(cash)}M\n"
            f"- **순차입금 (Net Debt)**: {_fmt(net_debt)}M\n"
            f"- **Net Debt/EBITDA**: {leverage:.1f}x\n\n"
            "## 차입금 상세\n"
            "| 대출처 | 잔액 | 비중 | 금리 | 만기 |\n"
            "|--------|------|------|------|------|\n"
            + "\n".join(debt_table)
            + "\n\n## 규칙 기반 분석 결과\n"
            + "\n".join(f"- {b}" for b in rule_commentary)
            + "\n\n## 분석 요구사항\n\n"
            "아래 4가지 관점에서 **각 2~4문장**으로 분석하세요:\n\n"
            "### 1. 레버리지 적정성\n"
            f"- Net Debt/EBITDA {leverage:.1f}x의 적정성 (PE 통상 기준: 3~5x)\n"
            "- 추가 차입 여력 (인수 금융 조달 가능성)\n\n"
            "### 2. 차환 리스크\n"
            "- 만기 도래 차입금 분석 (12개월 이내 만기 비중)\n"
            "- 차환 시 금리 상승 시나리오 영향\n\n"
            "### 3. 금리 민감도\n"
            f"- 현재 가중평균 금리 수준 평가\n"
            "- 금리 +100bp 시 이자 비용 증가 추정\n"
            "- 고정/변동 금리 비율 분석\n\n"
            "### 4. 인수 구조 시사점\n"
            "- 기존 차입금 상환 vs 인수 구조 편입 판단\n"
            "- Change of Control 조항 확인 필요성\n"
            "- LBO 구조 시 적정 부채 수준 추정\n"
        )
        return self._call("debt_analysis_narrative", prompt, max_tokens=2048)

    def generate_executive_summary(
        self,
        deal_name: str,
        bu_pl: dict[str, dict[str, Decimal]],
        hhi: Decimal,
        nwc_data: dict[str, Any],
        debt_items: list[dict],
        issues: list[dict[str, Any]],
    ) -> str:
        """Executive Summary 생성 (LLM 전용) — 구조화된 20+ 줄 출력."""
        periods = sorted(bu_pl.keys())

        # 손익 데이터 (다기간 + YoY 변동)
        is_summary = []
        prev_rev, prev_gp = ZERO, ZERO
        for p in periods:
            items = bu_pl[p]
            rev = items.get("매출액", ZERO)
            gp = items.get("매출이익", items.get("매출총이익", ZERO))
            op = items.get("영업이익", ZERO)
            margin = float(gp / rev * 100) if rev else 0
            op_margin = float(op / rev * 100) if rev else 0
            yoy_rev = (
                f" (YoY {float((rev - prev_rev) / prev_rev * 100):+.1f}%)"
                if prev_rev > ZERO
                else ""
            )
            yoy_gp = (
                f" (YoY {float((gp - prev_gp) / prev_gp * 100):+.1f}%)"
                if prev_gp > ZERO
                else ""
            )
            is_summary.append(
                f"{p}: 매출 {_fmt(rev)}M{yoy_rev}, GP {_fmt(gp)}M ({margin:.1f}%){yoy_gp}, "
                f"영업이익 {_fmt(op)}M ({op_margin:.1f}%)"
            )
            prev_rev, prev_gp = rev, gp

        # EBITDA (가용 시)
        ebitda_line = ""
        latest = bu_pl.get(periods[-1], {}) if periods else {}
        ebitda = latest.get("EBITDA", latest.get("상각전영업이익", ZERO))
        if ebitda > ZERO:
            ebitda_line = f"EBITDA: {_fmt(ebitda)}M"

        # 운전자본
        td = nwc_data.get("turnover_days", {})
        ar_days = td.get("ar_days", 0)
        inv_days = td.get("inventory_days", 0)
        ap_days = td.get("ap_days", 0)
        ccc = ar_days + inv_days - ap_days

        # 차입금
        total_debt = sum(d.get("_balance_dec", ZERO) for d in debt_items)
        cash = sum(
            d.get("_balance_dec", ZERO)
            for d in debt_items
            if "예금" in d.get("lender", "") or "현금" in d.get("lender", "")
        )
        net_debt = total_debt

        # 차입 상세
        debt_details = []
        for d in debt_items[:5]:
            debt_details.append(
                f"  - {d.get('lender', '?')}: {_fmt(d.get('_balance_dec', ZERO))}M, "
                f"금리 {d.get('_rate_dec', ZERO):.1f}%, 만기 {d.get('maturity', 'N/A')}"
            )

        # 이슈 분류
        high_issues = [i for i in issues if i.get("severity") == "HIGH"]
        med_issues = [i for i in issues if i.get("severity") == "MEDIUM"]
        issue_list = []
        for i in high_issues + med_issues:
            issue_list.append(f"- [{i['severity']}] {i['title']}: {i['description']}")

        prompt = (
            f"# {deal_name} Financial Due Diligence — Executive Summary\n\n"
            "아래 실사 데이터를 종합하여 PE 투자 의사결정에 필요한 Executive Summary를 작성하세요.\n\n"
            "## 제공 데이터\n\n"
            "### 1. 손익계산서 (다기간)\n"
            + "\n".join(is_summary)
            + (f"\n{ebitda_line}" if ebitda_line else "")
            + "\n\n### 2. 매출 집중도\n"
            f"- HHI: {hhi:,.0f} ({'고집중' if hhi > 2500 else '중집중' if hhi > 1500 else '분산'})\n"
            "\n### 3. 운전자본 분석\n"
            f"- AR Days: {ar_days:.0f}일, Inventory Days: {inv_days:.0f}일, AP Days: {ap_days:.0f}일\n"
            f"- CCC (Cash Conversion Cycle): {ccc:.0f}일\n"
            "\n### 4. 차입금 현황\n"
            f"- 총 차입금: {_fmt(total_debt)}M\n"
            + ("\n".join(debt_details) if debt_details else "")
            + f"\n\n### 5. 발견 이슈 ({len(high_issues)} HIGH, {len(med_issues)} MEDIUM)\n"
            + "\n".join(issue_list)
            + "\n\n---\n\n"
            "## 작성 요구사항\n\n"
            "다음 **6개 섹션**을 모두 포함하여 작성하세요. 각 섹션 앞에 ### 소제목을 붙이세요.\n\n"
            "### 1. 대상 기업 개요 (2~3문장)\n"
            f"- {deal_name}의 사업 성격, 주요 매출원, 분석 기간을 요약\n\n"
            "### 2. 핵심 재무 지표 (Key Financial Highlights)\n"
            "- 매출, GP 마진, 영업이익 추이를 YoY 변동률과 함께 분석 (3~5 불릿)\n"
            "- 각 불릿은 **수치 + 변동 원인 추정 + 시사점** 구조로 최소 2문장\n\n"
            "### 3. Quality of Earnings 이슈\n"
            "- Normalized EBITDA 조정 필요 항목 식별 (비경상 수익/비용, 일회성 항목)\n"
            "- Adjusted EBITDA와 Reported EBITDA 간 차이 분석\n\n"
            "### 4. 운전자본 & 현금 흐름\n"
            "- CCC 분석, AR Days 추이, 운전자본 효율성 평가\n"
            "- 인수 후 운전자본 개선 기회 식별\n\n"
            "### 5. Key Risks (최소 3개)\n"
            "- 매출 집중 리스크, 차입금 차환 리스크, 마진 압박 리스크 등\n"
            "- 각 리스크별 **심각도 + 발생 가능성 + 완화 방안** 명시\n\n"
            "### 6. 투자 고려사항 (Investment Considerations)\n"
            "- Due Diligence 추가 확인 필요 사항\n"
            "- 밸류에이션 시 조정 필요 항목\n"
            "- Deal Breaker 여부 판단\n\n"
            "**분량**: 최소 20줄 이상. 각 섹션은 구체적 수치를 인용하여 작성하세요.\n"
        )
        return self._call("executive_summary", prompt, max_tokens=4096)


def _init_llm_router() -> Any | None:
    """환경변수에서 LLM 클라이언트를 초기화하고 라우터를 구성한다.

    Returns:
        FDDModelRouter 또는 None (키 없으면)
    """
    try:
        from app.services.llm.client import AnthropicClient, GeminiClient, OpenAIClient
        from app.services.llm.routing.model_router import FDDModelRouter

        providers: dict[str, Any] = {}
        clients = [
            ("anthropic", AnthropicClient()),
            ("openai", OpenAIClient()),
            ("gemini", GeminiClient()),
        ]
        for name, client in clients:
            if client.is_available():
                providers[name] = client
                _p(f"    [LLM] {name}: available")
            else:
                _p(f"    [LLM] {name}: no API key")

        if not providers:
            _p("    [LLM] No providers available — skipping LLM commentary")
            return None

        router = FDDModelRouter(providers=providers)
        _p(f"    [LLM] Router initialized with {len(providers)} providers")
        return router

    except Exception as e:
        _p(f"    [LLM] Router init failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════
# Ralph Loop 경량판 — LLM 섹션 반복 개선
# ═══════════════════════════════════════════════════════════


def _generate_with_quality_loop(
    generate_fn: Callable[[], str],
    section_id: str,
    source_data: dict[str, Any] | None = None,
    tracker: Any | None = None,
    convergence: Any | None = None,
    max_iter: int = 3,
) -> str:
    """LLM 생성 콘텐츠를 Programmatic Gate로 평가 → 반복 개선.

    Args:
        generate_fn: 호출 시 LLM 텍스트를 반환하는 함수
        section_id: 섹션 식별자
        source_data: 교차검증용 소스 데이터
        tracker: ProgressTracker 인스턴스
        convergence: ConvergenceChecker 인스턴스
        max_iter: 최대 반복 횟수

    Returns:
        최종 LLM 텍스트 (실패 시 빈 문자열)
    """
    try:
        from app.ralph.gates.fdd_programmatic_gate import FDDProgrammaticGate
    except ImportError:
        # Gate 모듈 없으면 1회 생성만
        return generate_fn()

    gate = FDDProgrammaticGate()
    best_content = ""
    best_score = 0.0

    for iteration in range(max_iter):
        content = generate_fn()
        if not content:
            break

        # Gate 1: Programmatic 평가
        artifact_json = json.dumps(
            {
                "type": "text",
                "content": content,
            },
            ensure_ascii=False,
        )
        prd = {"id": section_id, "block_type": "text"}

        try:
            result = _run_gate_sync(gate, artifact_json, prd, source_data)
        except Exception as e:
            _p(f"      [Gate] {section_id} evaluation failed: {e}")
            best_content = content
            break

        score = result.weighted_score
        if score > best_score:
            best_score = score
            best_content = content

        # ProgressTracker에 기록
        if tracker is not None:
            try:
                tracker.record(section_id, iteration, result)
            except Exception:
                pass

        # 수렴 판정
        if convergence is not None and tracker is not None:
            try:
                verdict = convergence.check_section(section_id, result, tracker)
                if verdict.converged:
                    _p(
                        f"      [Loop] {section_id} converged: {verdict.reason} (score={score:.2f})"
                    )
                    break
            except Exception:
                pass

        # 통과 기준 달성이면 조기 종료
        if result.passed:
            _p(
                f"      [Loop] {section_id} PASS at iter {iteration + 1} (score={score:.2f})"
            )
            break

        _p(
            f"      [Loop] {section_id} iter {iteration + 1}: score={score:.2f}, retrying..."
        )

    return best_content


def _run_section_gates(
    sections: list[Any],
    tracker: Any | None = None,
) -> list[dict[str, Any]]:
    """전체 섹션에 Programmatic Gate를 1회씩 실행하여 품질 점수를 수집."""
    gate_results: list[dict[str, Any]] = []
    try:
        from app.ralph.gates.fdd_programmatic_gate import FDDProgrammaticGate
    except ImportError:
        _p("    [Quality] FDDProgrammaticGate not available — skipping")
        return gate_results

    gate = FDDProgrammaticGate()

    for idx, section in enumerate(sections):
        title = getattr(section, "title", f"section_{idx}")
        section_id = title[:30].replace(" ", "_").lower()

        artifact_json = _block_to_json(section)
        prd = {"id": section_id, "block_type": type(section).__name__}

        try:
            result = _run_gate_sync(gate, artifact_json, prd)
            gate_results.append(
                {
                    "section": title[:40],
                    "gate": "Programmatic",
                    "score": f"{result.weighted_score:.2f}/5.0",
                    "verdict": result.verdict.value,
                    "issues": len(result.issues),
                    "status": "PASS"
                    if result.passed
                    else ("COND" if result.verdict.value == "COND" else "FAIL"),
                }
            )
            if tracker is not None:
                try:
                    tracker.record(section_id, 0, result)
                except Exception:
                    pass
        except Exception as e:
            gate_results.append(
                {
                    "section": title[:40],
                    "gate": "Programmatic",
                    "score": "N/A",
                    "verdict": "ERROR",
                    "issues": 0,
                    "status": str(e)[:50],
                }
            )

    return gate_results


# ═══════════════════════════════════════════════════════════
# NWC 분석 모듈
# ═══════════════════════════════════════════════════════════


def compute_local_nwc(
    bs_data: dict[str, dict[str, Decimal]],
    is_data: dict[str, dict[str, Decimal]],
) -> dict[str, Any]:
    """BS + IS에서 NWC 분석 직접 계산.

    Returns:
        {"items": [...], "turnover_days": {"ar_days": Decimal, ...}, "nwc_by_period": {...}}
    """
    # BS 항목 키워드 매칭
    NWC_KEYWORDS = {
        "매출채권": (["매출채권", "외상매출금"], "asset"),
        "재고자산": (["재고자산", "상품", "제품", "원재료"], "asset"),
        "선급금": (["선급금", "선급비용"], "asset"),
        "매입채무": (["매입채무", "외상매입금"], "liability"),
        "미지급금": (["미지급금", "미지급비용"], "liability"),
        "선수금": (["선수금", "선수수익"], "liability"),
    }

    nwc_by_period: dict[str, dict[str, Decimal]] = {}
    for period, items in bs_data.items():
        nwc: dict[str, Decimal] = {}
        for nwc_name, (keywords, _side) in NWC_KEYWORDS.items():
            val = ZERO
            for account, amount in items.items():
                clean = account.replace(" ", "")
                if any(kw in clean for kw in keywords):
                    val += amount
            nwc[nwc_name] = val
        nwc["NWC"] = (
            nwc.get("매출채권", ZERO)
            + nwc.get("재고자산", ZERO)
            + nwc.get("선급금", ZERO)
            - nwc.get("매입채무", ZERO)
            - nwc.get("미지급금", ZERO)
            - nwc.get("선수금", ZERO)
        )
        nwc_by_period[period] = nwc

    # 회전일수 (FY24.9M 기준, 9개월)
    td: dict[str, Decimal] = {}
    fy24_bs = nwc_by_period.get("FY24.9M", {})
    fy24_is = is_data.get("FY24.9M", {})

    # 매출액 (백만원) — FS IS에서 찾기
    revenue = ZERO
    cogs = ZERO
    for k, v in fy24_is.items():
        clean = k.replace(" ", "")
        if clean.startswith("1.") and "매" in clean:
            revenue = v
        elif clean.startswith("2.") and "매" in clean and "원" in clean:
            cogs = v

    annualized_rev = revenue / _270 * _365 if revenue > ZERO else ZERO
    annualized_cogs = cogs / _270 * _365 if cogs > ZERO else ZERO

    ar = fy24_bs.get("매출채권", ZERO)
    inv = fy24_bs.get("재고자산", ZERO)
    ap = fy24_bs.get("매입채무", ZERO)

    td["ar_days"] = _q(ar / annualized_rev * _365) if annualized_rev > ZERO else ZERO
    td["inventory_days"] = (
        _q(inv / annualized_cogs * _365) if annualized_cogs > ZERO else ZERO
    )
    td["ap_days"] = _q(ap / annualized_cogs * _365) if annualized_cogs > ZERO else ZERO

    # NWC 테이블 rows
    nwc_rows: list[dict[str, Any]] = []
    for nwc_name, (_kw, side) in NWC_KEYWORDS.items():
        row: dict[str, Any] = {"name_ko": nwc_name, "type": side}
        for period in sorted(nwc_by_period.keys()):
            row[period] = _fmt(nwc_by_period[period].get(nwc_name, ZERO))
        nwc_rows.append(row)
    # NWC 합계
    nwc_total_row: dict[str, Any] = {"name_ko": "Net Working Capital", "type": "total"}
    for period in sorted(nwc_by_period.keys()):
        nwc_total_row[period] = _fmt(nwc_by_period[period].get("NWC", ZERO))
    nwc_rows.append(nwc_total_row)

    return {
        "items": nwc_rows,
        "turnover_days": td,
        "nwc_by_period": nwc_by_period,
    }


# ═══════════════════════════════════════════════════════════
# 교차검증 (Cross-check / Reconciliation)
# ═══════════════════════════════════════════════════════════
# 샘플 FDD 구조 빌더 함수들
# ═══════════════════════════════════════════════════════════


def _normalize_fs_data_periods(
    fs_data: dict[str, Any],
    bu_periods: list[str],
) -> dict[str, Any]:
    """FS 데이터의 기간 키를 bu_pl 기간 키와 일치시키고, 계정명 공백을 정리한다.

    1) 기간 키 매칭: FY23 → FY2023, FY24.9M → FY2024
    2) 계정명 공백 제거: "직    원     급    여" → "직원급여"
    3) 번호 접두사 제거: "1. 매출액" → "매출액"
    """
    result = dict(fs_data)
    for stmt in ["is", "bs"]:
        if stmt not in result:
            continue
        new_stmt: dict[str, Any] = {}
        for fs_key, items in result[stmt].items():
            # 계정명 공백 정리
            clean_items: dict[str, Any] = {}
            for acct, val in items.items():
                clean_acct = acct.replace(" ", "").strip()
                # 번호 접두사 제거 (예: "1.매출액" → "매출액", "10.당기순이익" → "당기순이익")
                clean_acct = re.sub(r"^\d+\.", "", clean_acct).strip()
                # 타임스탬프 행 스킵
                if re.match(r"^\d{4}/\d{2}/\d{2}", clean_acct):
                    continue
                if clean_acct:
                    clean_items[clean_acct] = val

            # 기간 키 매칭
            matched = False
            for bu_key in bu_periods:
                year_match = re.search(r"(\d{4})", bu_key)
                if year_match:
                    short_year = year_match.group(1)[2:]  # "2023" → "23"
                    if fs_key.startswith(f"FY{short_year}"):
                        new_stmt[bu_key] = clean_items
                        matched = True
                        break
            if not matched:
                new_stmt[fs_key] = clean_items  # 매칭 안 되면 원본 키 유지
        result[stmt] = new_stmt
    return result


def _yoy(curr: Decimal, prev: Decimal) -> str:
    """YoY 변동률 계산."""
    if prev == ZERO or curr == ZERO:
        return ""
    pct = float((curr - prev) / abs(prev) * _HUNDRED)
    return f"{pct:+.1f}%"


def build_pl_overview(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
    commentary_map: dict[str, str] | None = None,
) -> TableBlock:
    """PL Overview — 다기간 손익계산서 + YoY% + Comment + 마진분석.

    샘플의 'PL Overview' 시트와 동일한 구조.
    """
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    if not periods:
        return TableBlock(title="PL Overview", columns=[], rows=[])

    commentary_map = commentary_map or {}

    # IS 세부 항목을 fs_data["is"]에서 가져오기 (가능한 경우)
    # 없으면 bu_pl 사용
    is_accounts = [
        "매출액",
        "매출원가",
        "매출총이익",
        "판매비와관리비",
        "영업이익",
        "영업외수익",
        "영업외비용",
        "법인세차감전이익",
        "법인세등",
        "당기순이익",
    ]

    # fs_data["is"]에서 세부 항목 추출 (더 상세)
    all_accounts: list[tuple[str, int]] = []  # (계정명, indent)
    if fs_data.get("is"):
        sample_period = list(fs_data["is"].keys())[0] if fs_data["is"] else None
        if sample_period:
            for acct in fs_data["is"][sample_period].keys():
                is_subtotal = any(
                    k in acct
                    for k in [
                        "매출총이익",
                        "영업이익",
                        "당기순이익",
                        "합계",
                        "총계",
                        "법인세차감전",
                    ]
                )
                indent = 0 if is_subtotal or acct in is_accounts else 1
                all_accounts.append((acct, indent))
    if not all_accounts:
        for acct in is_accounts:
            all_accounts.append((acct, 0))

    rows: list[dict[str, Any]] = []
    for acct, indent in all_accounts:
        row: dict[str, Any] = {
            "account": ("  " * indent) + acct,
        }
        prev_val = ZERO
        for pi, p in enumerate(periods):
            # bu_pl 또는 fs_data에서 값 가져오기
            val = ZERO
            if fs_data.get("is") and p in fs_data["is"]:
                val = _safe_decimal(fs_data["is"][p].get(acct, 0))
            if val == ZERO:
                val = bu_pl.get(p, {}).get(acct, ZERO)
            row[f"fy_{pi}"] = _fmt(val) if val != ZERO else ""

            # YoY (두 번째 기간부터)
            if pi > 0 and prev_val != ZERO and val != ZERO:
                row[f"yoy_{pi}"] = _yoy(val, prev_val)
            elif pi > 0:
                row[f"yoy_{pi}"] = ""
            prev_val = val

        row["comment"] = commentary_map.get(acct, "")
        rows.append(row)

    # 하단: 마진 분석
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "comment": ""}
    )
    rows.append(
        {
            "account": "주요 마진 분석",
            **{f"fy_{i}": "" for i in range(len(periods))},
            "comment": "",
        }
    )

    margin_items = ["영업이익률", "당기순이익률", "판관비율", "인건비율"]
    for margin_name in margin_items:
        row = {"account": margin_name}
        for pi, p in enumerate(periods):
            items = bu_pl.get(p, {})
            rev = items.get("매출액", ZERO)
            if rev == ZERO:
                if fs_data.get("is") and p in fs_data["is"]:
                    rev = _safe_decimal(fs_data["is"][p].get("매출액", 0))
            if rev == ZERO:
                row[f"fy_{pi}"] = ""
                continue
            if margin_name == "영업이익률":
                op = items.get("영업이익", ZERO)
                if op == ZERO and fs_data.get("is") and p in fs_data["is"]:
                    op = _safe_decimal(fs_data["is"][p].get("영업이익", 0))
                row[f"fy_{pi}"] = (
                    f"{float(op / rev * _HUNDRED):.1f}%" if op != ZERO else ""
                )
            elif margin_name == "당기순이익률":
                ni = items.get("당기순이익", ZERO)
                if ni == ZERO and fs_data.get("is") and p in fs_data["is"]:
                    ni = _safe_decimal(
                        fs_data["is"][p].get(
                            "당기순이익", fs_data["is"][p].get("당기순이익(손실)", 0)
                        )
                    )
                row[f"fy_{pi}"] = (
                    f"{float(ni / rev * _HUNDRED):.1f}%" if ni != ZERO else ""
                )
            elif margin_name == "판관비율":
                sga = items.get("판매비와관리비", items.get("판관비", ZERO))
                if sga == ZERO and fs_data.get("is") and p in fs_data["is"]:
                    sga = _safe_decimal(fs_data["is"][p].get("판매비와관리비", 0))
                row[f"fy_{pi}"] = (
                    f"{float(sga / rev * _HUNDRED):.1f}%" if sga != ZERO else ""
                )
            elif margin_name == "인건비율":
                labor_keys = ["직원급여", "급여", "퇴직급여", "복리후생비"]
                labor_total = ZERO
                src = fs_data["is"].get(p, {}) if fs_data.get("is") else {}
                for lk in labor_keys:
                    labor_total += _safe_decimal(src.get(lk, items.get(lk, 0)))
                row[f"fy_{pi}"] = (
                    f"{float(labor_total / rev * _HUNDRED):.1f}%"
                    if labor_total != ZERO
                    else ""
                )
        row["comment"] = ""
        rows.append(row)

    # 컬럼 구성
    cols = [TableColumn(key="account", header="구분", width=3.0, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
        if pi > 0:
            yr_curr = re.search(r"(\d{4})", periods[pi])
            yr_prev = re.search(r"(\d{4})", periods[pi - 1])
            yr_label = (
                f"{yr_curr.group(1)}/{yr_prev.group(1)}"
                if yr_curr and yr_prev
                else f"{pi}"
            )
            cols.append(
                TableColumn(
                    key=f"yoy_{pi}",
                    header=f"YoY ({yr_label})",
                    width=1.2,
                    align=AlignType.CENTER,
                )
            )
    cols.append(
        TableColumn(key="comment", header="Comment", width=4.0, align=AlignType.LEFT)
    )

    return TableBlock(
        title="PL Overview", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_qoe_block(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
    llm_adjustments: list[dict[str, Any]] | None = None,
) -> TableBlock:
    """QoE (Quality of Earnings) — Adjusted EBITDA Bridge.

    샘플의 'QoE' 시트와 동일한 구조.
    """
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    rows: list[dict[str, Any]] = []

    def _row(
        label: str, vals: dict[str, Decimal], rationale: str = "", indent: int = 0
    ) -> dict:
        r: dict[str, Any] = {"account": ("  " * indent) + label}
        for pi, p in enumerate(periods):
            v = vals.get(p, ZERO)
            r[f"fy_{pi}"] = _fmt(v) if v != ZERO else ""
        r["rationale"] = rationale
        return r

    # A. Reported Revenue
    rev_by_period = {p: bu_pl[p].get("매출액", ZERO) for p in periods}
    rows.append(_row("A. Reported Revenue (보고 매출액)", rev_by_period))

    # Revenue 세부 항목
    revenue_subs = ["수입수수료", "기타매출", "제품매출", "상품매출", "용역매출"]
    for sub in revenue_subs:
        sub_vals = {}
        for p in periods:
            v = bu_pl[p].get(sub, ZERO)
            if v == ZERO and fs_data.get("is") and p in fs_data["is"]:
                v = _safe_decimal(fs_data["is"][p].get(sub, 0))
            if v != ZERO:
                sub_vals[p] = v
        if sub_vals:
            rows.append(_row(sub, sub_vals, indent=1))

    # Revenue Adjustments (규칙 기반)
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "rationale": ""}
    )
    rows.append(
        {
            "account": "Revenue Adjustments:",
            **{f"fy_{i}": "" for i in range(len(periods))},
            "rationale": "",
        }
    )

    # 일회성 수익 탐지 (전기 대비 2배 이상 증가 후 감소)
    adj_rev = dict(rev_by_period)  # 기본은 조정 없음
    rows.append(_row("B. Adjusted Revenue (조정 매출액)", adj_rev))

    # C. Reported Operating Profit
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "rationale": ""}
    )
    op_by_period = {p: bu_pl[p].get("영업이익", ZERO) for p in periods}
    rows.append(_row("C. Reported Operating Profit (보고 영업이익)", op_by_period))

    # D. Reported EBITDA 산출
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "rationale": ""}
    )
    rows.append(
        {
            "account": "D. Reported EBITDA 산출:",
            **{f"fy_{i}": "" for i in range(len(periods))},
            "rationale": "",
        }
    )
    rows.append(_row("보고 영업이익(손실)", op_by_period))

    depr_by_period: dict[str, Decimal] = {}
    amort_by_period: dict[str, Decimal] = {}
    for p in periods:
        items = bu_pl[p]
        fs_is = fs_data.get("is", {}).get(p, {})
        depr = ZERO
        amort = ZERO
        for k, v in {
            **items,
            **{kk: _safe_decimal(vv) for kk, vv in fs_is.items()},
        }.items():
            if "감가상각" in k and "무형" not in k and v != ZERO:
                depr = max(depr, abs(v))
            if "무형자산상각" in k and v != ZERO:
                amort = max(amort, abs(v))
        depr_by_period[p] = depr
        amort_by_period[p] = amort

    rows.append(_row("(+) 감가상각비", depr_by_period, "유형자산 감가상각", indent=1))
    rows.append(
        _row(
            "(+) 무형자산상각비",
            amort_by_period,
            "소프트웨어, 상표권 상각 등",
            indent=1,
        )
    )

    ebitda_by_period = {
        p: op_by_period.get(p, ZERO)
        + depr_by_period.get(p, ZERO)
        + amort_by_period.get(p, ZERO)
        for p in periods
    }
    rows.append(_row("D. Reported EBITDA", ebitda_by_period))

    # E. EBITDA Adjustments
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "rationale": ""}
    )
    rows.append(
        {
            "account": "E. EBITDA Adjustments:",
            **{f"fy_{i}": "" for i in range(len(periods))},
            "rationale": "",
        }
    )

    # 규칙 기반 조정 항목 탐지
    adj_total_by_period: dict[str, Decimal] = {p: ZERO for p in periods}
    adj_idx = 1

    # (1) 국고보조금/정부지원금 (비경상 수익)
    for p in periods:
        fs_is = fs_data.get("is", {}).get(p, {})
        for k, v in fs_is.items():
            v_dec = _safe_decimal(v)
            if ("국고" in k or "보조금" in k) and v_dec > ZERO:
                neg_vals = {p: -v_dec}
                rows.append(
                    _row(
                        f"({adj_idx}) {k} 제거",
                        neg_vals,
                        "비경상 정부지원금 — Normalized EBITDA에서 제거",
                        indent=1,
                    )
                )
                adj_total_by_period[p] += -v_dec
                adj_idx += 1

    # (2) 대규모 잡이익/잡손실 (비경상)
    for p in periods:
        fs_is = fs_data.get("is", {}).get(p, {})
        for k, v in fs_is.items():
            v_dec = _safe_decimal(v)
            if "잡이익" in k and abs(v_dec) > _safe_decimal(
                rev_by_period.get(p, 0)
            ) * Decimal("0.01"):
                neg_vals = {p: -v_dec}
                rows.append(
                    _row(
                        f"({adj_idx}) 비경상적 {k} 제거",
                        neg_vals,
                        "일회성 항목 (자산처분익 등)",
                        indent=1,
                    )
                )
                adj_total_by_period[p] += -v_dec
                adj_idx += 1

    # LLM 조정 항목 (있는 경우)
    if llm_adjustments:
        for adj in llm_adjustments:
            adj_vals = {}
            for p in periods:
                v = _safe_decimal(adj.get(p, 0))
                if v != ZERO:
                    adj_vals[p] = v
                    adj_total_by_period[p] += v
            if adj_vals:
                rows.append(
                    _row(
                        f"({adj_idx}) {adj.get('label', 'LLM 조정')}",
                        adj_vals,
                        adj.get("rationale", ""),
                        indent=1,
                    )
                )
                adj_idx += 1

    rows.append(_row("총 EBITDA 조정액", adj_total_by_period))

    # F. Adjusted EBITDA
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "rationale": ""}
    )
    adj_ebitda = {
        p: ebitda_by_period.get(p, ZERO) + adj_total_by_period.get(p, ZERO)
        for p in periods
    }
    rows.append(_row("F. Adjusted EBITDA", adj_ebitda))

    # Adjusted EBITDA Margin
    margin_row: dict[str, Any] = {"account": "Adjusted EBITDA Margin"}
    for pi, p in enumerate(periods):
        adj_rev_p = adj_rev.get(p, ZERO)
        adj_ebitda_p = adj_ebitda.get(p, ZERO)
        if adj_rev_p != ZERO:
            margin_row[f"fy_{pi}"] = (
                f"{float(adj_ebitda_p / adj_rev_p * _HUNDRED):.1f}%"
            )
        else:
            margin_row[f"fy_{pi}"] = ""
    margin_row["rationale"] = "Adjusted EBITDA / Adjusted Revenue"
    rows.append(margin_row)

    # 컬럼
    cols = [TableColumn(key="account", header="구분", width=3.5, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
    cols.append(
        TableColumn(
            key="rationale",
            header="비고 / Adjustment Rationale",
            width=5.0,
            align=AlignType.LEFT,
        )
    )

    return TableBlock(
        title="QoE (Quality of Earnings)",
        columns=cols,
        rows=rows,
        metadata={"style": "table"},
    )


def build_bs_overview(
    fs_data: dict[str, Any],
) -> TableBlock:
    """BS Overview — 다기간 재무상태표 + 증감."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    bs_data = fs_data.get("bs", {})
    periods = sorted(bs_data.keys())
    if not periods:
        return TableBlock(title="BS Overview", columns=[], rows=[])

    # 모든 계정명 수집 (순서 보존)
    all_accounts: list[str] = []
    seen: set[str] = set()
    for p in periods:
        for acct in bs_data[p].keys():
            if acct not in seen:
                all_accounts.append(acct)
                seen.add(acct)

    rows: list[dict[str, Any]] = []
    for acct in all_accounts:
        is_subtotal = any(
            k in acct
            for k in [
                "자산총계",
                "부채총계",
                "자본총계",
                "부채및자본총계",
                "합계",
                "소계",
            ]
        )
        row: dict[str, Any] = {
            "account": acct if is_subtotal else f"  {acct}",
        }
        vals: list[Decimal] = []
        for pi, p in enumerate(periods):
            v = _safe_decimal(bs_data[p].get(acct, 0))
            row[f"fy_{pi}"] = _fmt(v) if v != ZERO else ""
            vals.append(v)

        # 증감 (최신 - 직전)
        if len(vals) >= 2 and (vals[-1] != ZERO or vals[-2] != ZERO):
            delta = vals[-1] - vals[-2]
            row["delta"] = _fmt(delta) if delta != ZERO else ""
        else:
            row["delta"] = ""
        row["note"] = ""
        rows.append(row)

    cols = [TableColumn(key="account", header="구분", width=3.0, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
    cols.append(
        TableColumn(
            key="delta",
            header=f"증감 ({periods[-1][:4]} vs {periods[-2][:4]})"
            if len(periods) >= 2
            else "증감",
            width=1.5,
            align=AlignType.RIGHT,
        )
    )
    cols.append(TableColumn(key="note", header="비고", width=3.0, align=AlignType.LEFT))

    return TableBlock(
        title="BS Overview", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_qoa_block(
    debt_items: list[dict[str, Any]],
    cash_total: Decimal,
    nwc_data: dict[str, Any],
    fs_data: dict[str, Any],
    bu_pl: dict[str, dict[str, Decimal]],
) -> TableBlock:
    """QoA (Quality of Net Assets / Net Debt) — 샘플 구조."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    rows: list[dict[str, Any]] = []

    def _simple_row(label: str, values: dict[str, str], note: str = "") -> dict:
        r: dict[str, Any] = {"account": label}
        for pi in range(len(periods)):
            r[f"fy_{pi}"] = values.get(periods[pi], "") if pi < len(periods) else ""
        r["note"] = note
        return r

    # A. Net Debt / (Cash) Analysis
    rows.append(_simple_row("A. Net Debt / (Cash) Analysis", {}))
    rows.append(
        _simple_row(
            "현금 및 현금성자산",
            {periods[-1]: _fmt(cash_total)} if cash_total != ZERO else {},
        )
    )

    total_debt = sum(d.get("_balance_dec", ZERO) for d in debt_items)
    for d in debt_items:
        bal = d.get("_balance_dec", ZERO)
        if bal != ZERO:
            rows.append(
                _simple_row(
                    f"  {d.get('lender', '?')}",
                    {periods[-1]: _fmt(bal)},
                    f"금리 {d.get('_rate_dec', ZERO):.1f}%, 만기 {d.get('maturity', 'N/A')}",
                )
            )

    rows.append(_simple_row("Total Debt", {periods[-1]: _fmt(total_debt)}))
    net_debt = total_debt - cash_total
    nd_label = "Net Debt" if net_debt > ZERO else "Net Debt / (Net Cash)"
    rows.append(
        _simple_row(
            nd_label,
            {periods[-1]: _fmt(net_debt)},
            "마이너스 = Net Cash 포지션" if net_debt < ZERO else "",
        )
    )

    # Debt-like Items
    rows.append(_simple_row("", {}))
    rows.append(_simple_row("Debt-like Items (추가 검토 필요):", {}))
    bs = fs_data.get("bs", {})
    debt_like_keywords = ["선수금", "선수수익", "장기미지급", "퇴직급여충당"]
    for p in periods:
        for k, v in bs.get(p, {}).items():
            v_dec = _safe_decimal(v)
            if any(kw in k for kw in debt_like_keywords) and abs(v_dec) > ZERO:
                vals = {p: _fmt(v_dec)}
                rows.append(_simple_row(f"  {k}", vals, "Debt-like 여부 검토"))

    # B. NWC 요약
    rows.append(_simple_row("", {}))
    rows.append(_simple_row("B. Net Working Capital 요약", {}))
    nwc_items = nwc_data.get("items", [])
    for item in nwc_items:
        if isinstance(item, dict):
            label = item.get("label", item.get("name", "?"))
            amt = item.get("amount", ZERO)
            if isinstance(amt, Decimal) and amt != ZERO:
                rows.append(_simple_row(f"  {label}", {periods[-1]: _fmt(amt)}))

    # C. Reported Net Assets (자본총계)
    rows.append(_simple_row("", {}))
    equity_vals = {}
    for p in periods:
        for k, v in bs.get(p, {}).items():
            if "자본총계" in k:
                equity_vals[p] = _fmt(_safe_decimal(v))
    rows.append(_simple_row("C. Reported Net Assets (자본총계)", equity_vals))

    cols = [TableColumn(key="account", header="구분", width=3.5, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
    cols.append(TableColumn(key="note", header="비고", width=4.0, align=AlignType.LEFT))

    return TableBlock(
        title="QoA (Quality of Net Assets)",
        columns=cols,
        rows=rows,
        metadata={"style": "table"},
    )


def build_revenue_analysis(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
    customer_entries: list[dict[str, Any]],
    hhi: Decimal,
    observations: list[str] | None = None,
) -> TableBlock:
    """Revenue Analysis — 유형별 + 구성비 + Key Observations."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    rows: list[dict[str, Any]] = []

    # 매출 합계
    rev_by_period = {p: bu_pl[p].get("매출액", ZERO) for p in periods}
    total_row: dict[str, Any] = {"account": "매출액 합계"}
    for pi, p in enumerate(periods):
        total_row[f"fy_{pi}"] = _fmt(rev_by_period[p])
        if pi > 0:
            total_row[f"yoy_{pi}"] = _yoy(
                rev_by_period[p], rev_by_period[periods[pi - 1]]
            )
    total_row["comment"] = ""
    rows.append(total_row)
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "comment": ""}
    )

    # 매출 유형별 (fs_data IS에서 매출 하위 항목 추출)
    rows.append(
        {
            "account": "매출 유형별 분석:",
            **{f"fy_{i}": "" for i in range(len(periods))},
            "comment": "",
        }
    )
    rev_subs: dict[str, dict[str, Decimal]] = {}
    for p in periods:
        items = bu_pl[p]
        fs_is = fs_data.get("is", {}).get(p, {})
        for k, v in {
            **items,
            **{kk: _safe_decimal(vv) for kk, vv in fs_is.items()},
        }.items():
            if (
                k != "매출액"
                and ("매출" in k or "수수료" in k or "수익" in k)
                and "총이익" not in k
                and "원가" not in k
            ):
                v_dec = _safe_decimal(v) if not isinstance(v, Decimal) else v
                if v_dec != ZERO:
                    rev_subs.setdefault(k, {})[p] = v_dec

    for sub_name, sub_vals in rev_subs.items():
        sub_row: dict[str, Any] = {"account": f"  {sub_name}"}
        for pi, p in enumerate(periods):
            sub_row[f"fy_{pi}"] = _fmt(sub_vals.get(p, ZERO))
            if pi > 0:
                sub_row[f"yoy_{pi}"] = _yoy(
                    sub_vals.get(p, ZERO), sub_vals.get(periods[pi - 1], ZERO)
                )
        sub_row["comment"] = ""
        rows.append(sub_row)

    # 구성비
    rows.append(
        {"account": "", **{f"fy_{i}": "" for i in range(len(periods))}, "comment": ""}
    )
    rows.append(
        {
            "account": "매출 구성비 (%):",
            **{f"fy_{i}": "" for i in range(len(periods))},
            "comment": "",
        }
    )
    for sub_name, sub_vals in rev_subs.items():
        pct_row: dict[str, Any] = {"account": f"  {sub_name} 비중"}
        for pi, p in enumerate(periods):
            sub_v = sub_vals.get(p, ZERO)
            rev_v = rev_by_period.get(p, ZERO)
            if rev_v != ZERO and sub_v != ZERO:
                pct_row[f"fy_{pi}"] = f"{float(sub_v / rev_v * _HUNDRED):.1f}%"
            else:
                pct_row[f"fy_{pi}"] = ""
        pct_row["comment"] = ""
        rows.append(pct_row)

    # 집중도 정보
    if hhi > ZERO:
        rows.append(
            {
                "account": "",
                **{f"fy_{i}": "" for i in range(len(periods))},
                "comment": "",
            }
        )
        rows.append(
            {
                "account": f"매출 집중도 (HHI): {hhi:,.0f}",
                **{f"fy_{i}": "" for i in range(len(periods))},
                "comment": "2,500+ = 고집중",
            }
        )

    # Key Observations
    if observations:
        rows.append(
            {
                "account": "",
                **{f"fy_{i}": "" for i in range(len(periods))},
                "comment": "",
            }
        )
        rows.append(
            {
                "account": "Key Observations:",
                **{f"fy_{i}": "" for i in range(len(periods))},
                "comment": "",
            }
        )
        for idx_o, obs in enumerate(observations, 1):
            rows.append(
                {
                    "account": f"  {idx_o}",
                    **{f"fy_{i}": "" for i in range(len(periods))},
                    "comment": obs,
                }
            )

    cols = [TableColumn(key="account", header="구분", width=2.5, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
        if pi > 0:
            cols.append(
                TableColumn(
                    key=f"yoy_{pi}", header="YoY", width=1.0, align=AlignType.CENTER
                )
            )
    cols.append(
        TableColumn(key="comment", header="Comment", width=5.0, align=AlignType.LEFT)
    )

    return TableBlock(
        title="Revenue Analysis", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_sga_block(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
) -> TableBlock:
    """SGA Analysis — 카테고리별 판관비 + %Rev."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    rev_by_p = {p: bu_pl[p].get("매출액", ZERO) for p in periods}

    # SGA 카테고리 매핑
    categories = {
        "인건비": ["직원급여", "급여", "퇴직급여", "복리후생비", "잡급"],
        "시설/임차": ["지급임차료", "건물관리비", "수도광열비"],
        "외주/수수료": ["지급수수료", "외주비"],
        "마케팅": ["광고선전비"],
        "감가상각": ["감가상각비", "무형자산상각비"],
    }

    rows: list[dict[str, Any]] = []

    # 판관비 합계
    sga_total_row: dict[str, Any] = {"account": "판관비 합계"}
    for pi, p in enumerate(periods):
        sga = bu_pl[p].get("판매비와관리비", bu_pl[p].get("판관비", ZERO))
        if sga == ZERO and fs_data.get("is") and p in fs_data["is"]:
            sga = _safe_decimal(fs_data["is"][p].get("판매비와관리비", 0))
        sga_total_row[f"fy_{pi}"] = _fmt(sga)
        rev = rev_by_p.get(p, ZERO)
        sga_total_row[f"pct_{pi}"] = (
            f"{float(sga / rev * _HUNDRED):.1f}%" if rev != ZERO and sga != ZERO else ""
        )
    sga_total_row["comment"] = ""
    rows.append(sga_total_row)
    rows.append(
        {
            "account": "",
            **{f"fy_{i}": "" for i in range(len(periods))},
            **{f"pct_{i}": "" for i in range(len(periods))},
            "comment": "",
        }
    )

    # 카테고리별
    for cat_name, keywords in categories.items():
        cat_total: dict[str, Decimal] = {p: ZERO for p in periods}
        sub_items: list[tuple[str, dict[str, Decimal]]] = []

        for p in periods:
            items = bu_pl[p]
            fs_is = fs_data.get("is", {}).get(p, {})
            for k, v in {
                **items,
                **{kk: _safe_decimal(vv) for kk, vv in fs_is.items()},
            }.items():
                v_dec = _safe_decimal(v) if not isinstance(v, Decimal) else v
                if any(kw in k for kw in keywords) and abs(v_dec) > ZERO:
                    found = False
                    for sn, sv in sub_items:
                        if sn == k:
                            sv[p] = v_dec
                            found = True
                            break
                    if not found:
                        sub_items.append((k, {p: v_dec}))
                    cat_total[p] += abs(v_dec)

        if any(v != ZERO for v in cat_total.values()):
            # 소계 행
            cat_row: dict[str, Any] = {"account": f"{cat_name} 소계"}
            for pi, p in enumerate(periods):
                cat_row[f"fy_{pi}"] = _fmt(cat_total[p])
                rev = rev_by_p.get(p, ZERO)
                cat_row[f"pct_{pi}"] = (
                    f"{float(cat_total[p] / rev * _HUNDRED):.1f}%"
                    if rev != ZERO and cat_total[p] != ZERO
                    else ""
                )
            cat_row["comment"] = ""
            rows.append(cat_row)

            # 세부 항목
            for sub_name, sub_vals in sub_items:
                sub_row: dict[str, Any] = {"account": f"  {sub_name}"}
                for pi, p in enumerate(periods):
                    v = sub_vals.get(p, ZERO)
                    sub_row[f"fy_{pi}"] = _fmt(v)
                    rev = rev_by_p.get(p, ZERO)
                    sub_row[f"pct_{pi}"] = (
                        f"{float(abs(v) / rev * _HUNDRED):.1f}%"
                        if rev != ZERO and v != ZERO
                        else ""
                    )
                sub_row["comment"] = ""
                rows.append(sub_row)

            rows.append(
                {
                    "account": "",
                    **{f"fy_{i}": "" for i in range(len(periods))},
                    **{f"pct_{i}": "" for i in range(len(periods))},
                    "comment": "",
                }
            )

    # 기타 판관비 (카테고리에 안 들어간 항목)
    all_categorized: set[str] = set()
    for keywords in categories.values():
        all_categorized.update(keywords)

    other_items: list[tuple[str, dict[str, Decimal]]] = []
    for p in periods:
        fs_is = fs_data.get("is", {}).get(p, {})
        sga_keys = [
            k
            for k in {
                **bu_pl[p],
                **{kk: _safe_decimal(vv) for kk, vv in fs_is.items()},
            }.keys()
            if k
            not in {
                "매출액",
                "매출원가",
                "매출총이익",
                "매출이익",
                "영업이익",
                "판매비와관리비",
                "판관비",
                "영업외수익",
                "영업외비용",
                "법인세차감전이익",
                "법인세등",
                "당기순이익",
            }
            and not any(kw in k for kw in sum(categories.values(), []))
        ]
        for k in sga_keys:
            v = _safe_decimal(bu_pl[p].get(k, fs_is.get(k, 0)))
            if abs(v) > ZERO:
                found = False
                for sn, sv in other_items:
                    if sn == k:
                        sv[p] = v
                        found = True
                        break
                if not found:
                    other_items.append((k, {p: v}))

    cols = [TableColumn(key="account", header="과목", width=2.5, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
        cols.append(
            TableColumn(
                key=f"pct_{pi}", header="% Rev", width=1.0, align=AlignType.CENTER
            )
        )
    cols.append(
        TableColumn(key="comment", header="Comment", width=3.5, align=AlignType.LEFT)
    )

    return TableBlock(
        title="SGA Analysis", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_labor_block(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
) -> TableBlock:
    """Labor Cost & Headcount Analysis."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    rows: list[dict[str, Any]] = []

    def _lrow(label: str, vals: dict[str, str], note: str = "") -> dict:
        r: dict[str, Any] = {"account": label}
        for pi, p in enumerate(periods):
            r[f"fy_{pi}"] = vals.get(p, "")
        r["note"] = note
        return r

    # A. 인건비 분석
    rows.append(_lrow("A. 인건비 분석", {}))
    labor_components = ["직원급여", "급여", "퇴직급여", "복리후생비"]
    labor_totals: dict[str, Decimal] = {p: ZERO for p in periods}

    for comp in labor_components:
        comp_vals: dict[str, str] = {}
        has_data = False
        for p in periods:
            v = bu_pl[p].get(comp, ZERO)
            if v == ZERO and fs_data.get("is") and p in fs_data["is"]:
                v = _safe_decimal(fs_data["is"][p].get(comp, 0))
            if v != ZERO:
                comp_vals[p] = _fmt(v)
                labor_totals[p] += abs(v)
                has_data = True
        if has_data:
            rows.append(_lrow(f"  {comp}", comp_vals))

    rows.append(
        _lrow(
            "인건비 합계",
            {p: _fmt(labor_totals[p]) for p in periods if labor_totals[p] != ZERO},
        )
    )

    # B. 인원 (데이터 없으면 N/A)
    rows.append(_lrow("", {}))
    rows.append(_lrow("B. 인원 현황", {}))
    rows.append(
        _lrow(
            "  인원수",
            {p: "N/A (데이터 없음)" for p in periods},
            "급여대장 기준 인원 필요",
        )
    )

    # C. 인건비율
    rows.append(_lrow("", {}))
    rows.append(_lrow("C. 인건비율 분석", {}))
    rev_pct_vals: dict[str, str] = {}
    for p in periods:
        rev = bu_pl[p].get("매출액", ZERO)
        if rev == ZERO and fs_data.get("is") and p in fs_data["is"]:
            rev = _safe_decimal(fs_data["is"][p].get("매출액", 0))
        if rev != ZERO and labor_totals[p] != ZERO:
            rev_pct_vals[p] = f"{float(labor_totals[p] / rev * _HUNDRED):.1f}%"
    rows.append(_lrow("인건비 / 매출액", rev_pct_vals))

    cols = [TableColumn(key="account", header="구분", width=2.5, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=2.0, align=AlignType.RIGHT)
        )
    cols.append(
        TableColumn(key="note", header="Comment", width=4.0, align=AlignType.LEFT)
    )

    return TableBlock(
        title="Labor Analysis", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_nwc_block(
    nwc_data: dict[str, Any],
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
) -> TableBlock:
    """NWC Analysis — 매출/매입채권 + DSO/DPO + 변동."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    rows: list[dict[str, Any]] = []

    def _nrow(
        label: str, vals: dict[str, str], delta: str = "", note: str = ""
    ) -> dict:
        r: dict[str, Any] = {"account": label}
        for pi, p in enumerate(periods):
            r[f"fy_{pi}"] = vals.get(p, "")
        r["delta"] = delta
        r["note"] = note
        return r

    # NWC 항목을 BS에서 추출
    bs = fs_data.get("bs", {})
    receivable_keys = ["외상매출금", "매출채권", "미수수익", "미수금"]
    payable_keys = ["미지급금", "미지급비용", "예수금"]
    other_asset_keys = ["선급금", "선급비용"]
    other_liab_keys = ["부가세예수금", "선수금", "선수수익"]

    def _extract_group(keys: list[str], label: str) -> None:
        rows.append(_nrow(label, {}))
        group_total: dict[str, Decimal] = {p: ZERO for p in periods}
        for key in keys:
            vals: dict[str, str] = {}
            has = False
            for p in periods:
                v = _safe_decimal(bs.get(p, {}).get(key, 0))
                if v != ZERO:
                    vals[p] = _fmt(v)
                    group_total[p] += v
                    has = True
            if has:
                delta_str = ""
                if len(periods) >= 2:
                    last = _safe_decimal(bs.get(periods[-1], {}).get(key, 0))
                    prev = _safe_decimal(bs.get(periods[-2], {}).get(key, 0))
                    if last != ZERO or prev != ZERO:
                        delta_str = _fmt(last - prev)
                rows.append(_nrow(f"  {key}", vals, delta_str))

        total_vals = {
            p: _fmt(group_total[p]) for p in periods if group_total[p] != ZERO
        }
        delta_t = ""
        if len(periods) >= 2:
            delta_t = _fmt(group_total[periods[-1]] - group_total[periods[-2]])
        rows.append(_nrow(f"{label} 합계", total_vals, delta_t))

    _extract_group(receivable_keys, "Trade Receivables (매출채권)")
    rows.append(_nrow("", {}))
    _extract_group(other_asset_keys, "Other Current Assets")
    rows.append(_nrow("", {}))
    _extract_group(payable_keys, "Trade Payables (매입채무)")
    rows.append(_nrow("", {}))
    _extract_group(other_liab_keys, "Other Current Liabilities")

    # NWC 합계
    rows.append(_nrow("", {}))
    nwc_total = nwc_data.get("items", [])
    td = nwc_data.get("turnover_days", {})
    rows.append(
        _nrow(
            "Net Working Capital", {}, note="매출채권 + 기타자산 - 매입채무 - 기타부채"
        )
    )

    # DSO/DPO
    rows.append(_nrow("", {}))
    ar_days = td.get("ar_days", 0)
    ap_days = td.get("ap_days", 0)
    rows.append(
        _nrow(
            "DSO (매출채권 회전일수)",
            {periods[-1]: f"{ar_days:.0f}일"} if periods else {},
        )
    )
    rows.append(
        _nrow(
            "DPO (매입채무 회전일수)",
            {periods[-1]: f"{ap_days:.0f}일"} if periods else {},
        )
    )

    cols = [TableColumn(key="account", header="구분", width=3.0, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
    cols.append(
        TableColumn(key="delta", header="Δ 증감", width=1.5, align=AlignType.RIGHT)
    )
    cols.append(
        TableColumn(key="note", header="Comment", width=3.5, align=AlignType.LEFT)
    )

    return TableBlock(
        title="NWC Analysis", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_capex_block(
    fixed_assets: dict[str, dict[str, Decimal]],
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
) -> TableBlock:
    """CapEx & Fixed Asset Analysis."""
    from app.renderers.report_builder import AlignType, TableBlock, TableColumn

    periods = sorted(bu_pl.keys())
    fa_periods = sorted(fixed_assets.keys())
    rows: list[dict[str, Any]] = []

    def _crow(label: str, vals: dict[str, str], note: str = "") -> dict:
        r: dict[str, Any] = {"account": label}
        for pi in range(len(periods)):
            r[f"fy_{pi}"] = vals.get(periods[pi], "") if pi < len(periods) else ""
        r["note"] = note
        return r

    # A. 유형자산
    rows.append(_crow("A. 유형자산", {}))

    for p in fa_periods:
        if p in [pp for pp in periods]:
            assets = fixed_assets[p]
            for k, v in assets.items():
                if v != ZERO:
                    found = False
                    for existing in rows:
                        if existing["account"] == f"  {k}":
                            # 기존 행에 값 추가
                            pi = periods.index(p) if p in periods else -1
                            if pi >= 0:
                                existing[f"fy_{pi}"] = _fmt(v)
                            found = True
                            break
                    if not found:
                        vals = {p: _fmt(v)}
                        rows.append(_crow(f"  {k}", vals))

    # B. CapEx 추정 (감가상각비 역산)
    rows.append(_crow("", {}))
    rows.append(_crow("B. CapEx 추정", {}))

    depr_vals: dict[str, str] = {}
    for p in periods:
        items = bu_pl[p]
        fs_is = fs_data.get("is", {}).get(p, {})
        depr = ZERO
        for k, v in {
            **items,
            **{kk: _safe_decimal(vv) for kk, vv in fs_is.items()},
        }.items():
            if "감가상각" in k and "무형" not in k:
                depr = max(
                    depr, abs(_safe_decimal(v) if not isinstance(v, Decimal) else v)
                )
        if depr != ZERO:
            depr_vals[p] = _fmt(depr)
    rows.append(_crow("  감가상각비", depr_vals))

    # CapEx / Revenue
    rows.append(_crow("", {}))
    capex_rev_vals: dict[str, str] = {}
    for p in periods:
        rev = bu_pl[p].get("매출액", ZERO)
        if rev == ZERO and fs_data.get("is") and p in fs_data["is"]:
            rev = _safe_decimal(fs_data["is"][p].get("매출액", 0))
        # CapEx는 감가상각비를 대용 (실제 취득 데이터 없으면)
        depr = ZERO
        fs_is = fs_data.get("is", {}).get(p, {})
        for k, v in {
            **bu_pl[p],
            **{kk: _safe_decimal(vv) for kk, vv in fs_is.items()},
        }.items():
            if "감가상각" in k:
                depr += abs(_safe_decimal(v) if not isinstance(v, Decimal) else v)
        if rev != ZERO and depr != ZERO:
            capex_rev_vals[p] = f"{float(depr / rev * _HUNDRED):.1f}%"
    rows.append(
        _crow(
            "CapEx / Revenue",
            capex_rev_vals,
            "감가상각비 기준 (Maintenance CapEx proxy)",
        )
    )

    cols = [TableColumn(key="account", header="구분", width=3.0, align=AlignType.LEFT)]
    for pi, p in enumerate(periods):
        cols.append(
            TableColumn(key=f"fy_{pi}", header=p, width=1.8, align=AlignType.RIGHT)
        )
    cols.append(
        TableColumn(key="note", header="Comment", width=4.0, align=AlignType.LEFT)
    )

    return TableBlock(
        title="CapEx Analysis", columns=cols, rows=rows, metadata={"style": "table"}
    )


def build_cross_checks(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
    debt_items: list[dict[str, Any]],
    bs_data: dict[str, dict[str, Decimal]],
) -> list[dict[str, Any]]:
    """데이터 소스 간 교차검증."""
    checks: list[dict[str, Any]] = []

    # 1. BU P&L 매출 vs FS IS 매출 (FY2023)
    bu_fy23_rev = bu_pl.get("FY2023", {}).get("매출액", ZERO)
    fs_fy23_rev = ZERO
    # 정규화 후 키: "FY2023" 또는 원본 "FY23"
    fs_is_fy23 = fs_data.get("is", {}).get(
        "FY2023", fs_data.get("is", {}).get("FY23", {})
    )
    for k, v in fs_is_fy23.items():
        clean_k = k.replace(" ", "")
        # 매출(액)에 매칭하되, 매출원가/매출총이익은 제외
        if (
            "매출" in clean_k
            and "원가" not in clean_k
            and "이익" not in clean_k
            and "총" not in clean_k
        ):
            val = _safe_decimal(v)
            if val > ZERO:
                fs_fy23_rev = val
                break
    diff1 = bu_fy23_rev - fs_fy23_rev
    checks.append(
        {
            "check": "BU P&L 매출 vs FS IS 매출 (FY2023)",
            "source_a": "12-1. 사업부 매출이익현황",
            "source_b": "33. 재무제표 — 손익계산서",
            "expected": _fmt(bu_fy23_rev),
            "actual": _fmt(fs_fy23_rev),
            "difference": _fmt(abs(diff1)),
            "status": "Pass" if abs(diff1) < Decimal("10") else "Fail",
        }
    )

    # 2. BS 차입금 vs 차입금 현황표
    bs_debt = ZERO
    bs_fy24 = bs_data.get("FY2024", bs_data.get("FY24.9M", {}))
    for k, v in bs_fy24.items():
        clean = k.replace(" ", "")
        if "차입금" in clean and _safe_decimal(v) > ZERO:
            bs_debt += _safe_decimal(v)
    schedule_debt = sum(d.get("_balance_dec", ZERO) for d in debt_items)
    diff2 = bs_debt - schedule_debt
    checks.append(
        {
            "check": "BS 차입금 vs 차입금 현황표 잔액",
            "source_a": "33. 재무제표 — 재무상태표",
            "source_b": "26. 차입금 현황표",
            "expected": _fmt(bs_debt),
            "actual": _fmt(schedule_debt),
            "difference": _fmt(abs(diff2)),
            "status": "Pass" if abs(diff2) < Decimal("100") else "Fail",
        }
    )

    # 3. BS 자산 = 부채 + 자본 (대차균형 검증)
    for period in sorted(bs_data.keys()):
        items = bs_data[period]
        total_asset = ZERO
        total_liab = ZERO
        total_equity = ZERO
        for k, v in items.items():
            clean = k.replace(" ", "")
            if "자산총계" in clean:
                total_asset = v
            elif "부채총계" in clean:
                total_liab = v
            elif "자본총계" in clean:
                total_equity = v
        if total_asset > ZERO:
            diff3 = total_asset - (total_liab + total_equity)
            checks.append(
                {
                    "check": f"BS 대차균형 ({period})",
                    "source_a": f"자산총계 {_fmt(total_asset)}",
                    "source_b": f"부채+자본 {_fmt(total_liab + total_equity)}",
                    "expected": _fmt(total_asset),
                    "actual": _fmt(total_liab + total_equity),
                    "difference": _fmt(abs(diff3)),
                    "status": "Pass" if abs(diff3) < Decimal("1") else "Fail",
                }
            )

    return checks


# ═══════════════════════════════════════════════════════════
# IS 코드 매핑 확장 + FS 데이터 merge
# ═══════════════════════════════════════════════════════════


def build_amounts_by_period(
    bu_pl: dict[str, dict[str, Decimal]],
    fs_data: dict[str, Any],
) -> dict[str, dict[str, Decimal]]:
    """사업부 P&L + 재무제표 IS → multiperiod_engine 입력 형식.

    사업부 P&L: 매출액, 매출원가, 매출총이익 (4개년)
    재무제표 IS: 판관비, 이자비용, 순이익 등 (2개년) → merge
    """
    ITEM_MAP = {
        "매출액": "IS-REV-001",
        "매출": "IS-REV-001",
        "매출원가": "IS-COGS-001",
        "원가": "IS-COGS-001",
        "매출이익": "IS-GP-001",
        "매출총이익": "IS-GP-001",
    }

    amounts: dict[str, dict[str, Decimal]] = {}

    for period, items in bu_pl.items():
        period_data: dict[str, Decimal] = {}
        for item_name, value in items.items():
            code = ITEM_MAP.get(item_name)
            if not code:
                for keyword, c in ITEM_MAP.items():
                    if keyword in item_name:
                        code = c
                        break
            if code:
                period_data[code] = value

        rev = period_data.get("IS-REV-001", ZERO)
        cogs = period_data.get("IS-COGS-001", ZERO)
        gp = period_data.get("IS-GP-001", ZERO)
        if gp == ZERO and rev != ZERO:
            period_data["IS-GP-001"] = rev - cogs

        amounts[period] = period_data

    # FS IS 데이터 merge (FY24.9M → FY2024, FY23 → FY2023 매핑 시도)
    fs_is = fs_data.get("is", {})
    FS_PERIOD_MAP = {"FY24.9M": "FY2024", "FY23": "FY2023"}
    FS_ITEM_MAP = {
        "판매비": "IS-SGA-001",
        "판관비": "IS-SGA-001",
        "감가상각": "IS-DA-001",
        "영업이익": "IS-OI-001",
        "영업손": "IS-OI-001",
        "이자비용": "IS-INT-EXP-001",
        "당기순": "IS-NI-001",
    }

    for fs_period, bu_period in FS_PERIOD_MAP.items():
        if fs_period not in fs_is or bu_period not in amounts:
            continue
        fs_items = fs_is[fs_period]
        target = amounts[bu_period]

        for account, value in fs_items.items():
            clean = account.replace(" ", "")
            for keyword, code in FS_ITEM_MAP.items():
                if keyword in clean and code not in target:
                    target[code] = value
                    break

        # EBITDA = 영업이익 + 감가상각비
        oi = target.get("IS-OI-001", ZERO)
        da = target.get("IS-DA-001", ZERO)
        if oi != ZERO:
            target["IS-EBITDA-001"] = oi + abs(da)

    return amounts


# ═══════════════════════════════════════════════════════════
# 메인: 엔진 실행 + Report IR 조립 + Excel 렌더링
# ═══════════════════════════════════════════════════════════


def build_report(
    deal_name: str,
    input_dir: Path,
    industry_id: str = "general",
    use_llm: bool = False,
    no_quality: bool = False,
    quality_threshold: float = 3.5,
    max_llm_iterations: int = 3,
) -> Any:
    """Report IR을 조립한다."""
    global _guardrail_warnings
    _guardrail_warnings = []

    from app.renderers.report_builder import (
        AlignType,
        CoverBlock,
        ReportIR,
        ReportMetadata,
        TableBlock,
        TableColumn,
        build_issue_block,
    )

    # 품질 인프라 초기화
    tracker: Any = None
    convergence: Any = None
    if not no_quality:
        try:
            from app.ralph.convergence import ConvergenceChecker, ConvergenceConfig
            from app.ralph.progress_tracker import ProgressTracker

            tracker = ProgressTracker()
            convergence = ConvergenceChecker(
                ConvergenceConfig(
                    pass_threshold=quality_threshold,
                    improvement_threshold=0.3,
                    max_iterations_per_section=max_llm_iterations,
                    max_cost_usd=5.0,
                )
            )
            _p("[Quality] Ralph Loop infrastructure initialized")
        except ImportError as e:
            _p(f"[Quality] Ralph Loop not available ({e}) — single-pass mode")

    commentary = RuleBasedCommentary()
    llm_overlay: LLMCommentaryOverlay | None = None
    if use_llm:
        _p("\n[LLM] Initializing LLM router...")
        router = _init_llm_router()
        if router:
            llm_overlay = LLMCommentaryOverlay(router)

    _p("\n" + "=" * 60)
    _p(f"  {deal_name} FDD Working Paper Generation")
    _p(f"  Input: {input_dir}")
    _p("=" * 60)

    # ── 1. Parsing ──
    _p("\n[1/7] Financial Statements...")
    fs_data = parse_financial_statements(input_dir)

    _p("\n[2/7] Business Unit P&L...")
    bu_pl = parse_business_unit_pl(input_dir)

    _p("\n[3/7] Customer Revenue...")
    customer_entries = parse_customer_revenue(input_dir)

    _p("\n[4/7] Purchase Ledger...")
    purchase_entries = parse_purchase_ledger(input_dir)

    _p("\n[5/7] Debt / Assets / Cash...")
    debt_items = parse_debt_schedule(input_dir)
    fixed_assets = parse_fixed_assets(input_dir)
    cash_total = parse_cash(input_dir)

    _p("\n[6/7] NWC Analysis...")
    nwc_data = compute_local_nwc(
        fs_data.get("bs", {}),
        fs_data.get("is", {}),
    )
    _p(
        f"    [OK] NWC: {len(nwc_data['items'])} items, AR Days={nwc_data['turnover_days'].get('ar_days', 0):.0f}"
    )

    # ── FS 기간 키 정규화 (FY23 → FY2023, FY24.9M → FY2024) ──
    bu_period_keys = sorted(bu_pl.keys())
    _p(f"\n    [NORM] bu_pl periods: {bu_period_keys}")
    _p(f"    [NORM] fs_data IS periods: {sorted(fs_data.get('is', {}).keys())}")
    _p(f"    [NORM] fs_data BS periods: {sorted(fs_data.get('bs', {}).keys())}")
    fs_data = _normalize_fs_data_periods(fs_data, bu_period_keys)
    _p(f"    [NORM] normalized IS periods: {sorted(fs_data.get('is', {}).keys())}")
    _p(f"    [NORM] normalized BS periods: {sorted(fs_data.get('bs', {}).keys())}")

    # LLM overlay에 known_values 설정 (guardrails 용)
    if llm_overlay and bu_pl:
        known_vals: dict[str, str] = {}
        known_pcts: dict[str, str] = {}
        known_trends: dict[str, str] = {}
        periods = sorted(bu_pl.keys())
        for p in periods:
            items = bu_pl[p]
            # 모든 주요 계정의 금액을 known_values에 등록
            for acct_name, acct_val in items.items():
                if acct_val != ZERO and abs(acct_val) >= Decimal("100"):
                    known_vals[f"{p}_{acct_name}"] = str(int(acct_val))
            rev = items.get("매출액", ZERO)
            gp = items.get("매출이익", items.get("매출총이익", ZERO))
            op = items.get("영업이익", ZERO)
            if rev != ZERO:
                if gp != ZERO:
                    known_pcts[f"{p}_GP마진"] = f"{float(gp / rev * _HUNDRED):.1f}"
                if op != ZERO:
                    known_pcts[f"{p}_OP마진"] = f"{float(op / rev * _HUNDRED):.1f}"
        # 차입금/NWC 수치도 등록
        for d in debt_items:
            bal = d.get("_balance_dec", ZERO)
            if bal != ZERO:
                known_vals[f"debt_{d.get('lender', 'unknown')}"] = str(int(bal))
        total_debt_kv = sum(d.get("_balance_dec", ZERO) for d in debt_items)
        if total_debt_kv != ZERO:
            known_vals["total_debt"] = str(int(total_debt_kv))
        if cash_total != ZERO:
            known_vals["cash"] = str(int(cash_total))
        net_debt_kv = total_debt_kv - cash_total
        if net_debt_kv != ZERO:
            known_vals["net_debt"] = str(int(net_debt_kv))
        # NWC 항목
        for nwc_item in nwc_data.get("items", []):
            if isinstance(nwc_item, dict):
                nwc_amt = nwc_item.get("amount", ZERO)
                if isinstance(nwc_amt, Decimal) and abs(nwc_amt) >= Decimal("100"):
                    known_vals[f"nwc_{nwc_item.get('label', 'item')}"] = str(
                        int(nwc_amt)
                    )
        # YoY 트렌드
        if len(periods) >= 2:
            prev_items = bu_pl[periods[-2]]
            curr_items = bu_pl[periods[-1]]
            for metric_name in ["매출액", "매출총이익", "영업이익"]:
                prev_val = prev_items.get(metric_name, ZERO)
                curr_val = curr_items.get(metric_name, ZERO)
                if prev_val > ZERO and curr_val > ZERO:
                    known_trends[metric_name] = (
                        "increase" if curr_val > prev_val else "decrease"
                    )
                    # YoY 변동률도 known_pcts에 등록
                    yoy_pct = float((curr_val - prev_val) / prev_val * _HUNDRED)
                    known_pcts[f"{metric_name}_YoY"] = f"{yoy_pct:.1f}"
        llm_overlay._known_values = known_vals
        llm_overlay._known_pcts = known_pcts
        llm_overlay._known_trends = known_trends

    # ── 2. Report IR 조립 (FDD 샘플 13-시트 구조) ──
    _p("\n[7/7] Report IR assembly...")

    sections: list[Any] = []
    period_labels = sorted(bu_pl.keys())

    # ── 1. Cover ──
    sections.append(
        CoverBlock(
            deal_name=deal_name,
            deal_type="Financial Due Diligence",
            target_name=f"{deal_name}주식회사",
            date=date.today(),
            prepared_by="AMIC x PETRA Platform",
            confidentiality="CONFIDENTIAL",
        )
    )

    # ── 1b. Project Overview (TOC + 프로젝트 정보) ──
    overview_rows: list[dict[str, Any]] = [
        {"item": "대상 기업", "section": f"{deal_name}주식회사", "description": ""},
        {
            "item": "분석 기간",
            "section": f"{period_labels[0]} ~ {period_labels[-1]}"
            if period_labels
            else "N/A",
            "description": "",
        },
        {"item": "통화/단위", "section": "KRW (백만원)", "description": ""},
        {
            "item": "데이터 소스",
            "section": "재무제표, BU P&L, 매출원장, 매입원장, 차입금현황표, 유형자산명세서",
            "description": "",
        },
        {"item": "---", "section": "--- Table of Contents ---", "description": "---"},
        {"item": "1", "section": "Cover", "description": "프로젝트 개요"},
        {
            "item": "2",
            "section": "Executive Summary",
            "description": "핵심 분석 요약 (AI 생성)",
        },
        {
            "item": "3",
            "section": "PL Overview",
            "description": "다기간 손익계산서 + YoY + 마진분석",
        },
        {
            "item": "4",
            "section": "QoE",
            "description": "Quality of Earnings — Adjusted EBITDA Bridge",
        },
        {
            "item": "5",
            "section": "BS Overview",
            "description": "다기간 재무상태표 + 증감",
        },
        {
            "item": "6",
            "section": "QoA",
            "description": "Quality of Net Assets — Net Debt + NWC",
        },
        {
            "item": "7",
            "section": "Revenue",
            "description": "매출 유형별 분석 + 구성비 + 집중도",
        },
        {"item": "8", "section": "SGA", "description": "카테고리별 판관비 + %Revenue"},
        {"item": "9", "section": "Labor", "description": "인건비 + 인원 + 인건비율"},
        {"item": "10", "section": "NWC", "description": "순운전자본 + DSO/DPO + 변동"},
        {"item": "11", "section": "CapEx", "description": "유형/무형자산 + CapEx 역산"},
        {
            "item": "12",
            "section": "Key Issues & Findings",
            "description": "핵심 발견사항 및 리스크",
        },
    ]
    sections.append(
        TableBlock(
            title="Project Overview",
            columns=[
                TableColumn(key="item", header="#", width=0.8, align=AlignType.CENTER),
                TableColumn(
                    key="section", header="시트 / 정보", width=3.0, align=AlignType.LEFT
                ),
                TableColumn(
                    key="description", header="설명", width=5.0, align=AlignType.LEFT
                ),
            ],
            rows=overview_rows,
            metadata={"style": "table"},
        )
    )
    _p("    [OK] Project Overview (TOC)")

    # ── 사전 계산: Revenue HHI ──
    hhi = ZERO
    top5_share = ZERO
    top1_name = ""
    top1_share = ZERO
    revenue_observations: list[str] = []

    if customer_entries:
        try:
            from app.engines.revenue_engine import compute_revenue_breakdown

            cust_result, _ = compute_revenue_breakdown(
                customer_entries,
                dimension="customer",
                dimension_key="customer_name",
            )
            if cust_result.breakdown:
                hhi = cust_result.concentration_index or ZERO
                top5_share = cust_result.top_n_share or ZERO
                top1 = cust_result.breakdown[0]
                top1_name = top1.name
                top1_share = top1.share_pct
                revenue_observations = commentary.for_revenue_concentration(
                    hhi, top5_share, top1_name, top1_share
                )
                if llm_overlay and revenue_observations:
                    llm_rev = llm_overlay.enhance_revenue(
                        hhi, top5_share, top1_name, top1_share, revenue_observations
                    )
                    if llm_rev:
                        for line in llm_rev.split("\n"):
                            line = line.strip()
                            if line:
                                revenue_observations.append(f"[AI] {line}")
                if llm_overlay and hhi > ZERO:
                    llm_overlay._known_values["hhi"] = str(int(hhi))
                _p(f"    [OK] Revenue HHI={hhi:.0f}, Top1={top1_name}")
        except Exception as e:
            _p(f"    [FAIL] Revenue pre-calc: {e}")

    # ── 사전 계산: IS Commentary ──
    is_commentary = commentary.for_multiperiod_is(bu_pl)
    commentary_map: dict[str, str] = {}
    for bullet in is_commentary:
        for key in ["매출 ", "GP 마진", "매출 CAGR"]:
            if key in bullet:
                if "매출 CAGR" in bullet:
                    commentary_map["매출액"] = (
                        commentary_map.get("매출액", "") + " | " + bullet
                        if "매출액" in commentary_map
                        else bullet
                    )
                elif "GP 마진" in bullet:
                    for p in sorted(bu_pl.keys()):
                        if p in bullet:
                            commentary_map["매출총이익"] = (
                                commentary_map.get("매출총이익", "") + "; " + bullet
                                if "매출총이익" in commentary_map
                                else bullet
                            )
                else:
                    commentary_map["매출액"] = (
                        commentary_map.get("매출액", "") + "; " + bullet
                        if "매출액" in commentary_map
                        else bullet
                    )
    if llm_overlay:
        llm_is_text = llm_overlay.enhance_is(bu_pl, is_commentary)
        if llm_is_text:
            for line in llm_is_text.split("\n"):
                line = line.strip()
                if line:
                    commentary_map[f"[AI] {line[:60]}"] = line

    # ── 3. PL Overview ──
    pl_block = build_pl_overview(bu_pl, fs_data, commentary_map)
    sections.append(pl_block)
    _p(f"    [OK] PL Overview: {len(pl_block.rows)} rows")

    # ── 4. QoE (Quality of Earnings) ──
    qoe_block = build_qoe_block(bu_pl, fs_data)
    sections.append(qoe_block)
    _p(f"    [OK] QoE: {len(qoe_block.rows)} rows")

    # ── 5. BS Overview ──
    bs_block = build_bs_overview(fs_data)
    sections.append(bs_block)
    _p(f"    [OK] BS Overview: {len(bs_block.rows)} rows")

    # ── 6. QoA (Quality of Net Assets) ──
    qoa_block = build_qoa_block(debt_items, cash_total, nwc_data, fs_data, bu_pl)
    sections.append(qoa_block)
    _p(f"    [OK] QoA: {len(qoa_block.rows)} rows")

    # ── 7. Revenue Analysis ──
    rev_block = build_revenue_analysis(
        bu_pl, fs_data, customer_entries, hhi, revenue_observations
    )
    sections.append(rev_block)
    _p(f"    [OK] Revenue: {len(rev_block.rows)} rows")

    # ── 8. SGA Analysis ──
    sga_block_ir = build_sga_block(bu_pl, fs_data)
    sections.append(sga_block_ir)
    _p(f"    [OK] SGA: {len(sga_block_ir.rows)} rows")

    # ── 9. Labor Analysis ──
    labor_block_ir = build_labor_block(bu_pl, fs_data)
    sections.append(labor_block_ir)
    _p(f"    [OK] Labor: {len(labor_block_ir.rows)} rows")

    # ── 10. NWC Analysis ──
    nwc_block_ir = build_nwc_block(nwc_data, bu_pl, fs_data)
    sections.append(nwc_block_ir)
    _p(f"    [OK] NWC: {len(nwc_block_ir.rows)} rows")

    # ── 11. CapEx Analysis ──
    capex_block_ir = build_capex_block(fixed_assets, bu_pl, fs_data)
    sections.append(capex_block_ir)
    _p(f"    [OK] CapEx: {len(capex_block_ir.rows)} rows")

    # ── Cross-check (내부 검증, Quality Report에서 활용) ──
    checks = build_cross_checks(bu_pl, fs_data, debt_items, fs_data.get("bs", {}))
    if checks:
        pass_count = sum(1 for c in checks if c["status"] == "Pass")
        _p(f"    [OK] Cross-check: {pass_count}/{len(checks)} passed")

    # ── 12. Key Issues & Findings ──
    issues = commentary.for_issues(
        bu_pl, hhi, nwc_data, debt_items, cash_total, fs_data
    )
    if issues:
        sections.append(
            build_issue_block(issues, title="Key Issues & Findings (핵심 발견사항)")
        )
        _p(f"    [OK] Issues: {len(issues)} items detected")

    # ── LLM Executive Summary (--use-llm 전용, Ralph Loop 적용) ──
    if llm_overlay:
        _p("\n[LLM] Generating Executive Summary...")

        def _gen_es() -> str:
            return llm_overlay.generate_executive_summary(
                deal_name,
                bu_pl,
                hhi,
                nwc_data,
                debt_items,
                issues,
            )

        # Quality Loop: 점수 < threshold이면 최대 max_iter까지 재생성
        if tracker and convergence:
            llm_es = _generate_with_quality_loop(
                _gen_es,
                "executive_summary",
                source_data={"financial_statements": {}},
                tracker=tracker,
                convergence=convergence,
                max_iter=max_llm_iterations,
            )
        else:
            llm_es = _gen_es()

        if llm_es:
            # Executive Summary를 TableBlock으로 렌더
            es_rows = []
            for line in llm_es.split("\n"):
                line = line.strip()
                if line:
                    es_rows.append({"section": "", "content": line})
            sections.insert(
                2,
                TableBlock(  # Cover 다음, IS 앞에 삽입
                    title="Executive Summary (AI)",
                    columns=[
                        TableColumn(
                            key="section", header="", width=1.0, align=AlignType.LEFT
                        ),
                        TableColumn(
                            key="content",
                            header="분석",
                            width=8.0,
                            align=AlignType.LEFT,
                        ),
                    ],
                    rows=es_rows,
                    metadata={"style": "table"},
                ),
            )
            _p(f"    [OK] Executive Summary: {len(es_rows)} lines")

    # ── Quality Gate 평가 (전체 섹션) ──
    gate_results: list[dict[str, Any]] = []
    validation_result: dict[str, Any] = {}

    if not no_quality:
        _p("\n[Quality] Running Programmatic Gate on all sections...")
        gate_results = _run_section_gates(sections, tracker)
        pass_count = sum(1 for g in gate_results if g["status"] == "PASS")
        _p(f"    [Quality] {pass_count}/{len(gate_results)} sections PASS")

        # Cross-validation (validation.py)
        try:
            from app.services.report.validation import run_full_validation

            ir_dict = {"sections": [_block_to_dict(s) for s in sections]}
            validation_result = run_full_validation(ir_dict)
            v_passed = validation_result.get("passed", 0)
            v_total = validation_result.get("total_rules", 0)
            _p(f"    [Quality] Cross-validation: {v_passed}/{v_total} passed")
            for rule in validation_result.get("rules", []):
                _p(f"      {rule['status']}: {rule['message']}")
        except ImportError:
            _p("    [Quality] validation.py not available — skipping cross-validation")
        except Exception as e:
            _p(f"    [Quality] Cross-validation error: {e}")

    # ── Quality Report 시트 (실질화: 요약 통계 + 차원별 점수 + 개선 제안) ──
    if not no_quality and (gate_results or validation_result or _guardrail_warnings):
        quality_rows: list[dict[str, Any]] = []

        # ── 0. 요약 통계 헤더 ──
        total_sections = len(gate_results)
        pass_count_q = sum(1 for g in gate_results if g["status"] == "PASS")
        cond_count = sum(1 for g in gate_results if g["status"] == "COND")
        fail_count = sum(1 for g in gate_results if g["status"] == "FAIL")
        avg_score = sum(
            float(g["score"].split("/")[0])
            for g in gate_results
            if "/" in g.get("score", "")
        ) / max(total_sections, 1)
        v_passed = validation_result.get("passed", 0)
        v_total = validation_result.get("total_rules", 0)
        guardrail_count = len(_guardrail_warnings)

        quality_rows.append(
            {
                "section": "=== QUALITY SUMMARY ===",
                "gate": "",
                "score": f"평균 {avg_score:.2f}/5.0",
                "detail": f"PASS: {pass_count_q} | COND: {cond_count} | FAIL: {fail_count}",
                "status": "PASS" if fail_count == 0 else "REVIEW",
            }
        )
        quality_rows.append(
            {
                "section": "교차검증 (Cross-validation)",
                "gate": "",
                "score": f"{v_passed}/{v_total}",
                "detail": f"통과 {v_passed}건, 총 {v_total}건",
                "status": "PASS" if v_passed == v_total else "REVIEW",
            }
        )
        if guardrail_count > 0:
            quality_rows.append(
                {
                    "section": "Guardrails (할루시네이션 검증)",
                    "gate": "",
                    "score": f"{guardrail_count}건",
                    "detail": "아래 경고 상세 참조",
                    "status": "WARNING",
                }
            )
        quality_rows.append(
            {
                "section": "---",
                "gate": "---",
                "score": "---",
                "detail": "--- 아래: 섹션별 상세 ---",
                "status": "---",
            }
        )

        # ── 1. Programmatic Gate 결과 (차원별 점수 포함) ──
        for gr in gate_results:
            # 기본 행
            quality_rows.append(
                {
                    "section": gr["section"],
                    "gate": gr["gate"],
                    "score": gr["score"],
                    "detail": f"Verdict: {gr['verdict']}, Issues: {gr['issues']}",
                    "status": gr["status"],
                }
            )

        # ── 1b. ProgressTracker에서 차원별 점수 추출 ──
        if tracker is not None:
            quality_rows.append(
                {
                    "section": "---",
                    "gate": "---",
                    "score": "---",
                    "detail": "--- 차원별 점수 (Programmatic Gate) ---",
                    "status": "---",
                }
            )
            try:
                for section_id, records in tracker._records.items():
                    if not records:
                        continue
                    last_rec = records[-1]
                    for gr_dict in last_rec.gate_results:
                        dims = gr_dict.get("dimensions", [])
                        for dim in dims:
                            feedback_text = dim.get("feedback", "")
                            if not feedback_text or feedback_text == "":
                                feedback_text = "양호"
                            quality_rows.append(
                                {
                                    "section": f"  {section_id}",
                                    "gate": dim.get("label", dim.get("name", "")),
                                    "score": f"{dim.get('score', 0):.1f} (w={dim.get('weight', 0):.0%})",
                                    "detail": feedback_text[:80],
                                    "status": "OK"
                                    if dim.get("score", 0) >= 4.0
                                    else "LOW",
                                }
                            )
            except Exception:
                pass  # ProgressTracker 접근 실패 시 스킵

        # ── 2. Cross-validation 결과 ──
        if validation_result.get("rules"):
            quality_rows.append(
                {
                    "section": "---",
                    "gate": "---",
                    "score": "---",
                    "detail": "--- 교차검증 상세 ---",
                    "status": "---",
                }
            )
            for rule in validation_result.get("rules", []):
                detail_parts = []
                if rule.get("expected"):
                    detail_parts.append(f"Expected: {rule['expected']}")
                if rule.get("actual"):
                    detail_parts.append(f"Actual: {rule['actual']}")
                quality_rows.append(
                    {
                        "section": rule.get("rule_id", ""),
                        "gate": "Cross-validation",
                        "score": rule.get("status", ""),
                        "detail": rule.get("message", "")
                        + (" | " + ", ".join(detail_parts) if detail_parts else ""),
                        "status": rule.get("status", ""),
                    }
                )

        # ── 3. Guardrail 경고 ──
        if _guardrail_warnings:
            quality_rows.append(
                {
                    "section": "---",
                    "gate": "---",
                    "score": "---",
                    "detail": "--- Guardrail 경고 (할루시네이션 검증) ---",
                    "status": "---",
                }
            )
            for warning in _guardrail_warnings:
                quality_rows.append(
                    {
                        "section": "Guardrails",
                        "gate": "Hallucination",
                        "score": "—",
                        "detail": warning[:100],
                        "status": "WARNING",
                    }
                )

        # ── 4. 개선 제안 ──
        suggestions: list[str] = []
        if avg_score < 3.5:
            suggestions.append(
                "전체 평균 점수가 3.5 미만 — 데이터 품질 또는 파싱 정확도 개선 필요"
            )
        if fail_count > 0:
            suggestions.append(
                f"FAIL 섹션 {fail_count}개 — 해당 섹션 데이터 소스 재검토 필요"
            )
        if guardrail_count > 3:
            suggestions.append(
                f"Guardrail 경고 {guardrail_count}건 — LLM 코멘터리 교차검증 강화 권장"
            )
        if v_passed < v_total:
            suggestions.append("교차검증 불일치 — 재무제표 간 수치 정합성 재확인 필요")

        if suggestions:
            quality_rows.append(
                {
                    "section": "---",
                    "gate": "---",
                    "score": "---",
                    "detail": "--- 품질 개선 제안 ---",
                    "status": "---",
                }
            )
            for idx_s, suggestion in enumerate(suggestions, 1):
                quality_rows.append(
                    {
                        "section": f"제안 #{idx_s}",
                        "gate": "Recommendation",
                        "score": "—",
                        "detail": suggestion,
                        "status": "ACTION",
                    }
                )

        if quality_rows:
            quality_cols = [
                TableColumn(
                    key="section", header="Section", width=2.5, align=AlignType.LEFT
                ),
                TableColumn(
                    key="gate", header="Gate / 차원", width=2.0, align=AlignType.LEFT
                ),
                TableColumn(
                    key="score", header="Score", width=1.5, align=AlignType.CENTER
                ),
                TableColumn(
                    key="detail",
                    header="상세 / 피드백",
                    width=5.0,
                    align=AlignType.LEFT,
                ),
                TableColumn(
                    key="status", header="Status", width=1.0, align=AlignType.CENTER
                ),
            ]
            sections.append(
                TableBlock(
                    title="Quality Report",
                    columns=quality_cols,
                    rows=quality_rows,
                    metadata={"style": "table"},
                )
            )
            _p(f"    [Quality] Quality Report: {len(quality_rows)} items")

    # ── Report IR 조립 ──
    engine_versions = {
        "multiperiod": "0.1.0",
        "revenue": "0.1.0",
        "commentary": "rule-based-v1",
    }
    if not no_quality:
        engine_versions["quality_gate"] = "ralph-loop-v1"

    metadata = ReportMetadata(
        deal_id="wizcore-local",
        deal_name=deal_name,
        generated_at=datetime.utcnow().isoformat() + "Z",
        version="3.0-fdd-sample-structure",
        engine_versions=engine_versions,
    )

    report_ir = ReportIR(metadata=metadata, sections=sections)
    _p(f"\n  -> Report IR assembled: {len(sections)} sections")
    return report_ir


def main() -> None:
    parser = argparse.ArgumentParser(description="FDD Working Paper 로컬 생성")
    parser.add_argument("--input-dir", required=True, help="실사자료 FDD 폴더 경로")
    parser.add_argument(
        "--output",
        default="./generated/WizCore_FDD_WP.xlsx",
        help="출력 Excel 파일 경로",
    )
    parser.add_argument("--deal-name", default="WizCore", help="딜 이름")
    parser.add_argument("--industry", default="general", help="산업 식별자")
    parser.add_argument(
        "--use-llm", action="store_true", help="LLM 코멘터리 활성화 (API 키 필요)"
    )
    parser.add_argument(
        "--no-quality", action="store_true", help="품질 검증 비활성화 (속도 우선)"
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=3.5,
        help="LLM 반복 중단 기준 (기본 3.5)",
    )
    parser.add_argument(
        "--max-llm-iterations",
        type=int,
        default=3,
        help="LLM 섹션당 최대 반복 (기본 3)",
    )
    args = parser.parse_args()

    # .env 파일에서 환경변수 로딩 (dotenv 있으면)
    if args.use_llm:
        try:
            from dotenv import load_dotenv

            # 탐색 순서: fdd/backend/.env → fdd/.env → 프로젝트 루트/.env
            base = Path(__file__).resolve().parent.parent
            for env_candidate in [
                base / ".env",
                base.parent / ".env",
                base.parent.parent / ".env",
            ]:
                if env_candidate.exists():
                    load_dotenv(env_candidate)
                    print(f"[ENV] Loaded {env_candidate}")
                    break
        except ImportError:
            print("[ENV] python-dotenv not installed — using system env vars")

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_ir = build_report(
        args.deal_name,
        input_dir,
        args.industry,
        use_llm=args.use_llm,
        no_quality=args.no_quality,
        quality_threshold=args.quality_threshold,
        max_llm_iterations=args.max_llm_iterations,
    )

    print("\n[Rendering] Generating Excel WP...")
    from app.renderers.excel_renderer import render_excel_report

    render_excel_report(report_ir, output_path=output_path)

    print(f"\n{'=' * 60}")
    print("  [DONE] FDD Working Paper generated!")
    print(f"  Output: {output_path.resolve()}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
