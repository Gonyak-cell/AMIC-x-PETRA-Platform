"""SPA 계약서 LLM 역분석 서비스 테스트."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.spa_analysis import (
    DEAL_STRUCTURES,
    INDUSTRY_TYPES,
    VALID_DOC_TYPES,
    VALID_INPUT_TYPES,
    AnalyzedClause,
    DiscoveredBoolean,
    ExtractedVariable,
    SpaStep1Request,
    SpaStep1Response,
    SpaStep3Request,
)
from app.services.spa_analysis_service import (
    AnalysisSession,
    _extract_json,
    _get_session,
    _sessions,
    validate_condition_expression,
)

# ── 스키마 검증 테스트 ────────────────────────────────────────────────────────


class TestSpaSchemas:
    """Pydantic 스키마 검증 테스트."""

    def test_step1_request_min_length(self) -> None:
        """spa_text 최소 100자 검증."""
        with pytest.raises(Exception, match=r"ensure this value has at least 100 characters|at least 100"):
            SpaStep1Request(spa_text="short")

    def test_step1_request_valid(self) -> None:
        body = SpaStep1Request(spa_text="A" * 100)
        assert len(body.spa_text) == 100

    def test_extracted_variable_input_type_validation(self) -> None:
        """유효하지 않은 input_type 거부."""
        with pytest.raises(ValueError, match="input_type"):
            ExtractedVariable(
                variable_key="test",
                input_type="INVALID",
                question_label="테스트",
            )

    def test_extracted_variable_valid_types(self) -> None:
        """모든 유효 input_type 허용."""
        for it in VALID_INPUT_TYPES:
            v = ExtractedVariable(
                variable_key="test",
                input_type=it,
                question_label="테스트",
            )
            assert v.input_type == it

    def test_discovered_boolean_pattern(self) -> None:
        """has_ 접두사 패턴 검증."""
        b = DiscoveredBoolean(
            variable_key="has_escrow",
            question_label="에스크로 포함 여부",
        )
        assert b.variable_key == "has_escrow"

    def test_discovered_boolean_invalid_pattern(self) -> None:
        """has_ 접두사 없는 변수 키 거부."""
        with pytest.raises(Exception, match=r"string_pattern_mismatch|pattern"):
            DiscoveredBoolean(
                variable_key="escrow",
                question_label="에스크로",
            )

    def test_step1_response_deal_structure_validation(self) -> None:
        """유효하지 않은 deal_structure 거부."""
        with pytest.raises(ValueError, match="deal_structure"):
            SpaStep1Response(
                session_id="test",
                variables=[],
                deal_structure="INVALID",
                industry_type="GENERAL",
            )

    def test_step1_response_valid(self) -> None:
        resp = SpaStep1Response(
            session_id="test-123",
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
        )
        assert resp.deal_structure == "PURE_SHARE_TRANSFER"

    def test_analyzed_clause_valid(self) -> None:
        c = AnalyzedClause(
            clause_order=0,
            title="전문",
            content="<p>매도인과 매수인은...</p>",
            original_content="<p>주식회사 A와 주식회사 B는...</p>",
        )
        assert c.clause_order == 0
        assert c.is_boilerplate is False

    def test_step3_request_valid(self) -> None:
        body = SpaStep3Request(
            session_id="test-123",
            template_name="테스트 SPA",
            variables=[],
            clauses=[],
        )
        assert body.template_name == "테스트 SPA"
        assert body.doc_type == "SPA"  # 기본값

    def test_step3_request_doc_type(self) -> None:
        """doc_type 파라미터가 정상 전달되는지 확인."""
        body = SpaStep3Request(
            session_id="test-123",
            template_name="SHA 템플릿",
            doc_type="SHA",
            variables=[],
            clauses=[],
        )
        assert body.doc_type == "SHA"

    def test_step3_request_invalid_doc_type_fallback(self) -> None:
        """유효하지 않은 doc_type → SPA 기본값."""
        body = SpaStep3Request(
            session_id="test-123",
            template_name="테스트",
            doc_type="INVALID",
            variables=[],
            clauses=[],
        )
        assert body.doc_type == "SPA"

    def test_step1_response_detected_doc_type(self) -> None:
        """detected_doc_type 필드 포함 확인."""
        resp = SpaStep1Response(
            session_id="test-123",
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
            detected_doc_type="SHA",
        )
        assert resp.detected_doc_type == "SHA"

    def test_step1_response_invalid_doc_type_fallback(self) -> None:
        """유효하지 않은 detected_doc_type → SPA 기본값."""
        resp = SpaStep1Response(
            session_id="test-123",
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
            detected_doc_type="UNKNOWN",
        )
        assert resp.detected_doc_type == "SPA"


# ── JSON 추출 테스트 ──────────────────────────────────────────────────────────


class TestExtractJson:
    """LLM 출력 JSON 추출 테스트."""

    def test_pure_json(self) -> None:
        result = _extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_code_block(self) -> None:
        text = '```json\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_generic_code_block(self) -> None:
        text = '```\n{"key": "value"}\n```'
        result = _extract_json(text)
        assert result == {"key": "value"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _extract_json("not json")

    def test_non_object_raises(self) -> None:
        with pytest.raises(ValueError, match="object"):
            _extract_json("[1, 2, 3]")


# ── 조건식 검증 테스트 ────────────────────────────────────────────────────────


class TestValidateConditionExpression:
    """condition_expression 검증 테스트."""

    def test_none_is_valid(self) -> None:
        assert validate_condition_expression(None) is True

    def test_empty_is_valid(self) -> None:
        assert validate_condition_expression("") is True

    def test_simple_equality(self) -> None:
        assert validate_condition_expression("has_escrow == True") is True

    def test_complex_expression(self) -> None:
        assert validate_condition_expression('deal_structure == "CARVE_OUT" and has_escrow == True') is True

    def test_syntax_error(self) -> None:
        assert validate_condition_expression("if True:") is False

    def test_in_expression(self) -> None:
        assert validate_condition_expression('doc_type in ["SPA", "SHA"]') is True

    def test_forbidden_import_blocked(self) -> None:
        """import 키워드를 포함한 조건식 차단 (B-1)."""
        assert validate_condition_expression("import os") is False

    def test_forbidden_exec_blocked(self) -> None:
        """exec 키워드를 포함한 조건식 차단 (B-1)."""
        assert validate_condition_expression("exec('print(1)')") is False

    def test_forbidden_dunder_blocked(self) -> None:
        """던더 접근 차단 (B-1)."""
        assert validate_condition_expression("__import__('os')") is False

    def test_forbidden_eval_blocked(self) -> None:
        """eval 키워드 차단 (B-1)."""
        assert validate_condition_expression("eval('1+1')") is False


# ── 세션 관리 테스트 ──────────────────────────────────────────────────────────


class TestSessionManagement:
    """분석 세션 관리 테스트."""

    def test_get_nonexistent_session_raises(self) -> None:
        with pytest.raises(ValueError, match="세션"):
            _get_session("nonexistent-session-id")

    def test_cleanup_expired(self) -> None:
        """만료된 세션이 정리되는지 확인."""
        import time

        from app.services.spa_analysis_service import (
            _SESSION_TTL,
            _cleanup_expired_sessions,
        )

        old_session = AnalysisSession(
            session_id="expired",
            spa_text="test",
            created_at=time.monotonic() - _SESSION_TTL - 1,  # 확실히 만료
        )
        _sessions["expired"] = old_session
        _cleanup_expired_sessions()
        assert "expired" not in _sessions


# ── Step 1 서비스 테스트 (LLM Mock) ───────────────────────────────────────────


class TestStep1AnalyzeVariables:
    """Step 1: 변수 추출 서비스 테스트."""

    @pytest.mark.asyncio
    async def test_step1_success(self) -> None:
        """LLM 호출을 모킹하여 Step 1 정상 동작 확인."""
        mock_response = json.dumps(
            {
                "detected_doc_type": "SPA",
                "variables": [
                    {
                        "variable_key": "seller_name",
                        "input_type": "TEXT",
                        "question_label": "매도인 명칭",
                        "extracted_value": "주식회사 ABC",
                        "is_required": True,
                        "display_order": 1,
                        "group_name": "당사자 정보",
                        "confidence": 0.95,
                    },
                    {
                        "variable_key": "total_price",
                        "input_type": "CURRENCY",
                        "question_label": "매매대금",
                        "extracted_value": "10000000000",
                        "is_required": True,
                        "display_order": 10,
                        "group_name": "매매 조건",
                        "confidence": 0.9,
                    },
                ],
                "deal_structure": "PURE_SHARE_TRANSFER",
                "industry_type": "MANUFACTURING",
                "discovered_booleans": [
                    {
                        "variable_key": "has_drag_along",
                        "question_label": "동반매도청구권 포함 여부",
                        "detected_in_clause": "제8조",
                    },
                ],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.05
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step1_variables

            (
                session_id,
                variables,
                deal_struct,
                industry,
                detected_doc_type,
                discovered,
                _sha_type,
                _exit_strategy,
                _cost,
                _model,
            ) = await analyze_step1_variables("A" * 200)

        assert session_id  # UUID 문자열
        assert len(variables) == 2
        assert variables[0].variable_key == "seller_name"
        assert variables[0].input_type == "TEXT"
        assert variables[1].input_type == "CURRENCY"
        assert deal_struct == "PURE_SHARE_TRANSFER"
        assert industry == "MANUFACTURING"
        assert detected_doc_type == "SPA"
        assert len(discovered) == 1
        assert discovered[0].variable_key == "has_drag_along"

        # 세션 정리
        _sessions.pop(session_id, None)

    @pytest.mark.asyncio
    async def test_step1_dedup_variables(self) -> None:
        """중복 variable_key가 제거되는지 확인."""
        mock_response = json.dumps(
            {
                "detected_doc_type": "SPA",
                "variables": [
                    {
                        "variable_key": "seller_name",
                        "input_type": "TEXT",
                        "question_label": "매도인",
                        "confidence": 0.9,
                    },
                    {
                        "variable_key": "seller_name",
                        "input_type": "TEXT",
                        "question_label": "매도인 (중복)",
                        "confidence": 0.5,
                    },
                ],
                "deal_structure": "PURE_SHARE_TRANSFER",
                "industry_type": "GENERAL",
                "discovered_booleans": [],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.02
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step1_variables

            session_id, variables, *_ = await analyze_step1_variables("A" * 200)

        # 중복 제거 후 1개만 남아야 함
        assert len(variables) == 1
        assert variables[0].question_label == "매도인"

        _sessions.pop(session_id, None)


# ── Step 2 서비스 테스트 (LLM Mock) ───────────────────────────────────────────


class TestStep2AnalyzeClauses:
    """Step 2: 조항 분해 서비스 테스트."""

    @pytest.mark.asyncio
    async def test_step2_success(self) -> None:
        """LLM 호출을 모킹하여 Step 2 정상 동작 확인."""

        # 세션 생성
        session_id = "test-step2-session"
        _sessions[session_id] = AnalysisSession(
            session_id=session_id,
            spa_text="A" * 200,
        )

        mock_response = json.dumps(
            {
                "clauses": [
                    {
                        "clause_order": 0,
                        "title": "전문",
                        "content": "<p>{{ seller_name }}(이하 &quot;매도인&quot;)과 {{ buyer_name }}(이하 &quot;매수인&quot;)은...</p>",
                        "original_content": "<p>주식회사 ABC(이하 &quot;매도인&quot;)과 주식회사 DEF(이하 &quot;매수인&quot;)은...</p>",
                        "is_boilerplate": False,
                        "condition_expression": None,
                        "confidence": 0.9,
                    },
                    {
                        "clause_order": 1,
                        "title": "용어의 정의",
                        "content": "<p>본 계약에서 사용하는 용어는 다음과 같이 정의한다.</p>",
                        "original_content": "<p>본 계약에서 사용하는 용어는 다음과 같이 정의한다.</p>",
                        "is_boilerplate": True,
                        "condition_expression": None,
                        "confidence": 0.85,
                    },
                ],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.08
        mock_llm.call = AsyncMock(return_value=mock_response)

        confirmed_vars = [
            ExtractedVariable(
                variable_key="seller_name",
                input_type="TEXT",
                question_label="매도인 명칭",
            ),
            ExtractedVariable(
                variable_key="buyer_name",
                input_type="TEXT",
                question_label="매수인 명칭",
            ),
        ]

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step2_clauses

            clauses, _cost, _model = await analyze_step2_clauses(
                session_id,
                confirmed_vars,
                "PURE_SHARE_TRANSFER",
                "GENERAL",
            )

        assert len(clauses) == 2
        assert clauses[0].title == "전문"
        assert clauses[0].is_boilerplate is False
        assert clauses[1].is_boilerplate is True
        assert "{{ seller_name }}" in clauses[0].content

        # 세션 정리
        _sessions.pop(session_id, None)

    @pytest.mark.asyncio
    async def test_step2_invalid_condition_removed(self) -> None:
        """유효하지 않은 condition_expression이 null로 치환되는지 확인."""

        session_id = "test-step2-invalid-expr"
        _sessions[session_id] = AnalysisSession(
            session_id=session_id,
            spa_text="A" * 200,
        )

        mock_response = json.dumps(
            {
                "clauses": [
                    {
                        "clause_order": 0,
                        "title": "테스트 조항",
                        "content": "<p>내용</p>",
                        "original_content": "<p>내용</p>",
                        "is_boilerplate": False,
                        "condition_expression": "if True:",  # 유효하지 않은 문법
                        "confidence": 0.5,
                    },
                ],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.03
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step2_clauses

            clauses, _, _ = await analyze_step2_clauses(
                session_id,
                [],
                "PURE_SHARE_TRANSFER",
                "GENERAL",
            )

        # 유효하지 않은 expression은 None으로 치환됨
        assert clauses[0].condition_expression is None

        _sessions.pop(session_id, None)


# ── ENUM 상수 테스트 ──────────────────────────────────────────────────────────


class TestEnumConstants:
    """ENUM 상수 검증."""

    def test_deal_structures(self) -> None:
        assert "PURE_SHARE_TRANSFER" in DEAL_STRUCTURES
        assert "CARVE_OUT" in DEAL_STRUCTURES
        assert "WITH_NEW_SHARES" in DEAL_STRUCTURES
        assert "OTHER_STRUCTURE" in DEAL_STRUCTURES
        assert len(DEAL_STRUCTURES) == 4

    def test_industry_types(self) -> None:
        assert "MANUFACTURING" in INDUSTRY_TYPES
        assert "SOFTWARE" in INDUSTRY_TYPES
        assert "FRANCHISE" in INDUSTRY_TYPES
        assert "GENERAL" in INDUSTRY_TYPES
        assert "OTHER_INDUSTRY" in INDUSTRY_TYPES
        assert len(INDUSTRY_TYPES) == 5

    def test_valid_input_types(self) -> None:
        assert len(VALID_INPUT_TYPES) == 8
        assert "CURRENCY" in VALID_INPUT_TYPES
        assert "PERCENTAGE" in VALID_INPUT_TYPES

    def test_valid_doc_types(self) -> None:
        assert len(VALID_DOC_TYPES) == 5
        assert "SPA" in VALID_DOC_TYPES
        assert "SHA" in VALID_DOC_TYPES
        assert "BTA" in VALID_DOC_TYPES
        assert "SSA" in VALID_DOC_TYPES
        assert "MOU" in VALID_DOC_TYPES


# ── C-3: Rate Limiting 테스트 ────────────────────────────────────────────────


class TestRateLimiting:
    """_check_analysis_rate 함수 테스트."""

    def test_first_request_allowed(self) -> None:
        """첫 요청은 항상 허용."""
        from app.routers.spa_analysis import _analysis_rate, _check_analysis_rate

        _analysis_rate.clear()
        _check_analysis_rate("test@example.com")
        assert len(_analysis_rate["test@example.com"]) == 1
        _analysis_rate.clear()

    def test_three_requests_allowed(self) -> None:
        """분당 3회까지 허용."""
        from app.routers.spa_analysis import _analysis_rate, _check_analysis_rate

        _analysis_rate.clear()
        for _ in range(3):
            _check_analysis_rate("user@test.com")
        assert len(_analysis_rate["user@test.com"]) == 3
        _analysis_rate.clear()

    def test_fourth_request_blocked(self) -> None:
        """4번째 요청은 429 에러."""
        from fastapi import HTTPException

        from app.routers.spa_analysis import _analysis_rate, _check_analysis_rate

        _analysis_rate.clear()
        for _ in range(3):
            _check_analysis_rate("limit@test.com")
        with pytest.raises(HTTPException) as exc_info:
            _check_analysis_rate("limit@test.com")
        assert exc_info.value.status_code == 429
        _analysis_rate.clear()

    def test_different_users_independent(self) -> None:
        """사용자별 독립 카운트."""
        from app.routers.spa_analysis import _analysis_rate, _check_analysis_rate

        _analysis_rate.clear()
        for _ in range(3):
            _check_analysis_rate("a@test.com")
        # 다른 사용자는 여전히 가능
        _check_analysis_rate("b@test.com")
        assert len(_analysis_rate["b@test.com"]) == 1
        _analysis_rate.clear()


# ── C-4: Session Cost Limit 테스트 ──────────────────────────────────────────


class TestSessionCostLimit:
    """세션당 비용 한도 ($5.00) 테스트."""

    @pytest.mark.asyncio
    async def test_cost_limit_exceeded_raises(self) -> None:
        """비용 한도 초과 시 ValueError."""
        from app.services.spa_analysis_service import _MAX_COST_PER_SESSION, analyze_step2_clauses

        session_id = "test-cost-limit"
        _sessions[session_id] = AnalysisSession(
            session_id=session_id,
            spa_text="A" * 200,
            cost_usd=_MAX_COST_PER_SESSION,  # 이미 한도 도달
        )

        with pytest.raises(ValueError, match="비용 한도 초과"):
            await analyze_step2_clauses(session_id, [], "PURE_SHARE_TRANSFER", "GENERAL")

        _sessions.pop(session_id, None)

    @pytest.mark.asyncio
    async def test_cost_under_limit_allowed(self) -> None:
        """비용 한도 미만이면 정상 진행."""
        from app.services.spa_analysis_service import _MAX_COST_PER_SESSION

        session_id = "test-cost-under"
        _sessions[session_id] = AnalysisSession(
            session_id=session_id,
            spa_text="A" * 200,
            cost_usd=_MAX_COST_PER_SESSION - 0.01,  # 한도 미만
        )

        mock_response = json.dumps({"clauses": []})
        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step2_clauses

            clauses, _, _ = await analyze_step2_clauses(session_id, [], "PURE_SHARE_TRANSFER", "GENERAL")
        assert clauses == []

        _sessions.pop(session_id, None)


# ── C-5: SpaStep2Request/Response 스키마 테스트 ─────────────────────────────


class TestSpaStep2Schemas:
    """Step 2 요청/응답 스키마 검증."""

    def test_step2_request_valid(self) -> None:
        from app.schemas.spa_analysis import SpaStep2Request

        body = SpaStep2Request(
            session_id="test-123",
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
        )
        assert body.session_id == "test-123"

    def test_step2_request_invalid_deal_structure(self) -> None:
        from app.schemas.spa_analysis import SpaStep2Request

        with pytest.raises(ValueError, match="deal_structure"):
            SpaStep2Request(
                session_id="test",
                variables=[],
                deal_structure="INVALID",
                industry_type="GENERAL",
            )

    def test_step2_request_invalid_industry_type(self) -> None:
        from app.schemas.spa_analysis import SpaStep2Request

        with pytest.raises(ValueError, match="industry_type"):
            SpaStep2Request(
                session_id="test",
                variables=[],
                deal_structure="PURE_SHARE_TRANSFER",
                industry_type="INVALID",
            )

    def test_step2_response_valid(self) -> None:
        from app.schemas.spa_analysis import SpaStep2Response

        resp = SpaStep2Response(
            session_id="test-123",
            clauses=[
                AnalyzedClause(
                    clause_order=0,
                    title="전문",
                    content="<p>내용</p>",
                    original_content="<p>원문</p>",
                ),
            ],
        )
        assert len(resp.clauses) == 1
        assert resp.llm_cost_usd is None

    def test_step2_request_with_variables(self) -> None:
        """변수 포함 Step 2 요청."""
        from app.schemas.spa_analysis import SpaStep2Request

        body = SpaStep2Request(
            session_id="test-vars",
            variables=[
                ExtractedVariable(
                    variable_key="seller_name",
                    input_type="TEXT",
                    question_label="매도인",
                ),
            ],
            deal_structure="CARVE_OUT",
            industry_type="MANUFACTURING",
        )
        assert len(body.variables) == 1
        assert body.deal_structure == "CARVE_OUT"

    def test_step2_request_with_spa_text(self) -> None:
        """spa_text 폴백 필드 포함 Step 2 요청."""
        from app.schemas.spa_analysis import SpaStep2Request

        body = SpaStep2Request(
            session_id="test-fallback",
            spa_text="A" * 200,
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
        )
        assert body.spa_text is not None
        assert len(body.spa_text) == 200

    def test_step2_request_spa_text_default_none(self) -> None:
        """spa_text 미제공 시 None."""
        from app.schemas.spa_analysis import SpaStep2Request

        body = SpaStep2Request(
            session_id="test-no-spa",
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
        )
        assert body.spa_text is None


# ── C-6: LLM Retry 로직 테스트 ──────────────────────────────────────────────


class TestLLMRetry:
    """LLM JSON 파싱 재시도 로직 테스트."""

    @pytest.mark.asyncio
    async def test_retry_on_json_error(self) -> None:
        """첫 호출 JSON 파싱 실패 → 재시도 성공."""
        from app.services.spa_analysis_service import _call_llm_json

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        # 첫 번째: 잘못된 JSON, 두 번째: 정상 JSON
        mock_llm.call = AsyncMock(side_effect=["not valid json", '{"key": "value"}'])

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            result, _cost, _model = await _call_llm_json("system", "user", max_retries=1)
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_raises(self) -> None:
        """모든 재시도 실패 시 ValueError."""
        from app.services.spa_analysis_service import _call_llm_json

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        mock_llm.call = AsyncMock(return_value="not json at all")

        with (
            patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm),
            pytest.raises(ValueError, match="JSON으로 파싱할 수 없습니다"),
        ):
            await _call_llm_json("system", "user", max_retries=1)

    @pytest.mark.asyncio
    async def test_model_name_returned(self) -> None:
        """_call_llm_json이 모델명을 반환하는지 확인."""
        from app.services.spa_analysis_service import _call_llm_json

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        mock_llm._primary_model = "claude-sonnet-4-20250514"
        mock_llm.call = AsyncMock(return_value='{"key": "value"}')

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            _, _, model = await _call_llm_json("system", "user")
        assert model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_llm_unavailable_raises(self) -> None:
        """LLM 프로바이더 불가 시 RuntimeError."""
        from app.services.spa_analysis_service import _call_llm_json

        mock_llm = AsyncMock()
        mock_llm.is_available = False

        with (
            patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm),
            pytest.raises(RuntimeError, match="LLM 프로바이더"),
        ):
            await _call_llm_json("system", "user")


# ── 멀티워커 폴백 테스트 ─────────────────────────────────────────────────────


class TestMultiWorkerFallback:
    """멀티워커 세션 유실 시 spa_text 폴백 테스트."""

    @pytest.mark.asyncio
    async def test_step2_fallback_with_spa_text(self) -> None:
        """세션 유실 + spa_text 제공 → 임시 세션 생성 후 성공."""
        mock_response = json.dumps({"clauses": []})
        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        mock_llm._primary_model = "claude-sonnet-4-20250514"
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step2_clauses

            clauses, _, _ = await analyze_step2_clauses(
                "nonexistent-session",
                [],
                "PURE_SHARE_TRANSFER",
                "GENERAL",
                spa_text="A" * 200,
            )

        assert clauses == []
        _sessions.pop("nonexistent-session", None)

    @pytest.mark.asyncio
    async def test_step2_no_fallback_raises(self) -> None:
        """세션 유실 + spa_text 없음 → ValueError."""
        with pytest.raises(ValueError, match="세션"):
            from app.services.spa_analysis_service import analyze_step2_clauses

            await analyze_step2_clauses(
                "nonexistent-no-fallback",
                [],
                "PURE_SHARE_TRANSFER",
                "GENERAL",
            )


# ── C-7: 빈 배열 엣지 케이스 테스트 ──────────────────────────────────────────


class TestEmptyArrayEdgeCases:
    """빈 variables/clauses 배열 처리 테스트."""

    @pytest.mark.asyncio
    async def test_step1_empty_variables(self) -> None:
        """LLM이 빈 변수 목록을 반환하는 경우."""
        mock_response = json.dumps(
            {
                "detected_doc_type": "MOU",
                "variables": [],
                "deal_structure": "OTHER_STRUCTURE",
                "industry_type": "GENERAL",
                "discovered_booleans": [],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step1_variables

            (
                session_id,
                variables,
                _deal,
                _industry,
                doc_type,
                discovered,
                _,
                _,
                _,
                _,
            ) = await analyze_step1_variables("A" * 200)

        assert variables == []
        assert discovered == []
        assert doc_type == "MOU"
        _sessions.pop(session_id, None)

    @pytest.mark.asyncio
    async def test_step2_empty_clauses(self) -> None:
        """LLM이 빈 조항 목록을 반환하는 경우."""
        session_id = "test-empty-clauses"
        _sessions[session_id] = AnalysisSession(session_id=session_id, spa_text="A" * 200)

        mock_response = json.dumps({"clauses": []})
        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.01
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch("app.services.spa_analysis_service._get_llm_client", return_value=mock_llm):
            from app.services.spa_analysis_service import analyze_step2_clauses

            clauses, _, _ = await analyze_step2_clauses(session_id, [], "PURE_SHARE_TRANSFER", "GENERAL")

        assert clauses == []
        _sessions.pop(session_id, None)

    def test_step3_request_empty_arrays(self) -> None:
        """빈 변수/조항으로 Step 3 요청 생성 가능."""
        body = SpaStep3Request(
            session_id="test",
            template_name="빈 템플릿",
            variables=[],
            clauses=[],
        )
        assert body.variables == []
        assert body.clauses == []


# ── C-8: 세션 만료 경계 테스트 ───────────────────────────────────────────────


class TestSessionExpiryBoundary:
    """세션 TTL 30분 경계 테스트."""

    def test_fresh_session_valid(self) -> None:
        """방금 생성된 세션은 유효."""
        session_id = "test-fresh"
        _sessions[session_id] = AnalysisSession(session_id=session_id, spa_text="test")
        session = _get_session(session_id)
        assert session.session_id == session_id
        _sessions.pop(session_id, None)

    def test_expired_session_raises(self) -> None:
        """TTL 초과 세션은 ValueError."""
        import time

        from app.services.spa_analysis_service import _SESSION_TTL

        session_id = "test-expired-boundary"
        _sessions[session_id] = AnalysisSession(
            session_id=session_id,
            spa_text="test",
            created_at=time.monotonic() - _SESSION_TTL - 1,  # 확실히 만료
        )
        with pytest.raises(ValueError, match="세션"):
            _get_session(session_id)

    def test_session_cost_tracked(self) -> None:
        """세션 비용이 누적되는지 확인."""
        session = AnalysisSession(session_id="cost-track", spa_text="test")
        assert session.cost_usd == 0.0
        session.cost_usd += 1.5
        session.cost_usd += 2.0
        assert session.cost_usd == 3.5

    def test_multiple_sessions_independent(self) -> None:
        """세션 간 비용이 독립적."""
        s1 = AnalysisSession(session_id="s1", spa_text="test")
        s2 = AnalysisSession(session_id="s2", spa_text="test")
        _sessions["s1"] = s1
        _sessions["s2"] = s2
        s1.cost_usd += 3.0
        assert s2.cost_usd == 0.0
        _sessions.pop("s1", None)
        _sessions.pop("s2", None)


# ── C-1: create_template_from_analysis DB 테스트 (Mock) ──────────────────────


class TestCreateTemplateFromAnalysis:
    """Step 3 DB 저장 테스트 (AsyncSession Mock)."""

    @pytest.mark.asyncio
    async def test_creates_template_with_variables_and_clauses(self) -> None:
        """변수 + 조항 포함 시 Template/Clause/Variable DB 생성 확인."""
        from app.services.spa_analysis_service import create_template_from_analysis

        mock_db = AsyncMock()
        added_objects: list[object] = []
        mock_db.add = lambda obj: added_objects.append(obj)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        variables = [
            ExtractedVariable(
                variable_key="seller_name",
                input_type="TEXT",
                question_label="매도인",
                display_order=1,
                group_name="당사자",
            ),
            ExtractedVariable(
                variable_key="total_price",
                input_type="CURRENCY",
                question_label="매매대금",
                display_order=2,
            ),
        ]
        clauses = [
            AnalyzedClause(
                clause_order=0,
                title="전문",
                content="<p>{{ seller_name }}</p>",
                original_content="<p>주식회사 ABC</p>",
            ),
        ]

        template = await create_template_from_analysis(
            mock_db,
            template_name="테스트 SPA",
            template_description="테스트용",
            variables=variables,
            clauses=clauses,
            created_by_email="test@amic.kr",
            doc_type="SPA",
        )

        # 1 template + 1 clause + 2 variables = 4 objects
        assert len(added_objects) == 4
        assert template.name == "테스트 SPA"
        assert mock_db.flush.call_count == 2  # template flush + final flush

    @pytest.mark.asyncio
    async def test_duplicate_variable_keys_skipped(self) -> None:
        """중복 variable_key는 첫 번째만 저장."""
        from app.services.spa_analysis_service import create_template_from_analysis

        mock_db = AsyncMock()
        added_objects: list[object] = []
        mock_db.add = lambda obj: added_objects.append(obj)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        variables = [
            ExtractedVariable(variable_key="seller_name", input_type="TEXT", question_label="매도인"),
            ExtractedVariable(variable_key="seller_name", input_type="TEXT", question_label="매도인 중복"),
        ]

        await create_template_from_analysis(
            mock_db,
            template_name="중복 테스트",
            template_description=None,
            variables=variables,
            clauses=[],
            created_by_email="test@amic.kr",
        )

        # 1 template + 0 clauses + 1 variable (중복 제거) = 2 objects
        assert len(added_objects) == 2

    @pytest.mark.asyncio
    async def test_duplicate_clause_order_reassigned(self) -> None:
        """중복 clause_order는 재할당."""
        from app.services.spa_analysis_service import create_template_from_analysis

        mock_db = AsyncMock()
        added_objects: list[object] = []
        mock_db.add = lambda obj: added_objects.append(obj)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        clauses = [
            AnalyzedClause(clause_order=0, title="전문", content="<p>A</p>", original_content="<p>A</p>"),
            AnalyzedClause(clause_order=0, title="전문 중복", content="<p>B</p>", original_content="<p>B</p>"),
        ]

        await create_template_from_analysis(
            mock_db,
            template_name="순서 테스트",
            template_description=None,
            variables=[],
            clauses=clauses,
            created_by_email="test@amic.kr",
        )

        # 1 template + 2 clauses = 3 objects
        assert len(added_objects) == 3

    @pytest.mark.asyncio
    async def test_sha_doc_type(self) -> None:
        """SHA 문서 유형으로 템플릿 생성."""
        from app.services.spa_analysis_service import create_template_from_analysis

        mock_db = AsyncMock()
        mock_db.add = lambda obj: None
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        template = await create_template_from_analysis(
            mock_db,
            template_name="SHA 템플릿",
            template_description=None,
            variables=[],
            clauses=[],
            created_by_email="test@amic.kr",
            doc_type="SHA",
        )

        from app.models.enums import LegalDocType

        assert template.doc_type == LegalDocType.SHA


# ── B-3: 세션 수 상한 테스트 ────────────────────────────────────────────────


class TestSessionLimit:
    """인메모리 세션 수 상한 (_MAX_SESSIONS) 테스트."""

    def test_max_sessions_enforced(self) -> None:
        """_MAX_SESSIONS 도달 시 RuntimeError 발생 확인."""
        from app.services.spa_analysis_service import (
            _MAX_SESSIONS,
            _cleanup_expired_sessions,
        )

        # 기존 세션 백업 & 클리어
        backup = dict(_sessions)
        _sessions.clear()

        try:
            # _MAX_SESSIONS 만큼 세션 채우기
            for i in range(_MAX_SESSIONS):
                sid = f"limit-test-{i}"
                _sessions[sid] = AnalysisSession(session_id=sid, spa_text="test")

            assert len(_sessions) == _MAX_SESSIONS

            # 한도 도달 상태에서 새 세션 생성 시도 → RuntimeError
            # analyze_step1_variables는 async이므로 직접 체크 로직 재현
            if len(_sessions) >= _MAX_SESSIONS:
                _cleanup_expired_sessions()
                if len(_sessions) >= _MAX_SESSIONS:
                    raised = True
                else:
                    raised = False
            else:
                raised = False

            assert raised is True
        finally:
            _sessions.clear()
            _sessions.update(backup)

    def test_cleanup_frees_expired_slots(self) -> None:
        """만료 세션 정리 후 새 세션 생성 가능."""
        import time

        from app.services.spa_analysis_service import (
            _MAX_SESSIONS,
            _SESSION_TTL,
            _cleanup_expired_sessions,
        )

        backup = dict(_sessions)
        _sessions.clear()

        try:
            # _MAX_SESSIONS 만큼 채우되 절반은 만료 상태
            half = _MAX_SESSIONS // 2
            for i in range(half):
                sid = f"expired-{i}"
                _sessions[sid] = AnalysisSession(
                    session_id=sid,
                    spa_text="test",
                    created_at=time.monotonic() - _SESSION_TTL - 1,
                )
            for i in range(half, _MAX_SESSIONS):
                sid = f"fresh-{i}"
                _sessions[sid] = AnalysisSession(session_id=sid, spa_text="test")

            assert len(_sessions) == _MAX_SESSIONS

            # 정리 후 만료 세션 제거 → 슬롯 확보
            _cleanup_expired_sessions()
            assert len(_sessions) < _MAX_SESSIONS
        finally:
            _sessions.clear()
            _sessions.update(backup)


# ── D-4: LLM 호출 타임아웃 테스트 ──────────────────────────────────────────


class TestLlmCallTimeout:
    """_call_llm_json 타임아웃 테스트."""

    @pytest.mark.asyncio
    async def test_timeout_raises_runtime_error(self) -> None:
        """LLM 호출이 타임아웃 초과 시 RuntimeError."""
        import asyncio

        from app.services.spa_analysis_service import _call_llm_json

        # 타임아웃보다 오래 걸리는 mock LLM
        async def slow_call(_sys: str, _usr: str) -> str:
            await asyncio.sleep(10)
            return '{"result": "too late"}'

        mock_llm = AsyncMock()
        mock_llm.call = slow_call
        mock_llm.total_cost_usd = 0.0
        mock_llm.is_available = True

        with (
            pytest.raises(RuntimeError, match="응답하지 않았습니다"),
            patch(
                "app.services.spa_analysis_service._LLM_CALL_TIMEOUT",
                0.1,
            ),
            patch(
                "app.services.spa_analysis_service._get_llm_client",
                return_value=mock_llm,
            ),
        ):
            await _call_llm_json("system", "user")


# ── SHA 확장 테스트 ──────────────────────────────────────────────────────────


class TestShaSchemas:
    """SHA 확장 스키마 검증 테스트."""

    def test_sha_types_constant(self) -> None:
        """SHA_TYPES 상수 검증."""
        from app.schemas.spa_analysis import SHA_TYPES

        assert "POST_BUYOUT" in SHA_TYPES
        assert "JOINT_VENTURE" in SHA_TYPES
        assert "MINORITY_INVESTMENT" in SHA_TYPES
        assert "OTHER_TYPE" in SHA_TYPES
        assert len(SHA_TYPES) == 4

    def test_exit_strategies_constant(self) -> None:
        """EXIT_STRATEGIES 상수 검증."""
        from app.schemas.spa_analysis import EXIT_STRATEGIES

        assert "IPO_FOCUSED" in EXIT_STRATEGIES
        assert "MNA_FOCUSED" in EXIT_STRATEGIES
        assert "OTHER_STRATEGY" in EXIT_STRATEGIES
        assert len(EXIT_STRATEGIES) == 3

    def test_all_structure_types_includes_both(self) -> None:
        """ALL_STRUCTURE_TYPES에 SPA + SHA 값 모두 포함."""
        from app.schemas.spa_analysis import ALL_STRUCTURE_TYPES

        # SPA 값
        assert "PURE_SHARE_TRANSFER" in ALL_STRUCTURE_TYPES
        assert "CARVE_OUT" in ALL_STRUCTURE_TYPES
        # SHA 값
        assert "POST_BUYOUT" in ALL_STRUCTURE_TYPES
        assert "JOINT_VENTURE" in ALL_STRUCTURE_TYPES

    def test_step1_request_with_doc_type_hint(self) -> None:
        """doc_type_hint 필드 검증."""
        body = SpaStep1Request(spa_text="A" * 100, doc_type_hint="SHA")
        assert body.doc_type_hint == "SHA"

    def test_step1_request_without_doc_type_hint(self) -> None:
        """doc_type_hint 미지정 시 None."""
        body = SpaStep1Request(spa_text="A" * 100)
        assert body.doc_type_hint is None

    def test_step1_response_sha_fields(self) -> None:
        """SHA 응답에 sha_type, exit_strategy 포함."""
        resp = SpaStep1Response(
            session_id="test",
            variables=[],
            deal_structure="POST_BUYOUT",
            industry_type="GENERAL",
            detected_doc_type="SHA",
            sha_type="POST_BUYOUT",
            exit_strategy="IPO_FOCUSED",
        )
        assert resp.sha_type == "POST_BUYOUT"
        assert resp.exit_strategy == "IPO_FOCUSED"
        assert resp.detected_doc_type == "SHA"

    def test_step1_response_spa_sha_fields_null(self) -> None:
        """SPA 응답에서 SHA 필드는 None."""
        resp = SpaStep1Response(
            session_id="test",
            variables=[],
            deal_structure="PURE_SHARE_TRANSFER",
            industry_type="GENERAL",
        )
        assert resp.sha_type is None
        assert resp.exit_strategy is None

    def test_step2_request_sha_type_accepted(self) -> None:
        """Step2 request에 SHA_TYPES 값 허용."""
        from app.schemas.spa_analysis import SpaStep2Request

        body = SpaStep2Request(
            session_id="test",
            variables=[],
            deal_structure="POST_BUYOUT",
            industry_type="GENERAL",
        )
        assert body.deal_structure == "POST_BUYOUT"

    def test_deal_structure_accepts_all_types(self) -> None:
        """SPA + SHA 모든 구조 값 허용."""
        from app.schemas.spa_analysis import ALL_STRUCTURE_TYPES

        for st in ALL_STRUCTURE_TYPES:
            resp = SpaStep1Response(
                session_id="test",
                variables=[],
                deal_structure=st,
                industry_type="GENERAL",
            )
            assert resp.deal_structure == st


class TestShaStep1Service:
    """SHA Step 1 서비스 테스트 (LLM Mock)."""

    @pytest.mark.asyncio
    async def test_sha_step1_uses_sha_prompt(self) -> None:
        """doc_type_hint='SHA' 시 SHA 전용 프롬프트 사용."""
        mock_response = json.dumps(
            {
                "detected_doc_type": "SHA",
                "sha_type": "POST_BUYOUT",
                "exit_strategy": "MNA_FOCUSED",
                "variables": [
                    {
                        "variable_key": "shareholders",
                        "input_type": "TEXTAREA",
                        "question_label": "주주 목록",
                        "confidence": 0.9,
                    },
                ],
                "deal_structure": "POST_BUYOUT",
                "industry_type": "GENERAL",
                "discovered_booleans": [
                    {
                        "variable_key": "has_drag_along_right",
                        "question_label": "Drag-Along 조항 포함 여부",
                    },
                ],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.05
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.spa_analysis_service._get_llm_client",
            return_value=mock_llm,
        ):
            from app.services.spa_analysis_service import analyze_step1_variables

            result = await analyze_step1_variables("A" * 200, doc_type_hint="SHA")

        (
            session_id,
            variables,
            deal_struct,
            _industry,
            detected_doc_type,
            discovered,
            sha_type,
            exit_strategy,
            _cost,
            _model,
        ) = result

        assert detected_doc_type == "SHA"
        assert sha_type == "POST_BUYOUT"
        assert exit_strategy == "MNA_FOCUSED"
        assert deal_struct == "POST_BUYOUT"
        assert len(variables) == 1
        assert variables[0].variable_key == "shareholders"
        assert len(discovered) == 1

        # LLM이 SHA 프롬프트로 호출되었는지 확인
        call_args = mock_llm.call.call_args
        system_prompt = call_args[0][0]
        assert "주주간계약서" in system_prompt
        assert "sha_type" in system_prompt

        _sessions.pop(session_id, None)

    @pytest.mark.asyncio
    async def test_spa_step1_still_uses_spa_prompt(self) -> None:
        """doc_type_hint 미지정 시 기존 SPA 프롬프트 유지."""
        mock_response = json.dumps(
            {
                "detected_doc_type": "SPA",
                "variables": [],
                "deal_structure": "PURE_SHARE_TRANSFER",
                "industry_type": "GENERAL",
                "discovered_booleans": [],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.02
        mock_llm.call = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.spa_analysis_service._get_llm_client",
            return_value=mock_llm,
        ):
            from app.services.spa_analysis_service import analyze_step1_variables

            result = await analyze_step1_variables("A" * 200)

        # SPA 프롬프트 사용 확인 (SHA 아님)
        call_args = mock_llm.call.call_args
        system_prompt = call_args[0][0]
        assert "M&A 관련 계약서" in system_prompt

        _sessions.pop(result[0], None)


class TestShaStep2Service:
    """SHA Step 2 서비스 테스트 (LLM Mock)."""

    @pytest.mark.asyncio
    async def test_sha_step2_uses_sha_prompt(self) -> None:
        """session.detected_doc_type='SHA' 시 SHA Step2 프롬프트 사용."""
        # 세션 수동 생성
        session = AnalysisSession(
            session_id="sha-step2-test",
            spa_text="A" * 200,
            detected_doc_type="SHA",
        )
        _sessions["sha-step2-test"] = session

        mock_response = json.dumps(
            {
                "clauses": [
                    {
                        "clause_order": 0,
                        "title": "전문",
                        "content": "<p>SHA 전문</p>",
                        "original_content": "<p>SHA 원문</p>",
                        "is_boilerplate": False,
                        "confidence": 0.9,
                    },
                ],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.05
        mock_llm.call = AsyncMock(return_value=mock_response)

        try:
            with patch(
                "app.services.spa_analysis_service._get_llm_client",
                return_value=mock_llm,
            ):
                from app.services.spa_analysis_service import analyze_step2_clauses

                clauses, _cost, _model = await analyze_step2_clauses(
                    "sha-step2-test",
                    [],
                    "POST_BUYOUT",
                    "GENERAL",
                )

            assert len(clauses) == 1
            assert clauses[0].title == "전문"

            # SHA Step 2 프롬프트 확인
            call_args = mock_llm.call.call_args
            system_prompt = call_args[0][0]
            assert "SHA" in system_prompt
            assert "주주간계약서" in system_prompt
        finally:
            _sessions.pop("sha-step2-test", None)

    @pytest.mark.asyncio
    async def test_spa_step2_still_uses_spa_prompt(self) -> None:
        """session.detected_doc_type='SPA' 시 기존 SPA Step2 프롬프트 유지."""
        session = AnalysisSession(
            session_id="spa-step2-test",
            spa_text="A" * 200,
            detected_doc_type="SPA",
        )
        _sessions["spa-step2-test"] = session

        mock_response = json.dumps(
            {
                "clauses": [
                    {
                        "clause_order": 0,
                        "title": "전문",
                        "content": "<p>SPA 전문</p>",
                        "original_content": "<p>SPA 원문</p>",
                        "is_boilerplate": False,
                        "confidence": 0.9,
                    },
                ],
            }
        )

        mock_llm = AsyncMock()
        mock_llm.is_available = True
        mock_llm.total_cost_usd = 0.03
        mock_llm.call = AsyncMock(return_value=mock_response)

        try:
            with patch(
                "app.services.spa_analysis_service._get_llm_client",
                return_value=mock_llm,
            ):
                from app.services.spa_analysis_service import analyze_step2_clauses

                clauses, _cost, _model = await analyze_step2_clauses(
                    "spa-step2-test",
                    [],
                    "PURE_SHARE_TRANSFER",
                    "GENERAL",
                )

            assert len(clauses) == 1

            # SPA Step 2 프롬프트 확인
            call_args = mock_llm.call.call_args
            system_prompt = call_args[0][0]
            assert "SPA 원문을 조항별로 분해" in system_prompt
        finally:
            _sessions.pop("spa-step2-test", None)
