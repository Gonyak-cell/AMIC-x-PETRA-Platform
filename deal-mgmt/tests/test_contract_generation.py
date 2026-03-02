"""계약서 자동 생성 서비스 테스트."""

from __future__ import annotations

import pytest

from app.services.contract_generation_service import (
    _currency_format,
    _date_format,
    _normalize_boolean_vars,
    _number_format,
    assemble_clauses,
    build_html,
    evaluate_condition,
    sanitize_html,
    validate_variables,
)

# ── evaluate_condition ──────────────────────────────────────────────────────


class TestEvaluateCondition:
    def test_none_always_true(self) -> None:
        assert evaluate_condition(None, {}) is True

    def test_empty_always_true(self) -> None:
        assert evaluate_condition("", {}) is True

    def test_simple_equality_true(self) -> None:
        assert evaluate_condition("escrow_included == True", {"escrow_included": True}) is True

    def test_simple_equality_false(self) -> None:
        assert evaluate_condition("escrow_included == True", {"escrow_included": False}) is False

    def test_numeric_comparison(self) -> None:
        assert evaluate_condition("price > 1000", {"price": 2000}) is True
        assert evaluate_condition("price > 1000", {"price": 500}) is False

    def test_boolean_and(self) -> None:
        expr = "escrow_included == True and price > 1000"
        assert evaluate_condition(expr, {"escrow_included": True, "price": 2000}) is True
        assert evaluate_condition(expr, {"escrow_included": False, "price": 2000}) is False

    def test_boolean_or(self) -> None:
        expr = "escrow_included == True or warranty_included == True"
        assert evaluate_condition(expr, {"escrow_included": True, "warranty_included": False}) is True
        assert evaluate_condition(expr, {"escrow_included": False, "warranty_included": False}) is False

    def test_not_operator(self) -> None:
        assert evaluate_condition("not escrow_included", {"escrow_included": False}) is True
        assert evaluate_condition("not escrow_included", {"escrow_included": True}) is False

    def test_forbidden_tokens_rejected(self) -> None:
        assert evaluate_condition("import os", {}) is False
        assert evaluate_condition("exec('code')", {}) is False
        assert evaluate_condition("__builtins__", {}) is False

    def test_syntax_error_returns_false(self) -> None:
        assert evaluate_condition("if True:", {}) is False

    def test_in_operator(self) -> None:
        assert evaluate_condition('doc_type in ["SPA", "SHA"]', {"doc_type": "SPA"}) is True
        assert evaluate_condition('doc_type in ["SPA", "SHA"]', {"doc_type": "BTA"}) is False

    def test_not_in_operator(self) -> None:
        assert evaluate_condition('doc_type not in ["MOU"]', {"doc_type": "SPA"}) is True
        assert evaluate_condition('doc_type not in ["MOU"]', {"doc_type": "MOU"}) is False

    def test_missing_variable_returns_none(self) -> None:
        # None == True → False
        assert evaluate_condition("x == True", {}) is False


# ── validate_variables ──────────────────────────────────────────────────────


class _MockVar:
    """TemplateVariable 대역."""

    def __init__(
        self,
        variable_key: str,
        is_required: bool = True,
        visible_condition: str | None = None,
    ) -> None:
        self.variable_key = variable_key
        self.is_required = is_required
        self.visible_condition = visible_condition


class TestValidateVariables:
    def test_all_required_present(self) -> None:
        vars_def = [_MockVar("seller"), _MockVar("buyer")]
        assert validate_variables(vars_def, {"seller": "A", "buyer": "B"}) == []  # type: ignore[arg-type]

    def test_missing_required(self) -> None:
        vars_def = [_MockVar("seller"), _MockVar("buyer")]
        missing = validate_variables(vars_def, {"seller": "A"})  # type: ignore[arg-type]
        assert missing == ["buyer"]

    def test_optional_not_flagged(self) -> None:
        vars_def = [_MockVar("seller"), _MockVar("notes", is_required=False)]
        assert validate_variables(vars_def, {"seller": "A"}) == []  # type: ignore[arg-type]

    def test_conditional_visibility_skipped(self) -> None:
        vars_def = [
            _MockVar("escrow_amount", is_required=True, visible_condition="escrow_included == True"),
        ]
        # escrow_included가 False이면 escrow_amount는 필수가 아님
        assert validate_variables(vars_def, {"escrow_included": False}) == []  # type: ignore[arg-type]


