#!/usr/bin/env python3
"""에러 로그 분석: logs/errors.jsonl → knowledge/bug-patterns.md 생성.

사용법:
    python analyze_bugs.py [--days N] [--project-dir PATH]
"""
import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

# 공유 유틸리티 import
sys.path.insert(0, str(Path(__file__).resolve().parent / ".." / ".." / "_shared"))
from text_utils import normalize_snippet, parse_timestamp, KST  # noqa: E402


def load_errors(log_path: Path, days: int) -> list[dict]:
    """JSONL 파일에서 최근 N일치 에러 로드."""
    if not log_path.exists():
        return []

    cutoff = datetime.now(KST) - timedelta(days=days)
    entries = []

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = parse_timestamp(entry.get("ts", "2000-01-01"))
                if ts >= cutoff:
                    entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue

    return entries


def cluster_errors(entries: list[dict]) -> list[dict]:
    """유사한 에러를 클러스터링하여 패턴 추출."""
    patterns: list[dict] = []

    for entry in entries:
        snippet = entry.get("error_snippet", "")
        norm = normalize_snippet(snippet)
        command = entry.get("command", "")
        category = entry.get("category", "other")

        matched = False
        for pattern in patterns:
            # 같은 카테고리 + 유사한 에러 스니펫 = 같은 패턴
            if pattern["category"] == category:
                similarity = SequenceMatcher(None, pattern["norm_key"], norm).ratio()
                if similarity > 0.6:
                    pattern["count"] += 1
                    pattern["sessions"].add(entry.get("session_id", ""))
                    pattern["last_ts"] = max(pattern["last_ts"], entry.get("ts", ""))
                    pattern["commands"].add(command[:100])
                    if len(pattern["examples"]) < 3:
                        pattern["examples"].append(snippet[:200])
                    matched = True
                    break

        if not matched:
            patterns.append({
                "norm_key": norm,
                "category": category,
                "count": 1,
                "sessions": {entry.get("session_id", "")},
                "last_ts": entry.get("ts", ""),
                "commands": {command[:100]},
                "examples": [snippet[:200]],
                "first_snippet": snippet[:300],
            })

    # 빈도 내림차순 정렬
    patterns.sort(key=lambda p: p["count"], reverse=True)
    return patterns


