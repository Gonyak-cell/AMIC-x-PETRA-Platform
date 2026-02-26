#!/usr/bin/env python3
"""지시 로그 분석: logs/prompts.jsonl → knowledge/prompt-patterns.md 생성.

사용법:
    python analyze_prompts.py [--days N] [--session SESSION_ID] [--project-dir PATH]
"""
import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ── 재지시 감지 키워드 ────────────────────────────────────
REWORK_INDICATORS = [
    "여전히", "아직", "안됨", "안돼", "다시", "또",
    "왜", "아니", "별로", "문제", "되돌려", "취소",
    "수정 안", "동일한 문제", "still", "again", "not working", "revert",
]

# ── 시스템 프리픽스 (neutral 판별용) ──────────────────────
_SYSTEM_PREFIXES = ("<task-notification>", "<ide_opened_file>", "<ide_selection>")


def _parse_ts_naive(ts_str: str) -> datetime:
    """타임스탬프를 naive datetime으로 파싱 (timezone 제거)."""
    ts = datetime.fromisoformat(ts_str)
    return ts.replace(tzinfo=None)


def _strip_system_prefix(prompt: str) -> str:
    """시스템 프리픽스를 제거하고 실제 사용자 지시 텍스트만 반환."""
    text = prompt
    # XML-like 태그 전체 제거
    text = re.sub(r"<[^>]+>", "", text).strip()
    return text


# ── 기존 함수 ─────────────────────────────────────────────


def load_prompts(log_path: Path, days: int, session_id: str | None = None) -> list[dict]:
    """JSONL 파일에서 최근 N일치 프롬프트 로드."""
    if not log_path.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    entries = []

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = _parse_ts_naive(entry.get("ts", "2000-01-01"))
                # Strip timezone info to avoid naive vs aware comparison
                if ts >= cutoff:
                    if session_id and entry.get("session_id") != session_id:
                        continue
                    entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    return entries


def load_errors(log_path: Path, days: int) -> list[dict]:
    """errors.jsonl에서 최근 N일치 에러 로드."""
    if not log_path.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    entries = []

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = _parse_ts_naive(entry.get("ts", "2000-01-01"))
                if ts >= cutoff:
                    entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    return entries


def extract_keywords(prompt: str) -> list[str]:
    """프롬프트에서 주요 키워드 추출 (불용어 제거)."""
    stopwords_ko = {"해줘", "해", "좀", "하고", "하는", "하면", "해주세요", "합니다", "이", "그",
                    "를", "을", "에", "의", "가", "은", "는", "도", "나", "로", "으로", "에서",
                    "와", "과", "하여", "한", "된", "되는", "것", "수", "있", "없", "이런",
                    "저런", "어떻게", "왜", "뭐", "좀", "다", "더", "잘"}
    stopwords_en = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                    "have", "has", "had", "do", "does", "did", "will", "would", "could",
                    "should", "may", "might", "can", "to", "of", "in", "for", "on", "with",
                    "at", "by", "from", "it", "this", "that", "and", "or", "but", "not",
                    "if", "then", "so", "me", "my", "i", "you", "your", "we", "our", "please"}

    # 한글+영문 단어 추출
    words = re.findall(r"[가-힣]{2,}|[a-zA-Z]{3,}", prompt)
    keywords = [w for w in words if w.lower() not in stopwords_ko and w.lower() not in stopwords_en]
    return keywords[:10]  # 최대 10개


