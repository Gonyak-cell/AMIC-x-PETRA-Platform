"""LDD 별첨(Appendix) 시스템 테스트.

Phase 4: appendix_types, appendix_generator 테스트.
"""

import pytest

from app.ralph.generators.ldd.appendix_generator import AppendixGenerator
from app.ralph.generators.ldd.appendix_types import (
    APPENDIX_COLUMNS,
    APPENDIX_SECTION_MAP,
    APPENDIX_TITLES,
    AppendixResult,
    AppendixRow,
    AppendixTable,
    AppendixType,
)

# ── AppendixType 테스트 ──────────────────────────────────────────────────

class TestAppendixType:
    """별첨 타입 enum 테스트."""

    def test_six_types(self):
        assert len(AppendixType) == 6

    def test_values(self):
        expected = {"LITIGATION", "IP", "REAL_ESTATE", "CONTRACTS", "INSURANCE", "PERMITS"}
        assert {t.value for t in AppendixType} == expected

    def test_columns_for_all_types(self):
        for t in AppendixType:
            assert t in APPENDIX_COLUMNS or t.value in APPENDIX_COLUMNS, f"{t}: 컬럼 정의 없음"

    def test_section_map_for_all_types(self):
        for t in AppendixType:
            assert t in APPENDIX_SECTION_MAP or t.value in APPENDIX_SECTION_MAP

    def test_titles_for_all_types(self):
        for t in AppendixType:
            assert t in APPENDIX_TITLES or t.value in APPENDIX_TITLES


# ── AppendixRow 테스트 ───────────────────────────────────────────────────

class TestAppendixRow:
    """별첨 행 테스트."""

    def test_to_list(self):
        row = AppendixRow(values={"연번": "1", "항목": "test", "상태": "OK"})
        result = row.to_list(["연번", "항목", "상태", "비고"])
        assert result == ["1", "test", "OK", "-"]

    def test_empty_row(self):
        row = AppendixRow()
        result = row.to_list(["연번", "항목"])
        assert result == ["-", "-"]


# ── AppendixTable 테스트 ─────────────────────────────────────────────────

class TestAppendixTable:
    """별첨 테이블 테스트."""

    def test_auto_columns(self):
        table = AppendixTable(
            appendix_type=AppendixType.LITIGATION,
            title="별지 1",
        )
        assert len(table.columns) == 10  # LITIGATION 컬럼 수

    def test_is_empty(self):
        table = AppendixTable(appendix_type=AppendixType.IP, title="별지 2")
        assert table.is_empty
        assert table.row_count == 0

    def test_with_rows(self):
        table = AppendixTable(appendix_type=AppendixType.IP, title="별지 2")
        table.rows.append(AppendixRow(values={"연번": "1"}))
        assert not table.is_empty
        assert table.row_count == 1

    def test_to_dict(self):
        table = AppendixTable(appendix_type=AppendixType.CONTRACTS, title="별지 4")
        table.rows.append(AppendixRow(values={"연번": "1", "계약명": "공급계약"}))
        d = table.to_dict()
        assert d["appendix_type"] == "CONTRACTS"
        assert d["title"] == "별지 4"
        assert d["row_count"] == 1
        assert len(d["rows"]) == 1
        assert d["rows"][0][0] == "1"  # 연번


# ── AppendixResult 테스트 ────────────────────────────────────────────────

class TestAppendixResult:
    """별첨 결과 테스트."""

    def test_empty_result(self):
        r = AppendixResult()
        assert r.total_tables == 0
        assert r.non_empty_tables == 0
        assert r.total_rows == 0

    def test_result_with_tables(self):
        t1 = AppendixTable(appendix_type=AppendixType.LITIGATION, title="별지 1")
        t1.rows.append(AppendixRow(values={"연번": "1"}))
        t2 = AppendixTable(appendix_type=AppendixType.IP, title="별지 2")
        r = AppendixResult(tables=[t1, t2])
        assert r.total_tables == 2
        assert r.non_empty_tables == 1
        assert r.total_rows == 1

    def test_to_dict(self):
        r = AppendixResult(
            tables=[
                AppendixTable(appendix_type=AppendixType.PERMITS, title="별지 6"),
            ],
        )
        d = r.to_dict()
        assert "total_tables" in d
        assert "tables" in d
        assert len(d["tables"]) == 1


# ── AppendixGenerator 테스트 ─────────────────────────────────────────────

