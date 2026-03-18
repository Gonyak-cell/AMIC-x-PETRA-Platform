"""릴리즈 노트 자동 생성 — sync-version.sh에서 호출

사용법: python3 generate-release-note.py <version> <prev_commit> <release_file>

git log에서 feat/fix/refactor/perf 커밋을 파싱하여
releaseNotes.ts에 새 버전 항목을 삽입한다.
"""

import re
import subprocess
import sys
from datetime import date
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 4:
        print(
            "사용법: python3 generate-release-note.py <version> <prev_commit> <release_file>"
        )
        sys.exit(1)

    version = sys.argv[1]
    prev_commit = sys.argv[2]
    release_file = Path(sys.argv[3])

    if not release_file.exists():
        print(f"  ⚠️  릴리즈 노트 파일 미발견: {release_file}", file=sys.stderr)
        return

    # git log에서 conventional commit 추출
    try:
        result = subprocess.run(
            ["git", "log", f"{prev_commit}..HEAD", "--oneline", "--no-merges"],
            capture_output=True,
            text=True,
            cwd=str(release_file.parent.parent.parent.parent),
            encoding="utf-8",
        )
        log_lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        log_lines = []

    features: list[str] = []
    fixes: list[str] = []
    improvements: list[str] = []

    for line in log_lines:
        if not line.strip():
            continue
        msg = line.split(" ", 1)[1] if " " in line else line
        m = re.match(r"(feat|fix|refactor|perf)\([^)]*\):\s*(.*)", msg)
        if m:
            typ, desc = m.group(1), m.group(2).strip()
            if typ == "feat":
                features.append(desc)
            elif typ == "fix":
                fixes.append(desc)
            elif typ in ("refactor", "perf"):
                improvements.append(desc)

    # 중복 제거 + 상한
    features = list(dict.fromkeys(features))[:8]
    fixes = list(dict.fromkeys(fixes))[:5]
    improvements = list(dict.fromkeys(improvements))[:3]

    highlights = features[:3] if features else ["버그 수정 및 개선"]

    # changes 배열 생성
    changes_lines: list[str] = []
    for f in features:
        changes_lines.append(f'    {{ type: "feature", description: "{f}" }},')
    for f in improvements:
        changes_lines.append(f'    {{ type: "improvement", description: "{f}" }},')
    for f in fixes:
        changes_lines.append(f'    {{ type: "fix", description: "{f}" }},')

    if not changes_lines:
        changes_lines.append(
            '    { type: "improvement", description: "안정성 개선 및 버그 수정" },'
        )

    highlights_str = ", ".join([f'"{h}"' for h in highlights])
    changes_str = "\n".join(changes_lines)
    today = date.today().isoformat()

    new_entry = f"""  {{
    version: "{version}",
    date: "{today}",
    highlights: [{highlights_str}],
    changes: [
{changes_str}
    ],
  }},"""

    # releaseNotes.ts에 삽입
    content = release_file.read_text(encoding="utf-8")
    marker = "export const RELEASE_NOTES: ReleaseNote[] = ["
    if marker in content:
        content = content.replace(marker, marker + "\n" + new_entry, 1)
        release_file.write_text(content, encoding="utf-8")
        msg = (
            f"  [OK] releaseNotes.ts v{version} added "
            f"(feat {len(features)}, fix {len(fixes)}, improvement {len(improvements)})"
        )
        sys.stdout.buffer.write((msg + "\n").encode("utf-8"))
    else:
        sys.stderr.buffer.write(
            "  [WARN] releaseNotes.ts marker not found\n".encode("utf-8")
        )


if __name__ == "__main__":
    main()
