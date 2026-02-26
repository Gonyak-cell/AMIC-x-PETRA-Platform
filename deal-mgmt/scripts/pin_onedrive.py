"""OneDrive 파일을 로컬에 고정(pin)하여 다운로드를 트리거한다.

attrib +P -U <file> 명령으로 "이 디바이스에 항상 유지" 설정.
"""
import os
import pathlib
import subprocess
import sys

BASE = pathlib.Path(
    r"C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스"
    r"\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives"
    r"\10_Pjt. Green\실사자료"
)

# Step 1: attrib 상태 확인 (처음 5개)
print("=== Step 1: attrib 상태 확인 ===")
files = list(BASE.rglob("*"))
real_files = [f for f in files if f.is_file()]
print(f"Total files: {len(real_files)}")

for f in real_files[:5]:
    result = subprocess.run(
        ["attrib", str(f)],
        capture_output=True, text=True, encoding="cp949", errors="replace"
    )
    print(f"  {result.stdout.strip()}")

# Step 2: 폴더 전체 pin (attrib +P -U /S /D)
print(f"\n=== Step 2: 폴더 전체 pin 시도 ===")
print(f"  대상: {BASE}")
result = subprocess.run(
    ["attrib", "+P", "-U", "/S", "/D", str(BASE / "*")],
    capture_output=True, text=True, encoding="cp949", errors="replace",
    timeout=120,
)
print(f"  stdout: {result.stdout[:500] if result.stdout else '(empty)'}")
print(f"  stderr: {result.stderr[:500] if result.stderr else '(empty)'}")
print(f"  returncode: {result.returncode}")

# Step 3: 잠시 후 다시 확인
import time
print("\n=== Step 3: 10초 대기 후 재확인 ===")
time.sleep(10)

ok = 0
fail = 0
for f in real_files[:10]:
    try:
        with open(f, "rb") as fh:
            fh.read(10)
        ok += 1
        print(f"  OK  : {f.name}")
    except Exception as e:
        fail += 1
        print(f"  FAIL: {f.name} - {e}")

print(f"\nResult: OK={ok}, FAIL={fail}")
if fail > 0:
    print("\n파일이 아직 다운로드 중입니다. OneDrive 트레이 아이콘에서 다운로드 진행률을 확인하세요.")
    print("모든 파일이 다운로드되면 파이프라인을 다시 실행하세요.")