# ── assemble_clauses ────────────────────────────────────────────────────────


class _MockClause:
    """ContractClause 대역."""

    def __init__(
        self,
        clause_order: int,
        title: str,
        content: str,
        is_boilerplate: bool = False,
        condition_expression: str | None = None,
    ) -> None:
        self.clause_order = clause_order
        self.title = title
        self.content = content
        self.is_boilerplate = is_boilerplate
        self.condition_expression = condition_expression


class TestAssembleClauses:
    def test_all_included(self) -> None:
        clauses = [
            _MockClause(1, "정의", "<p>정의 조항</p>"),
            _MockClause(2, "양도", "<p>양도 조항</p>"),
        ]
        assembled, skipped = assemble_clauses(clauses, {})  # type: ignore[arg-type]
        assert len(assembled) == 2
        assert skipped == 0

    def test_conditional_filtering(self) -> None:
        clauses = [
            _MockClause(1, "정의", "<p>정의</p>"),
            _MockClause(2, "에스크로", "<p>에스크로</p>", condition_expression="escrow == True"),
        ]
        assembled, skipped = assemble_clauses(clauses, {"escrow": False})  # type: ignore[arg-type]
        assert len(assembled) == 1
        assert skipped == 1

    def test_jinja_rendering(self) -> None:
        clauses = [
            _MockClause(1, "양도", "<p>매도인 {{ seller }}이 매수인 {{ buyer }}에게 양도</p>"),
        ]
        assembled, _ = assemble_clauses(clauses, {"seller": "홍길동", "buyer": "김철수"})  # type: ignore[arg-type]
        assert "홍길동" in assembled[0]["content"]
        assert "김철수" in assembled[0]["content"]

    def test_jinja_filters(self) -> None:
        clauses = [
            _MockClause(1, "금액", "<p>합계 {{ price | number_format }}원</p>"),
        ]
        assembled, _ = assemble_clauses(clauses, {"price": 1000000})  # type: ignore[arg-type]
        assert "1,000,000" in assembled[0]["content"]

    def test_ordering(self) -> None:
        clauses = [
            _MockClause(3, "C", "c"),
            _MockClause(1, "A", "a"),
            _MockClause(2, "B", "b"),
        ]
        assembled, _ = assemble_clauses(clauses, {})  # type: ignore[arg-type]
        assert [c["title"] for c in assembled] == ["A", "B", "C"]

    def test_xss_variable_escaped(self) -> None:
        """사용자 입력 변수에 <script> 태그가 있으면 이스케이핑되어야 한다."""
        clauses = [
            _MockClause(1, "당사자", "<p>매도인: {{ seller }}</p>"),
        ]
        xss_payload = '<script>alert("xss")</script>'
        assembled, _ = assemble_clauses(clauses, {"seller": xss_payload})  # type: ignore[arg-type]
        content = assembled[0]["content"]
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_jinja_syntax_error_fallback(self) -> None:
        """Jinja 구문 오류가 있는 조항은 원본 content를 그대로 반환한다."""
        clauses = [
            _MockClause(1, "오류조항", "<p>{{ unclosed_var </p>"),
        ]
        assembled, _ = assemble_clauses(clauses, {})  # type: ignore[arg-type]
        assert len(assembled) == 1
        assert assembled[0]["content"] == "<p>{{ unclosed_var </p>"


# ── build_html ──────────────────────────────────────────────────────────────


class TestBuildHtml:
    def test_basic_structure(self) -> None:
        assembled = [
            {"order": "1", "title": "정의", "content": "<p>정의 내용</p>", "is_boilerplate": "False"},
        ]
        html = build_html(assembled, "SPA", "주식매매계약서")
        assert "contract-document" in html
        assert "SPA" in html
        assert "주식매매계약서" in html
        assert "제1조" in html
        assert "정의" in html

    def test_multiple_clauses(self) -> None:
        assembled = [
            {"order": "1", "title": "A", "content": "a", "is_boilerplate": "False"},
            {"order": "2", "title": "B", "content": "b", "is_boilerplate": "False"},
            {"order": "3", "title": "C", "content": "c", "is_boilerplate": "False"},
        ]
        html = build_html(assembled, "SPA", "테스트")
        assert "제1조" in html
        assert "제2조" in html
        assert "제3조" in html

    def test_empty_clauses(self) -> None:
        """빈 조항 리스트로도 유효한 HTML을 반환해야 한다."""
        html = build_html([], "SPA", "빈 계약서")
        assert "contract-document" in html
        assert "빈 계약서" in html
        assert "제1조" not in html


