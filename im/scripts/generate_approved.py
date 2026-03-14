"""승인 PNG baseline 생성 스크립트 — IM (tm_default / dm_default / im_full).

> 마지막 수정: 2026-03-14

Usage::

    # 전체 variant (tm_default, dm_default, im_full)
    python scripts/generate_approved.py

    # 특정 variant만
    python scripts/generate_approved.py --variant tm_default dm_default

    # 기존 approved 있어도 강제 덮어쓰기
    python scripts/generate_approved.py --force

사전 요건:
    - LibreOffice headless 설치 (``libreoffice --headless`` 실행 가능)
    - pdf2image + poppler 설치
    - im/ 루트에서 실행 (PYTHONPATH 자동 설정)
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
# 스크립트는 im/scripts/ 에 위치 → 부모의 부모가 im/ 루트
_SCRIPT_DIR = Path(__file__).resolve().parent
_MODULE_ROOT = _SCRIPT_DIR.parent  # im/

if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

_FIXTURES_DIR = _MODULE_ROOT / "tests" / "fixtures" / "golden_samples"
_VISUAL_DIFF_DIR = _MODULE_ROOT / "tests" / "visual_diff"

VARIANTS: list[str] = ["tm_default", "dm_default", "im_full"]


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────


def check_libreoffice() -> None:
    """LibreOffice 설치 여부를 확인한다. 없으면 에러 메시지 출력 후 exit(1)."""
    from tests.visual_diff.diff_utils import _find_libreoffice

    try:
        _find_libreoffice()
    except FileNotFoundError as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)


def clean_approved_pngs(approved_dir: Path) -> int:
    """approved/ 디렉토리의 기존 slide_*.png를 삭제하고 삭제 수를 반환한다."""
    if not approved_dir.exists():
        approved_dir.mkdir(parents=True, exist_ok=True)
        return 0
    removed = 0
    for png in approved_dir.glob("slide_*.png"):
        png.unlink()
        removed += 1
    return removed


def generate_variant(variant: str, force: bool) -> None:
    """단일 variant의 승인 PNG를 생성한다."""
    from src.design_renderer.pipeline import IMPipeline
    from tests.visual_diff.diff_utils import pptx_to_pngs

    approved_dir = _FIXTURES_DIR / variant / "approved"

    # --force 없이 기존 PNG가 있으면 건너뜀
    if not force and any(approved_dir.glob("slide_*.png")):
        existing = list(approved_dir.glob("slide_*.png"))
        print(
            f"[{variant}] approved/ 에 이미 {len(existing)}개의 PNG가 있습니다.\n"
            f"  덮어쓰려면 --force 옵션을 사용하세요. 건너뜁니다."
        )
        return

    print(f"[{variant}] 생성 시작...")

    # 1. IMDocumentData 구성 (shared builder 사용)
    from tests.visual_diff.sample_builders import VARIANT_BUILDERS

    builder = VARIANT_BUILDERS[variant]
    data = builder()  # type: ignore[operator]

    # 2. PPTX 생성 (임시 디렉토리 사용)
    pipeline = IMPipeline()
    with tempfile.TemporaryDirectory() as tmpdir:
        pptx_path = Path(tmpdir) / f"{variant}.pptx"
        result = pipeline.generate_pptx(data, output_path=str(pptx_path))

        if not result.success:
            errors_str = "; ".join(result.errors)
            raise RuntimeError(f"PPTX 생성 실패: {errors_str}")

        print(
            f"  PPTX 생성 완료: {result.total_pptx_slides}개 슬라이드"
            f" (경고 {len(result.warnings)}건)"
        )

        # 3. PNG 변환
        png_tmp_dir = Path(tmpdir) / "pngs"
        png_paths = pptx_to_pngs(str(pptx_path), str(png_tmp_dir), dpi=150)

        if not png_paths:
            print(
                "  오류: PNG 변환 결과가 없습니다. LibreOffice/pdf2image 확인 필요.",
                file=sys.stderr,
            )
            sys.exit(1)

        print(f"  PNG 변환 완료: {len(png_paths)}개")

        # 4. 기존 approved PNG 정리
        removed = clean_approved_pngs(approved_dir)
        if removed:
            print(f"  기존 PNG {removed}개 삭제")

        # 5. 새 PNG를 approved/ 에 복사
        for png_src in sorted(Path(png_tmp_dir).glob("slide_*.png")):
            dst = approved_dir / png_src.name
            shutil.copy2(str(png_src), str(dst))

    # 6. 결과 출력
    final_pngs = sorted(approved_dir.glob("slide_*.png"))
    print(f"  저장 완료: {approved_dir}")
    for p in final_pngs:
        print(f"    {p.name}")
    print(f"  슬라이드 수: {len(final_pngs)}개\n")


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    """CLI 인수를 파싱한다."""
    parser = argparse.ArgumentParser(
        description="IM golden sample 승인 PNG baseline 생성",
    )
    parser.add_argument(
        "--variant",
        nargs="*",
        choices=VARIANTS,
        default=None,
        metavar="VARIANT",
        help=f"생성할 variant ({', '.join(VARIANTS)}). 미지정 시 전체 생성.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 approved PNG가 있어도 덮어쓰기.",
    )
    return parser.parse_args()


def main() -> None:
    """메인 진입점."""
    args = parse_args()
    targets: list[str] = args.variant if args.variant else VARIANTS

    check_libreoffice()

    print(f"=== IM 승인 PNG 생성 (variant: {targets}) ===\n")

    errors: list[str] = []
    for variant in targets:
        try:
            generate_variant(variant, force=args.force)
        except FileNotFoundError as exc:
            msg = f"[{variant}] 파일 없음: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)
        except Exception as exc:
            msg = f"[{variant}] 생성 실패: {exc}"
            print(msg, file=sys.stderr)
            errors.append(msg)

    if errors:
        print(f"\n오류 {len(errors)}건 발생:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    print("=== 완료 ===")


if __name__ == "__main__":
    main()
