"""FDD + KIIS + IM 3개 DB에 AMIC 사용자를 시딩하는 스크립트.

사용법:
  # Docker 환경 (기본 DB URL)
  python scripts/seed-users.py

  # 로컬 환경 (포트 매핑)
  python scripts/seed-users.py --local
"""

import argparse
import sys
import uuid

try:
    import bcrypt
except ImportError:
    print("Error: bcrypt 패키지가 필요합니다.")
    print("  pip install bcrypt")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 패키지가 필요합니다.")
    print("  pip install psycopg2-binary")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 비밀번호 해싱 (bcrypt — FDD/KIIS/IM 공통)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """bcrypt 12 라운드 해싱 (FDD app/auth/password.py와 동일)."""
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
    return hashed.decode()


# ---------------------------------------------------------------------------
# 사용자 목록 (6명 — 고정, 변경 금지)
# ---------------------------------------------------------------------------

USERS = [
    {
        "email": "ytkim@amic.kr",
        "display_name": "김양태",
        "title": "대표 / 회계사",
        "username": "ytkim",
        "full_name": "김양태",
        "fdd_role": "ADMIN",
        "kiis_role": "admin",
        "im_role": "ADMIN",
        "password": "1111",
    },
    {
        "email": "jwsuh@amic.kr",
        "display_name": "서지원",
        "title": "변호사",
        "username": "jwsuh",
        "full_name": "서지원",
        "fdd_role": "ADMIN",
        "kiis_role": "admin",
        "im_role": "ADMIN",
        "password": "1111",
    },
    {
        "email": "yhlim@amic.kr",
        "display_name": "임영훈",
        "title": "변호사",
        "username": "yhlim",
        "full_name": "임영훈",
        "fdd_role": "ANALYST",
        "kiis_role": "analyst",
        "im_role": "USER",
        "password": "1111",
    },
    {
        "email": "bj.park@amic.kr",
        "display_name": "박병준",
        "title": "변호사",
        "username": "bjpark",
        "full_name": "박병준",
        "fdd_role": "ANALYST",
        "kiis_role": "analyst",
        "im_role": "USER",
        "password": "1111",
    },
    {
        "email": "wsjo@amic.kr",
        "display_name": "조우상",
        "title": "이사",
        "username": "wsjo",
        "full_name": "조우상",
        "fdd_role": "ANALYST",
        "kiis_role": "analyst",
        "im_role": "USER",
        "password": "1111",
    },
    {
        "email": "tryoon@amic.kr",
        "display_name": "윤태리",
        "title": "실장",
        "username": "tryoon",
        "full_name": "윤태리",
        "fdd_role": "ANALYST",
        "kiis_role": "analyst",
        "im_role": "USER",
        "password": "1111",
    },
]


# ---------------------------------------------------------------------------
# DB 연결 정보
# ---------------------------------------------------------------------------

# Docker 내부 (docker compose exec 등에서 사용)
DOCKER_DBS = {
    "fdd": "postgresql://autofdd:autofdd_dev@fdd-db:5432/autofdd",
    "kiis": "postgresql://kiis_user:kiis_dev_password@kiis-db:5432/kiis",
    "im": "postgresql://postgres:postgres@im-db:5432/imgen",
}

# 로컬 (docker compose port mapping)
LOCAL_DBS = {
    "fdd": "postgresql://autofdd:autofdd_dev@localhost:5433/autofdd",
    "kiis": "postgresql://kiis_user:kiis_dev_password@localhost:5434/kiis",
    "im": "postgresql://postgres:postgres@localhost:5435/imgen",
}


# ---------------------------------------------------------------------------
# 스키마 보장 (title 컬럼이 없으면 추가)
# ---------------------------------------------------------------------------