# ── Jinja 필터 경계값 ──────────────────────────────────────────────────────


class TestJinjaFilters:
    def test_currency_format_zero(self) -> None:
        assert _currency_format(0) == "금 0원"

    def test_currency_format_negative(self) -> None:
        assert _currency_format(-1000) == "금 -1,000원"

    def test_number_format_non_numeric(self) -> None:
        assert _number_format("abc") == "abc"

    def test_number_format_none(self) -> None:
        assert _number_format(None) == "None"


# ── _normalize_boolean_vars ──────────────────────────────────────────────────


class TestNormalizeBooleanVars:
    def test_string_true_to_bool(self) -> None:
        result = _normalize_boolean_vars({"flag": "true"})
        assert result["flag"] is True

    def test_string_false_to_bool(self) -> None:
        result = _normalize_boolean_vars({"flag": "false"})
        assert result["flag"] is False

    def test_case_insensitive(self) -> None:
        result = _normalize_boolean_vars({"a": "True", "b": "FALSE"})
        assert result["a"] is True
        assert result["b"] is False

    def test_non_boolean_strings_unchanged(self) -> None:
        result = _normalize_boolean_vars({"name": "홍길동", "count": 42})
        assert result["name"] == "홍길동"
        assert result["count"] == 42

    def test_already_bool_unchanged(self) -> None:
        result = _normalize_boolean_vars({"flag": True})
        assert result["flag"] is True

    def test_empty_dict(self) -> None:
        assert _normalize_boolean_vars({}) == {}


# ── sanitize_html ────────────────────────────────────────────────────────────


class TestSanitizeHtml:
    def test_removes_script_tags(self) -> None:
        assert "<script>" not in sanitize_html('<p>safe</p><script>alert("xss")</script>')

    def test_removes_iframe(self) -> None:
        assert "<iframe" not in sanitize_html('<iframe src="evil.com"></iframe><p>ok</p>')

    def test_removes_event_handlers(self) -> None:
        result = sanitize_html('<p onclick="alert(1)">text</p>')
        assert "onclick" not in result

    def test_removes_javascript_url(self) -> None:
        result = sanitize_html('<a href="javascript:alert(1)">click</a>')
        assert "javascript:" not in result

    def test_removes_data_url(self) -> None:
        result = sanitize_html('<img src="data:text/html,<script>alert(1)</script>">')
        assert "data:" not in result

    def test_preserves_safe_html(self) -> None:
        safe = "<p>안전한 <strong>내용</strong></p>"
        assert sanitize_html(safe) == safe

    def test_removes_svg(self) -> None:
        assert "<svg" not in sanitize_html('<svg onload="alert(1)"><circle/></svg>')


# ── _date_format ─────────────────────────────────────────────────────────────


class TestDateFormat:
    def test_valid_date(self) -> None:
        assert _date_format("2024-01-15") == "2024년 01월 15일"

    def test_none_value(self) -> None:
        assert _date_format(None) == "None"  # type: ignore[arg-type]

    def test_empty_string(self) -> None:
        assert _date_format("") == ""

    def test_invalid_format(self) -> None:
        assert _date_format("not-a-date") == "not-a-date"

    def test_long_string_truncated_to_date(self) -> None:
        assert _date_format("2024-01-15T12:00:00") == "2024년 01월 15일"

    def test_non_string_input(self) -> None:
        assert _date_format(12345) == "12345"  # type: ignore[arg-type]


# ── validate_variables_size (Pydantic) ───────────────────────────────────────


