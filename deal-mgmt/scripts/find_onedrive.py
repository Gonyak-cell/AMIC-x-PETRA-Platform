"""OneDrive 폴더 경로 탐색 및 파일 접근성 확인."""
import pathlib

user_home = pathlib.Path(r"C:\Users\서지원")

# Step 1: OneDrive 폴더 찾기
print("=== OneDrive folders ===")
for d in user_home.iterdir():
    if d.is_dir() and ("OneDrive" in d.name or "페트라" in d.name):
        print(f"  {d}")

# Step 2: 경로 단계별 확인
segments = [
    "OneDrive - 주식회사 페트라브릿지파트너스",
    "AMIC의 파일 - 1. AMIC",
    "5. 기업 인수&합병",
    "99_Archives",
]

current = user_home
for seg in segments:
    current = current / seg
    exists = current.exists()
    print(f"\n{seg}: exists={exists}")
    if not exists:
        # 상위 폴더에서 비슷한 이름 찾기
        parent = current.parent
        if parent.exists():
            print(f"  Contents of {parent.name}:")
            for item in sorted(parent.iterdir()):
                if item.is_dir():
                    print(f"    [DIR] {item.name}")
        break
    else:
        # 하위 폴더 목록
        dirs = sorted([d.name for d in current.iterdir() if d.is_dir()])
        if dirs:
            print(f"  Subdirs: {dirs[:10]}")

# Step 3: Pjt. Green 찾기
if current.exists():
    print(f"\n=== Looking for Pjt. Green in {current} ===")
    for d in sorted(current.iterdir()):
        if d.is_dir():
            print(f"  [DIR] {d.name}")
            if "Green" in d.name or "green" in d.name:
                green_dir = d
                print(f"\n=== Pjt Green found: {green_dir} ===")
                for item in sorted(green_dir.iterdir()):
                    print(f"    {'[DIR]' if item.is_dir() else '[FILE]'} {item.name}")

                # 실사자료 찾기
                for sub in green_dir.iterdir():
                    if sub.is_dir() and "실사" in sub.name:
                        print(f"\n=== 실사자료: {sub} ===")
                        # 파일 수 세기
                        all_files = list(sub.rglob("*"))
                        file_count = sum(1 for f in all_files if f.is_file())
                        print(f"Total files: {file_count}")

                        # 읽기 테스트
                        test_files = [f for f in all_files if f.is_file()][:5]
                        for f in test_files:
                            try:
                                with open(f, "rb") as fh:
                                    fh.read(10)
                                print(f"OK  : {f.name} ({f.stat().st_size} bytes)")
                            except Exception as e:
                                print(f"FAIL: {f.name} - {e}")
                        break
                break