def analyze_session_flows(entries: list[dict]) -> list[dict]:
    """세션 내 지시 카테고리 흐름 분석."""
    sessions: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        sid = entry.get("session_id", "unknown")
        cat = entry.get("category", "other")
        sessions[sid].append(cat)

    # 연속 패턴 추출
    flow_counter: Counter = Counter()
    for sid, cats in sessions.items():
        for i in range(len(cats) - 1):
            pair = f"{cats[i]} → {cats[i+1]}"
            flow_counter[pair] += 1

    # 문제 패턴 감지
    problem_patterns = []
    for flow, count in flow_counter.most_common():
        if count >= 2:
            suggestion = ""
            if "implement → fix" in flow:
                suggestion = "구현 후 수정이 빈번합니다. 구현 전 설계 검토(플랜 모드) 활용을 권장합니다."
            elif "fix → fix" in flow:
                suggestion = "연속 수정 패턴입니다. 첫 지시에 에러 메시지 전체와 재현 단계를 포함하면 한 번에 해결될 확률이 높아집니다."
            elif "review → fix" in flow:
                suggestion = "리뷰 후 수정 패턴. 리뷰와 자동 수정을 동시에 요청하면 효율적입니다."
            elif "implement → implement" in flow:
                suggestion = "연속 구현 지시입니다. 한 지시에 여러 기능을 묶어 요청하면 컨텍스트 전환 비용을 줄일 수 있습니다."

            problem_patterns.append({
                "flow": flow,
                "count": count,
                "suggestion": suggestion,
            })

    return problem_patterns


def generate_efficiency_suggestions(entries: list[dict], flows: list[dict]) -> list[str]:
    """효율성 개선 제안 생성."""
    suggestions = []

    # 1. 평균 프롬프트 길이 분석
    lengths = [e.get("prompt_len", 0) for e in entries]
    avg_len = sum(lengths) / len(lengths) if lengths else 0

    if avg_len < 30:
        suggestions.append(
            "평균 지시 길이가 짧습니다 ({:.0f}자). 구체적인 맥락(파일 경로, 에러 메시지, 기대 동작)을 "
            "포함하면 Claude가 더 정확하게 작업할 수 있습니다.".format(avg_len)
        )
    elif avg_len > 300:
        suggestions.append(
            "평균 지시 길이가 깁니다 ({:.0f}자). 핵심 요구사항을 먼저 제시하고 세부사항은 "
            "번호 목록으로 정리하면 처리 효율이 높아집니다.".format(avg_len)
        )

    # 2. 카테고리 분포 분석
    cats = Counter(e.get("category", "other") for e in entries)
    total = sum(cats.values())
    fix_ratio = cats.get("fix", 0) / total if total > 0 else 0

    if fix_ratio > 0.4:
        suggestions.append(
            f"전체 지시의 {fix_ratio:.0%}가 수정(fix) 요청입니다. TDD 방식이나 구현 전 "
            "플랜 모드를 활용하면 버그 발생을 줄일 수 있습니다."
        )

    # 3. 세션 흐름 패턴에서 제안
    for flow in flows:
        if flow["suggestion"]:
            suggestions.append(flow["suggestion"])

    # 4. 키워드 반복 분석
    all_keywords = []
    for e in entries:
        all_keywords.extend(extract_keywords(e.get("prompt", "")))
    keyword_freq = Counter(all_keywords)
    top_keywords = keyword_freq.most_common(5)

    if top_keywords:
        kw_str = ", ".join(f"'{k}' ({v}회)" for k, v in top_keywords)
        suggestions.append(
            f"자주 언급되는 키워드: {kw_str}. "
            "반복 작업이 있다면 슬래시 커맨드(/command)나 스킬로 자동화를 고려해보세요."
        )

    return suggestions


# ── 최적 프롬프트 분석 함수 (신규) ────────────────────────


