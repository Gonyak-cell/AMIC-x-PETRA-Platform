"""M&A 뉴스 멀티라벨 섹션 분류기

kiwipiepy 형태소 분석 기반으로 기사를 ma / governance / fund 3개 섹션으로 분류한다.
동의어 치환 → 형태소 추출 → 키워드 점수 → 동시출현 보너스/드롭 → 임계값 판정.

법률/실무 용어(자본시장법 기반):
- M&A: 주식매매계약, 포괄적 교환, 경영권 양수도, 분할합병, 공개매수
- 거버넌스: 주주행동주의, 다중대표소송, 위임장 대결, 집중투표제
- 펀드: 사모펀드, 무한책임사원, 유한책임사원, 바이아웃, 블라인드펀드

사용법:
    classifier = MASectionClassifier()
    result = classifier.classify("제목", "본문 또는 lead_text")
    # result.primary   -> "ma" | "governance" | "fund" | None
    # result.labels    -> ["ma", "governance"]
    # result.scores    -> {"ma": 15, "governance": 12, "fund": 3}
    # result.detail    -> {...}  분류 근거 JSON
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "ma_section_rules.json"

# kiwipiepy lazy init (서버 시작 시 1회만 로드)
_kiwi_instance = None


def _get_kiwi():
    """kiwipiepy Kiwi 인스턴스를 lazy-init한다."""
    global _kiwi_instance
    if _kiwi_instance is None:
        try:
            from kiwipiepy import Kiwi

            _kiwi_instance = Kiwi()
            logger.info("kiwipiepy 형태소 분석기 초기화 완료")
        except ImportError:
            logger.warning("kiwipiepy 미설치 — 형태소 분석 없이 exact match로 폴백")
    return _kiwi_instance


@dataclass(frozen=True)
class ClassifyResult:
    """섹션 분류 결과."""

    primary: str | None
    labels: list[str]
    scores: dict[str, float]
    detail: dict


def _load_rules() -> dict:
    if not _RULES_PATH.exists():
        logger.warning("ma_section_rules.json 미발견: %s", _RULES_PATH)
        return {}
    with open(_RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


_RULES: dict = _load_rules()

# 공백 정규화
_MULTI_SPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """공백 정규화."""
    return _MULTI_SPACE.sub(" ", text).strip()


def _extract_nouns(text: str) -> list[str]:
    """kiwipiepy로 명사(NNG, NNP, NNB)를 추출한다.

    kiwipiepy 미설치 시 공백 분리 폴백.
    """
    kiwi = _get_kiwi()
    if kiwi is None:
        return text.split()
    tokens = kiwi.tokenize(text)
    # 명사류(NNG 일반명사, NNP 고유명사, NNB 의존명사) + 외국어(SL) 추출
    nouns: list[str] = []
    for token in tokens:
        if token.tag in ("NNG", "NNP", "NNB", "SL", "SH"):
            nouns.append(token.form)
    return nouns


class MASectionClassifier:
    """규칙 기반 멀티라벨 섹션 분류기 (kiwipiepy 형태소 분석 통합)."""

    def __init__(self, rules: dict | None = None) -> None:
        self.rules = rules or _RULES
        self.title_weight: int = self.rules.get("title_weight", 3)
        self.body_weight: int = self.rules.get("body_weight", 1)
        self.threshold: int = self.rules.get("threshold", 10)
        self.cooccurrence_window: int = self.rules.get("cooccurrence_window", 5)
        self.synonyms: dict[str, list[str]] = self.rules.get("synonyms", {})
        self.context_synonyms: dict[str, dict] = self.rules.get("context_synonyms", {})
        self.sections: dict[str, dict] = self.rules.get("sections", {})
        self.version: str = self.rules.get("version", "unknown")

        # 긴 변형어 우선 치환을 위한 정렬된 (variant, canonical) 쌍
        self._synonym_pairs: list[tuple[str, str]] = []
        for canonical, variants in self.synonyms.items():
            for variant in variants:
                self._synonym_pairs.append((variant, canonical))
        # 긴 패턴 우선 (SPA보다 "주식양수도계약"이 먼저)
        self._synonym_pairs.sort(key=lambda x: len(x[0]), reverse=True)

    # ── 동의어 치환 ──────────────────────────────────

    def _apply_synonyms(self, text: str) -> str:
        """일반 동의어 치환 (긴 패턴 우선)."""
        for variant, canonical in self._synonym_pairs:
            if variant in text:
                text = text.replace(variant, canonical)
        return text

    def _apply_context_synonyms(self, text: str, full_text: str) -> str:
        """문맥 조건부 동의어 치환 (GP/LP/운용사 등)."""
        for token, rule in self.context_synonyms.items():
            if token not in text:
                continue
            triggers = rule.get("trigger_context", [])
            if any(t in full_text for t in triggers):
                text = text.replace(token, rule["maps_to"])
        return text

    def _preprocess(self, title: str, body: str) -> tuple[str, str]:
        """전처리: 동의어 치환 적용."""
        full_text = f"{title} {body}"
        title = _normalize(self._apply_synonyms(title))
        body = _normalize(self._apply_synonyms(body))
        title = self._apply_context_synonyms(title, full_text)
        body = self._apply_context_synonyms(body, full_text)
        return title, body

    # ── 키워드 점수 계산 ─────────────────────────────

    def _score_keywords(
        self, text: str, core_keywords: list[str], support_keywords: list[str], cfg: dict
    ) -> tuple[float, list[str], list[str]]:
        """텍스트에서 키워드 출현 빈도 × 배점으로 점수를 계산한다.

        동일 키워드가 여러 번 출현하면 그만큼 점수가 누적된다.
        예: 핵심어 2회 출현 → 5×2 = 10점.
        """
        core_score = cfg.get("core_score", 5)
        support_score = cfg.get("support_score", 2)
        score = 0.0
        core_hits: list[str] = []
        support_hits: list[str] = []
        for kw in core_keywords:
            count = text.count(kw)
            if count > 0:
                score += core_score * count
                core_hits.append(kw)
        for kw in support_keywords:
            count = text.count(kw)
            if count > 0:
                score += support_score * count
                support_hits.append(kw)
        return score, core_hits, support_hits

    # ── 동시출현 / 드롭 ─────────────────────────────

    def _check_cooccurrence(self, text: str, rules: list[dict]) -> float:
        """동시출현 보너스를 계산한다 (±N어절 윈도우)."""
        words = text.split()
        bonus = 0.0
        for rule in rules:
            anchor = rule.get("anchor", "")
            contexts = rule.get("context", [])
            rule_bonus = rule.get("bonus", 0)
            anchor_positions = [i for i, w in enumerate(words) if anchor in w]
            if not anchor_positions:
                continue
            for pos in anchor_positions:
                window_start = max(0, pos - self.cooccurrence_window)
                window_end = min(len(words), pos + self.cooccurrence_window + 1)
                window_text = " ".join(words[window_start:window_end])
                if any(ctx in window_text for ctx in contexts):
                    bonus += rule_bonus
                    break
        return bonus

    def _check_drop(self, text: str, rules: list[dict]) -> bool:
        """드롭 규칙 충족 시 True."""
        words = text.split()
        for rule in rules:
            anchor = rule.get("anchor", "")
            contexts = rule.get("context", [])
            if anchor not in text:
                continue
            if not contexts:
                return True
            anchor_positions = [i for i, w in enumerate(words) if anchor in w]
            for pos in anchor_positions:
                window_start = max(0, pos - self.cooccurrence_window)
                window_end = min(len(words), pos + self.cooccurrence_window + 1)
                window_text = " ".join(words[window_start:window_end])
                if any(ctx in window_text for ctx in contexts):
                    return True
        return False

    def _check_global_drop(self, body: str, cfg: dict) -> bool:
        """글로벌 드롭: body에 특정 키워드 출현 시 해당 섹션 0점."""
        global_drop = cfg.get("global_drop")
        if not global_drop:
            return False
        keywords = global_drop.get("keywords", [])
        return any(kw in body for kw in keywords)

    # ── 분류 메인 ────────────────────────────────────

    def classify(self, title: str, body: str | None = None) -> ClassifyResult:
        """기사를 3개 섹션으로 멀티라벨 분류한다.

        파이프라인:
        1. 동의어 치환 (SPA → 주식매매계약, PEF → 사모펀드 등)
        2. 키워드 점수 계산 (제목 3배, 본문 1배)
        3. 동시출현 보너스 (국민연금+스튜어드십 → 거버넌스 +3)
        4. 드롭 규칙 (국민연금+단순투자 → 거버넌스 0점)
        5. 임계값 판정 (≥10점 → 해당 섹션 태그)

        Args:
            title: 기사 제목
            body: 기사 본문 또는 lead_text (없으면 빈 문자열)

        Returns:
            ClassifyResult
        """
        body = body or ""
        title_p, body_p = self._preprocess(title, body)
        combined = f"{title_p} {body_p}"

        scores: dict[str, float] = {}
        detail: dict[str, dict] = {}
        fallback = not body

        for section_key, cfg in self.sections.items():
            core_kw = cfg.get("core_keywords", [])
            support_kw = cfg.get("support_keywords", [])

            # 제목 점수 (3배 가중치)
            t_score, t_core, t_support = self._score_keywords(title_p, core_kw, support_kw, cfg)
            # 본문 점수 (1배)
            b_score, b_core, b_support = self._score_keywords(body_p, core_kw, support_kw, cfg)

            raw_score = (t_score * self.title_weight) + (b_score * self.body_weight)

            # 동시출현 보너스
            cooc_bonus = self._check_cooccurrence(combined, cfg.get("cooccurrence_bonus", []))
            raw_score += cooc_bonus

            # 드롭 규칙 (local → global 순서)
            dropped = self._check_drop(combined, cfg.get("drop_rules", []))
            if not dropped:
                dropped = self._check_global_drop(body_p or title_p, cfg)

            final_score = 0.0 if dropped else raw_score
            scores[section_key] = final_score

            detail[section_key] = {
                "title_hits": {"core": t_core, "support": t_support},
                "body_hits": {"core": b_core, "support": b_support},
                "title_score": t_score * self.title_weight,
                "body_score": b_score * self.body_weight,
                "cooccurrence_bonus": cooc_bonus,
                "dropped": dropped,
                "final_score": final_score,
            }

        # 임계값 판정
        labels = [k for k, v in scores.items() if v >= self.threshold]

        # primary 결정: 최고점 → 제목 히트 수 → ma > governance > fund
        priority_order = list(self.sections.keys())
        primary: str | None = None
        if labels:

            def _sort_key(label: str) -> tuple[float, int, int]:
                s = scores[label]
                t_hits = len(detail[label]["title_hits"]["core"]) + len(detail[label]["title_hits"]["support"])
                order = priority_order.index(label) if label in priority_order else 99
                return (-s, -t_hits, order)

            labels_sorted = sorted(labels, key=_sort_key)
            primary = labels_sorted[0]

        full_detail = {
            "sections": detail,
            "threshold": self.threshold,
            "fallback": fallback,
            "version": self.version,
        }

        return ClassifyResult(
            primary=primary,
            labels=sorted(labels),
            scores=scores,
            detail=full_detail,
        )
