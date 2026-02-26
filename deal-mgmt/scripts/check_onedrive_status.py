"""OneDrive 프로세스 상태 및 네트워크 활동 확인."""
import pathlib
import subprocess

# 1. OneDrive 프로세스 확인
print("=== OneDrive Process ===")
result = subprocess.run(
    ["tasklist", "/FI", "IMAGENAME eq OneDrive.exe"],
    capture_output=True, text=True, encoding="cp949", errors="replace"
)
print(result.stdout.strip())

# 2. OneDrive 동기화 상태 파일 확인
print("\n=== OneDrive Settings/Logs ===")
od_dir = pathlib.Path.home() / "AppData" / "Local" / "Microsoft" / "OneDrive"
if od_dir.exists():
    # settings 파일 찾기
    settings = list(od_dir.rglob("*.ini"))[:3]
    for s in settings:
        print(f"  {s.relative_to(od_dir)}")

    # 로그 파일 확인 (최근)
    logs = sorted(od_dir.rglob("*.odl"), key=lambda f: f.stat().st_mtime, reverse=True)[:2]
    for log in logs:
        print(f"  Log: {log.name} ({log.stat().st_size} bytes, modified recently)")

# 3. OneDrive가 실제로 다운로드 중인지 확인 - 네트워크 연결
print("\n=== OneDrive Network Connections ===")
result = subprocess.run(
    ["netstat", "-b", "-n"],
    capture_output=True, text=True, encoding="cp949", errors="replace",
    timeout=30,
)
lines = result.stdout.split("\n")
od_connections = [l for l in lines if "OneDrive" in l or "onedrive" in l.lower()]
print(f"  OneDrive connections: {len(od_connections)}")
for c in od_connections[:5]:
    print(f"    {c.strip()}")

# 4. 대안: 실사자료 폴더가 아닌, 이미 로컬에 있는 파일 찾기
print("\n=== Already Local Files Check ===")
BASE = pathlib.Path(
    r"C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스"
    r"\AMIC의 파일 - 1. AMIC\5. 기업 인수&합병\99_Archives"
    r"\10_Pjt. Green"
)

# Pjt. Green 루트의 파일들 (실사자료 폴더 밖)
root_files = [f for f in BASE.iterdir() if f.is_file()]
local_ok = 0
for f in root_files:
    try:
        with open(f, "rb") as fh:
            fh.read(10)
        local_ok += 1
        print(f"  OK  : {f.name} ({f.stat().st_size} bytes)")
    except Exception as e:
        print(f"  FAIL: {f.name} - {type(e).__name__}")

print(f"\nPjt. Green 루트 파일: {local_ok}/{len(root_files)} 읽기 가능")

# 5. 실사자료 하위 폴더별 첫 파일 상태
print("\n=== 실사자료 하위 폴더별 상태 ===")
silsa = BASE / "실사자료"
if silsa.exists():
    for sub in sorted(silsa.iterdir()):
        if sub.is_dir():
            files = list(sub.rglob("*"))
            file_count = sum(1 for f in files if f.is_file())
            # 첫 파일 읽기 시도
            first_file = next((f for f in files if f.is_file()), None)
            status = "N/A"
            if first_file:
                try:
                    with open(first_file, "rb") as fh:
                        fh.read(10)
                    status = "LOCAL"
                except:
                    status = "CLOUD"
            print(f"  {sub.name}: {file_count} files, status={status}")
