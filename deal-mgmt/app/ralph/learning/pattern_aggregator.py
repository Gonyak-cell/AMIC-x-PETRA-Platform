"""과거 Ralph Loop 세션에서 반복 패턴을 집계한다.

DB의 ralph_sessions 테이블에서:
- 자주 발생한 이슈 (섹션별)
- 높은 점수를 받은 세션의 공통 패턴
을 추출하여 새 세션의 LLM 프롬프트에 주입한다.
"""

from __future__ import annotations

import logging
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PatternAggregator:
    """과거 세션의 반복 패턴을 집계한다."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_common_issues(
        self,
        doc_type: str,
        section_id: str = "",
        limit: int = 5,
    ) -> list[str]:
        """해당 문서 유형/섹션에서 자주 발생한 이슈 Top N.

        ralph_sessions.progress JSONB에서 gate_results → issues를 추출하여
        빈도순으로 정렬한다.
        """
        from app.models.ralph_session import RalphSession, RalphSessionStatus

        q = (
            select(RalphSession.progress)
            .where(
                RalphSession.doc_type == doc_type,
                RalphSession.status == RalphSessionStatus.COMPLETED,
                RalphSession.progress.isnot(None),
            )
            .order_by(RalphSession.created_at.desc())
            .limit(20)  # 최근 20개 세션만
        )
        result = await self._db.execute(q)
        rows = result.scalars().all()

        issue_counter: Counter[str] = Counter()
        for progress in rows:
            if not isinstance(progress, dict):
                continue
            records = progress.get("records", {})
            target_sections = [section_id] if section_id else list(records.keys())
            for sid in target_sections:
                for rec in records.get(sid, []):
                    for gr in rec.get("gate_results", []):
                        for issue in gr.get("issues", []):
                            if issue and len(issue) > 10:  # 의미 있는 이슈만
                                issue_counter[issue] += 1

        return [issue for issue, _ in issue_counter.most_common(limit)]

    async def get_best_practices(
        self,
        doc_type: str,
        min_score: float = 4.5,
        limit: int = 5,
    ) -> list[str]:
        """높은 점수(4.5+)를 받은 세션들의 공통 패턴을 추출한다.

        높은 점수 세션의 suggestions에서 긍정적 패턴을 추출한다.
        """
        from app.models.ralph_session import RalphSession, RalphSessionStatus

        q = (
            select(RalphSession.progress)
            .where(
                RalphSession.doc_type == doc_type,
                RalphSession.status == RalphSessionStatus.COMPLETED,
                RalphSession.final_score >= min_score,
                RalphSession.progress.isnot(None),
            )
            .order_by(RalphSession.final_score.desc())
            .limit(10)
        )
        result = await self._db.execute(q)
        rows = result.scalars().all()

        suggestion_counter: Counter[str] = Counter()
        for progress in rows:
            if not isinstance(progress, dict):
                continue
            for _sid, recs in progress.get("records", {}).items():
                for rec in recs:
                    for gr in rec.get("gate_results", []):
                        for suggestion in gr.get("suggestions", []):
                            if suggestion and len(suggestion) > 10:
                                suggestion_counter[suggestion] += 1

        return [s for s, _ in suggestion_counter.most_common(limit)]

    async def get_learned_patterns(
        self,
        doc_type: str,
        section_id: str = "",
    ) -> list[str]:
        """이슈 + 베스트 프랙티스를 통합하여 학습 패턴을 반환한다."""
        issues = await self.get_common_issues(doc_type, section_id)
        practices = await self.get_best_practices(doc_type)

        patterns: list[str] = []
        if issues:
            patterns.append("## 자주 발생하는 이슈 (피해야 할 패턴)")
            for issue in issues:
                patterns.append(f"- {issue}")
        if practices:
            patterns.append("## 높은 점수를 받은 세션의 패턴 (따라야 할 패턴)")
            for practice in practices:
                patterns.append(f"- {practice}")

        return patterns