class TestAppendixGenerator:
    """별첨 생성기 테스트."""

    @pytest.fixture
    def sample_section_results(self) -> dict:
        return {
            "LITIGATION": [
                {
                    "item_id": "LIT-01",
                    "name": "진행중 소송 현황",
                    "status": "ISSUE",
                    "issue_level": "HIGH",
                    "description": "특허 침해 소송 진행중",
                    "case_number": "2025가합12345",
                    "court": "서울중앙지방법원",
                    "parties": "원고: A사 / 피고: 대상회사",
                    "claim_amount": "50억원",
                },
                {
                    "item_id": "LIT-02",
                    "name": "종결 소송",
                    "status": "OK",
                    "description": "노동 소송 종결",
                },
            ],
            "IP": [
                {
                    "item_id": "IP-01",
                    "name": "특허 현황",
                    "status": "OK",
                    "ip_type": "특허",
                    "registration_number": "10-1234567",
                    "ip_name": "데이터 처리 방법",
                    "holder": "대상회사",
                },
            ],
            "CONTRACTS": [
                {
                    "item_id": "CON-01",
                    "name": "주요 공급계약",
                    "status": "ISSUE",
                    "issue_level": "MEDIUM",
                    "contract_name": "원재료 공급계약",
                    "counterparty": "B사",
                    "contract_type": "공급계약",
                    "coc_clause": "COC 시 해지 가능",
                    "description": "COC 조항 존재",
                },
            ],
            "GOVERNANCE": [
                {
                    "item_id": "GOV-01",
                    "name": "이사회 구성",
                    "status": "OK",
                },
            ],
            "PERMITS": [
                {
                    "item_id": "PER-01",
                    "name": "영업허가",
                    "status": "ISSUE",
                    "issue_level": "LOW",
                    "permit_name": "식품제조업 허가",
                    "authority": "식약처",
                    "description": "유효기간 내",
                },
                {
                    "item_id": "PER-02",
                    "name": "NA 항목",
                    "status": "NA",
                },
            ],
        }

    def test_generate_creates_six_tables(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results)
        assert result.total_tables == 6

    def test_litigation_table(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results)
        lit_table = next(t for t in result.tables if t.appendix_type == AppendixType.LITIGATION)
        # ISSUE 1개만 포함 (OK는 제외, include_ok=False)
        assert lit_table.row_count == 1

    def test_include_ok_flag(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results, include_ok=True)
        lit_table = next(t for t in result.tables if t.appendix_type == AppendixType.LITIGATION)
        assert lit_table.row_count == 2  # ISSUE + OK

    def test_na_pending_excluded(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results)
        per_table = next(t for t in result.tables if t.appendix_type == AppendixType.PERMITS)
        # PER-01 (ISSUE) 포함, PER-02 (NA) 제외
        assert per_table.row_count == 1

    def test_contracts_table_content(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results)
        con_table = next(t for t in result.tables if t.appendix_type == AppendixType.CONTRACTS)
        assert con_table.row_count == 1
        row_values = con_table.rows[0].to_list(con_table.columns)
        # 계약명이 포함되어 있는지 확인
        assert "원재료 공급계약" in row_values

    def test_empty_section_results(self):
        gen = AppendixGenerator()
        result = gen.generate({})
        assert result.total_tables == 6
        assert result.non_empty_tables == 0
        assert result.total_rows == 0

    def test_unrelated_section_ignored(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results)
        # GOVERNANCE는 어떤 별첨에도 매핑되지 않음
        ins_table = next(t for t in result.tables if t.appendix_type == AppendixType.INSURANCE)
        assert ins_table.is_empty

    def test_to_dict_roundtrip(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "total_tables" in d
        assert d["total_tables"] == 6
        assert d["non_empty_tables"] >= 2

    def test_row_numbering(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results, include_ok=True)
        lit_table = next(t for t in result.tables if t.appendix_type == AppendixType.LITIGATION)
        if lit_table.row_count >= 2:
            row1 = lit_table.rows[0].values.get("연번")
            row2 = lit_table.rows[1].values.get("연번")
            assert row1 == "1"
            assert row2 == "2"

    def test_ip_table_content(self, sample_section_results):
        gen = AppendixGenerator()
        result = gen.generate(sample_section_results, include_ok=True)
        ip_table = next(t for t in result.tables if t.appendix_type == AppendixType.IP)
        assert ip_table.row_count == 1
        row = ip_table.rows[0]
        assert row.values.get("등록번호") == "10-1234567"

    def test_description_truncation(self):
        gen = AppendixGenerator()
        long_desc = "A" * 200
        result = gen.generate({
            "LITIGATION": [{
                "item_id": "X",
                "name": "test",
                "status": "ISSUE",
                "description": long_desc,
            }],
        })
        lit_table = next(t for t in result.tables if t.appendix_type == AppendixType.LITIGATION)
        assert lit_table.row_count == 1
        desc = lit_table.rows[0].values.get("비고", "")
        assert len(desc) <= 103  # 100 + "..."
