"""법률 조항 + 판례 데이터베이스 (수동 큐레이션).

섹션별로 관련 법조문과 판례를 검색하는 인터페이스를 제공한다.
LLM이 '선택'만 하도록 사전 주입하여 환각을 방지한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StatuteEntry:
    """법률 조항 엔트리."""

    statute_id: str  # 예: "상법_374_1"
    law_name: str  # 예: "상법"
    article: str  # 예: "제374조 제1항"
    title: str  # 조항 제목
    summary: str  # 핵심 내용 요약 (1-2문장)
    section_types: list[str] = field(default_factory=list)  # 관련 섹션 유형


@dataclass(frozen=True)
class PrecedentEntry:
    """판례 엔트리."""

    precedent_id: str  # 예: "대법원_2017다212095"
    court: str  # 예: "대법원"
    case_number: str  # 예: "2017다212095"
    date: str  # 예: "2018.01.25."
    title: str  # 판례 요지 제목
    summary: str  # 핵심 판시 요약 (1-2문장)
    section_types: list[str] = field(default_factory=list)


class CitationDB:
    """법률 조항 + 판례 레지스트리.

    수동 큐레이션된 데이터를 메모리에 보유하고 섹션별 조회를 제공한다.
    """

    def __init__(self) -> None:
        self._statutes: list[StatuteEntry] = []
        self._precedents: list[PrecedentEntry] = []
        self._statute_index: dict[str, list[StatuteEntry]] = {}
        self._precedent_index: dict[str, list[PrecedentEntry]] = {}
        self._loaded = False

    def load(self) -> None:
        """큐레이션 데이터를 로드한다."""
        if self._loaded:
            return

        from app.ralph.generators.ldd.legal_citations.korean_precedents import PRECEDENTS
        from app.ralph.generators.ldd.legal_citations.korean_statutes import STATUTES

        self._statutes = STATUTES
        self._precedents = PRECEDENTS

        # 섹션별 인덱스 구축
        for s in self._statutes:
            for st in s.section_types:
                self._statute_index.setdefault(st, []).append(s)

        for p in self._precedents:
            for st in p.section_types:
                self._precedent_index.setdefault(st, []).append(p)

        self._loaded = True

    def get_statutes(self, section_type: str) -> list[StatuteEntry]:
        """섹션 유형에 관련된 법률 조항 목록을 반환한다."""
        if not self._loaded:
            self.load()
        return self._statute_index.get(section_type, [])

    def get_precedents(self, section_type: str) -> list[PrecedentEntry]:
        """섹션 유형에 관련된 판례 목록을 반환한다."""
        if not self._loaded:
            self.load()
        return self._precedent_index.get(section_type, [])

    def get_all_statutes(self) -> list[StatuteEntry]:
        if not self._loaded:
            self.load()
        return list(self._statutes)

    def get_all_precedents(self) -> list[PrecedentEntry]:
        if not self._loaded:
            self.load()
        return list(self._precedents)

    def find_statute(self, statute_id: str) -> StatuteEntry | None:
        """ID로 법률 조항을 검색한다."""
        if not self._loaded:
            self.load()
        for s in self._statutes:
            if s.statute_id == statute_id:
                return s
        return None

    def find_precedent(self, precedent_id: str) -> PrecedentEntry | None:
        """ID로 판례를 검색한다."""
        if not self._loaded:
            self.load()
        for p in self._precedents:
            if p.precedent_id == precedent_id:
                return p
        return None

    @property
    def statute_count(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._statutes)

    @property
    def precedent_count(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._precedents)
