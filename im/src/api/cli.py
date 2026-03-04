"""CLI 유틸리티 — ADMIN 시드 생성.

> 마지막 수정: 2026-02-10 19:30:00

배포 후 최초 ADMIN 계정을 생성하는 CLI 명령을 제공한다.

사용법:
    python -m src.api.cli create-admin --email admin@example.com --password P@ssw0rd --name 관리자
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from src.api.db.models.user import User
from src.api.db import session as db_session
from src.api.security.password import hash_password


async def _create_admin(email: str, password: str, full_name: str) -> None:
    """ADMIN 사용자를 생성한다.

    Args:
        email: 이메일 주소.
        password: 평문 비밀번호.
        full_name: 이름.
    """
    db_session.init_engine()
    assert db_session.AsyncSessionFactory is not None
    async with db_session.AsyncSessionFactory() as session:  # type: AsyncSession
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none() is not None:
            print(f"이미 존재하는 이메일입니다: {email}")
            sys.exit(1)

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role="ADMIN",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        print(f"ADMIN 계정 생성 완료: {user.email} (id={user.id})")


def main() -> None:
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(description="Auto-IM Generator CLI")
    sub = parser.add_subparsers(dest="command")

    create_admin = sub.add_parser("create-admin", help="ADMIN 계정 생성")
    create_admin.add_argument("--email", required=True, help="이메일 주소")
    create_admin.add_argument("--password", required=True, help="비밀번호")
    create_admin.add_argument("--name", required=True, help="이름")

    args = parser.parse_args()

    if args.command == "create-admin":
        asyncio.run(_create_admin(args.email, args.password, args.name))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
