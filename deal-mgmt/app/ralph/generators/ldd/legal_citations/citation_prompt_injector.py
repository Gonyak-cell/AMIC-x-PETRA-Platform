"""법률 인용 프롬프트 주입기.

섹션 유형에 맞는 법조문과 판례를 LLM 프롬프트에 사전 주입하여
LLM이 인용을 "생성"하는 대신 "선택"만 하도록 유도한다.
"""

from __future__ import annotations

from app.ralph.generators.ldd.legal_citations.citation_db import (
    CitationDB,
    PrecedentEntry,
    StatuteEntry,
)


class CitationPromptInjector:
    """법률 컨텍스트를 프롬프트에 주입한다."""

    def __init__(self, db: CitationDB | None = None) -> None:
        self._db = db or CitationDB()

    def build_legal_context(
        self,
        section_type: str,
        *,
        max_statutes: int = 15,
        max_precedents: int = 8,
    ) -> str:
        """섹션 유형에 관련된 법조문과 판례를 텍스트 블록으로 구성한다.

        Args:
            section_type: LDD 섹션 유형 (예: "GOVERNANCE")
            max_statutes: 주입할 최대 법조문 수
            max_precedents: 주입할 최대 판례 수

        Returns:
            프롬프트에 삽입할 법률 컨텍스트 텍스트
        """
        statutes = self._db.get_statutes(section_type)[:max_statutes]
        precedents = self._db.get_precedents(section_type)[:max_precedents]

        if not statutes and not precedents:
            return "(해당 섹션에 대한 큐레이션된 법률 컨텍스트 없음)"

        parts: list[str] = []

        if statutes:
            parts.append("### 관련 법률 조항")
            parts.append("아래 법조문 중 관련성이 높은 것을 선택하여 인용하세요.")
            parts.append("인용 형식: [법률명 제X조 제Y항]")
            parts.append("")
            for s in statutes:
                parts.append(self._format_statute(s))
            parts.append("")

        if precedents:
            parts.append("### 관련 판례")
            parts.append("아래 판례 중 관련성이 높은 것을 선택하여 인용하세요.")
            parts.append("인용 형식: [대법원 YYYY.MM.DD. 선고 사건번호 판결]")
            parts.append("")
            for p in precedents:
                parts.append(self._format_precedent(p))
            parts.append("")

        parts.append("주의: 위 목록에 없는 법조문이나 판례를 임의로 생성하지 마세요.")
        parts.append("인용할 때 반드시 위 목록의 ID를 [cite:ID] 형식으로 태그하세요.")

        return "\n".join(parts)

    def extract_citation_ids(self, text: str) -> list[str]:
        """텍스트에서 [cite:ID] 형식의 인용 ID를 추출한다."""
        import re

        return re.findall(r"\[cite:([^\]]+)\]", text)

    def _format_statute(self, s: StatuteEntry) -> str:
        return f"- **[{s.statute_id}]** {s.law_name} {s.article} ({s.title}): {s.summary}"

    def _format_precedent(self, p: PrecedentEntry) -> str:
        return f"- **[{p.precedent_id}]** {p.court} {p.date} 선고 {p.case_number} ({p.title}): {p.summary}"
