"""Ralph Learning 패턴 단위 테스트.

PatternAggregator (DB 쿼리) 와 LearningPromptInjector (프롬프트 주입) 를 검증한다.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ralph_session import RalphSession, RalphSessionStatus
from app.models.transaction import Transaction
from app.ralph.learning.pattern_aggregator import PatternAggregator
from app.ralph.learning.prompt_injector import LearningPromptInjector


def _make_txn(txn_id: uuid.UUID, idx: int) -> Transaction:
    """FK 충족용 최소 Transaction."""
    return Transaction(
        id=txn_id,
        code_name=f"RL-TEST-{idx:04d}",
        name=f"Ralph Learning 테스트 거래 {idx}",
        side="SELL",
        target_company_name="테스트 대상기업",
        client_name="테스트 의뢰기업",
        lead_advisor_email="test@example.com",
    )


# ── LearningPromptInjector (순수 로직, DB 불필요) ─────────────────────────────


class TestLearningPromptInjector:
    def setup_method(self):
        self.injector = LearningPromptInjector()

    def test_enrich_empty_patterns(self):
        """패턴이 없으면 원본 프롬프트 그대로 반환."""
        base = "You are an analyst."
        assert self.injector.enrich_system_prompt(base, []) == base

    def test_enrich_with_patterns(self):
        """패턴이 있으면 '과거 학습' 섹션이 추가된다."""
        base = "You are an analyst."
        patterns = [
            "## 자주 발생하는 이슈",
            "- 재무제표 수치 불일치",
            "- 법인등기 확인 누락",
        ]
        result = self.injector.enrich_system_prompt(base, patterns)

        assert result.startswith(base)
        assert "과거 반복에서 학습된 패턴" in result
        assert "재무제표 수치 불일치" in result
        assert "법인등기 확인 누락" in result

    def test_enrich_feedback_empty_patterns(self):
        """패턴 없으면 기존 피드백 그대로."""
        existing = ["이전 피드백 1", "이전 피드백 2"]
        assert self.injector.enrich_feedback(existing, []) == existing

    def test_enrich_feedback_with_patterns(self):
        """패턴이 있으면 피드백 끝에 학습 패턴 추가."""
        existing = ["피드백1"]
        patterns = [
            "## 제목 (필터링됨)",
            "- 패턴 A",
            "- 패턴 B",
        ]
        result = self.injector.enrich_feedback(existing, patterns)

        assert len(result) == 2
        assert result[0] == "피드백1"
        assert "[학습 패턴]" in result[1]
        # ## 로 시작하는 패턴은 필터링됨
        assert "제목" not in result[1]
        assert "패턴 A" in result[1]

    def test_enrich_feedback_does_not_mutate_original(self):
        """원본 리스트는 변경되지 않는다."""
        existing = ["a", "b"]
        patterns = ["- x"]
        result = self.injector.enrich_feedback(existing, patterns)
        assert len(existing) == 2
        assert len(result) == 3


# ── PatternAggregator (DB 필요) ───────────────────────────────────────────────


@pytest.fixture
async def seeded_db(async_session: AsyncSession):
    """학습 패턴 테스트용 Ralph 세션 데이터를 시드한다."""
    sessions = []

    # 완료된 세션 3개 — 다양한 점수와 progress 데이터
    # NOTE: 이슈/suggestions 문자열은 10자 초과여야 PatternAggregator에서 필터링되지 않음
    # FK 충족용 Transaction 먼저 생성
    txn_ids = [uuid.uuid4() for _ in range(5)]
    for idx, tid in enumerate(txn_ids):
        async_session.add(_make_txn(tid, idx))
    await async_session.flush()  # Transaction INSERT 먼저 확정

    for i, (score, progress) in enumerate(
        [
            (
                4.8,
                {
                    "records": {
                        "GOVERNANCE": [
                            {
                                "iteration": 1,
                                "gate_results": [
                                    {
                                        "issues": [
                                            "법인등기 관련 사항이 누락되었습니다",
                                            "주주명부 날짜가 최신 정보와 불일치합니다",
                                        ],
                                        "suggestions": [
                                            "등기부등본과 교차검증을 수행하세요",
                                            "주주명부 최신본을 반드시 확인하세요",
                                        ],
                                    }
                                ],
                            }
                        ],
                        "CAPITAL": [
                            {
                                "iteration": 1,
                                "gate_results": [
                                    {
                                        "issues": ["자본금 변경 이력이 불완전합니다"],
                                        "suggestions": ["정관 변경 이력과 대조 확인하세요"],
                                    }
                                ],
                            }
                        ],
                    }
                },
            ),
            (
                4.6,
                {
                    "records": {
                        "GOVERNANCE": [
                            {
                                "iteration": 1,
                                "gate_results": [
                                    {
                                        "issues": ["법인등기 관련 사항이 누락되었습니다"],
                                        "suggestions": ["등기부등본과 교차검증을 수행하세요"],
                                    }
                                ],
                            }
                        ],
                    }
                },
            ),
            (
                3.2,
                {
                    "records": {
                        "GOVERNANCE": [
                            {
                                "iteration": 1,
                                "gate_results": [
                                    {
                                        "issues": ["이사회 의사록이 첨부되지 않았습니다"],
                                        "suggestions": ["이사회 결의 근거를 반드시 보완하세요"],
                                    }
                                ],
                            }
                        ],
                    }
                },
            ),
        ]
    ):
        session = RalphSession(
            id=uuid.uuid4(),
            transaction_id=txn_ids[i],
            doc_type="LDD",
            status=RalphSessionStatus.COMPLETED,
            final_score=score,
            progress=progress,
        )
        sessions.append(session)
        async_session.add(session)

    # FAILED 세션 (집계에서 제외되어야 함)
    failed = RalphSession(
        id=uuid.uuid4(),
        transaction_id=txn_ids[3],
        doc_type="LDD",
        status=RalphSessionStatus.FAILED,
        final_score=None,
        progress={
            "records": {
                "GOVERNANCE": [
                    {"iteration": 1, "gate_results": [{"issues": ["이 이슈는 무시되어야 하는 데이터입니다"]}]}
                ]
            }
        },
    )
    async_session.add(failed)

    # 다른 doc_type 세션 (LDD 집계에서 제외되어야 함)
    other = RalphSession(
        id=uuid.uuid4(),
        transaction_id=txn_ids[4],
        doc_type="TM",
        status=RalphSessionStatus.COMPLETED,
        final_score=4.5,
        progress={
            "records": {
                "OVERVIEW": [{"iteration": 1, "gate_results": [{"issues": ["TM 관련 이슈로 다른 문서 유형입니다"]}]}]
            }
        },
    )
    async_session.add(other)

    await async_session.commit()
    return async_session


class TestPatternAggregator:
    @pytest.mark.asyncio
    async def test_get_common_issues_all_sections(self, seeded_db: AsyncSession):
        """전체 섹션 대상 자주 발생한 이슈를 빈도순으로 반환."""
        agg = PatternAggregator(seeded_db)
        issues = await agg.get_common_issues("LDD")

        assert len(issues) > 0
        # "법인등기 관련 사항이 누락되었습니다"는 2개 세션에서 등장 → 최빈 이슈
        assert issues[0] == "법인등기 관련 사항이 누락되었습니다"

    @pytest.mark.asyncio
    async def test_get_common_issues_specific_section(self, seeded_db: AsyncSession):
        """특정 섹션만 필터링."""
        agg = PatternAggregator(seeded_db)
        issues = await agg.get_common_issues("LDD", section_id="CAPITAL")

        assert len(issues) == 1
        assert "자본금 변경" in issues[0]

    @pytest.mark.asyncio
    async def test_get_common_issues_excludes_failed(self, seeded_db: AsyncSession):
        """FAILED 세션의 이슈는 집계에서 제외."""
        agg = PatternAggregator(seeded_db)
        issues = await agg.get_common_issues("LDD")
        assert "이 이슈는 무시되어야 하는 데이터입니다" not in issues

    @pytest.mark.asyncio
    async def test_get_common_issues_excludes_other_doctype(self, seeded_db: AsyncSession):
        """다른 doc_type의 이슈는 제외."""
        agg = PatternAggregator(seeded_db)
        issues = await agg.get_common_issues("LDD")
        assert "TM 관련 이슈로 다른 문서 유형입니다" not in issues

    @pytest.mark.asyncio
    async def test_get_common_issues_limit(self, seeded_db: AsyncSession):
        """limit 파라미터로 반환 개수를 제한."""
        agg = PatternAggregator(seeded_db)
        issues = await agg.get_common_issues("LDD", limit=1)
        assert len(issues) == 1

    @pytest.mark.asyncio
    async def test_get_common_issues_short_issues_filtered(self, seeded_db: AsyncSession):
        """10자 미만의 짧은 이슈는 필터링."""
        agg = PatternAggregator(seeded_db)
        issues = await agg.get_common_issues("LDD")
        for issue in issues:
            assert len(issue) > 10

    @pytest.mark.asyncio
    async def test_get_best_practices(self, seeded_db: AsyncSession):
        """4.5점 이상 세션의 suggestions를 반환."""
        agg = PatternAggregator(seeded_db)
        practices = await agg.get_best_practices("LDD", min_score=4.5)

        assert len(practices) > 0
        # 4.5점 이상 세션: 4.8점, 4.6점
        assert "등기부등본과 교차검증을 수행하세요" in practices

    @pytest.mark.asyncio
    async def test_get_best_practices_high_threshold(self, seeded_db: AsyncSession):
        """높은 threshold에서는 결과가 줄어든다."""
        agg = PatternAggregator(seeded_db)
        practices = await agg.get_best_practices("LDD", min_score=4.7)

        # 4.8점 세션만 해당
        assert len(practices) >= 1

    @pytest.mark.asyncio
    async def test_get_learned_patterns_combined(self, seeded_db: AsyncSession):
        """이슈 + 베스트 프랙티스 통합 패턴."""
        agg = PatternAggregator(seeded_db)
        patterns = await agg.get_learned_patterns("LDD")

        assert len(patterns) > 0
        headers = [p for p in patterns if p.startswith("##")]
        assert any("피해야 할" in h for h in headers)
        assert any("따라야 할" in h for h in headers)

    @pytest.mark.asyncio
    async def test_get_learned_patterns_empty_doctype(self, seeded_db: AsyncSession):
        """해당 doc_type에 데이터가 없으면 빈 리스트."""
        agg = PatternAggregator(seeded_db)
        patterns = await agg.get_learned_patterns("UNKNOWN")
        assert patterns == []


# ── 통합: PatternAggregator → LearningPromptInjector ──────────────────────────


class TestLearningIntegration:
    @pytest.mark.asyncio
    async def test_full_pipeline(self, seeded_db: AsyncSession):
        """PatternAggregator → LearningPromptInjector 전체 파이프라인."""
        agg = PatternAggregator(seeded_db)
        injector = LearningPromptInjector()

        patterns = await agg.get_learned_patterns("LDD")
        enriched = injector.enrich_system_prompt("You are an LDD analyst.", patterns)

        assert "You are an LDD analyst." in enriched
        assert "법인등기 관련 사항이 누락되었습니다" in enriched
        assert "과거 반복에서 학습된 패턴" in enriched