def ensure_title_column(cur, table: str = "users") -> None:
    """title 컬럼이 존재하지 않으면 ALTER TABLE로 추가."""
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = %s AND column_name = 'title'
    """, (table,))
    if not cur.fetchone():
        cur.execute(f"ALTER TABLE {table} ADD COLUMN title VARCHAR(100) NOT NULL DEFAULT ''")
        print(f"  [SCHEMA] title 컬럼 추가됨")


# ---------------------------------------------------------------------------
# 시딩 함수
# ---------------------------------------------------------------------------

def seed_fdd(db_url: str) -> None:
    """FDD DB에 사용자 시딩.

    스키마: id (UUID), email, hashed_password, display_name, title, role, is_active
    """
    print(f"\n{'='*50}")
    print(f"[FDD] 연결: {db_url}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        ensure_title_column(cur)

        for u in USERS:
            cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
            existing = cur.fetchone()
            if existing:
                hashed = hash_password(u["password"])
                cur.execute(
                    """UPDATE users
                       SET hashed_password = %s, display_name = %s, title = %s,
                           is_active = true, role = %s
                       WHERE email = %s""",
                    (hashed, u["display_name"], u["title"], u["fdd_role"], u["email"]),
                )
                print(f"  [UPDATE] {u['email']} ({u['display_name']} {u['title']})")
            else:
                user_id = str(uuid.uuid4())
                hashed = hash_password(u["password"])
                cur.execute(
                    """INSERT INTO users (id, email, hashed_password, display_name, title, role, is_active, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, true, NOW(), NOW())""",
                    (user_id, u["email"], hashed, u["display_name"], u["title"], u["fdd_role"]),
                )
                print(f"  [CREATE] {u['email']} ({u['display_name']} {u['title']}) — role: {u['fdd_role']}")
    finally:
        cur.close()
        conn.close()

    print("[FDD] 완료")


def seed_kiis(db_url: str) -> None:
    """KIIS DB에 사용자 시딩.

    스키마: id (serial), username, email, hashed_password, title, role, is_active
    """
    print(f"\n{'='*50}")
    print(f"[KIIS] 연결: {db_url}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        ensure_title_column(cur)

        for u in USERS:
            cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
            existing = cur.fetchone()
            if existing:
                hashed = hash_password(u["password"])
                cur.execute(
                    """UPDATE users
                       SET hashed_password = %s, username = %s, title = %s,
                           is_active = true, role = %s
                       WHERE email = %s""",
                    (hashed, u["username"], u["title"], u["kiis_role"], u["email"]),
                )
                print(f"  [UPDATE] {u['email']} ({u['display_name']} {u['title']})")
            else:
                hashed = hash_password(u["password"])
                cur.execute(
                    """INSERT INTO users (username, email, hashed_password, title, role, is_active, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())""",
                    (u["username"], u["email"], hashed, u["title"], u["kiis_role"]),
                )
                print(f"  [CREATE] {u['email']} ({u['display_name']} {u['title']}) — role: {u['kiis_role']}")
    finally:
        cur.close()
        conn.close()

    print("[KIIS] 완료")


def seed_im(db_url: str) -> None:
    """IM DB에 사용자 시딩.

    스키마: id (UUID), email, hashed_password, full_name, title, role, is_active
    """
    print(f"\n{'='*50}")
    print(f"[IM] 연결: {db_url}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        ensure_title_column(cur)

        for u in USERS:
            cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
            existing = cur.fetchone()
            if existing:
                hashed = hash_password(u["password"])
                cur.execute(
                    """UPDATE users
                       SET hashed_password = %s, full_name = %s, title = %s,
                           is_active = true, role = %s
                       WHERE email = %s""",
                    (hashed, u["full_name"], u["title"], u["im_role"], u["email"]),
                )
                print(f"  [UPDATE] {u['email']} ({u['full_name']} {u['title']})")
            else:
                user_id = str(uuid.uuid4())
                hashed = hash_password(u["password"])
                cur.execute(
                    """INSERT INTO users (id, email, hashed_password, full_name, title, role, is_active, created_at, updated_at)
                       VALUES (%s, %s, %s, %s, %s, %s, true, NOW(), NOW())""",
                    (user_id, u["email"], hashed, u["full_name"], u["title"], u["im_role"]),
                )
                print(f"  [CREATE] {u['email']} ({u['full_name']} {u['title']}) — role: {u['im_role']}")
    finally:
        cur.close()
        conn.close()

    print("[IM] 완료")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="AMIC 플랫폼 사용자 시딩 (FDD + KIIS + IM)")
    parser.add_argument(
        "--local",
        action="store_true",
        help="로컬 포트 매핑 사용 (localhost:5433/5434/5435)",
    )
    parser.add_argument("--fdd-url", help="FDD DB URL 직접 지정")
    parser.add_argument("--kiis-url", help="KIIS DB URL 직접 지정")
    parser.add_argument("--im-url", help="IM DB URL 직접 지정")
    args = parser.parse_args()

    dbs = LOCAL_DBS if args.local else DOCKER_DBS

    fdd_url = args.fdd_url or dbs["fdd"]
    kiis_url = args.kiis_url or dbs["kiis"]
    im_url = args.im_url or dbs["im"]

    print("=" * 50)
    print("AMIC 플랫폼 — 사용자 시딩")
    print(f"대상 계정: {len(USERS)}명")
    for u in USERS:
        print(f"  - {u['email']} ({u['display_name']} {u['title']}) — {u['fdd_role']}")
    print("=" * 50)

    errors = []

    # FDD
    try:
        seed_fdd(fdd_url)
    except psycopg2.OperationalError as e:
        print(f"\n[FDD] DB 연결 실패: {e}")
        errors.append("FDD")

    # KIIS
    try:
        seed_kiis(kiis_url)
    except psycopg2.OperationalError as e:
        print(f"\n[KIIS] DB 연결 실패: {e}")
        errors.append("KIIS")

    # IM
    try:
        seed_im(im_url)
    except psycopg2.OperationalError as e:
        print(f"\n[IM] DB 연결 실패: {e}")
        errors.append("IM")

    # 결과 요약
    print(f"\n{'='*50}")
    if errors:
        print(f"일부 DB 연결 실패: {', '.join(errors)}")
        print("  Docker 컨테이너가 실행 중인지 확인하세요: docker compose ps")
    else:
        print("전체 시딩 완료!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
