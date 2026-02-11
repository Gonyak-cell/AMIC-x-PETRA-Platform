"""FDD DB에 기본 admin 사용자를 생성하는 시딩 스크립트.

사용법:
  # Docker 환경 (기본 DB URL)
  python scripts/seed-users.py

  # 로컬 환경 (커스텀 DB URL)
  python scripts/seed-users.py --db-url postgresql://autofdd:autofdd_dev@localhost:5433/autofdd

  # 커스텀 admin 정보
  python scripts/seed-users.py --email admin@company.com --password MySecurePass!
"""

import argparse
import hashlib
import os
import sys
import uuid

try:
    import psycopg2
except ImportError:
    print("Error: psycopg2 패키지가 필요합니다.")
    print("  pip install psycopg2-binary")
    sys.exit(1)


# ---------------------------------------------------------------------------
# 패스워드 해싱 (Auto FDD/backend/app/auth/password.py 로직과 동일)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """PBKDF2 + salt 해싱."""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return salt.hex() + ":" + key.hex()


# ---------------------------------------------------------------------------
# 시딩 로직
# ---------------------------------------------------------------------------

DEFAULT_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://autofdd:autofdd_dev@fdd-db:5432/autofdd",
)

DEFAULT_EMAIL = "admin@amic.com"
DEFAULT_PASSWORD = "admin1234!"
DEFAULT_DISPLAY_NAME = "관리자"
DEFAULT_ROLE = "ADMIN"


def seed_admin(db_url: str, email: str, password: str, display_name: str) -> None:
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        # 중복 확인 (멱등성)
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            print(f"이미 존재하는 사용자입니다: {email} (id: {existing[0]})")
            return

        user_id = str(uuid.uuid4())
        hashed = hash_password(password)

        cur.execute(
            """
            INSERT INTO users (id, email, hashed_password, display_name, role, is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, true, NOW(), NOW())
            """,
            (user_id, email, hashed, display_name, DEFAULT_ROLE),
        )
        print(f"Admin 사용자 생성 완료: {email} (id: {user_id})")
        print(f"  비밀번호: {password}")
        print(f"  역할: {DEFAULT_ROLE}")
        print()
        print("⚠ 최초 로그인 후 비밀번호를 변경하세요.")

    finally:
        cur.close()
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="FDD DB에 기본 admin 사용자 생성")
    parser.add_argument(
        "--db-url",
        default=DEFAULT_DB_URL,
        help=f"PostgreSQL 연결 URL (기본값: DATABASE_URL 환경변수 또는 {DEFAULT_DB_URL})",
    )
    parser.add_argument("--email", default=DEFAULT_EMAIL, help=f"Admin 이메일 (기본값: {DEFAULT_EMAIL})")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Admin 비밀번호 (기본값: admin1234!)")
    parser.add_argument("--display-name", default=DEFAULT_DISPLAY_NAME, help=f"표시 이름 (기본값: {DEFAULT_DISPLAY_NAME})")
    args = parser.parse_args()

    print(f"DB 연결: {args.db_url}")
    print()

    try:
        seed_admin(args.db_url, args.email, args.password, args.display_name)
    except psycopg2.OperationalError as e:
        print(f"DB 연결 실패: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