class TestValidateVariablesSize:
    def test_accepts_valid_variables(self) -> None:
        from app.schemas.contract_generation import ContractGenerateRequest

        req = ContractGenerateRequest(
            template_id="00000000-0000-0000-0000-000000000001",
            title="테스트",
            variables={"key1": "val1", "key2": "val2"},
        )
        assert len(req.variables) == 2

    def test_rejects_over_50_keys(self) -> None:
        from app.schemas.contract_generation import ContractGenerateRequest

        with pytest.raises(ValueError, match="최대 50개"):
            ContractGenerateRequest(
                template_id="00000000-0000-0000-0000-000000000001",
                title="테스트",
                variables={f"key_{i}": f"val_{i}" for i in range(51)},
            )

    def test_rejects_long_key(self) -> None:
        from app.schemas.contract_generation import ContractGenerateRequest

        with pytest.raises(ValueError, match="키 길이"):
            ContractGenerateRequest(
                template_id="00000000-0000-0000-0000-000000000001",
                title="테스트",
                variables={"x" * 101: "val"},
            )

    def test_rejects_long_value(self) -> None:
        from app.schemas.contract_generation import ContractGenerateRequest

        with pytest.raises(ValueError, match="값 길이"):
            ContractGenerateRequest(
                template_id="00000000-0000-0000-0000-000000000001",
                title="테스트",
                variables={"key": "x" * 10_001},
            )


# ── save_html OCC ─────────────────────────────────────────────────────────


class TestSaveHtmlOCC:
    """save_html의 OCC 원자적 갱신 로직을 검증한다."""

    @pytest.mark.asyncio
    async def test_save_success(self) -> None:
        """rowcount=1이면 정상 저장된다."""
        import uuid as _uuid
        from unittest.mock import AsyncMock, MagicMock

        from app.services.contract_generation_service import save_html

        mock_db = AsyncMock()
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 1
        mock_doc = MagicMock()
        mock_doc.updated_at = "2024-01-01T00:00:00"
        mock_select_result = MagicMock()
        mock_select_result.scalar_one.return_value = mock_doc
        mock_db.execute = AsyncMock(side_effect=[mock_update_result, mock_select_result])

        doc = await save_html(mock_db, _uuid.uuid4(), _uuid.uuid4(), "<p>test</p>")
        assert doc == mock_doc

    @pytest.mark.asyncio
    async def test_doc_not_found(self) -> None:
        """rowcount=0 + 문서 미존재 → DocumentNotFoundError."""
        import uuid as _uuid
        from unittest.mock import AsyncMock, MagicMock

        from app.core.exceptions import DocumentNotFoundError
        from app.services.contract_generation_service import save_html

        mock_db = AsyncMock()
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 0
        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[mock_update_result, mock_check_result])

        with pytest.raises(DocumentNotFoundError):
            await save_html(mock_db, _uuid.uuid4(), _uuid.uuid4(), "<p>test</p>")

    @pytest.mark.asyncio
    async def test_occ_conflict(self) -> None:
        """rowcount=0 + 문서 존재 + last_modified_at 불일치 → ValueError (OCC 충돌)."""
        import uuid as _uuid
        from unittest.mock import AsyncMock, MagicMock

        from app.services.contract_generation_service import save_html

        mock_db = AsyncMock()
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 0
        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = _uuid.uuid4()
        mock_db.execute = AsyncMock(side_effect=[mock_update_result, mock_check_result])

        with pytest.raises(ValueError, match="다른 사용자"):
            await save_html(
                mock_db,
                _uuid.uuid4(),
                _uuid.uuid4(),
                "<p>test</p>",
                last_modified_at="2024-01-01T00:00:00",
            )


# ── Rate Limiter ──────────────────────────────────────────────────────────


class TestRateLimiter:
    """인메모리 Rate Limiter 동작을 검증한다."""

    def setup_method(self) -> None:
        from app.routers.contract_generation import _generate_rate

        _generate_rate.clear()

    def test_allows_under_limit(self) -> None:
        """분당 5회 이하는 허용된다."""
        from app.routers.contract_generation import _check_generate_rate

        for _ in range(5):
            _check_generate_rate("test@example.com")

    def test_blocks_over_limit(self) -> None:
        """분당 6회째부터 429를 반환한다."""
        from fastapi import HTTPException

        from app.routers.contract_generation import _check_generate_rate

        for _ in range(5):
            _check_generate_rate("test@example.com")
        with pytest.raises(HTTPException) as exc_info:
            _check_generate_rate("test@example.com")
        assert exc_info.value.status_code == 429

    def test_different_users_independent(self) -> None:
        """사용자별로 독립적인 제한이 적용된다."""
        from app.routers.contract_generation import _check_generate_rate

        for _ in range(5):
            _check_generate_rate("user1@example.com")
        # 다른 사용자는 제한 없음
        _check_generate_rate("user2@example.com")


# ── sanitize_html (entity encoding 우회 방지) ──────────────────────────────