def generate_markdown(patterns: list[dict], total: int, days: int) -> str:
    """knowledge/bug-patterns.md 내용 생성."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    recurring = [p for p in patterns if p["count"] >= 3]
    occasional = [p for p in patterns if 1 < p["count"] < 3]
    one_off = [p for p in patterns if p["count"] == 1]

    # 카테고리별 집계
    cat_counter = Counter()
    for p in patterns:
        cat_counter[p["category"]] += p["count"]

    lines = [
        "# Bug Pattern Knowledge Base",
        f"> 기간: 최근 {days}일 | 총 {total}건 에러 | 반복 패턴 {len(recurring)}개 | 마지막 분석: {now}",
        "",
        "## 카테고리별 분포",
        "",
        "| 카테고리 | 건수 | 비율 |",
        "|---------|------|------|",
    ]

    for cat, count in cat_counter.most_common():
        pct = f"{count / total * 100:.0f}%" if total > 0 else "0%"
        lines.append(f"| {cat} | {count} | {pct} |")

    lines.extend(["", "## 반복 패턴 (3회 이상 발생)", ""])

    if not recurring:
        lines.append("반복 패턴 없음.")
    else:
        for i, p in enumerate(recurring, 1):
            lines.extend([
                f"### [P-{i:03d}] {p['category'].upper()} 에러 ({p['count']}회, 세션 {len(p['sessions'])}개)",
                f"- **에러 예시**: `{p['first_snippet'][:150]}`",
                f"- **관련 명령**: {', '.join(f'`{c}`' for c in list(p['commands'])[:3])}",
                f"- **마지막 발생**: {p['last_ts']}",
                f"- **해결 방법**: (분석 후 수동 기입 권장)",
                "",
            ])

    if occasional:
        lines.extend(["## 간헐적 에러 (2회)", ""])
        for p in occasional:
            lines.append(f"- **{p['category']}**: `{p['first_snippet'][:100]}` ({p['count']}회)")
        lines.append("")

    lines.extend([
        f"## 단발성 에러 ({len(one_off)}건)",
        "",
        f"최근 {days}일간 1회만 발생한 에러 {len(one_off)}건. 상세 내용은 `logs/errors.jsonl` 참조.",
        "",
        "---",
        f"*자동 생성: {now} | analyze_bugs.py*",
    ])

    return "\n".join(lines)


def rotate_logs(log_path: Path, days: int):
    """오래된 로그를 archive 파일로 이동."""
    if not log_path.exists():
        return

    cutoff = datetime.now() - timedelta(days=days)
    archive_path = log_path.parent / "errors.archive.jsonl"
    recent = []
    archived = 0

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry.get("ts", "2000-01-01"))
                if ts >= cutoff:
                    recent.append(line)
                else:
                    with open(archive_path, "a", encoding="utf-8") as af:
                        af.write(line + "\n")
                    archived += 1
            except (json.JSONDecodeError, ValueError):
                recent.append(line)

    if archived > 0:
        with open(log_path, "w", encoding="utf-8") as f:
            for line in recent:
                f.write(line + "\n")
        print(f"로그 로테이션: {archived}건 아카이브 이동")


def copy_to_memory(knowledge_path: Path):
    """knowledge/bug-patterns.md → memory 폴더에 복사."""
    memory_dir = Path.home() / ".claude" / "projects" / "c--Users-----OneDrive-Documents-Coding-AMIC-x-PETRA-Platform" / "memory"
    if memory_dir.exists():
        dest = memory_dir / "bug-patterns.md"
        shutil.copy2(knowledge_path, dest)
        print(f"memory 복사: {dest}")


def main():
    parser = argparse.ArgumentParser(description="에러 로그 분석")
    parser.add_argument("--days", type=int, default=30, help="분석 기간 (일)")
    parser.add_argument("--project-dir", type=str, default=None, help="프로젝트 루트")
    args = parser.parse_args()

    project_dir = Path(args.project_dir) if args.project_dir else Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    log_path = project_dir / "logs" / "errors.jsonl"
    knowledge_dir = project_dir / "knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    print(f"에러 로그 분석 (최근 {args.days}일)...")
    entries = load_errors(log_path, args.days)

    if not entries:
        print("에러 로그 없음.")
        # 빈 knowledge 파일 생성
        md = f"# Bug Pattern Knowledge Base\n> 기간: 최근 {args.days}일 | 에러 0건 | 마지막 분석: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n에러 로그가 아직 없습니다.\n"
        output_path = knowledge_dir / "bug-patterns.md"
        output_path.write_text(md, encoding="utf-8")
        copy_to_memory(output_path)
        return

    patterns = cluster_errors(entries)
    md = generate_markdown(patterns, len(entries), args.days)

    output_path = knowledge_dir / "bug-patterns.md"
    output_path.write_text(md, encoding="utf-8")
    print(f"생성 완료: {output_path}")

    # 로그 로테이션
    rotate_logs(log_path, args.days)

    # memory 폴더에 복사
    copy_to_memory(output_path)

    # 요약 출력
    recurring = [p for p in patterns if p["count"] >= 3]
    print(f"\n=== 분석 요약 ===")
    print(f"총 에러: {len(entries)}건")
    print(f"고유 패턴: {len(patterns)}개")
    print(f"반복 패턴 (3+회): {len(recurring)}개")

    if recurring:
        print(f"\nTOP 반복 패턴:")
        for p in recurring[:5]:
            print(f"  [{p['category']}] {p['count']}회 — {p['first_snippet'][:80]}")


if __name__ == "__main__":
    main()