def classify_prompt_outcomes(
    prompts: list[dict],
    errors: list[dict],
) -> list[dict]:
    """각 프롬프트에 outcome 라벨을 부여한다.

    outcome: 'success' | 'rework' | 'error_trigger' | 'neutral'
    """
    # 에러를 세션별 + 시간순으로 인덱싱
    errors_by_session: dict[str, list[datetime]] = defaultdict(list)
    for err in errors:
        sid = err.get("session_id", "")
        try:
            ts = _parse_ts_naive(err.get("ts", "2000-01-01"))
            errors_by_session[sid].append(ts)
        except (ValueError, TypeError):
            continue

    for sid in errors_by_session:
        errors_by_session[sid].sort()

    # 프롬프트를 세션별로 그룹핑 (순서 보존)
    session_prompts: dict[str, list[dict]] = defaultdict(list)
    for p in prompts:
        sid = p.get("session_id", "unknown")
        session_prompts[sid].append(p)

    # 각 프롬프트에 outcome 부여
    result = []
    for sid, session_entries in session_prompts.items():
        # 시간순 정렬
        session_entries.sort(key=lambda x: x.get("ts", ""))

        for idx, entry in enumerate(session_entries):
            prompt_text = entry.get("prompt", "")
            prompt_len = entry.get("prompt_len", 0)
            category = entry.get("category", "other")

            # 1. neutral: 시스템 프리픽스 또는 너무 짧은 응답
            stripped = _strip_system_prefix(prompt_text)
            if (prompt_text.startswith(_SYSTEM_PREFIXES)
                    and len(stripped) < 10):
                entry["outcome"] = "neutral"
                result.append(entry)
                continue

            if prompt_len <= 5:
                entry["outcome"] = "neutral"
                result.append(entry)
                continue

            # 2. error_trigger: 이 프롬프트 이후 10분 내 에러 3건 이상 집중 발생
            try:
                prompt_ts = _parse_ts_naive(entry.get("ts", "2000-01-01"))
            except (ValueError, TypeError):
                entry["outcome"] = "neutral"
                result.append(entry)
                continue

            error_window = timedelta(minutes=10)
            session_errors = errors_by_session.get(sid, [])
            errors_in_window = sum(
                1 for err_ts in session_errors
                if prompt_ts < err_ts <= prompt_ts + error_window
            )
            has_error_after = errors_in_window >= 3

            # 3. rework: 다음 사용자 프롬프트가 fix이거나 재지시 키워드 포함
            is_rework = False
            if category in ("implement", "other", "review"):
                # 다음 실제 사용자 프롬프트 찾기 (시스템 프리픽스 건너뛰기)
                next_prompt = None
                for j in range(idx + 1, len(session_entries)):
                    np = session_entries[j]
                    np_text = np.get("prompt", "")
                    np_stripped = _strip_system_prefix(np_text)
                    if np.get("prompt_len", 0) > 5 and len(np_stripped) >= 10:
                        next_prompt = np
                        break

                if next_prompt:
                    next_cat = next_prompt.get("category", "other")
                    next_text = next_prompt.get("prompt", "").lower()

                    # 다음이 fix 카테고리
                    if next_cat == "fix":
                        is_rework = True
                    # 재지시 키워드 포함
                    elif any(kw in next_text for kw in REWORK_INDICATORS):
                        is_rework = True

            # 4. outcome 결정 (우선순위: rework > error_trigger > success)
            if is_rework:
                entry["outcome"] = "rework"
            elif has_error_after:
                entry["outcome"] = "error_trigger"
            elif category == "implement":
                entry["outcome"] = "success"
            else:
                entry["outcome"] = "neutral"

            result.append(entry)

    return result


def _has_file_path(prompt: str) -> bool:
    """프롬프트에 파일 경로가 포함되어 있는지."""
    return bool(re.search(r"[/\\][\w\-.]+\.\w{1,5}", prompt))


def _has_error_message(prompt: str) -> bool:
    """프롬프트에 에러 메시지/코드가 포함되어 있는지."""
    return bool(re.search(
        r"error|에러|오류|500|404|422|401|failed|traceback|exception|TypeError|KeyError",
        prompt, re.IGNORECASE,
    ))


def _has_structure(prompt: str) -> bool:
    """프롬프트가 구조화되어 있는지 (줄바꿈, 번호 목록 등)."""
    has_newlines = "\n" in prompt and prompt.count("\n") >= 2
    has_numbers = bool(re.search(r"^\s*\d+[\.\)]\s", prompt, re.MULTILINE))
    has_bullets = bool(re.search(r"^\s*[-*]\s", prompt, re.MULTILINE))
    return has_newlines or has_numbers or has_bullets


def _has_expected_behavior(prompt: str) -> bool:
    """프롬프트에 기대 동작이 명시되어 있는지."""
    return bool(re.search(
        r"기대|expected|결과|되어야|해야|should|want|원하|처럼|동일하게|같이|같은",
        prompt, re.IGNORECASE,
    ))