class TestSanitizeHtmlEntityEncoding:
    """SEC-1: HTML entity 인코딩을 통한 이벤트 핸들러 우회를 방지한다."""

    def test_removes_entity_encoded_event_handler(self) -> None:
        """&#111;nclick → onclick 디코딩 후 제거."""
        html = '<div &#111;nclick="alert(1)">test</div>'
        result = sanitize_html(html)
        assert "onclick" not in result.lower()
        assert "alert" not in result

    def test_removes_entity_encoded_dangerous_tag(self) -> None:
        """<scr&#105;pt> → <script> 디코딩 후 제거."""
        html = "<scr&#105;pt>alert(1)</scr&#105;pt>"
        result = sanitize_html(html)
        assert "<script" not in result.lower()
        assert "alert(1)" not in result or "<scr" not in result


# ── _sanitize_param_values ─────────────────────────────────────────────────


class TestSanitizeParamValues:
    """DATA-1: 파라미터 문자열 값에서 HTML 태그를 제거한다."""

    def test_strips_html_tags(self) -> None:
        from app.services.contract_generation_service import _sanitize_param_values

        result = _sanitize_param_values({"name": "<script>alert(1)</script>홍길동"})
        assert result["name"] == "alert(1)홍길동"

    def test_preserves_normal_text(self) -> None:
        from app.services.contract_generation_service import _sanitize_param_values

        result = _sanitize_param_values({"name": "홍길동", "price": 1000})
        assert result == {"name": "홍길동", "price": 1000}

    def test_preserves_ampersand_in_text(self) -> None:
        from app.services.contract_generation_service import _sanitize_param_values

        result = _sanitize_param_values({"company": "A&B 합작법인"})
        assert result["company"] == "A&B 합작법인"


# ── smooth_with_llm ────────────────────────────────────────────────────────


