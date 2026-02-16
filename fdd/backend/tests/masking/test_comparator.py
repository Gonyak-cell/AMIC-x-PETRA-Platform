"""내부/외부 비교 + 누출 검사 테스트 — FDD-1404, FDD-1405."""

import pytest

from app.services.masking.comparator import (
    ComparisonResult,
    check_sensitive_data_leak,
    compare_reports,
)
from app.services.masking.engine import DistributionMode, MaskingEngine


def _make_internal_ir():
    return {
        "sections": [
            {
                "id": "qoe",
                "blocks": [
                    {"type": "kpi", "value": "1234567"},
                    {"type": "table", "rows": [{"a": 100, "b": "text"}]},
                    {"type": "text", "content": "매출 1,234,567원 발생"},
                ],
            }
        ],
    }


def _make_masked_ir(engine: MaskingEngine, internal_ir: dict) -> dict:
    return engine.mask_report_ir(internal_ir)


# ── compare_reports ────────────────────────────────────


def test_compare_valid_external():
    internal = _make_internal_ir()
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    external = _make_masked_ir(engine, internal)

    result = compare_reports(internal, external, DistributionMode.EXTERNAL_BUYER)
    assert result.internal_mode == "INTERNAL"
    assert result.external_mode == "EXTERNAL_BUYER"
    assert isinstance(result.total_checks, int)
    assert result.total_checks > 0


def test_compare_missing_mode_flag():
    internal = _make_internal_ir()
    external = {"sections": []}  # no distribution_mode
    result = compare_reports(internal, external, DistributionMode.EXTERNAL_BUYER)
    assert any("모드" in issue.message for issue in result.issues)


def test_compare_unmasked_kpi():
    internal = _make_internal_ir()
    external = {
        "distribution_mode": "EXTERNAL_BUYER",
        "sections": [{
            "id": "qoe",
            "blocks": [{"type": "kpi", "value": "1234567"}],
        }],
    }
    result = compare_reports(internal, external, DistributionMode.EXTERNAL_BUYER)
    kpi_issues = [i for i in result.issues if "KPI" in i.message]
    assert len(kpi_issues) > 0


# ── check_sensitive_data_leak ──────────────────────────


def test_leak_check_no_issues():
    ir = {"sections": [{"blocks": [{"type": "text", "content": "정상 텍스트입니다."}]}]}
    issues = check_sensitive_data_leak(ir)
    assert len(issues) == 0


def test_leak_check_email():
    ir = {"content": "담당자: hong@company.com 입니다"}
    issues = check_sensitive_data_leak(ir)
    assert any("이메일" in i.message for i in issues)


def test_leak_check_phone():
    ir = {"content": "연락처: 010-1234-5678"}
    issues = check_sensitive_data_leak(ir)
    assert any("전화번호" in i.message for i in issues)


def test_leak_check_custom_pattern():
    ir = {"data": "사업자번호 123-45-67890 확인"}
    issues = check_sensitive_data_leak(ir, sensitive_patterns=[r"\d{3}-\d{2}-\d{5}"])
    assert len(issues) >= 1
    assert any("패턴" in i.message for i in issues)


def test_leak_check_nested():
    ir = {
        "sections": [{
            "blocks": [{
                "cells": [{"value": "admin@fdd.dev"}]
            }]
        }]
    }
    issues = check_sensitive_data_leak(ir)
    assert any("이메일" in i.message for i in issues)
