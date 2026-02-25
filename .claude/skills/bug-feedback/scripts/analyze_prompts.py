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
                ts = datetime.fromisoformat(entry.get("ts", "2000-01-01"))
                if ts >= cutoff:
                    if session_id and entry.get("session_id") != session_id:
                        continue
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


def generate_markdown(
    entries: list[dict],
    flows: list[dict],
    suggestions: list[str],
    days: int,
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
        md = f"# Prompt Pattern Analysis\n> 기간: 최근 {args.days}일 | 지시 0건 | 마지막 분석: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n지시 로그가 아직 없습니다.\n"
        output_path = knowledge_dir / "prompt-patterns.md"
        output_path.write_text(md, encoding="utf-8")
        return

    flows = analyze_session_flows(entries)
    suggestions = generate_efficiency_suggestions(entries, flows)
    md = generate_markdown(entries, flows, suggestions, args.days)

    output_path = knowledge_dir / "prompt-patterns.md"
    output_path.write_text(md, encoding="utf-8")
    print(f"생성 완료: {output_path}")

    # 요약 출력
    cats = Counter(e.get("category", "other") for e in entries)
    print(f"\n=== 분석 요약 ===")
    print(f"총 지시: {len(entries)}건")
    print(f"세션 수: {len(set(e.get('session_id', '') for e in entries))}개")
    print(f"카테고리 분포: {dict(cats.most_common(5))}")

    if suggestions:
        print(f"\n개선 제안 {len(suggestions)}개:")
        for s in suggestions[:3]:
            print(f"  - {s[:100]}")


if __name__ == "__main__":
    main()