class TestSmoothWithLlm:
    """TEST-1: LLM 스무딩 3단계 검증 + graceful degradation 테스트."""

    @pytest.mark.asyncio
    async def test_llm_unavailable_returns_original(self) -> None:
        """LLM 프로바이더 없으면 원본 HTML을 그대로 반환한다."""
        from unittest.mock import MagicMock, patch

        from app.services.contract_generation_service import smooth_with_llm

        mock_client = MagicMock()
        mock_client.is_available = False

        with patch("app.services.contract_generation_service._get_llm_client", return_value=mock_client):
            result, cost = await smooth_with_llm("<p>원본</p>", "SPA")

        assert result == "<p>원본</p>"
        assert cost is None

    @pytest.mark.asyncio
    async def test_section_count_mismatch_returns_original(self) -> None:
        """LLM이 섹션 수를 변경하면 원본을 반환한다."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import smooth_with_llm

        original = "<section>A</section><section>B</section>"
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.call = AsyncMock(return_value="<section>A</section>")  # 1개로 축소
        mock_client.total_cost_usd = 0.01

        with patch("app.services.contract_generation_service._get_llm_client", return_value=mock_client):
            result, cost = await smooth_with_llm(original, "SPA")

        assert result == original
        assert cost is None

    @pytest.mark.asyncio
    async def test_h2_count_mismatch_returns_original(self) -> None:
        """LLM이 h2(조항 제목) 수를 변경하면 원본을 반환한다."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import smooth_with_llm

        original = "<h2>제1조</h2><p>내용</p><h2>제2조</h2><p>내용</p>"
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.call = AsyncMock(return_value="<h2>제1조</h2><p>내용</p>")  # h2 1개로 축소
        mock_client.total_cost_usd = 0.02

        with patch("app.services.contract_generation_service._get_llm_client", return_value=mock_client):
            result, cost = await smooth_with_llm(original, "SHA")

        assert result == original
        assert cost is None

    @pytest.mark.asyncio
    async def test_length_ratio_exceeded_returns_original(self) -> None:
        """LLM 출력 길이가 ±30%를 초과하면 원본을 반환한다."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import smooth_with_llm

        original = "<p>" + "가" * 100 + "</p>"
        # 원본 대비 10% 미만으로 축소
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.call = AsyncMock(return_value="<p>짧음</p>")
        mock_client.total_cost_usd = 0.005

        with patch("app.services.contract_generation_service._get_llm_client", return_value=mock_client):
            result, cost = await smooth_with_llm(original, "BTA")

        assert result == original
        assert cost is None

    @pytest.mark.asyncio
    async def test_llm_exception_returns_original(self) -> None:
        """LLM 호출 중 예외 발생 시 원본을 반환한다."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import smooth_with_llm

        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.call = AsyncMock(side_effect=RuntimeError("API timeout"))

        with patch("app.services.contract_generation_service._get_llm_client", return_value=mock_client):
            result, cost = await smooth_with_llm("<p>원본</p>", "MOU")

        assert result == "<p>원본</p>"
        assert cost is None

    @pytest.mark.asyncio
    async def test_successful_smoothing(self) -> None:
        """정상 스무딩: 구조 보존된 결과와 비용을 반환한다."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import smooth_with_llm

        original = "<section><h2>제1조</h2><p>내용 A</p></section>"
        smoothed = "<section><h2>제1조 (정의)</h2><p>내용 A</p></section>"
        mock_client = MagicMock()
        mock_client.is_available = True
        mock_client.call = AsyncMock(return_value=smoothed)
        mock_client.total_cost_usd = 0.03

        with patch("app.services.contract_generation_service._get_llm_client", return_value=mock_client):
            result, cost = await smooth_with_llm(original, "SPA")

        assert "제1조 (정의)" in result
        assert cost == 0.03


# ── generate_contract_html (파이프라인 통합) ────────────────────────────────


class TestGenerateContractHtml:
    """TEST-2: 메인 파이프라인 핵심 경로 테스트."""

    @pytest.mark.asyncio
    async def test_missing_required_vars_raises(self) -> None:
        """필수 변수 누락 시 ValueError를 발생시킨다."""
        import uuid
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import generate_contract_html

        mock_db = AsyncMock()
        mock_template = MagicMock()
        mock_template.doc_type = MagicMock()
        mock_template.doc_type.value = "SPA"
        mock_template.clauses = []
        mock_template.variables = [_MockVar("seller", is_required=True)]

        with (
            patch(
                "app.services.contract_generation_service.get_template_with_details",
                return_value=mock_template,
            ),
            pytest.raises(ValueError, match="필수 변수"),
        ):
            await generate_contract_html(
                mock_db,
                uuid.uuid4(),
                uuid.uuid4(),
                "테스트 계약서",
                {},  # seller 누락
                use_llm=False,
            )

    @pytest.mark.asyncio
    async def test_template_not_found_raises(self) -> None:
        """존재하지 않는 템플릿 ID → DocumentNotFoundError."""
        import uuid
        from unittest.mock import AsyncMock, patch

        from app.core.exceptions import DocumentNotFoundError
        from app.services.contract_generation_service import generate_contract_html

        with (
            patch(
                "app.services.contract_generation_service.get_template_with_details",
                side_effect=DocumentNotFoundError("템플릿을 찾을 수 없습니다."),
            ),
            pytest.raises(DocumentNotFoundError),
        ):
            await generate_contract_html(
                AsyncMock(),
                uuid.uuid4(),
                uuid.uuid4(),
                "테스트 계약서",
                {},
                use_llm=False,
            )

    @pytest.mark.asyncio
    async def test_happy_path_returns_with_timing(self) -> None:
        """정상 경로: LegalDocument + 사용/건너뜀 수 + 타이밍 dict 반환."""
        import uuid
        from unittest.mock import AsyncMock, MagicMock, patch

        from app.services.contract_generation_service import generate_contract_html

        mock_db = AsyncMock()
        mock_template = MagicMock()
        mock_template.doc_type = MagicMock()
        mock_template.doc_type.value = "SPA"
        mock_template.variables = []
        clause = _MockClause(1, "제1조 정의", "<p>정의 조항입니다.</p>")
        mock_template.clauses = [clause]

        mock_legal_doc = MagicMock()
        mock_legal_doc.id = uuid.uuid4()

        with (
            patch(
                "app.services.contract_generation_service.get_template_with_details",
                return_value=mock_template,
            ),
            patch(
                "app.services.contract_generation_service.LegalDocument",
                return_value=mock_legal_doc,
            ),
        ):
            result = await generate_contract_html(
                mock_db,
                uuid.uuid4(),
                uuid.uuid4(),
                "SPA 계약서",
                {},
                use_llm=False,
            )

        assert result.legal_document == mock_legal_doc
        assert result.clauses_used == 1
        assert result.clauses_skipped == 0
        assert result.llm_smoothed is False
        assert result.llm_cost is None
        assert "total" in result.timing
        assert "template_lookup" in result.timing