def _pct(count: int, total: int) -> str:
    """비율 문자열."""
    return f"{count / total * 100:.0f}" if total > 0 else "0"


def analyze_optimal_patterns(classified: list[dict]) -> dict:
    """성공/실패 프롬프트의 특성을 비교 분석한다."""
    success = [p for p in classified if p.get("outcome") == "success"]
    rework = [p for p in classified if p.get("outcome") == "rework"]
    error_trigger = [p for p in classified if p.get("outcome") == "error_trigger"]
    non_neutral = [p for p in classified if p.get("outcome") != "neutral"]

    total = len(non_neutral)
    if total == 0:
        return {"insufficient_data": True}

    # 통계 계산 헬퍼
    def _stats(group: list[dict]) -> dict:
        if not group:
            return {"count": 0, "avg_len": 0, "file_pct": 0, "error_pct": 0,
                    "struct_pct": 0, "expected_pct": 0}
        n = len(group)
        return {
            "count": n,
            "avg_len": sum(p.get("prompt_len", 0) for p in group) / n,
            "file_pct": sum(1 for p in group if _has_file_path(p.get("prompt", ""))) / n * 100,
            "error_pct": sum(1 for p in group if _has_error_message(p.get("prompt", ""))) / n * 100,
            "struct_pct": sum(1 for p in group if _has_structure(p.get("prompt", ""))) / n * 100,
            "expected_pct": sum(1 for p in group if _has_expected_behavior(p.get("prompt", ""))) / n * 100,
        }

    success_stats = _stats(success)
    rework_stats = _stats(rework)

    # 최적 프롬프트 규칙 도출 (데이터 기반)
    optimal_traits = []
    anti_patterns = []

    # 규칙 1: 길이 비교
    if success_stats["count"] > 0 and rework_stats["count"] > 0:
        s_len = success_stats["avg_len"]
        r_len = rework_stats["avg_len"]
        if s_len > r_len * 1.3:
            optimal_traits.append({
                "rule": "충분한 맥락 제공",
                "detail": f"성공 프롬프트 평균 {s_len:.0f}자 vs 재수정 {r_len:.0f}자. "
                          "충분한 배경/요구사항을 한 번에 전달하면 재수정을 줄일 수 있습니다.",
            })
        elif r_len > s_len * 1.3:
            optimal_traits.append({
                "rule": "핵심 우선 전달",
                "detail": f"재수정 프롬프트가 오히려 길었습니다 ({r_len:.0f}자 vs {s_len:.0f}자). "
                          "길이보다 구조와 명확성이 중요합니다.",
            })

    # 규칙 2: 파일 경로 포함
    if success_stats["file_pct"] > rework_stats["file_pct"] + 15:
        optimal_traits.append({
            "rule": "파일 경로 명시",
            "detail": f"성공 {success_stats['file_pct']:.0f}% vs 재수정 {rework_stats['file_pct']:.0f}%가 "
                      "파일 경로 포함. 수정 대상 파일을 직접 지정하면 정확도가 높아집니다.",
        })

    # 규칙 3: 에러 메시지 포함
    if success_stats["error_pct"] > rework_stats["error_pct"] + 10:
        optimal_traits.append({
            "rule": "에러 메시지 첨부",
            "detail": f"성공 {success_stats['error_pct']:.0f}% vs 재수정 {rework_stats['error_pct']:.0f}%가 "
                      "에러 메시지 포함. 에러 전문을 첨부하면 근본 원인을 빠르게 파악합니다.",
        })

    # 규칙 4: 구조화
    if success_stats["struct_pct"] > rework_stats["struct_pct"] + 10:
        optimal_traits.append({
            "rule": "구조화된 지시",
            "detail": f"성공 {success_stats['struct_pct']:.0f}% vs 재수정 {rework_stats['struct_pct']:.0f}%가 "
                      "줄바꿈/번호 목록 사용. 복잡한 요구사항은 번호 목록으로 정리하세요.",
        })

    # 규칙 5: 기대 동작 명시
    if success_stats["expected_pct"] > rework_stats["expected_pct"] + 10:
        optimal_traits.append({
            "rule": "기대 동작 명시",
            "detail": f"성공 {success_stats['expected_pct']:.0f}% vs 재수정 {rework_stats['expected_pct']:.0f}%가 "
                      "기대 결과 포함. '~되어야 한다', '~처럼 동작' 등으로 완료 기준을 명시하세요.",
        })

    # 데이터에서 규칙이 도출되지 않은 경우 기본 규칙 추가
    if not optimal_traits:
        optimal_traits.append({
            "rule": "데이터 기반 규칙 도출 중",
            "detail": "성공/재수정 간 통계적 차이가 뚜렷하지 않습니다. 더 많은 데이터가 쌓이면 "
                      "구체적 규칙이 도출됩니다.",
        })

    # 안티패턴: 재수정 프롬프트의 공통 특성
    if rework_stats["count"] >= 3:
        if rework_stats["file_pct"] < 20:
            anti_patterns.append({
                "pattern": "파일 경로 미지정",
                "count": rework_stats["count"],
                "detail": f"재수정 프롬프트 중 {100 - rework_stats['file_pct']:.0f}%가 대상 파일을 명시하지 않음",
            })
        if rework_stats["struct_pct"] < 20:
            anti_patterns.append({
                "pattern": "비구조적 한 줄 지시",
                "count": rework_stats["count"],
                "detail": f"재수정 프롬프트 중 {100 - rework_stats['struct_pct']:.0f}%가 구조화 없는 단순 텍스트",
            })

    # Before/After 예시 추출
    before_after = _extract_before_after(classified)

    return {
        "insufficient_data": (len(success) + len(rework)) < 10,
        "total": total,
        "success_stats": success_stats,
        "rework_stats": rework_stats,
        "error_trigger_count": len(error_trigger),
        "optimal_traits": optimal_traits,
        "anti_patterns": anti_patterns,
        "before_after": before_after,
    }


