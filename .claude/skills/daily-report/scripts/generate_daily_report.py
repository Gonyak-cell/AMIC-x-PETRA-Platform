#!/usr/bin/env python3
"""일일 작업 리포트 생성: errors.jsonl + prompts.jsonl + git log → logs/daily/YYYY-MM-DD.md

사용법:
    python generate_daily_report.py [--date YYYY-MM-DD] [--project-dir PATH]

    --date: 대상 날짜 (기본값: 어제)
    --project-dir: 프로젝트 루트 (기본값: $CLAUDE_PROJECT_DIR 또는 cwd)
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# 같은 디렉토리의 error_fix_linker 모듈
sys.path.insert(0, str(Path(__file__).parent))
from error_fix_linker import ErrorFixLinker, FixStatus, RecurrenceRisk, sanitize_str


def load_jsonl_by_date(path: Path, date: str) -> list:
    """JSONL에서 특정 날짜의 엔트리만 로드."""
    entries = []
    if not path.exists():
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("ts", "").startswith(date):
                    entries.append(entry)
            except (json.JSONDecodeError, ValueError):
                continue
    return entries


def section_summary(errors: list, prompts: list, commits: list, linked: list) -> str:
    """섹션 1: 일일 요약."""
    total_added = 0
    total_deleted = 0
    total_files = set()

    for commit in commits:
        for f in commit.get("files", []):
            total_files.add(f)

    # 커밋별 numstat은 비용이 높으므로, 파일 수만 기록
    fixed_count = sum(1 for le in linked if le.fix_status == FixStatus.FIXED)
    likely_count = sum(1 for le in linked if le.fix_status == FixStatus.LIKELY_FIXED)
    unresolved_count = sum(
        1
        for le in linked
        if le.fix_status in (FixStatus.UNRESOLVED, FixStatus.RECURRING)
    )

    # 세션 수
    session_ids = set()
    for e in errors:
        session_ids.add(e.get("session_id", ""))
    for p in prompts:
        session_ids.add(p.get("session_id", ""))
    session_ids.discard("")

    # 사용자 프롬프트만 (task-notification 제외)
    user_prompts = [
        p for p in prompts if not p.get("prompt", "").startswith("<task-notification>")
    ]

    lines = [
        "## 1. 일일 요약\n",
        "| 항목 | 수치 |",
        "|------|------|",
        f"| 총 커밋 | {len(commits)}건 |",
        f"| 변경 파일 | {len(total_files)}개 |",
        f"| 에러 발생 | {len(errors)}건 ({len(linked)}개 고유 패턴) |",
        f"| 에러 수정 완료 | {fixed_count}건 |",
        f"| 수정 추정 | {likely_count}건 |",
        f"| 미해결 에러 | {unresolved_count}건 |",
        f"| 세션 수 | {len(session_ids)}개 |",
        f"| 사용자 지시 | {len(user_prompts)}건 |",
    ]

    return "\n".join(lines)


def section_commits(commits: list) -> str:
    """섹션 2: 커밋별 수정 내역."""
    if not commits:
        return "## 2. 커밋별 수정 내역\n\n커밋 없음."

    lines = ["## 2. 커밋별 수정 내역\n"]

    # 시간순 정렬 (오래된 것부터)
    sorted_commits = sorted(commits, key=lambda c: c.get("timestamp", ""))

    for i, commit in enumerate(sorted_commits, 1):
        ts = commit.get("timestamp", "")[:19]
        time_str = ts.split(" ")[1] if " " in ts else ts[11:]
        subject = commit.get("subject", "")
        commit_type = commit.get("type", "other")
        scope = commit.get("scope", "")
        files = commit.get("files", [])

        type_label = {
            "feat": "기능 추가",
            "fix": "버그 수정",
            "refactor": "리팩토링",
            "chore": "설정/관리",
            "docs": "문서",
            "test": "테스트",
            "perf": "성능 개선",
            "style": "스타일",
            "debug": "디버깅",
        }.get(commit_type, commit_type)

        lines.append(f"### {i}. `{commit['hash']}` {subject}")
        lines.append(f"- **시간**: {time_str}")
        lines.append(f"- **유형**: {type_label}")
        if scope:
            lines.append(f"- **범위**: {scope}")
        lines.append(f"- **변경 파일**: {len(files)}개")
        if files:
            shown = files[:5]
            file_list = ", ".join(f"`{f}`" for f in shown)
            if len(files) > 5:
                file_list += f" 외 {len(files) - 5}개"
            lines.append(f"- **주요 파일**: {file_list}")
        lines.append("")

    return "\n".join(lines)


def section_error_tracking(linked: list) -> str:
    """섹션 3: 에러 추적표 (핵심)."""
    if not linked:
        return "## 3. 에러 추적표\n\n에러 발생 없음."

    lines = [
        "## 3. 에러 추적표\n",
        "| # | 시간 | 카테고리 | 에러 내용 | 수정 취지 | 수정 여부 | 발생 맥락 | 수정 맥락 | 재발 가능성 |",
        "|---|------|---------|----------|----------|----------|----------|----------|-----------|",
    ]

    for i, le in enumerate(linked, 1):
        error = le.error
        ts = error.get("ts", "")
        time_str = ts[11:19] if len(ts) >= 19 else ts

        category = error.get("category", "other")
        snippet = error.get("error_snippet", "")[:60].replace("\n", " ").replace("|", "\\|")

        fix_status_str = le.fix_status.value
        if le.fix_commits:
            commit_hash = le.fix_commits[0].get("commit", {}).get("hash", "")
            if commit_hash:
                fix_status_str += f" ({commit_hash})"

        fix_reason = le.fix_reason[:50].replace("|", "\\|") if le.fix_reason else "-"
        work_ctx = le.work_context[:40].replace("|", "\\|") if le.work_context else "-"
        fix_ctx = le.fix_context[:40].replace("|", "\\|") if le.fix_context else "-"
        recurrence = le.recurrence_risk.value

        count_str = f" (x{le.cluster_count})" if le.cluster_count > 1 else ""

        lines.append(
            f"| E-{i:03d}{count_str} | {time_str} | {category} | {snippet} | {fix_reason} | {fix_status_str} | {work_ctx} | {fix_ctx} | {recurrence} |"
        )

    return "\n".join(lines)


def section_timeline(errors: list, prompts: list) -> str:
    """섹션 4: 세션 타임라인."""
    # 사용자 프롬프트만
    user_prompts = [
        p for p in prompts if not p.get("prompt", "").startswith("<task-notification>")
    ]

    if not user_prompts and not errors:
        return "## 4. 세션 타임라인\n\n활동 없음."

    # 시간대별 그룹핑 (3시간 단위)
    time_blocks = defaultdict(lambda: {"prompts": [], "errors": [], "sessions": set()})

    for p in user_prompts:
        ts = p.get("ts", "")
        if len(ts) >= 13:
            hour = int(ts[11:13])
            block = f"{(hour // 3) * 3:02d}:00 ~ {(hour // 3) * 3 + 2:02d}:59"
            time_blocks[block]["prompts"].append(p)
            time_blocks[block]["sessions"].add(p.get("session_id", ""))

    for e in errors:
        ts = e.get("ts", "")
        if len(ts) >= 13:
            hour = int(ts[11:13])
            block = f"{(hour // 3) * 3:02d}:00 ~ {(hour // 3) * 3 + 2:02d}:59"
            time_blocks[block]["errors"].append(e)
            time_blocks[block]["sessions"].add(e.get("session_id", ""))

    lines = ["## 4. 세션 타임라인\n"]

    for block_key in sorted(time_blocks.keys()):
        data = time_blocks[block_key]
        session_count = len(data["sessions"] - {""})
        prompt_count = len(data["prompts"])
        error_count = len(data["errors"])

        lines.append(f"### {block_key} (세션 {session_count}개)")

        # 에러 카테고리 분포
        if data["errors"]:
            cats = Counter(e.get("category", "other") for e in data["errors"])
            cat_str = ", ".join(f"{k} {v}" for k, v in cats.most_common())
            lines.append(f"- **에러**: {error_count}건 ({cat_str})")

        # 주요 작업 요약 (프롬프트 카테고리 + 샘플)
        if data["prompts"]:
            cats = Counter(p.get("category", "other") for p in data["prompts"])
            cat_str = ", ".join(f"{k} {v}" for k, v in cats.most_common())
            lines.append(f"- **지시**: {prompt_count}건 ({cat_str})")

            # 대표 프롬프트 (최대 3개)
            samples = data["prompts"][:3]
            for p in samples:
                text = p.get("prompt", "")[:60].replace("\n", " ")
                lines.append(f"  - `{text}`")

        lines.append("")

    return "\n".join(lines)


def section_category_distribution(errors: list, linked: list) -> str:
    """섹션 5: 카테고리별 에러 분포."""
    if not errors:
        return "## 5. 카테고리별 에러 분포\n\n에러 발생 없음."

    total = len(errors)
    cat_counter = Counter(e.get("category", "other") for e in errors)

    # 카테고리별 수정률 계산
    cat_fix = defaultdict(lambda: {"total": 0, "fixed": 0})
    for le in linked:
        cat = le.error.get("category", "other")
        cat_fix[cat]["total"] += le.cluster_count
        if le.fix_status in (FixStatus.FIXED, FixStatus.LIKELY_FIXED):
            cat_fix[cat]["fixed"] += le.cluster_count

    lines = [
        "## 5. 카테고리별 에러 분포\n",
        "| 카테고리 | 건수 | 비율 | 수정률 |",
        "|---------|------|------|-------|",
    ]

    for cat, count in cat_counter.most_common():
        pct = f"{count / total * 100:.0f}%"
        fix_data = cat_fix.get(cat, {"total": 0, "fixed": 0})
        fix_rate = (
            f"{fix_data['fixed'] / fix_data['total'] * 100:.0f}%"
            if fix_data["total"] > 0
            else "-"
        )
        lines.append(f"| {cat} | {count} | {pct} | {fix_rate} |")

    return "\n".join(lines)


def section_insights(errors: list, commits: list, linked: list) -> str:
    """섹션 6: 주요 인사이트 (자동 생성)."""
    lines = ["## 6. 주요 인사이트\n"]
    insights = []

    if not errors and not commits:
        lines.append("활동 없음.")
        return "\n".join(lines)

    # 인사이트 1: 에러 집중 시간대
    if errors:
        hour_counter = Counter()
        for e in errors:
            ts = e.get("ts", "")
            if len(ts) >= 13:
                hour_counter[int(ts[11:13])] += 1
        if hour_counter:
            peak_hour, peak_count = hour_counter.most_common(1)[0]
            insights.append(
                f"**에러 집중 시간대**: {peak_hour:02d}시에 {peak_count}건으로 가장 많은 에러 발생"
            )

    # 인사이트 2: 가장 많은 에러 카테고리
    if errors:
        cat_counter = Counter(e.get("category", "other") for e in errors)
        top_cat, top_count = cat_counter.most_common(1)[0]
        pct = top_count / len(errors) * 100
        if top_cat == "other" and pct > 40:
            insights.append(
                f"**'other' 카테고리 비중 높음**: {pct:.0f}%가 미분류. 에러 카테고리 규칙 확장 권장"
            )
        else:
            insights.append(
                f"**주요 에러 유형**: {top_cat} ({top_count}건, {pct:.0f}%)"
            )

    # 인사이트 3: 수정률
    if linked:
        fixed = sum(
            1
            for le in linked
            if le.fix_status in (FixStatus.FIXED, FixStatus.LIKELY_FIXED)
        )
        rate = fixed / len(linked) * 100
        insights.append(f"**에러 수정률**: {rate:.0f}% ({fixed}/{len(linked)})")

    # 인사이트 4: 재발 위험 높은 에러
    high_risk = [le for le in linked if le.recurrence_risk == RecurrenceRisk.HIGH]
    if high_risk:
        insights.append(
            f"**재발 위험 HIGH**: {len(high_risk)}건 — 추가 조치 필요"
        )

    # 인사이트 5: 커밋 유형 분포
    if commits:
        type_counter = Counter(c.get("type", "other") for c in commits)
        type_str = ", ".join(f"{t} {n}건" for t, n in type_counter.most_common(3))
        insights.append(f"**커밋 유형**: {type_str}")

    for i, insight in enumerate(insights, 1):
        lines.append(f"{i}. {insight}")

    return "\n".join(lines)


def generate_report(project_dir: str, target_date: str) -> str:
    """전체 리포트 생성 파이프라인."""
    project_path = Path(project_dir)

    # 1. 데이터 수집
    errors_path = project_path / "logs" / "errors.jsonl"
    prompts_path = project_path / "logs" / "prompts.jsonl"

    errors = load_jsonl_by_date(errors_path, target_date)
    prompts = load_jsonl_by_date(prompts_path, target_date)

    # 2. git 커밋 로드
    linker = ErrorFixLinker(project_dir, target_date)
    commits = linker.load_git_commits()

    # 3. 에러-수정 연결
    linked = linker.link_all(errors, commits, prompts)

    # 4. 각 섹션 생성
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"# 일일 작업 리포트: {target_date}\n\n> 자동 생성: {now} | generate_daily_report.py\n"

    sections = [
        header,
        section_summary(errors, prompts, commits, linked),
        section_commits(commits),
        section_error_tracking(linked),
        section_timeline(errors, prompts),
        section_category_distribution(errors, linked),
        section_insights(errors, commits, linked),
        f"\n---\n*자동 생성: {now} | generate_daily_report.py v1.0*",
    ]

    return "\n\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description="일일 작업 리포트 생성")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="대상 날짜 YYYY-MM-DD (기본: 어제)",
    )
    parser.add_argument(
        "--project-dir",
        type=str,
        default=None,
        help="프로젝트 루트 디렉토리",
    )
    args = parser.parse_args()

    # 날짜 결정
    if args.date:
        target_date = args.date
    else:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 프로젝트 디렉토리 결정
    project_dir = (
        args.project_dir
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )
    project_dir = sanitize_str(project_dir)

    print(f"일일 리포트 생성: {target_date} (프로젝트: {project_dir})")

    # 리포트 생성
    report = generate_report(project_dir, target_date)

    # 저장
    output_dir = Path(project_dir) / "logs" / "daily"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{target_date}.md"
    output_path.write_text(report, encoding="utf-8")

    print(f"리포트 저장 완료: {output_path}")

    # 간략 요약 출력
    errors = load_jsonl_by_date(Path(project_dir) / "logs" / "errors.jsonl", target_date)
    prompts = load_jsonl_by_date(Path(project_dir) / "logs" / "prompts.jsonl", target_date)
    linker = ErrorFixLinker(project_dir, target_date)
    commits = linker.load_git_commits()

    print(f"\n=== {target_date} 요약 ===")
    print(f"커밋: {len(commits)}건 | 에러: {len(errors)}건 | 지시: {len(prompts)}건")


if __name__ == "__main__":
    main()
