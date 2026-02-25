"""법률 문서 생성 파일 정리 스크립트.

사용법:
  python scripts/cleanup_old_files.py               # 기본: 30일 초과 파일 삭제
  python scripts/cleanup_old_files.py --days 60     # 60일 초과 파일 삭제
  python scripts/cleanup_old_files.py --dry-run     # 삭제 대상만 출력 (실제 삭제 없음)

Cron 예시 (매일 자정 실행):
  0 0 * * * cd /app && python scripts/cleanup_old_files.py >> /var/log/cleanup.log 2>&1
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (직접 실행 시)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

GENERATED_DIR = _PROJECT_ROOT / "generated" / "legal"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="법률 문서 생성 파일 정리")
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="이 일수를 초과한 파일을 삭제합니다 (기본: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="삭제 대상 목록만 출력하고 실제 삭제하지 않습니다",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_DIR,
        help=f"대상 디렉터리 (기본: {GENERATED_DIR})",
    )
    return parser.parse_args()


def cleanup(output_dir: Path, retention_days: int, dry_run: bool) -> dict:
    """지정 디렉터리에서 오래된 .docx 파일을 정리한다.

    Returns:
        dict: {"scanned": int, "deleted": int, "freed_bytes": int, "errors": list}
    """
    if not output_dir.exists():
        print(f"[INFO] 디렉터리가 존재하지 않습니다: {output_dir}")
        return {"scanned": 0, "deleted": 0, "freed_bytes": 0, "errors": []}

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    stats = {"scanned": 0, "deleted": 0, "freed_bytes": 0, "errors": []}

    for path in output_dir.glob("*.docx"):
        stats["scanned"] += 1
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if mtime < cutoff:
                size = path.stat().st_size
                age_days = (datetime.now(UTC) - mtime).days
                if dry_run:
                    print(f"  [DRY-RUN] 삭제 예정: {path.name} (수정일: {mtime.date()}, {age_days}일 경과, {size:,} bytes)")
                else:
                    path.unlink()
                    stats["deleted"] += 1
                    stats["freed_bytes"] += size
                    print(f"  [삭제] {path.name} ({age_days}일 경과, {size:,} bytes)")
        except OSError as e:
            stats["errors"].append(str(e))
            print(f"  [오류] {path.name}: {e}", file=sys.stderr)

    return stats


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()

    # 안전 경로 검증 — 프로젝트 루트 외부 삭제 방지
    if not str(output_dir).startswith(str(_PROJECT_ROOT)):
        print(f"[오류] 지정된 디렉터리가 프로젝트 루트 외부입니다: {output_dir}", file=sys.stderr)
        sys.exit(1)

    mode = "DRY-RUN" if args.dry_run else "실행"
    print(f"[{datetime.now(UTC).isoformat()}] 파일 정리 시작 ({mode})")
    print(f"  대상 디렉터리: {output_dir}")
    print(f"  보존 기간: {args.days}일")
    print()

    stats = cleanup(output_dir, args.days, args.dry_run)

    print()
    print("─" * 50)
    print(f"  검사 파일: {stats['scanned']}개")
    if args.dry_run:
        print(f"  삭제 예정: {stats['deleted']}개")
    else:
        print(f"  삭제 완료: {stats['deleted']}개")
        freed_mb = stats["freed_bytes"] / (1024 * 1024)
        print(f"  회수 공간: {freed_mb:.2f} MB")
    if stats["errors"]:
        print(f"  오류 발생: {len(stats['errors'])}개")
        for err in stats["errors"]:
            print(f"    - {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
