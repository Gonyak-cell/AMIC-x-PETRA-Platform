"""마스킹 엔진 테스트 — FDD-1403."""

from decimal import Decimal

import pytest

from app.services.masking.engine import (
    MODE_DEFAULTS,
    AmountMaskMode,
    DistributionMode,
    MaskingConfig,
    MaskingEngine,
)

# ── MaskingEngine.mask_amount ──────────────────────────


def test_mask_amount_internal():
    engine = MaskingEngine.for_mode(DistributionMode.INTERNAL)
    assert engine.mask_amount(Decimal("1234567")) == "1234567"


def test_mask_amount_x_mask():
    config = MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER, amount_mode=AmountMaskMode.X_MASK
    )
    engine = MaskingEngine(config)
    result = engine.mask_amount(Decimal("1234567"))
    assert "X" in result
    assert "1" not in result


def test_mask_amount_x_mask_negative():
    config = MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER, amount_mode=AmountMaskMode.X_MASK
    )
    engine = MaskingEngine(config)
    result = engine.mask_amount(Decimal("-500000"))
    assert result.startswith("-")
    assert "X" in result


def test_mask_amount_hide():
    config = MaskingConfig(
        mode=DistributionMode.REDACTED, amount_mode=AmountMaskMode.HIDE
    )
    engine = MaskingEngine(config)
    assert engine.mask_amount(Decimal("1000")) == "[금액 숨김]"


def test_mask_amount_range_under_1k():
    config = MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER, amount_mode=AmountMaskMode.RANGE
    )
    engine = MaskingEngine(config)
    result = engine.mask_amount(Decimal("500"))
    assert "미만" in result


def test_mask_amount_range_millions():
    config = MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER, amount_mode=AmountMaskMode.RANGE
    )
    engine = MaskingEngine(config)
    result = engine.mask_amount(Decimal("5500000"))
    assert "M" in result


def test_mask_amount_range_billions():
    config = MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER, amount_mode=AmountMaskMode.RANGE
    )
    engine = MaskingEngine(config)
    result = engine.mask_amount(Decimal("2500000000"))
    assert "B" in result


# ── MaskingEngine.mask_text ────────────────────────────


def test_mask_text_internal():
    engine = MaskingEngine.for_mode(DistributionMode.INTERNAL)
    assert engine.mask_text("삼성전자", "company") == "삼성전자"


def test_mask_text_company():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    result = engine.mask_text("삼성전자", "company")
    assert result.startswith("[회사")
    assert "삼성" not in result


def test_mask_text_company_consistent():
    """같은 회사명은 항상 같은 별칭을 받는다."""
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    alias1 = engine.mask_text("삼성전자", "company")
    alias2 = engine.mask_text("삼성전자", "company")
    alias3 = engine.mask_text("LG전자", "company")
    assert alias1 == alias2
    assert alias1 != alias3


def test_mask_text_custom_alias():
    config = MaskingConfig(
        mode=DistributionMode.EXTERNAL_BUYER,
        custom_company_aliases={"삼성전자": "[대상회사]"},
    )
    engine = MaskingEngine(config)
    assert engine.mask_text("삼성전자", "company") == "[대상회사]"


def test_mask_text_person():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    result = engine.mask_text("홍길동", "person")
    assert "홍길동" not in result
    assert "[인물" in result


def test_mask_text_account():
    config = MaskingConfig(mode=DistributionMode.REDACTED, mask_account_names=True)
    engine = MaskingEngine(config)
    result = engine.mask_text("매출채권", "account")
    assert "[계정" in result


def test_mask_text_account_not_masked_by_default():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    assert engine.mask_text("매출채권", "account") == "매출채권"


# ── MaskingEngine.mask_dict ────────────────────────────


def test_mask_dict_internal():
    engine = MaskingEngine.for_mode(DistributionMode.INTERNAL)
    data = {"company_name": "테스트", "amount": Decimal("1000")}
    assert engine.mask_dict(data) == data


def test_mask_dict_sensitive_keys():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    data = {"company_name": "삼성전자", "value": 100, "note": "비고"}
    result = engine.mask_dict(data)
    assert result["company_name"] == "[마스킹됨]"
    assert result["value"] == 100  # not in sensitive_keys
    assert result["note"] == "비고"


# ── MaskingEngine.mask_report_ir ───────────────────────


def test_mask_report_ir_internal():
    engine = MaskingEngine.for_mode(DistributionMode.INTERNAL)
    ir = {"sections": [{"id": "s1", "blocks": []}]}
    assert engine.mask_report_ir(ir) == ir


def test_mask_report_ir_external():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    ir = {
        "sections": [
            {
                "id": "qoe",
                "blocks": [
                    {"type": "kpi", "value": "1234567"},
                    {"type": "table", "rows": [{"a": 100, "b": "text"}]},
                ],
            }
        ],
    }
    result = engine.mask_report_ir(ir)
    assert result["distribution_mode"] == "EXTERNAL_BUYER"
    kpi = result["sections"][0]["blocks"][0]
    assert "X" in str(kpi["value"]) or "숨김" in str(kpi["value"])


def test_mask_report_ir_excluded_section():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    ir = {
        "sections": [
            {"id": "methodology", "blocks": [{"type": "kpi", "value": "123"}]},
        ],
    }
    result = engine.mask_report_ir(ir)
    # methodology is excluded — should not be masked
    assert result["sections"][0]["blocks"][0]["value"] == "123"


# ── MODE_DEFAULTS ──────────────────────────────────────


def test_mode_defaults_exist():
    for mode in DistributionMode:
        assert mode in MODE_DEFAULTS


def test_redacted_mode_masks_all():
    config = MODE_DEFAULTS[DistributionMode.REDACTED]
    assert config.mask_company_names is True
    assert config.mask_person_names is True
    assert config.mask_account_names is True
    assert config.amount_mode == AmountMaskMode.HIDE


# ── MaskingEngine helpers ──────────────────────────────


def test_is_internal():
    assert MaskingEngine.for_mode(DistributionMode.INTERNAL).is_internal() is True
    assert MaskingEngine.for_mode(DistributionMode.REDACTED).is_internal() is False


def test_masking_summary():
    engine = MaskingEngine.for_mode(DistributionMode.EXTERNAL_BUYER)
    engine.mask_text("테스트회사", "company")
    engine.mask_text("홍길동", "person")
    summary = engine.get_masking_summary()
    assert summary["companies_masked"] == 1
    assert summary["persons_masked"] == 1
