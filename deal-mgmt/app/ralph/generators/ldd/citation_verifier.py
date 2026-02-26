"""LDD 법률 인용 검증기.

LLM이 생성한 서술에서 법률 인용을 추출하고,
큐레이션 레지스트리와 대조하여 환각(hallucination)을 필터한다.

검증 결과:
- VERIFIED: 레지스트리에 존재하는 인용
- UNVERIFIED: 레지스트리에 없는 인용 (환각 가능성) → [미확인] 태그
- PATTERN_MATCH: 정규식으로 인식되었으나 ID 태그 없음 → 참조 경고
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.ralph.generators.ldd.legal_citations.citation_db import CitationDB

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CitationRef:
    """서술에서 추출된 인용 참조."""

    citation_id: str
    citation_type: str  # "statute" | "precedent" | "unknown"
    original_text: str  # 원문에서 추출된 텍스트
    status: str = "UNVERIFIED"  # VERIFIED | UNVERIFIED | PATTERN_MATCH
    registry_match: str = ""  # 매칭된 레지스트리 항목 요약


@dataclass
class VerificationResult:
    """인용 검증 결과."""

    total_citations: int = 0
    verified: int = 0
    unverified: int = 0
    pattern_only: int = 0
    citations: list[CitationRef] = field(default_factory=list)
    annotated_text: str = ""  # [미확인] 태그가 추가된 텍스트

    def to_dict(self) -> dict:
        return {
            "total_citations": self.total_citations,
            "verified": self.verified,
            "unverified": self.unverified,
            "pattern_only": self.pattern_only,
            "citations": [
                {
                    "citation_id": c.citation_id,
                    "citation_type": c.citation_type,
                    "original_text": c.original_text,
                    "status": c.status,
                    "registry_match": c.registry_match,
                }
                for c in self.citations
            ],
        }


# ── 인용 패턴 정규식 ──────────────────────────────────────────────────────────

# [cite:ID] 형식 (CitationPromptInjector가 유도하는 형식)
_CITE_TAG_RE = re.compile(r"\[cite:([^\]]+)\]")

# 법조문 패턴: "~법 제X조" 또는 "~법 제X조 제Y항"
_STATUTE_RE = re.compile(
    r"([\w가-힣]+법)\s+제(\d+)조(?:의(\d+))?(?:\s+제(\d+)항)?",
)

# 판례 패턴: "대법원 YYYY.MM.DD. 선고 사건번호 판결" 또는 "대법원 사건번호"
_PRECEDENT_RE = re.compile(
    r"(대법원|서울고등법원|서울중앙지방법원)[\s,]*"
    r"(?:(\d{4}[.\s]+\d{1,2}[.\s]+\d{1,2})[.\s]*선고\s+)?"
    r"(\d{4}[다두]\w+)",
)


class CitationVerifier:
    """LLM 생성 서술의 법률 인용을 검증한다."""

    def __init__(self, db: CitationDB | None = None) -> None:
        self._db = db or CitationDB()

    def verify_text(self, text: str) -> VerificationResult:
        """서술 텍스트에서 인용을 추출하고 검증한다.

        Returns:
            VerificationResult with annotated text
        """
        citations: list[CitationRef] = []
        seen_ids: set[str] = set()

        # 1. [cite:ID] 태그 추출 및 검증
        for match in _CITE_TAG_RE.finditer(text):
            cid = match.group(1)
            if cid in seen_ids:
                continue
            seen_ids.add(cid)

            ref = self._verify_citation_id(cid, match.group(0))
            citations.append(ref)

        # 2. 법조문 패턴 매칭 (태그 없는 인용)
        for match in _STATUTE_RE.finditer(text):
            full_text = match.group(0)
            # 이미 태그로 검증된 인용은 스킵
            if any(c.original_text in full_text or full_text in c.original_text for c in citations):
                continue

            statute_id = self._guess_statute_id(match)
            if statute_id and statute_id not in seen_ids:
                seen_ids.add(statute_id)
                ref = self._verify_citation_id(statute_id, full_text)
                if ref.status == "UNVERIFIED":
                    # 정규식으로 인식은 됐으나 레지스트리에 없음
                    ref = CitationRef(
                        citation_id=statute_id,
                        citation_type="statute",
                        original_text=full_text,
                        status="PATTERN_MATCH",
                    )
                citations.append(ref)

        # 3. 판례 패턴 매칭 (태그 없는 인용)
        for match in _PRECEDENT_RE.finditer(text):
            full_text = match.group(0)
            if any(c.original_text in full_text or full_text in c.original_text for c in citations):
                continue

            case_number = match.group(3)
            court = match.group(1)
            precedent_id = f"{court}_{case_number}"
            if precedent_id not in seen_ids:
                seen_ids.add(precedent_id)
                ref = self._verify_citation_id(precedent_id, full_text)
                if ref.status == "UNVERIFIED":
                    ref = CitationRef(
                        citation_id=precedent_id,
                        citation_type="precedent",
                        original_text=full_text,
                        status="PATTERN_MATCH",
                    )
                citations.append(ref)

        # 4. 결과 집계
        verified_count = sum(1 for c in citations if c.status == "VERIFIED")
        unverified_count = sum(1 for c in citations if c.status == "UNVERIFIED")
        pattern_count = sum(1 for c in citations if c.status == "PATTERN_MATCH")

        # 5. 미확인 인용에 태그 추가
        annotated = self._annotate_unverified(text, citations)

        return VerificationResult(
            total_citations=len(citations),
            verified=verified_count,
            unverified=unverified_count,
            pattern_only=pattern_count,
            citations=citations,
            annotated_text=annotated,
        )

    def verify_narrative_sections(
        self,
        narrative_sections: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        """전체 narrative_sections의 인용을 검증한다.

        각 NarrativeResult dict의 blocks 내 content를 검증하고,
        citation_verification 필드를 추가한다.

        Returns:
            검증 정보가 추가된 narrative_sections
        """
        result: dict[str, list[dict]] = {}

        for section_type, items in narrative_sections.items():
            verified_items: list[dict] = []
            for item in items:
                item_copy = dict(item)
                all_citations: list[dict] = []

                for block in item_copy.get("blocks", []):
                    content = block.get("content", "")
                    if not content:
                        continue
                    vr = self.verify_text(content)
                    block["content"] = vr.annotated_text
                    all_citations.extend(vr.to_dict()["citations"])

                item_copy["citation_verification"] = {
                    "total": len(all_citations),
                    "verified": sum(1 for c in all_citations if c["status"] == "VERIFIED"),
                    "unverified": sum(1 for c in all_citations if c["status"] == "UNVERIFIED"),
                    "pattern_only": sum(1 for c in all_citations if c["status"] == "PATTERN_MATCH"),
                    "citations": all_citations,
                }
                verified_items.append(item_copy)

            result[section_type] = verified_items

        return result

    def _verify_citation_id(self, cid: str, original_text: str) -> CitationRef:
        """인용 ID를 레지스트리에서 검증한다."""
        # 법조문 검색
        statute = self._db.find_statute(cid)
        if statute:
            return CitationRef(
                citation_id=cid,
                citation_type="statute",
                original_text=original_text,
                status="VERIFIED",
                registry_match=f"{statute.law_name} {statute.article} ({statute.title})",
            )

        # 판례 검색
        precedent = self._db.find_precedent(cid)
        if precedent:
            return CitationRef(
                citation_id=cid,
                citation_type="precedent",
                original_text=original_text,
                status="VERIFIED",
                registry_match=f"{precedent.court} {precedent.case_number} ({precedent.title})",
            )

        return CitationRef(
            citation_id=cid,
            citation_type="unknown",
            original_text=original_text,
            status="UNVERIFIED",
        )

    def _guess_statute_id(self, match: re.Match) -> str | None:
        """정규식 매칭에서 statute_id를 추측한다."""
        law_name = match.group(1)
        article = match.group(2)
        sub_article = match.group(3)  # 조의X

        # 법률명 → statute_id prefix 매핑 (korean_statutes.py 커버리지 확대)
        name_map: dict[str, str] = {
            "상법": "상법",
            "민법": "민법",
            "자본시장법": "자본시장법",
            "독점규제법": "독점규제법",
            "근로기준법": "근로기준법",
            "특허법": "특허법",
            "상표법": "상표법",
            "저작권법": "저작권법",
            "개인정보보호법": "개인정보보호법",
            "법인세법": "법인세법",
            "부가가치세법": "부가가치세법",
            "건축법": "건축법",
            # 추가 매핑 (korean_statutes.py 대응)
            "부정경쟁방지법": "부정경쟁방지법",
            "노동조합법": "노동조합법",
            "산업안전보건법": "산업안전보건법",
            "국토계획법": "국토계획법",
            "농지법": "농지법",
            "부동산실명법": "부동산실명법",
            "외국인투자촉진법": "외국인투자촉진법",
            "국제조세조정법": "국제조세조정법",
            "정보통신망법": "정보통신망법",
            "민사소송법": "민사소송법",
            "형사소송법": "형사소송법",
            "행정소송법": "행정소송법",
        }

        prefix = name_map.get(law_name)
        if not prefix:
            return None

        if sub_article:
            return f"{prefix}_{article}_{sub_article}"
        return f"{prefix}_{article}"

    def _annotate_unverified(
        self,
        text: str,
        citations: list[CitationRef],
    ) -> str:
        """미확인 인용에 [미확인] 태그를 추가한다."""
        annotated = text

        for c in citations:
            if c.status == "UNVERIFIED" and c.original_text in annotated:
                annotated = annotated.replace(
                    c.original_text,
                    f"{c.original_text} [미확인]",
                    1,
                )

        return annotated
