"""SI 시딩 재실행 — 036이 프로덕션에서 stamp-only 된 경우 대응.

프로덕션에서 036 마이그레이션이 VARCHAR(20) 초과 데이터로 실패 후
stamp head 폴백됨. 이 마이그레이션은 수정된 036 로직을 재실행한다.
이미 데이터가 있으면 스킵(idempotent).

Revision ID: 037
Revises: 036
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    # 036 모듈을 동적 로딩하여 upgrade() 재실행 (idempotent)
    mod_path = Path(__file__).parent / "036_seed_si_reference_data.py"
    spec = importlib.util.spec_from_file_location("migration_036", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    logger.info("036 시딩 로직 재실행 (stamp-only 복구)")
    mod.upgrade()


def downgrade() -> None:
    # 036의 downgrade가 데이터 삭제 담당
    pass