def _extract_before_after(classified: list[dict], max_examples: int = 3) -> list[dict]:
    """같은 세션에서 rework 프롬프트와 성공 프롬프트를 대조한다.

    두 가지 전략:
    A. 같은 세션 내 rework 직후 success 프롬프트 대조
    B. rework 그룹 vs success 그룹의 대표 사례 대조
    """
    # 세션별로 그룹핑
    sessions: dict[str, list[dict]] = defaultdict(list)
    for p in classified:
        sid = p.get("session_id", "unknown")
        sessions[sid].append(p)

    examples = []

    # 전략 A: 같은 세션에서 rework → (non-rework 실제 프롬프트) 대조
    for sid, entries in sessions.items():
        entries.sort(key=lambda x: x.get("ts", ""))
        for i in range(len(entries) - 1):
            if len(examples) >= max_examples:
                break
            curr = entries[i]

            if curr.get("outcome") != "rework":
                continue

            # rework 이후 success/neutral 프롬프트 찾기 (재지시 키워드 없는 것)
            after_entry = None
            for j in range(i + 1, len(entries)):
                nxt = entries[j]
                nxt_text = nxt.get("prompt", "").lower()
                nxt_outcome = nxt.get("outcome", "")

                # 불만/재지시 프롬프트는 "After"에 부적절 → skip
                if any(kw in nxt_text for kw in REWORK_INDICATORS):
                    continue
                if nxt_outcome == "rework":
                    continue
                if nxt.get("prompt_len", 0) <= 10:
                    continue

                after_entry = nxt
                break

            if not after_entry:
                continue

            before_text = _strip_system_prefix(curr.get("prompt", ""))
            after_text = _strip_system_prefix(after_entry.get("prompt", ""))

            if len(before_text) < 10 or len(after_text) < 10:
                continue

            # 개선 포인트 자동 감지
            improvements = []
            if after_entry.get("prompt_len", 0) > curr.get("prompt_len", 0) * 1.3:
                improvements.append("더 상세한 맥락 추가")
            if _has_file_path(after_text) and not _has_file_path(before_text):
                improvements.append("파일 경로 명시")
            if _has_expected_behavior(after_text) and not _has_expected_behavior(before_text):
                improvements.append("기대 동작 명시")
            if _has_structure(after_text) and not _has_structure(before_text):
                improvements.append("구조화(번호/줄바꿈)")
            if not improvements:
                improvements.append("더 구체적인 요구사항 기술")

            examples.append({
                "before": before_text[:200],
                "after": after_text[:200],
                "improvement": ", ".join(improvements),
            })

        if len(examples) >= max_examples:
            break

    # 전략 B: 예시 부족 시 rework/success 그룹 대표 사례 대조
    if len(examples) < max_examples:
        rework_prompts = [p for p in classified if p.get("outcome") == "rework"]
        success_prompts = [p for p in classified if p.get("outcome") == "success"]

        # 가장 짧은 rework vs 가장 긴 success
        rework_prompts.sort(key=lambda x: x.get("prompt_len", 0))
        success_prompts.sort(key=lambda x: x.get("prompt_len", 0), reverse=True)

        for rw, sc in zip(rework_prompts, success_prompts):
            if len(examples) >= max_examples:
                break
            before_text = _strip_system_prefix(rw.get("prompt", ""))
            after_text = _strip_system_prefix(sc.get("prompt", ""))
            if len(before_text) < 10 or len(after_text) < 10:
                continue

            improvements = []
            if sc.get("prompt_len", 0) > rw.get("prompt_len", 0) * 1.3:
                improvements.append("더 상세한 맥락 추가")
            if _has_file_path(after_text) and not _has_file_path(before_text):
                improvements.append("파일 경로 명시")
            if _has_structure(after_text) and not _has_structure(before_text):
                improvements.append("구조화(번호/줄바꿈)")
            if not improvements:
                improvements.append("더 구체적인 요구사항 기술")

            examples.append({
                "before": before_text[:200],
                "after": after_text[:200],
                "improvement": ", ".join(improvements),
            })

    return examples


