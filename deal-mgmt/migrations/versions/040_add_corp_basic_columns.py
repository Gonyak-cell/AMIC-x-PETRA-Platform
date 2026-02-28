"""SI 기업 테이블에 기업기본정보 컬럼 10개 추가.

금융위 getCorpOutline_V2 API 데이터를 사전 적재하여
SI 상세 패널에서 즉시 표시할 수 있도록 한다.

Revision ID: 040
Revises: 039
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "040"
down_revision = "039"
branch_labels = None
depends_on = None

_TABLE = "si_companies"

_COLUMNS: list[tuple[str, sa.types.TypeEngine, dict]] = [
    ("representative", sa.String(200), {"comment": "대표자 (enpRprFnm)"}),
    ("founded_date", sa.String(8), {"comment": "설립일 YYYYMMDD (enpEstbDt)"}),
    ("address", sa.Text(), {"comment": "기본주소 (enpBsadr)"}),
    ("homepage", sa.String(500), {"comment": "홈페이지 URL (enpHmpgUrl)"}),
    ("employee_count", sa.String(20), {"comment": "종업원수 (enpEmpeCnt)"}),
    ("industry_name", sa.String(300), {"comment": "업종명 (sicNm)"}),
    ("main_business", sa.Text(), {"comment": "주요사업 (enpMainBizNm)"}),
    ("market_type", sa.String(20), {"comment": "시장구분 P:유가 K:코스닥 N:코넥스 E:기타"}),
    (
        "market_type_name",
        sa.String(50),
        {"comment": "시장구분명 (corpRegMrktDcdNm)"},
    ),
    (
        "corp_basic_synced_at",
        sa.DateTime(timezone=True),
        {"comment": "기업기본정보 최종 동기화 시점"},
    ),
]


def upgrade() -> None:
    for col_name, col_type, kwargs in _COLUMNS:
        op.add_column(
            _TABLE,
            sa.Column(col_name, col_type, nullable=True, **kwargs),
        )


def downgrade() -> None:
    for col_name, _col_type, _kwargs in reversed(_COLUMNS):
        op.drop_column(_TABLE, col_name)
