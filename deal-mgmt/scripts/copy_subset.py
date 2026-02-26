"""실사자료 중 PDF 5개만 로컬에 복사하여 다운로드를 트리거한다."""
import pathlib
import subprocess

BASE = pathlib.Path(
    r"C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스"
    r"\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives"
    r"\10_Pjt. Green\실사자료"
)
DST = pathlib.Path(r"C:\temp\ldd_test")
DST.mkdir(parents=True, exist_ok=True)

# PDF 파일 5개 선택
pdfs = [f for f in BASE.rglob("*.pdf") if f.is_file()][:5]
print(f"PDF 파일 {len(pdfs)}개 선택:")
for p in pdfs:
    print(f"  {p.name} ({p.stat().st_size} bytes)")

# 방법 1: subprocess copy 명령
print("\n=== copy 명령으로 복사 시도 ===")
for p in pdfs[:2]:
    dst_path = DST / p.name
    result = subprocess.run(
        ["cmd", "/c", "copy", str(p), str(dst_path)],
        capture_output=True, text=True, encoding="cp949", errors="replace",
        timeout=60,
    )
    print(f"  {p.name}: rc={result.returncode}")
    if result.stderr:
        print(f"    stderr: {result.stderr.strip()}")
    if dst_path.exists():
        print(f"    OK: copied {dst_path.stat().st_size} bytes")

# 방법 2: robocopy (단일 파일)
print("\n=== robocopy로 복사 시도 ===")
for p in pdfs[2:4]:
    result = subprocess.run(
        ["robocopy", str(p.parent), str(DST), p.name, "/R:1", "/W:1"],
        capture_output=True, text=True, encoding="cp949", errors="replace",
        timeout=60,
    )
    dst_path = DST / p.name
    if dst_path.exists():
        print(f"  OK: {p.name} ({dst_path.stat().st_size} bytes)")
    else:
        print(f"  FAIL: {p.name} (rc={result.returncode})")
        if result.stderr:
            print(f"    {result.stderr.strip()[:200]}")

# 방법 3: PowerShell Start-BitsTransfer (로컬 파일도 가능)
print("\n=== 최종 확인: 로컬 복사본 ===")
for f in DST.iterdir():
    try:
        with open(f, "rb") as fh:
            data = fh.read(10)
        print(f"  OK  : {f.name} ({f.stat().st_size} bytes, first bytes: {data[:5].hex()})")
    except Exception as e:
        print(f"  FAIL: {f.name} - {e}")