def generate_optimal_prompt_section(analysis: dict) -> str:
    """최적 프롬프트 피드백 섹션 Markdown 생성."""
    lines = ["", "## 최적 프롬프트 피드백", ""]

    if analysis.get("insufficient_data"):
        total = analysis.get("total", 0)
        s_count = analysis.get("success_stats", {}).get("count", 0)
        r_count = analysis.get("rework_stats", {}).get("count", 0)
        lines.append(
            f"분석 대상 {total}건 (성공 {s_count}, 재수정 {r_count}) — "
            "데이터가 부족하여 통계적 비교가 제한적입니다. "
            "더 많은 세션이 쌓이면 정밀 분석이 가능합니다."
        )
        lines.append("")

        # 데이터 부족해도 기본 규칙은 표시
        if analysis.get("optimal_traits"):
            lines.extend(["### 기본 작성 규칙", ""])
            for i, trait in enumerate(analysis["optimal_traits"], 1):
                lines.append(f"{i}. **{trait['rule']}** — {trait['detail']}")
            lines.append("")

        return "\n".join(lines)

    ss = analysis["success_stats"]
    rs = analysis["rework_stats"]
    et = analysis.get("error_trigger_count", 0)
    total = analysis["total"]

    # 성과 분류 요약
    lines.extend([
        "### 프롬프트 성과 분류",
        "",
        f"- 분석 대상: **{total}건** (neutral 제외)",
        f"- 성공 (한 번에 완료): **{ss['count']}건** ({_pct(ss['count'], total)}%)",
        f"- 재수정 필요: **{rs['count']}건** ({_pct(rs['count'], total)}%)",
        f"- 에러 유발: **{et}건** ({_pct(et, total)}%)",
        "",
    ])

    # 특성 비교표
    if ss["count"] > 0 and rs["count"] > 0:
        lines.extend([
            "### 성공 vs 재수정 프롬프트 특성 비교",
            "",
            "| 특성 | 성공 프롬프트 | 재수정 프롬프트 | 차이 |",
            "|------|------------|--------------|------|",
            f"| 평균 길이 | {ss['avg_len']:.0f}자 | {rs['avg_len']:.0f}자 | "
            f"{'+' if ss['avg_len'] > rs['avg_len'] else ''}{ss['avg_len'] - rs['avg_len']:.0f}자 |",
            f"| 파일 경로 포함 | {ss['file_pct']:.0f}% | {rs['file_pct']:.0f}% | "
            f"{'+' if ss['file_pct'] > rs['file_pct'] else ''}{ss['file_pct'] - rs['file_pct']:.0f}%p |",
            f"| 에러 메시지 포함 | {ss['error_pct']:.0f}% | {rs['error_pct']:.0f}% | "
            f"{'+' if ss['error_pct'] > rs['error_pct'] else ''}{ss['error_pct'] - rs['error_pct']:.0f}%p |",
            f"| 구조화 (번호/줄바꿈) | {ss['struct_pct']:.0f}% | {rs['struct_pct']:.0f}% | "
            f"{'+' if ss['struct_pct'] > rs['struct_pct'] else ''}{ss['struct_pct'] - rs['struct_pct']:.0f}%p |",
            f"| 기대 동작 명시 | {ss['expected_pct']:.0f}% | {rs['expected_pct']:.0f}% | "
            f"{'+' if ss['expected_pct'] > rs['expected_pct'] else ''}{ss['expected_pct'] - rs['expected_pct']:.0f}%p |",
            "",
        ])

    # 데이터 기반 작성 규칙
    traits = analysis.get("optimal_traits", [])
    if traits:
        lines.extend(["### 데이터 기반 작성 규칙", ""])
        for i, trait in enumerate(traits, 1):
            lines.append(f"{i}. **{trait['rule']}** — {trait['detail']}")
        lines.append("")

    # Before/After 예시
    examples = analysis.get("before_after", [])
    if examples:
        lines.extend(["### Before / After 예시", ""])
        for i, ex in enumerate(examples, 1):
            lines.extend([
                f"**예시 {i}**",
                f"- Before (재수정 발생): \"{ex['before']}\"",
                f"- After (개선된 지시): \"{ex['after']}\"",
                f"- 개선 포인트: {ex['improvement']}",
                "",
            ])

    # 안티패턴
    antis = analysis.get("anti_patterns", [])
    if antis:
        lines.extend(["### 안티패턴 (피해야 할 프롬프트 유형)", ""])
        for i, ap in enumerate(antis, 1):
            lines.append(f"{i}. **{ap['pattern']}** — {ap['detail']}")
        lines.append("")

    return "\n".join(lines)


