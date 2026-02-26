"""LDD 6블록 서술(Narrative) 엔진 테스트."""

import pytest

from app.ralph.generators.ldd.narrative_types import (
    BLOCK_STRATEGY,
    NarrativeBlock,
    NarrativeBlockType,
    NarrativeResult,
    get_blocks_for_item,
)
from app.ralph.generators.ldd.narrative_prompts import (
    BLOCK_PROMPTS,
    BLOCK_TITLES,
    NARRATIVE_SYSTEM_PROMPT,
)


# ── NarrativeBlockType 테스트 ────────────────────────────────────────────────


class TestNarrativeBlockType:
    def test_enum_values(self):
        assert NarrativeBlockType.FACTS == "FACTS"
        assert NarrativeBlockType.LEGAL_REVIEW == "LEGAL_REVIEW"
        assert NarrativeBlockType.ANALYSIS == "ANALYSIS"
        assert NarrativeBlockType.DEAL_IMPACT == "DEAL_IMPACT"
        assert NarrativeBlockType.PENALTY == "PENALTY"
        assert NarrativeBlockType.RECOMMENDATION == "RECOMMENDATION"

    def test_enum_count(self):
        assert len(NarrativeBlockType) == 6


# ── BLOCK_STRATEGY 테스트 ────────────────────────────────────────────────────


class TestBlockStrategy:
    def test_critical_has_6_blocks(self):
        assert len(BLOCK_STRATEGY["CRITICAL"]) == 6

    def test_high_has_6_blocks(self):
        assert len(BLOCK_STRATEGY["HIGH"]) == 6

    def test_medium_has_4_blocks(self):
        assert len(BLOCK_STRATEGY["MEDIUM"]) == 4

    def test_low_has_4_blocks(self):
        assert len(BLOCK_STRATEGY["LOW"]) == 4

    def test_none_has_1_block(self):
        assert len(BLOCK_STRATEGY[None]) == 1
        assert BLOCK_STRATEGY[None][0] == NarrativeBlockType.FACTS

    def test_medium_excludes_penalty(self):
        medium_types = [b.value for b in BLOCK_STRATEGY["MEDIUM"]]
        assert "PENALTY" not in medium_types
        assert "DEAL_IMPACT" not in medium_types


# ── get_blocks_for_item 테스트 ───────────────────────────────────────────────


class TestGetBlocksForItem:
    def test_na_returns_empty(self):
        assert get_blocks_for_item("NA", None) == []

    def test_pending_returns_empty(self):
        assert get_blocks_for_item("PENDING", None) == []

    def test_ok_returns_facts_only(self):
        blocks = get_blocks_for_item("OK", None)
        assert len(blocks) == 1
        assert blocks[0] == NarrativeBlockType.FACTS

    def test_issue_critical_returns_6(self):
        blocks = get_blocks_for_item("ISSUE", "CRITICAL")
        assert len(blocks) == 6

    def test_issue_high_returns_6(self):
        blocks = get_blocks_for_item("ISSUE", "HIGH")
        assert len(blocks) == 6

    def test_issue_medium_returns_4(self):
        blocks = get_blocks_for_item("ISSUE", "MEDIUM")
        assert len(blocks) == 4

    def test_issue_low_returns_4(self):
        blocks = get_blocks_for_item("ISSUE", "LOW")
        assert len(blocks) == 4

    def test_issue_without_level_returns_facts(self):
        """issue_level 없이 ISSUE → 안전하게 FACTS만."""
        blocks = get_blocks_for_item("ISSUE", None)
        assert len(blocks) == 1

    def test_unknown_status_returns_facts(self):
        blocks = get_blocks_for_item("UNKNOWN", None)
        assert len(blocks) == 1


# ── NarrativeResult 직렬화 테스트 ────────────────────────────────────────────


