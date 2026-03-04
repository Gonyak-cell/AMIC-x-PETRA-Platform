"""TemplateExtractor 단위 테스트.

> 마지막 수정: 2026-02-17

참조 보고서에서 YAML 템플릿 초안을 자동 생성하는 TemplateExtractor를
외부 API 없이 테스트한다.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.narrative_generator.templates.extractor import (
    ExtractionResult,
    SectionChunk,
    TemplateExtractor,
)


# ===========================================================================
# TestExtractionResult
# ===========================================================================


class TestExtractionResult:
    """ExtractionResult 데이터클래스 테스트."""

    def test_save_yaml_creates_file(self, tmp_path: Path) -> None:
        result = ExtractionResult(
            section_id="executive_summary",
            yaml_content="section_id: executive_summary\nversion: '1.0'",
            source_file="test.pdf",
        )
        output = tmp_path / "templates" / "executive_summary.yaml"
        saved = result.save_yaml(output)
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == result.yaml_content

    def test_save_yaml_creates_parent_dirs(self, tmp_path: Path) -> None:
        result = ExtractionResult(
            section_id="test",
            yaml_content="test: yaml",
        )
        output = tmp_path / "deep" / "nested" / "dir" / "test.yaml"
        saved = result.save_yaml(output)
        assert saved.exists()

    def test_empty_result(self) -> None:
        result = ExtractionResult(
            section_id="unknown",
            yaml_content="",
            warnings=["텍스트 추출 실패"],
        )
        assert result.yaml_content == ""
        assert len(result.warnings) == 1


# ===========================================================================
# TestTemplateExtractor — 텍스트 추출
# ===========================================================================


class TestTextExtraction:
    """파일 텍스트 추출 테스트 (PDF/PPTX 없이 TXT만 테스트)."""

    def test_extract_txt_file(self, tmp_path: Path) -> None:
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text("테스트 IM 보고서 텍스트입니다.", encoding="utf-8")

        extractor = TemplateExtractor()
        text = extractor._extract_text(txt_file)
        assert "테스트 IM 보고서" in text

    def test_extract_unsupported_format(self, tmp_path: Path) -> None:
        other = tmp_path / "sample.docx"
        other.write_text("content", encoding="utf-8")

        extractor = TemplateExtractor()
        text = extractor._extract_text(other)
        assert text == ""


# ===========================================================================
# TestTemplateExtractor — 섹션 식별
# ===========================================================================


class TestSectionGuessing:
    """_guess_section_id 텍스트 기반 섹션 식별 테스트."""

    def test_guess_executive_summary(self) -> None:
        text = "Executive Summary 본 보고서는 대상회사의 경영진 요약을 제시합니다."
        assert TemplateExtractor._guess_section_id(text) == "executive_summary"

    def test_guess_financial_analysis(self) -> None:
        text = "재무 분석 Financial Analysis 대상회사의 최근 3개년 매출은..."
        assert TemplateExtractor._guess_section_id(text) == "financial_analysis"

    def test_guess_contact(self) -> None:
        text = "Contact 연락처 담당자 정보"
        assert TemplateExtractor._guess_section_id(text) == "contact"

    def test_guess_unknown_text(self) -> None:
        text = "이것은 특정 섹션과 매칭되지 않는 일반 텍스트입니다."
        result = TemplateExtractor._guess_section_id(text)
        # 아무 패턴도 매치하지 않으면 "unknown" 반환
        assert isinstance(result, str)

    def test_guess_market_overview(self) -> None:
        text = "시장 분석 및 Industry Overview 대상 시장의 규모는..."
        assert TemplateExtractor._guess_section_id(text) == "market_overview"

    def test_guess_company_overview(self) -> None:
        text = "회사 개요 Company Overview"
        assert TemplateExtractor._guess_section_id(text) == "company_overview"


# ===========================================================================
# TestTemplateExtractor — 휴리스틱 분석
# ===========================================================================


class TestHeuristicAnalysis:
    """LLM 없이 휴리스틱으로 부동문자/슬롯 분류 테스트."""

    def test_heuristic_identifies_numeric_lines_as_l3(self) -> None:
        text = (
            "대상회사는 국내 IT 서비스 시장의 선도기업입니다.\n"
            "2024년 매출은 1,500억원으로 전년 대비 22.5% 성장하였습니다.\n"
            "본 자료는 정보 제공 목적으로 작성되었습니다."
        )
        extractor = TemplateExtractor()
        result_json = extractor._analyze_heuristic(text, "executive_summary")
        parsed = json.loads(result_json)

        assert parsed["section_id"] == "executive_summary"
        # 수치 2개 이상 포함 줄은 L3 슬롯
        assert len(parsed["slots"]) >= 1
        first_slot = list(parsed["slots"].values())[0]
        assert first_slot["level"] == "L3"

    def test_heuristic_keeps_boilerplate_as_body(self) -> None:
        text = (
            "본 자료는 비밀유지 의무가 있습니다.\n투자 결정은 신중히 하시기 바랍니다."
        )
        extractor = TemplateExtractor()
        result_json = extractor._analyze_heuristic(text, "disclaimer")
        parsed = json.loads(result_json)

        # 수치가 없으므로 슬롯 0개, body에 원문 유지
        assert len(parsed["slots"]) == 0
        assert "비밀유지" in parsed["body"]

    def test_heuristic_returns_valid_json(self) -> None:
        text = "단순 텍스트"
        extractor = TemplateExtractor()
        result_json = extractor._analyze_heuristic(text, "test")
        parsed = json.loads(result_json)
        assert "section_id" in parsed
        assert "slots" in parsed
        assert "body" in parsed
        assert "conditional_blocks" in parsed


# ===========================================================================
# TestTemplateExtractor — 휴리스틱 섹션 분할
# ===========================================================================


class TestHeuristicSectionSplit:
    """_split_sections_heuristic 테스트."""

    def test_split_by_numbered_headers(self) -> None:
        text = (
            "1. Executive Summary\n"
            "대상회사는 선도기업입니다.\n"
            "2. Financial Analysis\n"
            "최근 3개년 매출은 성장하였습니다.\n"
            "3. Contact\n"
            "담당자 연락처입니다."
        )
        extractor = TemplateExtractor()
        chunks = extractor._split_sections_heuristic(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert isinstance(chunk, SectionChunk)
            assert len(chunk.text) > 0
            assert len(chunk.section_id) > 0

    def test_split_single_section(self) -> None:
        """헤더가 없으면 전체를 하나의 섹션으로."""
        text = "단일 섹션 텍스트입니다. 별도 헤더 없음."
        extractor = TemplateExtractor()
        chunks = extractor._split_sections_heuristic(text)
        assert len(chunks) == 1


# ===========================================================================
# TestTemplateExtractor — LLM 응답 파싱
# ===========================================================================


class TestLLMResponseParsing:
    """_parse_llm_response 정적 메서드 테스트."""

    def test_parse_json_code_block(self) -> None:
        raw = (
            "분석 결과:\n"
            "```json\n"
            '{"section_id": "exec", "slots": {}, "body": "테스트"}\n'
            "```"
        )
        result = TemplateExtractor._parse_llm_response(raw)
        assert result is not None
        assert result["section_id"] == "exec"

    def test_parse_raw_json(self) -> None:
        raw = '{"section_id": "test", "slots": {}, "body": "본문"}'
        result = TemplateExtractor._parse_llm_response(raw)
        assert result is not None
        assert result["body"] == "본문"

    def test_parse_invalid_returns_none(self) -> None:
        assert TemplateExtractor._parse_llm_response("not json at all") is None
        assert TemplateExtractor._parse_llm_response("") is None

    def test_parse_json_array(self) -> None:
        raw = '[{"section_id": "a"}, {"section_id": "b"}]'
        result = TemplateExtractor._parse_json_response(raw)
        assert isinstance(result, list)
        assert len(result) == 2


# ===========================================================================
# TestTemplateExtractor — YAML 생성
# ===========================================================================


class TestYAMLGeneration:
    """_build_yaml, _build_fallback_yaml 테스트."""

    def test_build_yaml_from_parsed(self) -> None:
        parsed = {
            "section_id": "executive_summary",
            "slots": {
                "company_name": {
                    "level": "L2",
                    "source": "company_name_kr",
                },
                "company_intro": {
                    "level": "L3",
                    "type": "paragraph",
                    "hint": "기업 소개",
                    "max_tokens": 100,
                    "data_keys": ["company_name_kr"],
                },
            },
            "body": "{{company_name}}은 {{company_intro}}",
            "conditional_blocks": [
                {
                    "condition": "industry == 'tech'",
                    "insert_after": "company_intro",
                    "text": "SaaS 특화 분석",
                },
            ],
        }
        extractor = TemplateExtractor()
        yaml_content = extractor._build_yaml(parsed, "executive_summary", "test.pdf")

        assert "section_id: executive_summary" in yaml_content
        assert "company_name:" in yaml_content
        assert "level: L2" in yaml_content
        assert "company_intro:" in yaml_content
        assert "level: L3" in yaml_content
        assert "hint:" in yaml_content
        assert "body:" in yaml_content
        assert "conditional_blocks:" in yaml_content
        assert "industry == 'tech'" in yaml_content

    def test_build_fallback_yaml(self) -> None:
        yaml_content = TemplateExtractor._build_fallback_yaml(
            "executive_summary",
            "원본 텍스트 내용",
            "LLM 원본 응답",
        )
        assert "수동 편집 필요" in yaml_content
        assert "원본 텍스트 내용" in yaml_content
        assert "LLM 원본 응답" in yaml_content
        assert "section_id: executive_summary" in yaml_content


# ===========================================================================
# TestTemplateExtractor — 통합 (LLM 모킹)
# ===========================================================================


class TestExtractorIntegration:
    """extract_from_file / extract_all_sections 통합 테스트 (LLM 모킹)."""

    @staticmethod
    def _create_mock_llm(response_text: str) -> MagicMock:
        mock_message = MagicMock()
        mock_message.content = response_text
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @pytest.mark.asyncio
    async def test_extract_from_txt_with_mock_llm(self, tmp_path: Path) -> None:
        """TXT 파일에서 모킹된 LLM으로 추출."""
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text(
            "Executive Summary\n"
            "테스트기업(이하 대상회사)은 국내 IT 서비스 시장의 선도기업으로,\n"
            "2024년 매출 1,500억원을 달성하였습니다.",
            encoding="utf-8",
        )

        llm_response = json.dumps(
            {
                "section_id": "executive_summary",
                "slots": {
                    "company_name": {"level": "L2", "source": "company_name_kr"},
                    "revenue_info": {
                        "level": "L3",
                        "type": "sentence",
                        "hint": "매출 하이라이트",
                        "max_tokens": 60,
                        "data_keys": ["financial_statements.revenue"],
                    },
                },
                "body": "{{company_name}}(이하 대상회사)은 국내 IT 서비스 시장의 선도기업으로, {{revenue_info}}",
                "conditional_blocks": [],
            },
            ensure_ascii=False,
        )

        mock_client = self._create_mock_llm(llm_response)
        extractor = TemplateExtractor(llm_client=mock_client)

        result = await extractor.extract_from_file(
            txt_file,
            section_id="executive_summary",
        )

        assert result.section_id == "executive_summary"
        assert len(result.yaml_content) > 0
        assert "company_name" in result.yaml_content
        assert "revenue_info" in result.yaml_content
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_extract_without_llm_uses_heuristic(self, tmp_path: Path) -> None:
        """LLM 클라이언트 없으면 휴리스틱 모드."""
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text(
            "대상회사의 매출은 1,500억원으로 전년 대비 22.5% 성장하였습니다.",
            encoding="utf-8",
        )

        extractor = TemplateExtractor(llm_client=None)
        result = await extractor.extract_from_file(
            txt_file,
            section_id="financial_analysis",
        )

        assert result.section_id == "financial_analysis"
        assert len(result.yaml_content) > 0

    @pytest.mark.asyncio
    async def test_extract_with_section_text_provided(self) -> None:
        """section_text를 직접 제공하면 파일 읽기 없이 처리."""
        extractor = TemplateExtractor(llm_client=None)
        result = await extractor.extract_from_file(
            "dummy.txt",
            section_id="test_section",
            section_text="본 자료는 정보 제공 목적입니다. 매출 500억원, 영업이익 100억원.",
        )

        assert result.section_id == "test_section"
        assert len(result.yaml_content) > 0

    @pytest.mark.asyncio
    async def test_extract_nonexistent_file(self) -> None:
        """존재하지 않는 PDF 파일 → 경고와 빈 YAML."""
        extractor = TemplateExtractor()
        result = await extractor.extract_from_file(
            "/nonexistent/path.pdf",
            section_id="test",
        )

        assert len(result.warnings) >= 1
        assert result.yaml_content == ""

    @pytest.mark.asyncio
    async def test_extract_auto_guesses_section_id(self, tmp_path: Path) -> None:
        """section_id 미지정 시 자동 추정."""
        txt_file = tmp_path / "sample.txt"
        txt_file.write_text(
            "Financial Analysis 재무 분석\n매출 1,000억원, EBITDA 200억원.",
            encoding="utf-8",
        )

        extractor = TemplateExtractor(llm_client=None)
        result = await extractor.extract_from_file(txt_file)

        assert result.section_id == "financial_analysis"

    @pytest.mark.asyncio
    async def test_extract_all_sections_with_heuristic_split(
        self, tmp_path: Path
    ) -> None:
        """전체 보고서 추출 — 휴리스틱 섹션 분할."""
        txt_file = tmp_path / "full_report.txt"
        txt_file.write_text(
            "1. Executive Summary\n"
            "대상회사는 선도기업입니다.\n\n"
            "2. Financial Analysis\n"
            "매출은 1,500억원으로 22.5% 성장하였습니다.\n\n"
            "3. Contact\n"
            "담당자: 홍길동\n",
            encoding="utf-8",
        )

        extractor = TemplateExtractor(llm_client=None)
        results = await extractor.extract_all_sections(txt_file)

        assert len(results) >= 2
        [r.section_id for r in results]
        # 추출된 결과에 YAML 내용이 있어야 함
        for r in results:
            assert len(r.yaml_content) > 0


# ===========================================================================
# TestTemplateExtractor — 유틸리티
# ===========================================================================


class TestExtractorUtils:
    """유틸리티 메서드 테스트."""

    def test_truncate_short_text(self) -> None:
        text = "짧은 텍스트"
        assert TemplateExtractor._truncate(text, 100) == text

    def test_truncate_long_text(self) -> None:
        text = "가" * 200
        result = TemplateExtractor._truncate(text, 50)
        assert len(result) < 200
        assert "이하 생략" in result

    def test_escape_yaml_str(self) -> None:
        assert (
            TemplateExtractor._escape_yaml_str('He said "hello"')
            == 'He said \\"hello\\"'
        )
        assert TemplateExtractor._escape_yaml_str("back\\slash") == "back\\\\slash"
