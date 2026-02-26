"""정성적 분석 엔진 — 인터뷰 구조화, 테마 추출, 리스크 플래그.

순수 함수만 포함. DB 접근 절대 금지.
LLM 호출 없음 — 키워드/패턴 기반 구조화.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

ENGINE_VERSION = "0.1.0"

# ── Data Types ───────────────────────────────────────────


@dataclass(frozen=True)
class EvidenceLinkData:
    target_type: str
    source_type: str
    source_id: str
    source_detail: dict[str, Any] | None = None


@dataclass(frozen=True)
class InterviewNote:
    """구조화된 인터뷰 노트."""

    note_id: str
    source: str                      # "management", "employee", "third_party"
    topic: str                       # 주제
    content: str                     # 내용
    risk_flags: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    sentiment: str = "neutral"       # "positive", "neutral", "negative"


@dataclass(frozen=True)
class ThemeItem:
    """추출된 테마."""

    theme: str
    frequency: int                   # 언급 빈도
    sources: list[str]               # 언급 출처
    sentiment_distribution: dict[str, int] = field(default_factory=dict)
    related_risks: list[str] = field(default_factory=list)


@dataclass
class InterviewStructureResult:
    """인터뷰 구조화 결과."""

    notes: list[InterviewNote]
    total_notes: int
    source_distribution: dict[str, int]       # {source: count}
    topic_distribution: dict[str, int]        # {topic: count}
    risk_flag_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class ThemeExtractionResult:
    """테마 추출 결과."""

    themes: list[ThemeItem]
    total_themes: int
    top_themes: list[str]                     # 상위 N 테마
    risk_themes: list[str]                    # 리스크 관련 테마
    warnings: list[str] = field(default_factory=list)


# ── 키워드 사전 ──────────────────────────────────────────

_RISK_KEYWORDS = {
    "litigation", "lawsuit", "소송", "분쟁",
    "compliance", "violation", "위반", "규제",
    "fraud", "irregularity", "부정", "횡령",
    "related party", "특수관계", "관계사",
    "contingent", "우발", "잠재",
    "going concern", "계속기업",
    "impairment", "손상",
    "covenant", "breach", "위약",
    "turnover", "이직", "퇴직",
    "overdue", "연체", "미수",
    "obsolete", "진부화", "재고 부진",
    "warranty", "보증", "하자",
    "environmental", "환경", "오염",
    "tax dispute", "세무 분쟁", "추징",
}

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "revenue": ["매출", "수주", "매출액", "revenue", "sales", "order"],
    "cost": ["원가", "비용", "인건비", "cost", "expense", "personnel"],
    "operations": ["운영", "생산", "공정", "operation", "production", "process"],
    "strategy": ["전략", "사업계획", "성장", "strategy", "growth", "plan"],
    "compliance": ["규제", "법률", "준법", "compliance", "regulation", "legal"],
    "hr": ["인사", "조직", "인력", "hr", "organization", "talent"],
    "it": ["IT", "시스템", "디지털", "system", "technology", "digital"],
    "finance": ["재무", "자금", "회계", "finance", "funding", "accounting"],
    "risk": ["리스크", "위험", "risk", "threat", "vulnerability"],
    "customer": ["고객", "거래처", "customer", "client"],
}

_SENTIMENT_POSITIVE = {"성장", "증가", "개선", "확대", "호전", "growth", "improvement", "increase", "positive", "strong"}
_SENTIMENT_NEGATIVE = {"감소", "하락", "악화", "위험", "부정", "decline", "decrease", "risk", "concern", "weak", "loss"}


# ── Core: Interview Structuring ──────────────────────────


def structure_interviews(
    raw_notes: list[dict[str, Any]],
    *,
    content_key: str = "content",
    source_key: str = "source",
    topic_key: str = "topic",
) -> tuple[InterviewStructureResult, list[EvidenceLinkData]]:
    """비정형 인터뷰 노트를 구조화한다.

    Args:
        raw_notes: 인터뷰 노트 리스트
            [{"content": "...", "source": "management", "topic": "매출"}, ...]

    Returns:
        (InterviewStructureResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    if not raw_notes:
        return InterviewStructureResult(
            notes=[],
            total_notes=0,
            source_distribution={},
            topic_distribution={},
            risk_flag_count=0,
            warnings=["INTERVIEW_EMPTY: No interview data"],
        ), evidence

    structured: list[InterviewNote] = []
    source_dist: dict[str, int] = {}
    topic_dist: dict[str, int] = {}
    risk_count = 0

    for i, raw in enumerate(raw_notes):
        content = str(raw.get(content_key, "")).strip()
        source = str(raw.get(source_key, "unknown")).strip().lower()
        topic = str(raw.get(topic_key, "")).strip()

        if not content:
            continue

        # 토픽 자동 분류 (미지정 시)
        if not topic:
            topic = _classify_topic(content)

        # 리스크 플래그 감지
        flags = _detect_risk_flags(content)
        risk_count += len(flags)

        # 테마 추출
        themes = _extract_themes_from_text(content)

        # 감정 분석 (키워드 기반)
        sentiment = _analyze_sentiment(content)

        note = InterviewNote(
            note_id=f"INT-{i + 1:03d}",
            source=source,
            topic=topic,
            content=content,
            risk_flags=flags,
            themes=themes,
            sentiment=sentiment,
        )
        structured.append(note)

        source_dist[source] = source_dist.get(source, 0) + 1
        topic_dist[topic] = topic_dist.get(topic, 0) + 1

    # 경고
    if risk_count > len(structured) * 0.5:
        warnings.append(
            f"INTERVIEW_HIGH_RISK: {risk_count} risk flags in {len(structured)} notes"
        )
    if len(source_dist) == 1:
        warnings.append(
            f"INTERVIEW_SINGLE_SOURCE: All notes from '{list(source_dist.keys())[0]}'"
        )

    evidence.append(EvidenceLinkData(
        target_type="interview_structure",
        source_type="computed",
        source_id="interview:summary",
        source_detail={
            "total": len(structured),
            "sources": dict(source_dist),
            "risk_flags": risk_count,
        },
    ))

    return InterviewStructureResult(
        notes=structured,
        total_notes=len(structured),
        source_distribution=source_dist,
        topic_distribution=topic_dist,
        risk_flag_count=risk_count,
        warnings=warnings,
    ), evidence


# ── Core: Theme Extraction ───────────────────────────────


def extract_themes(
    structured_notes: list[InterviewNote],
    *,
    top_n: int = 10,
) -> tuple[ThemeExtractionResult, list[EvidenceLinkData]]:
    """구조화된 인터뷰에서 테마를 추출한다.

    Args:
        structured_notes: 구조화된 인터뷰 노트
        top_n: 상위 N개 테마

    Returns:
        (ThemeExtractionResult, list[EvidenceLinkData])
    """
    evidence: list[EvidenceLinkData] = []
    warnings: list[str] = []

    if not structured_notes:
        return ThemeExtractionResult(
            themes=[],
            total_themes=0,
            top_themes=[],
            risk_themes=[],
            warnings=["THEME_EMPTY: No notes for theme extraction"],
        ), evidence

    # 테마별 빈도/출처/감정 집계
    theme_data: dict[str, dict[str, Any]] = {}

    for note in structured_notes:
        for theme in note.themes:
            if theme not in theme_data:
                theme_data[theme] = {
                    "freq": 0,
                    "sources": set(),
                    "sentiments": {"positive": 0, "neutral": 0, "negative": 0},
                    "risks": set(),
                }
            theme_data[theme]["freq"] += 1
            theme_data[theme]["sources"].add(note.source)
            theme_data[theme]["sentiments"][note.sentiment] += 1
            for flag in note.risk_flags:
                theme_data[theme]["risks"].add(flag)

    # ThemeItem 생성 + 정렬
    items: list[ThemeItem] = []
    for theme, data in theme_data.items():
        items.append(ThemeItem(
            theme=theme,
            frequency=data["freq"],
            sources=sorted(data["sources"]),
            sentiment_distribution=dict(data["sentiments"]),
            related_risks=sorted(data["risks"]),
        ))

    items.sort(key=lambda x: x.frequency, reverse=True)
    top_themes = [t.theme for t in items[:top_n]]
    risk_themes = [t.theme for t in items if t.related_risks]

    evidence.append(EvidenceLinkData(
        target_type="theme_extraction",
        source_type="computed",
        source_id="themes:summary",
        source_detail={
            "total_themes": len(items),
            "top_themes": top_themes[:5],
        },
    ))

    return ThemeExtractionResult(
        themes=items,
        total_themes=len(items),
        top_themes=top_themes,
        risk_themes=risk_themes,
        warnings=warnings,
    ), evidence


# ── Helpers ──────────────────────────────────────────────


def _classify_topic(text: str) -> str:
    """텍스트에서 토픽 자동 분류."""
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for topic, keywords in _TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text_lower)
        if score > 0:
            scores[topic] = score

    if scores:
        return max(scores, key=scores.get)  # type: ignore[arg-type]
    return "general"


def _detect_risk_flags(text: str) -> list[str]:
    """텍스트에서 리스크 키워드 감지."""
    text_lower = text.lower()
    return sorted(kw for kw in _RISK_KEYWORDS if kw.lower() in text_lower)


def _extract_themes_from_text(text: str) -> list[str]:
    """텍스트에서 매칭되는 토픽 키워드 기반 테마 추출."""
    text_lower = text.lower()
    themes: list[str] = []

    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            themes.append(topic)

    return themes if themes else ["general"]


def _analyze_sentiment(text: str) -> str:
    """키워드 기반 감정 분석 (positive/neutral/negative)."""
    text_lower = text.lower()
    pos = sum(1 for kw in _SENTIMENT_POSITIVE if kw.lower() in text_lower)
    neg = sum(1 for kw in _SENTIMENT_NEGATIVE if kw.lower() in text_lower)

    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"