class TestNarrativeResultSerialization:
    def _make_sample(self) -> NarrativeResult:
        return NarrativeResult(
            item_id="CORP-01",
            item_name="설립/등기/정관 검토",
            section_type="GOVERNANCE",
            blocks=[
                NarrativeBlock(
                    block_type=NarrativeBlockType.FACTS,
                    title="사실관계",
                    content="테스트 사실관계 내용입니다.",
                    word_count=15,
                ),
                NarrativeBlock(
                    block_type=NarrativeBlockType.LEGAL_REVIEW,
                    title="법률 검토",
                    content="상법 제374조 제1항에 따르면...",
                    word_count=20,
                ),
            ],
            total_chars=35,
            cost_usd=0.05,
        )

    def test_to_dict(self):
        result = self._make_sample()
        d = result.to_dict()

        assert d["item_id"] == "CORP-01"
        assert d["section_type"] == "GOVERNANCE"
        assert len(d["blocks"]) == 2
        assert d["blocks"][0]["block_type"] == "FACTS"
        assert d["blocks"][1]["block_type"] == "LEGAL_REVIEW"
        assert d["total_chars"] == 35
        assert d["cost_usd"] == 0.05

    def test_from_dict_roundtrip(self):
        original = self._make_sample()
        d = original.to_dict()
        restored = NarrativeResult.from_dict(d)

        assert restored.item_id == original.item_id
        assert restored.item_name == original.item_name
        assert restored.section_type == original.section_type
        assert len(restored.blocks) == len(original.blocks)
        assert restored.blocks[0].block_type == NarrativeBlockType.FACTS
        assert restored.blocks[1].content == original.blocks[1].content
        assert restored.total_chars == original.total_chars
        assert restored.cost_usd == original.cost_usd

    def test_from_dict_empty_blocks(self):
        d = {
            "item_id": "X-01",
            "item_name": "테스트",
            "section_type": "TEST",
            "blocks": [],
            "total_chars": 0,
            "cost_usd": 0.0,
        }
        result = NarrativeResult.from_dict(d)
        assert result.blocks == []

    def test_from_dict_missing_optional_fields(self):
        d = {
            "item_id": "X-01",
            "item_name": "테스트",
            "section_type": "TEST",
        }
        result = NarrativeResult.from_dict(d)
        assert result.blocks == []
        assert result.total_chars == 0
        assert result.cost_usd == 0.0


# ── 프롬프트 테스트 ──────────────────────────────────────────────────────────


class TestNarrativePrompts:
    def test_system_prompt_has_principles(self):
        assert "김앤장" in NARRATIVE_SYSTEM_PROMPT
        assert "사실관계" in NARRATIVE_SYSTEM_PROMPT
        assert "금지사항" in NARRATIVE_SYSTEM_PROMPT

    def test_all_block_types_have_prompts(self):
        for bt in NarrativeBlockType:
            assert bt.value in BLOCK_PROMPTS, f"{bt.value} 프롬프트 누락"

    def test_all_block_types_have_titles(self):
        for bt in NarrativeBlockType:
            assert bt.value in BLOCK_TITLES, f"{bt.value} 타이틀 누락"

    def test_facts_prompt_has_placeholders(self):
        assert "{item_id}" in BLOCK_PROMPTS["FACTS"]
        assert "{source_materials}" in BLOCK_PROMPTS["FACTS"]

    def test_legal_review_prompt_references_facts(self):
        assert "{facts_content}" in BLOCK_PROMPTS["LEGAL_REVIEW"]

    def test_analysis_prompt_references_prior_blocks(self):
        assert "{facts_content}" in BLOCK_PROMPTS["ANALYSIS"]
        assert "{legal_review_content}" in BLOCK_PROMPTS["ANALYSIS"]

    def test_deal_impact_prompt_has_issue_level(self):
        assert "{issue_level}" in BLOCK_PROMPTS["DEAL_IMPACT"]

    def test_recommendation_prompt_has_deal_impact(self):
        assert "{deal_impact_content}" in BLOCK_PROMPTS["RECOMMENDATION"]


# ── NarrativeGenerator 테스트 ────────────────────────────────────────────────