# ── Markdown 생성 + main ──────────────────────────────────


def generate_markdown(
    entries: list[dict],
    flows: list[dict],
    suggestions: list[str],
    days: int,
    optimal_analysis: dict | None = None,
) -> str:
    """knowledge/prompt-patterns.md 생성."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cats = Counter(e.get("category", "other") for e in entries)
    total = len(entries)
    sessions = len(set(e.get("session_id", "") for e in entries))
    lengths = [e.get("prompt_len", 0) for e in entries]
    avg_len = sum(lengths) / len(lengths) if lengths else 0

    lines = [
        "# Prompt Pattern Analysis",
        f"> 기간: 최근 {days}일 | 총 {total}건 지시 | 세션 {sessions}개 | 마지막 분석: {now}",
        "",
        "## 지시 통계",
        "",
        f"- 총 지시 횟수: {total}회",
        f"- 세션 수: {sessions}개",
        f"- 평균 지시 길이: {avg_len:.0f}자",
        "",
        "## 카테고리별 분포",
        "",
        "| 카테고리 | 횟수 | 비율 |",
        "|---------|------|------|",
    ]

    for cat, count in cats.most_common():
        pct = f"{count / total * 100:.0f}%" if total > 0 else "0%"
        lines.append(f"| {cat} | {count} | {pct} |")

    lines.extend(["", "## 세션 흐름 패턴", ""])

    if flows:
        lines.extend([
            "| 패턴 | 횟수 | 의미 |",
            "|------|------|------|",
        ])
        for f in flows[:10]:
            meaning = f["suggestion"][:60] + "..." if len(f.get("suggestion", "")) > 60 else f.get("suggestion", "—")
            lines.append(f"| {f['flow']} | {f['count']} | {meaning} |")
    else:
        lines.append("흐름 패턴 데이터 부족 (세션당 2개 이상 지시 필요).")

    lines.extend(["", "## 키워드 빈도 TOP 10", ""])

    all_keywords = []
    for e in entries:
        all_keywords.extend(extract_keywords(e.get("prompt", "")))
    keyword_freq = Counter(all_keywords)

    if keyword_freq:
        lines.extend([
            "| 키워드 | 횟수 |",
            "|--------|------|",
        ])
        for kw, cnt in keyword_freq.most_common(10):
            lines.append(f"| {kw} | {cnt} |")
    else:
        lines.append("키워드 데이터 없음.")

    lines.extend(["", "## 효율성 개선 제안", ""])

    if suggestions:
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")
    else:
        lines.append("현재 특별한 개선 제안이 없습니다. 지시 패턴이 효율적입니다.")

    # 최적 프롬프트 피드백 섹션 (신규)
    if optimal_analysis:
        lines.append(generate_optimal_prompt_section(optimal_analysis))

    lines.extend([
        "",
        "---",
        f"*자동 생성: {now} | analyze_prompts.py*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="지시 로그 분석")
    parser.add_argument("--days", type=int, default=30, help="분석 기간 (일)")
    parser.add_argument("--session", type=str, default=None, help="특정 세션만 분석")
    parser.add_argument("--project-dir", type=str, default=None, help="프로젝트 루트")
    args = parser.parse_args()

    project_dir = Path(args.project_dir) if args.project_dir else Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    log_path = project_dir / "logs" / "prompts.jsonl"
    knowledge_dir = project_dir / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    print(f"지시 로그 분석 (최근 {args.days}일)...")
    entries = load_prompts(log_path, args.days, args.session)

    if not entries:
        print("지시 로그 없음.")
        md = (
            f"# Prompt Pattern Analysis\n"
            f"> 기간: 최근 {args.days}일 | 지시 0건 | "
            f"마지막 분석: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            "지시 로그가 아직 없습니다.\n"
        )
        output_path = knowledge_dir / "prompt-patterns.md"
        output_path.write_text(md, encoding="utf-8")
        return

    # 에러 로그 로드 + 성과 분류 + 최적 패턴 분석
    error_log_path = project_dir / "logs" / "errors.jsonl"
    errors = load_errors(error_log_path, args.days)
    classified = classify_prompt_outcomes(entries, errors)
    optimal_analysis = analyze_optimal_patterns(classified)

    flows = analyze_session_flows(entries)
    suggestions = generate_efficiency_suggestions(entries, flows)
    md = generate_markdown(entries, flows, suggestions, args.days, optimal_analysis)

    output_path = knowledge_dir / "prompt-patterns.md"
    output_path.write_text(md, encoding="utf-8")
    print(f"생성 완료: {output_path}")

    # 요약 출력
    cats = Counter(e.get("category", "other") for e in entries)
    print(f"\n=== 분석 요약 ===")
    print(f"총 지시: {len(entries)}건")
    print(f"세션 수: {len(set(e.get('session_id', '') for e in entries))}개")
    print(f"카테고리 분포: {dict(cats.most_common(5))}")

    # 최적 프롬프트 요약
    if optimal_analysis and not optimal_analysis.get("insufficient_data"):
        ss = optimal_analysis["success_stats"]
        rs = optimal_analysis["rework_stats"]
        print(f"\n=== 프롬프트 성과 ===")
        print(f"성공: {ss['count']}건 | 재수정: {rs['count']}건 | 에러유발: {optimal_analysis.get('error_trigger_count', 0)}건")
        if optimal_analysis.get("optimal_traits"):
            print(f"도출된 작성 규칙: {len(optimal_analysis['optimal_traits'])}개")

    if suggestions:
        print(f"\n개선 제안 {len(suggestions)}개:")
        for s in suggestions[:3]:
            print(f"  - {s[:100]}")


if __name__ == "__main__":
    main()
