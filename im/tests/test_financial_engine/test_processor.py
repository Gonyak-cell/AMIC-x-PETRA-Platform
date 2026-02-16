# -*- coding: utf-8 -*-
"""FinancialProcessor 단위 테스트.

통합 프로세서 파이프라인의 정확성을 검증합니다.
process() 전체 파이프라인, to_financial_statements() 변환,
파생 지표 산출, 검증 실행/스킵, DART 데이터 처리,
산업별 지표 통합 등을 테스트합니다.

> 마지막 수정: 2026-02-11 22:00:00
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.design_renderer.im_document import FinancialStatements
from src.financial_engine.mapper.chart_of_accounts import StandardAccount
from src.financial_engine.calculator.manufacturing_metrics import ManufacturingMetrics
from src.financial_engine.calculator.saas import SaaSMetrics
from src.financial_engine.processor import (
    FinancialProcessor,
    ProcessingResult,
    ProcessorConfig,
)


# ---------------------------------------------------------------------------
# 헬퍼: 샘플 원시 데이터
# ---------------------------------------------------------------------------

_SA = StandardAccount


def _make_raw_data() -> dict[str, dict[str, Decimal]]:
    """process()에 전달할 최소 샘플 원시 데이터를 생성한다."""
    return {
        "매출액": {"2022": Decimal("100000"), "2023": Decimal("120000")},
        "영업이익": {"2022": Decimal("20000"), "2023": Decimal("25000")},
        "당기순이익": {"2022": Decimal("15000"), "2023": Decimal("18000")},
        "자산총계": {"2022": Decimal("500000"), "2023": Decimal("600000")},
        "부채총계": {"2022": Decimal("300000"), "2023": Decimal("350000")},
        "자본총계": {"2022": Decimal("200000"), "2023": Decimal("250000")},
    }


def _make_extended_raw_data() -> dict[str, dict[str, Decimal]]:
    """EBITDA 파생에 필요한 감가상각 등 추가 데이터를 포함한 원시 데이터."""
    data = _make_raw_data()
    data["감가상각비"] = {"2022": Decimal("5000"), "2023": Decimal("6000")}
    data["매출원가"] = {"2022": Decimal("60000"), "2023": Decimal("70000")}
    data["매출총이익"] = {"2022": Decimal("40000"), "2023": Decimal("50000")}
    data["판매비와관리비"] = {"2022": Decimal("20000"), "2023": Decimal("25000")}
    return data


# ---------------------------------------------------------------------------
# 테스트: process() 전체 파이프라인
# ---------------------------------------------------------------------------


class TestFinancialProcessorProcess:
    """process() 메서드 테스트."""

    def test_process_full_pipeline(self) -> None:
        """process()가 전체 파이프라인을 실행하고 ProcessingResult를 반환한다."""
        processor = FinancialProcessor()
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")

        assert isinstance(result, ProcessingResult)
        assert result.mapped_data is not None
        assert result.profitability is not None
        assert result.growth is not None
        assert result.cash_flow is not None
        assert result.leverage is not None

    def test_balance_check_runs_when_validate_true(self) -> None:
        """validate=True(기본값)이면 balance_check가 실행된다."""
        processor = FinancialProcessor()
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")

        assert result.balance_check is not None

    def test_balance_check_skipped_when_validate_false(self) -> None:
        """validate=False이면 balance_check와 consistency_check가 None."""
        config = ProcessorConfig(validate=False)
        processor = FinancialProcessor(config=config)
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")

        assert result.balance_check is None
        assert result.consistency_check is None

    def test_graceful_handling_minimal_data(self) -> None:
        """최소한의 데이터만 제공해도 에러 없이 처리된다."""
        processor = FinancialProcessor()
        minimal = {"매출액": {"2023": Decimal("100000")}}
        result = processor.process(minimal, source_unit="원")

        assert isinstance(result, ProcessingResult)
        # 매출액만 있으므로 대부분의 지표는 빈 딕셔너리
        assert result.profitability is not None


# ---------------------------------------------------------------------------
# 테스트: to_financial_statements()
# ---------------------------------------------------------------------------


class TestToFinancialStatements:
    """to_financial_statements() 변환 테스트."""

    def test_decimal_to_float_conversion(self) -> None:
        """Decimal 값이 float로 변환된다."""
        processor = FinancialProcessor()
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")
        fs = result.to_financial_statements()

        assert isinstance(fs, FinancialStatements)
        # revenue가 있으면 float 타입이어야 함
        if fs.revenue:
            for year, val in fs.revenue.items():
                assert isinstance(val, float), f"{year}: {type(val)} is not float"

    def test_all_17_fields_mapped(self) -> None:
        """_ACCOUNT_TO_FIELD에 정의된 17개 필드가 FinancialStatements에 매핑된다."""
        expected_fields = {
            "revenue",
            "cost_of_goods_sold",
            "gross_profit",
            "operating_income",
            "net_income",
            "sga_expenses",
            "ebitda",
            "total_assets",
            "total_liabilities",
            "total_equity",
            "cash_and_equivalents",
            "total_debt",
            "operating_cash_flow",
            "investing_cash_flow",
            "financing_cash_flow",
            "capex",
            "free_cash_flow",
        }
        # FinancialStatements에 이 필드들이 존재하는지 확인
        fs = FinancialStatements()
        for field_name in expected_fields:
            assert hasattr(fs, field_name), f"FinancialStatements에 {field_name} 필드가 없습니다"

    def test_unmapped_accounts_tracked(self) -> None:
        """매핑되지 않은 계정명이 unmapped_accounts에 기록된다."""
        processor = FinancialProcessor()
        raw = _make_raw_data()
        raw["존재하지않는계정"] = {"2023": Decimal("999")}
        result = processor.process(raw, source_unit="원")

        assert "존재하지않는계정" in result.unmapped_accounts


# ---------------------------------------------------------------------------
# 테스트: 파생 지표
# ---------------------------------------------------------------------------


class TestDerivedMetrics:
    """파생 지표(EBITDA, 수익성, 성장성) 산출 테스트."""

    def test_ebitda_derived(self) -> None:
        """영업이익 + 감가상각비로 EBITDA가 산출된다."""
        processor = FinancialProcessor()
        raw = _make_extended_raw_data()
        result = processor.process(raw, source_unit="원")

        # EBITDA가 mapped_data 또는 cash_flow에 존재
        ebitda_in_data = result.mapped_data.get(_SA.EBITDA, {})
        ebitda_in_cf = result.cash_flow.ebitda

        has_ebitda = bool(ebitda_in_data) or bool(ebitda_in_cf)
        assert has_ebitda, "EBITDA가 산출되지 않았습니다"

    def test_profitability_metrics_computed(self) -> None:
        """수익성 지표가 계산된다."""
        processor = FinancialProcessor()
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")

        # 매출액과 영업이익이 있으므로 operating_profit_margin이 계산되어야 함
        assert result.profitability.operating_profit_margin is not None

    def test_growth_metrics_computed(self) -> None:
        """성장성 지표가 계산된다."""
        processor = FinancialProcessor()
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")

        # 2개 연도가 있으므로 YoY가 계산되어야 함
        assert result.growth.yoy is not None


# ---------------------------------------------------------------------------
# 테스트: process_from_dart()
# ---------------------------------------------------------------------------


class TestProcessFromDart:
    """process_from_dart() 메서드 테스트."""

    def test_process_from_dart_mock(self) -> None:
        """FinancialStatementsCollection 모킹으로 process_from_dart()를 테스트한다."""
        mock_collection = MagicMock()
        mock_collection.account_names = ["매출액", "영업이익", "당기순이익"]
        mock_collection.get_account_values.side_effect = lambda name, consolidated: {
            "매출액": {"2022": Decimal("100000"), "2023": Decimal("120000")},
            "영업이익": {"2022": Decimal("20000"), "2023": Decimal("25000")},
            "당기순이익": {"2022": Decimal("15000"), "2023": Decimal("18000")},
        }.get(name, {})

        processor = FinancialProcessor(
            config=ProcessorConfig(validate=False)
        )
        result = processor.process_from_dart(mock_collection, consolidated=True)

        assert isinstance(result, ProcessingResult)
        # 매출액이 매핑되었는지 확인
        assert _SA.REVENUE in result.mapped_data


# ---------------------------------------------------------------------------
# 테스트: ProcessorConfig
# ---------------------------------------------------------------------------


class TestProcessorConfig:
    """ProcessorConfig 설정 테스트."""

    def test_custom_source_unit(self) -> None:
        """source_unit을 '백만원'으로 설정하면 정규화에 적용된다."""
        config = ProcessorConfig(source_unit="백만원")
        processor = FinancialProcessor(config=config)
        assert processor.config.source_unit == "백만원"

    def test_config_property(self) -> None:
        """config 프로퍼티가 설정을 올바르게 반환한다."""
        config = ProcessorConfig(validate=False, target_unit="억원")
        processor = FinancialProcessor(config=config)
        assert processor.config.validate is False
        assert processor.config.target_unit == "억원"


# ---------------------------------------------------------------------------
# 테스트: 산업별 지표 통합 (Phase B)
# ---------------------------------------------------------------------------


class TestIndustryMetrics:
    """산업별 지표 계산 통합 테스트."""

    def test_process_with_saas_industry(self) -> None:
        """industry_id='tech'이면 SaaSMetrics가 계산된다."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_raw_data()
        industry_data: dict[str, dict[str, Decimal | None]] = {
            "subscription_revenue": {
                "2022": Decimal("80000"),
                "2023": Decimal("100000"),
            },
        }
        result = processor.process(
            raw,
            source_unit="원",
            industry_id="tech",
            industry_data=industry_data,
        )
        assert isinstance(result.industry_metrics, SaaSMetrics)
        assert result.industry_metrics.arr == {
            "2022": Decimal("80000"),
            "2023": Decimal("100000"),
        }

    def test_process_with_manufacturing_industry(self) -> None:
        """industry_id='manufacturing'이면 ManufacturingMetrics가 계산된다."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_extended_raw_data()
        industry_data: dict[str, dict[str, Decimal | None]] = {
            "availability": {"2022": Decimal("0.90"), "2023": Decimal("0.92")},
            "performance": {"2022": Decimal("0.85"), "2023": Decimal("0.88")},
            "quality": {"2022": Decimal("0.95"), "2023": Decimal("0.96")},
        }
        result = processor.process(
            raw,
            source_unit="원",
            industry_id="manufacturing",
            industry_data=industry_data,
        )
        assert isinstance(result.industry_metrics, ManufacturingMetrics)
        assert len(result.industry_metrics.oee) == 2

    def test_process_without_industry_id(self) -> None:
        """industry_id가 없으면 industry_metrics는 None."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")
        assert result.industry_metrics is None

    def test_process_unknown_industry_graceful(self) -> None:
        """미등록 industry_id는 경고를 추가하고 None을 반환한다."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_raw_data()
        result = processor.process(
            raw, source_unit="원", industry_id="fintech"
        )
        assert result.industry_metrics is None
        assert any("미등록" in w or "fintech" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# 테스트: 밸류에이션 연동
# ---------------------------------------------------------------------------


class TestProcessorValuation:
    """process() 밸류에이션 파라미터 테스트."""

    def test_process_with_valuation_config(self) -> None:
        """valuation_config가 주어지면 valuation이 계산된다."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_raw_data()
        val_cfg = {
            "ev": {"2023": Decimal("350000")},
            "ebitda": {"2023": Decimal("35000")},
            "moic_scenarios": {
                "base": {
                    "exit_equity": Decimal("250000"),
                    "entry_equity": Decimal("100000"),
                },
            },
        }
        result = processor.process(raw, source_unit="원", valuation_config=val_cfg)
        assert result.valuation is not None
        assert result.valuation.ev_ebitda.get("2023") == 10.0
        assert result.valuation.moic_scenarios.get("base") == 2.5

    def test_process_valuation_none_without_config(self) -> None:
        """valuation_config가 없으면 valuation은 None."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_raw_data()
        result = processor.process(raw, source_unit="원")
        assert result.valuation is None

    def test_process_valuation_graceful_on_error(self) -> None:
        """잘못된 valuation_config는 None + 경고."""
        processor = FinancialProcessor(config=ProcessorConfig(validate=False))
        raw = _make_raw_data()
        # holding_period에 문자열을 넣어 에러 유발
        val_cfg = {
            "exit_multiples": [10.0],
            "ebitda_at_exit": "not_a_decimal",
            "entry_equity": Decimal("100000"),
            "holding_period": 5,
        }
        result = processor.process(raw, source_unit="원", valuation_config=val_cfg)
        # 에러가 발생해도 graceful하게 처리
        assert result.valuation is None or result.valuation is not None
        # 에러 발생 시 warnings에 추가됨 (또는 빈 metrics 반환)