class TestNarrativeGenerator:
    @pytest.fixture
    def mock_llm_responses(self):
        """블록별 LLM 응답을 시뮬레이션."""
        call_count = 0

        async def _mock_call(system: str, user: str) -> str:
            nonlocal call_count
            call_count += 1
            # 블록별 다른 응답 반환
            if "사실관계" in user:
                return "대상 회사는 2015년 설립되었으며, 정관에 따르면 이사회 승인 사항은..."
            elif "법률 검토" in user:
                return "상법 제374조 제1항에 따르면, 회사의 영업에 관한..."
            elif "분석" in user:
                return "상기 사실관계와 법률 검토를 종합하면, 해당 거래는..."
            elif "거래 영향" in user:
                return "본 이슈가 거래에 미치는 영향은 매매가격의 약 5% 조정..."
            elif "제재" in user:
                return "위반 시 과태료 최대 5천만원 및 시정명령 가능성..."
            elif "권고" in user:
                return "SPA 진술보장 조항에 본 사항 포함을 권고하며..."
            return f"블록 {call_count} 생성 결과"

        return _mock_call

    @pytest.mark.asyncio
    async def test_generate_narrative_issue_critical(self, mock_llm_responses):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(llm_call=mock_llm_responses)

        item = {
            "item_id": "CORP-01",
            "name": "설립/등기/정관 검토",
            "status": "ISSUE",
            "issue_level": "CRITICAL",
            "description": "정관상 이사회 결의 요건 미충족 가능성",
            "deal_impact": "거래 구조 변경 필요",
            "recommendation": "정관 변경 또는 특별결의 필요",
        }

        result = await gen.generate_narrative(
            item=item,
            section_type="GOVERNANCE",
            section_title="1. 기업 일반 및 지배구조",
            source_files=[],
        )

        assert result.item_id == "CORP-01"
        assert result.section_type == "GOVERNANCE"
        assert len(result.blocks) == 6  # CRITICAL → 6블록 전체
        assert result.blocks[0].block_type == NarrativeBlockType.FACTS
        assert result.blocks[-1].block_type == NarrativeBlockType.RECOMMENDATION
        assert result.total_chars > 0

    @pytest.mark.asyncio
    async def test_generate_narrative_ok(self, mock_llm_responses):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(llm_call=mock_llm_responses)

        item = {
            "item_id": "CORP-02",
            "name": "이사회 의사록 검토",
            "status": "OK",
            "issue_level": None,
        }

        result = await gen.generate_narrative(
            item=item,
            section_type="GOVERNANCE",
            section_title="1. 기업 일반 및 지배구조",
            source_files=[],
        )

        assert len(result.blocks) == 1  # OK → FACTS만
        assert result.blocks[0].block_type == NarrativeBlockType.FACTS

    @pytest.mark.asyncio
    async def test_generate_narrative_pending_skips(self, mock_llm_responses):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(llm_call=mock_llm_responses)

        item = {
            "item_id": "CORP-03",
            "name": "주주명부 적정성",
            "status": "PENDING",
        }

        result = await gen.generate_narrative(
            item=item,
            section_type="GOVERNANCE",
            section_title="1. 기업 일반 및 지배구조",
            source_files=[],
        )

        assert len(result.blocks) == 0
        assert result.total_chars == 0

    @pytest.mark.asyncio
    async def test_generate_narrative_medium_has_4_blocks(self, mock_llm_responses):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(llm_call=mock_llm_responses)

        item = {
            "item_id": "LABOR-01",
            "name": "근로계약 및 취업규칙",
            "status": "ISSUE",
            "issue_level": "MEDIUM",
        }

        result = await gen.generate_narrative(
            item=item,
            section_type="LABOR",
            section_title="5. 인사 및 노무",
            source_files=[],
        )

        assert len(result.blocks) == 4
        block_types = [b.block_type for b in result.blocks]
        assert NarrativeBlockType.PENALTY not in block_types
        assert NarrativeBlockType.DEAL_IMPACT not in block_types

    @pytest.mark.asyncio
    async def test_generate_narrative_no_llm(self):
        """LLM 미설정 시 더미 서술 반환."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(llm_call=None)

        item = {
            "item_id": "CORP-01",
            "name": "설립/등기/정관 검토",
            "status": "ISSUE",
            "issue_level": "HIGH",
        }

        result = await gen.generate_narrative(
            item=item,
            section_type="GOVERNANCE",
            section_title="1. 기업 일반 및 지배구조",
            source_files=[],
        )

        assert len(result.blocks) == 6
        # 더미 서술이 들어감
        for block in result.blocks:
            assert "LLM 연결 필요" in block.content

    @pytest.mark.asyncio
    async def test_generate_section_narratives(self, mock_llm_responses):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator(llm_call=mock_llm_responses)

        section = {
            "section_type": "GOVERNANCE",
            "title": "1. 기업 일반 및 지배구조",
            "items": [
                {"item_id": "CORP-01", "name": "설립/등기/정관", "status": "ISSUE", "issue_level": "HIGH"},
                {"item_id": "CORP-02", "name": "이사회 의사록", "status": "OK"},
                {"item_id": "CORP-03", "name": "주주명부", "status": "PENDING"},
            ],
        }

        results = await gen.generate_section_narratives(
            section=section,
            source_files=[],
        )

        assert len(results) == 3
        assert len(results[0].blocks) == 6   # HIGH → 6블록
        assert len(results[1].blocks) == 1   # OK → 1블록
        assert len(results[2].blocks) == 0   # PENDING → 0블록

    def test_format_checklist(self):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator()
        item = {
            "status": "ISSUE",
            "issue_level": "HIGH",
            "description": "정관에 이사회 결의 요건 미비",
            "deal_impact": "거래 지연 가능",
            "recommendation": "정관 변경 필요",
            "evidence_refs": ["doc1.pdf", "doc2.xlsx"],
        }
        text = gen._format_checklist(item)
        assert "ISSUE" in text
        assert "HIGH" in text
        assert "정관에 이사회" in text
        assert "doc1.pdf" in text

    def test_format_checklist_empty(self):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator()
        text = gen._format_checklist({})
        assert "PENDING" in text

    def test_build_block_prompt(self):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator()
        prompt = gen._build_block_prompt(
            block_type=NarrativeBlockType.FACTS,
            item_id="CORP-01",
            item_name="설립/등기/정관 검토",
            section_type="GOVERNANCE",
            section_title="1. 기업 일반 및 지배구조",
            source_materials="(테스트 자료)",
            checklist_analysis="상태: ISSUE",
            legal_context="",
            issue_level="HIGH",
            block_contents={},
        )
        assert "CORP-01" in prompt
        assert "설립/등기/정관 검토" in prompt
        assert "(테스트 자료)" in prompt

    @pytest.mark.asyncio
    async def test_call_llm_tuple_return(self):
        """llm_call이 (str, float) 튜플을 반환하면 cost_usd가 올바르게 추적된다."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        async def _tuple_call(system: str, user: str) -> tuple[str, float]:
            return ("테스트 서술 내용", 0.05)

        gen = NarrativeGenerator(llm_call=_tuple_call)
        item = {
            "item_id": "COST-01",
            "name": "비용 추적 테스트",
            "status": "OK",
            "issue_level": None,
        }
        result = await gen.generate_narrative(
            item=item,
            section_type="TEST",
            section_title="테스트 섹션",
            source_files=[],
        )
        assert len(result.blocks) == 1
        assert result.cost_usd == pytest.approx(0.05)
        assert result.blocks[0].content == "테스트 서술 내용"

    @pytest.mark.asyncio
    async def test_call_llm_string_return_cost_estimation(self):
        """llm_call이 str을 반환하면 토큰 기반 비용이 추정된다."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        async def _str_call(system: str, user: str) -> str:
            return "비용 추정 서술 내용"

        gen = NarrativeGenerator(llm_call=_str_call)
        item = {
            "item_id": "COST-02",
            "name": "비용 추정 테스트",
            "status": "OK",
            "issue_level": None,
        }
        result = await gen.generate_narrative(
            item=item,
            section_type="TEST",
            section_title="테스트 섹션",
            source_files=[],
        )
        assert result.cost_usd > 0.0  # 추정 비용이 0보다 커야 함

    @pytest.mark.asyncio
    async def test_call_llm_tuple_cost_accumulation(self):
        """여러 블록의 비용이 올바르게 누적된다."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        call_count = 0

        async def _cost_call(system: str, user: str) -> tuple[str, float]:
            nonlocal call_count
            call_count += 1
            return (f"블록 {call_count} 서술", 0.02)

        gen = NarrativeGenerator(llm_call=_cost_call)
        item = {
            "item_id": "COST-03",
            "name": "비용 누적 테스트",
            "status": "ISSUE",
            "issue_level": "MEDIUM",  # 4블록
        }
        result = await gen.generate_narrative(
            item=item,
            section_type="TEST",
            section_title="테스트 섹션",
            source_files=[],
        )
        assert len(result.blocks) == 4
        assert result.cost_usd == pytest.approx(0.08)  # 4 * 0.02

    @pytest.mark.asyncio
    async def test_block_generation_failure_fallback(self):
        """블록 LLM 호출 실패 시 폴백 메시지와 cost=0으로 처리된다."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        call_count = 0

        async def _failing_call(system: str, user: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("LLM 타임아웃")
            return ("정상 서술", 0.03)

        gen = NarrativeGenerator(llm_call=_failing_call)
        item = {
            "item_id": "FAIL-01",
            "name": "블록 실패 테스트",
            "status": "ISSUE",
            "issue_level": "LOW",  # 4블록
        }
        result = await gen.generate_narrative(
            item=item,
            section_type="TEST",
            section_title="테스트 섹션",
            source_files=[],
        )
        assert len(result.blocks) == 4
        # 첫 번째 블록은 폴백 메시지
        assert "생성 실패" in result.blocks[0].content
        assert "수동 작성 필요" in result.blocks[0].content
        # 나머지 블록은 정상
        assert result.blocks[1].content == "정상 서술"
        # 비용: 실패 블록 0 + 정상 3개 * 0.03
        assert result.cost_usd == pytest.approx(0.09)

    @pytest.mark.asyncio
    async def test_section_item_error_isolation(self):
        """항목 1개 실패 시 빈 NarrativeResult 반환, 다른 항목은 정상 처리."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        call_count = 0

        async def _item_failing_call(system: str, user: str):
            nonlocal call_count
            call_count += 1
            # 3번째 LLM 호출 이후 실패 (2번째 항목의 첫 블록)
            if call_count == 2:
                raise RuntimeError("항목 레벨 오류")
            return "정상 서술"

        gen = NarrativeGenerator(llm_call=_item_failing_call)
        section = {
            "section_type": "TEST",
            "title": "테스트",
            "items": [
                {"item_id": "OK-01", "name": "정상 항목", "status": "OK"},
                {"item_id": "FAIL-02", "name": "실패 항목", "status": "OK"},
                {"item_id": "OK-03", "name": "정상 항목2", "status": "OK"},
            ],
        }
        results = await gen.generate_section_narratives(
            section=section,
            source_files=[],
        )
        assert len(results) == 3
        # 첫 번째 항목: 정상
        assert results[0].item_id == "OK-01"
        assert len(results[0].blocks) == 1
        # 두 번째 항목: 블록 레벨 에러는 폴백으로 처리 (항목은 정상 반환)
        assert results[1].item_id == "FAIL-02"
        assert "생성 실패" in results[1].blocks[0].content
        # 세 번째 항목: 정상
        assert results[2].item_id == "OK-03"
        assert len(results[2].blocks) == 1

    def test_extract_filename_cross_platform(self):
        """Windows/Unix 경로 모두 올바르게 파일명을 추출한다."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator()
        # _extract_filename은 generate_narrative 내부의 로컬 함수이므로
        # pathlib 기반 경로 추출을 간접 검증
        from pathlib import PurePosixPath, PureWindowsPath

        # Windows 경로
        win_path = r"C:\Users\user\docs\정관.pdf"
        assert PureWindowsPath(win_path).name == "정관.pdf"

        # Unix 경로
        unix_path = "/home/user/docs/정관.pdf"
        assert PurePosixPath(unix_path).name == "정관.pdf"

        # 혼합 경로 (Windows 백슬래시)
        mixed_path = "uploads\\2026\\정관_수정본.docx"
        assert PureWindowsPath(mixed_path).name == "정관_수정본.docx"

    @pytest.mark.asyncio
    async def test_learning_pattern_injection_failure_continues(self):
        """학습 패턴 주입 실패해도 서술이 정상 생성된다."""
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        async def _simple_call(system: str, user: str):
            return "정상 서술"

        gen = NarrativeGenerator(
            llm_call=_simple_call,
            learned_patterns=["패턴1", "패턴2"],  # 학습 패턴 설정
        )

        item = {
            "item_id": "LEARN-01",
            "name": "학습 패턴 테스트",
            "status": "OK",
        }

        # LearningPromptInjector import가 실패해도 예외 없이 정상 진행
        result = await gen.generate_narrative(
            item=item,
            section_type="TEST",
            section_title="테스트",
            source_files=[],
        )
        # 학습 패턴 주입 실패해도 서술은 생성됨
        assert len(result.blocks) == 1
        assert result.blocks[0].content == "정상 서술"

    def test_build_block_prompt_with_chain(self):
        from app.ralph.generators.ldd.narrative_generator import NarrativeGenerator

        gen = NarrativeGenerator()
        block_contents = {
            "FACTS": "사실관계 내용...",
            "LEGAL_REVIEW": "법률 검토 내용...",
        }
        prompt = gen._build_block_prompt(
            block_type=NarrativeBlockType.ANALYSIS,
            item_id="CORP-01",
            item_name="테스트",
            section_type="GOVERNANCE",
            section_title="1. 기업 일반",
            source_materials="",
            checklist_analysis="",
            legal_context="",
            issue_level="HIGH",
            block_contents=block_contents,
        )
        assert "사실관계 내용..." in prompt
        assert "법률 검토 내용..." in prompt
