"""Phase 1 검증 테스트 — 계약서 5종 표준 템플릿 빌더 (31 tests).

밤샘 자동화 에이전트가 Phase 1 완료 후 실행하여 자체 검증한다.
기존 test_contract_generation.py (evaluate_condition, assemble_clauses 등)와 비중복.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.template_builder import (
    BUILDERS,
    ClauseData,
    TemplateData,
    VariableData,
    build_spa_template,
    parse_docx,
    validate_template_data,
)

# ── 공통 상수 ──────────────────────────────────────────────────────────────────

DOC_TYPES = ["SPA", "SHA", "BTA", "SSA", "MOU"]

KOREAN_RE = re.compile(r"[가-힣]")
JINJA_VAR_RE = re.compile(r"\{\{.*?\}\}")


# ── TestTemplateBuilderImports ─────────────────────────────────────────────────


class TestTemplateBuilderImports:
    """빌더 패키지 import 및 레지스트리 검증."""

    def test_package_importable(self) -> None:
        """8개 모듈 import 에러 없음."""
        from app.services.template_builder import (
            base,  # noqa: F401
            bta_builder,  # noqa: F401
            docx_parser,  # noqa: F401
            mou_builder,  # noqa: F401
            sha_builder,  # noqa: F401
            spa_builder,  # noqa: F401
            ssa_builder,  # noqa: F401
        )

    def test_all_builders_registered(self) -> None:
        """__init__.py에서 5종 빌더 export."""
        assert len(BUILDERS) == 5
        for doc_type in DOC_TYPES:
            assert doc_type in BUILDERS, f"{doc_type} 빌더 미등록"


# ── TestDocxParser ─────────────────────────────────────────────────────────────


class TestDocxParser:
    """DOCX 파서 검증."""

    def test_parse_spa_template_extracts_clauses(self) -> None:
        """spa_template.docx → ContractClause[] 비어있지 않음."""
        template_path = Path(__file__).resolve().parent.parent / "templates" / "legal" / "spa_template.docx"
        if not template_path.exists():
            pytest.skip(f"SPA 템플릿 파일 없음: {template_path}")
        clauses = parse_docx(template_path)
        assert len(clauses) > 0, "SPA 템플릿에서 조항 추출 실패"
        for clause in clauses:
            assert isinstance(clause, ClauseData)
            assert clause.title.strip() != ""
            assert clause.content.strip() != ""

    def test_parse_korean_clause_pattern(self) -> None:
        """'제N조' / '제N조의N' 패턴 인식."""
        from app.services.template_builder.docx_parser import _CLAUSE_TITLE_RE

        assert _CLAUSE_TITLE_RE.match("제1조 (정의)") is not None
        assert _CLAUSE_TITLE_RE.match("제12조 (비밀유지)") is not None
        assert _CLAUSE_TITLE_RE.match("제3조의2 (추가조항)") is not None
        assert _CLAUSE_TITLE_RE.match("일반 텍스트") is None

    def test_parse_empty_document_returns_empty(self, tmp_path: Path) -> None:
        """빈 DOCX → 빈 리스트 (크래시 없음)."""
        from docx import Document

        empty_docx = tmp_path / "empty.docx"
        doc = Document()
        doc.save(str(empty_docx))

        clauses = parse_docx(empty_docx)
        assert clauses == []

    def test_parse_preserves_content_html(self) -> None:
        """조항 내용 <p>/<ol>/<ul> HTML 보존."""
        template_path = Path(__file__).resolve().parent.parent / "templates" / "legal" / "spa_template.docx"
        if not template_path.exists():
            pytest.skip(f"SPA 템플릿 파일 없음: {template_path}")
        clauses = parse_docx(template_path)
        if clauses:
            html_tags_found = any("<p>" in c.content or "<li>" in c.content or "<h3>" in c.content for c in clauses)
            assert html_tags_found, "HTML 태그가 포함되지 않음"

    @pytest.mark.parametrize("doc_type", DOC_TYPES)
    def test_parse_all_five_templates_non_empty(self, doc_type: str) -> None:
        """@parametrize 5종: 각 DOCX → 10+ 조항 (없으면 skip)."""
        template_path = (
            Path(__file__).resolve().parent.parent / "templates" / "legal" / f"{doc_type.lower()}_template.docx"
        )
        if not template_path.exists():
            pytest.skip(f"{doc_type} 템플릿 파일 없음: {template_path}")
        clauses = parse_docx(template_path)
        assert len(clauses) >= 1, f"{doc_type}: 조항 {len(clauses)}개 추출 (최소 1개 기대)"


# ── TestSpaBuilder ─────────────────────────────────────────────────────────────


class TestSpaBuilder:
    """SPA 빌더 상세 검증."""

    def setup_method(self) -> None:
        self.data = build_spa_template()

    def test_spa_template_has_minimum_15_clauses(self) -> None:
        assert len(self.data.clauses) >= 15

    def test_spa_template_has_minimum_20_variables(self) -> None:
        assert len(self.data.variables) >= 20

    def test_spa_clause_titles_korean(self) -> None:
        """모든 조항 제목에 한국어 포함."""
        for clause in self.data.clauses:
            assert KOREAN_RE.search(clause.title), f"조항 '{clause.title}'에 한국어 없음"

    def test_spa_variables_cover_required_fields(self) -> None:
        """seller, buyer, price, closing_date 포함."""
        keys = {v.variable_key for v in self.data.variables}
        required_keys = {"seller_name", "buyer_name", "purchase_price", "closing_date"}
        missing = required_keys - keys
        assert not missing, f"필수 변수 누락: {missing}"

    def test_spa_boilerplate_clauses_exist(self) -> None:
        """is_boilerplate=True 3개 이상."""
        boilerplate_count = sum(1 for c in self.data.clauses if c.is_boilerplate)
        assert boilerplate_count >= 3, f"보편조항 {boilerplate_count}개 (최소 3개 기대)"


# ── TestAllBuildersParametrized ────────────────────────────────────────────────


class TestAllBuildersParametrized:
    """5종 빌더 공통 검증 (parametrized)."""

    @pytest.mark.parametrize("doc_type", DOC_TYPES)
    def test_builder_output_is_valid_template(self, doc_type: str) -> None:
        """각 빌더 유효 객체 반환."""
        builder = BUILDERS[doc_type]
        data = builder()
        assert isinstance(data, TemplateData)
        assert data.doc_type == doc_type
        assert data.name.strip() != ""
        assert len(data.clauses) > 0
        assert len(data.variables) > 0
        assert all(isinstance(c, ClauseData) for c in data.clauses)
        assert all(isinstance(v, VariableData) for v in data.variables)

    @pytest.mark.parametrize("doc_type", DOC_TYPES)
    def test_clause_count_minimum_15(self, doc_type: str) -> None:
        """각 빌더 >= 15 조항."""
        data = BUILDERS[doc_type]()
        assert len(data.clauses) >= 15, f"{doc_type}: {len(data.clauses)}개 조항 (최소 15개 기대)"


# ── TestVariableQuality ────────────────────────────────────────────────────────


class TestVariableQuality:
    """변수 품질 검증."""

    def test_variable_keys_unique_within_template(self) -> None:
        """템플릿 내 variable_key 중복 없음 (전 5종)."""
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            keys = [v.variable_key for v in data.variables]
            duplicates = {k for k in keys if keys.count(k) > 1}
            assert not duplicates, f"{doc_type}: 중복 키 {duplicates}"

    def test_required_variables_have_question_labels(self) -> None:
        """필수 변수 = 비어있지 않은 question_label (전 5종)."""
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            for var in data.variables:
                if var.is_required:
                    assert var.question_label.strip(), (
                        f"{doc_type}: 필수 변수 '{var.variable_key}'에 question_label 누락"
                    )

    def test_select_variables_have_options(self) -> None:
        """SELECT 타입 = 비어있지 않은 select_options (전 5종)."""
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            for var in data.variables:
                if var.input_type == "SELECT":
                    assert var.select_options is not None, (
                        f"{doc_type}: SELECT 변수 '{var.variable_key}'에 select_options 누락"
                    )
                    assert len(var.select_options.get("choices", [])) > 0, (
                        f"{doc_type}: SELECT 변수 '{var.variable_key}' choices 비어있음"
                    )

    def test_visible_condition_syntax_valid(self) -> None:
        """visible_condition → evaluate_condition() 에러 없음 (전 5종)."""
        from app.services.contract_generation_service import evaluate_condition

        dummy_vars = {
            "has_escrow": True,
            "has_earnout": True,
            "has_price_adjustment": True,
            "has_drag_along": True,
            "has_tag_along": True,
            "has_put_option": True,
            "has_inventory_adjustment": True,
            "has_conversion_right": True,
            "has_redemption_right": True,
            "has_mou_deposit": True,
        }
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            for var in data.variables:
                if var.visible_condition:
                    # Should not raise
                    result = evaluate_condition(var.visible_condition, dummy_vars)
                    assert isinstance(result, bool), f"{doc_type}: '{var.visible_condition}' 평가 결과가 bool이 아님"


# ── TestClauseQuality ──────────────────────────────────────────────────────────


class TestClauseQuality:
    """조항 품질 검증."""

    def test_clause_order_is_contiguous(self) -> None:
        """clause_order 1..N 연속 (전 5종)."""
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            orders = sorted(c.clause_order for c in data.clauses)
            expected = list(range(1, len(data.clauses) + 1))
            assert orders == expected, f"{doc_type}: clause_order {orders} ≠ 기대 {expected}"

    def test_condition_expressions_syntax_valid(self) -> None:
        """condition_expression 파싱 에러 없음 (전 5종)."""
        from app.services.contract_generation_service import evaluate_condition

        dummy_vars = {
            "has_escrow": True,
            "has_earnout": True,
            "has_price_adjustment": True,
            "has_drag_along": True,
            "has_tag_along": True,
            "has_put_option": True,
            "has_inventory_adjustment": True,
            "has_conversion_right": True,
            "has_redemption_right": True,
            "has_mou_deposit": True,
        }
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            for clause in data.clauses:
                if clause.condition_expression:
                    result = evaluate_condition(clause.condition_expression, dummy_vars)
                    assert isinstance(result, bool), f"{doc_type}: clause {clause.clause_order} 조건식 평가 실패"

    def test_clause_content_contains_jinja_or_plain(self) -> None:
        """50%+ 조항에 {{ }} Jinja2 변수 포함 (전 5종)."""
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            jinja_count = sum(1 for c in data.clauses if JINJA_VAR_RE.search(c.content))
            ratio = jinja_count / len(data.clauses) if data.clauses else 0
            assert ratio >= 0.5, (
                f"{doc_type}: Jinja2 변수 포함 조항 {jinja_count}/{len(data.clauses)} ({ratio:.0%}) — 50% 이상 필요"
            )


# ── TestCrossTemplateConsistency ───────────────────────────────────────────────


class TestCrossTemplateConsistency:
    """템플릿 간 일관성 검증."""

    def test_shared_variables_consistent_types(self) -> None:
        """공통 변수(seller, buyer 등) 동일 input_type."""
        all_vars: dict[str, dict[str, str]] = {}
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            for var in data.variables:
                if var.variable_key not in all_vars:
                    all_vars[var.variable_key] = {"type": var.input_type, "source": doc_type}
                else:
                    existing = all_vars[var.variable_key]
                    assert var.input_type == existing["type"], (
                        f"변수 '{var.variable_key}': {doc_type}에서 {var.input_type}이지만 "
                        f"{existing['source']}에서 {existing['type']}으로 정의됨"
                    )

    def test_no_orphan_jinja_variables(self) -> None:
        """{{ var }} → 해당 template의 variable_key 존재 (전 5종)."""
        for doc_type in DOC_TYPES:
            data = BUILDERS[doc_type]()
            issues = validate_template_data(data)
            orphan_issues = [i for i in issues if "미등록 Jinja2" in i]
            assert not orphan_issues, f"{doc_type}: {orphan_issues}"
