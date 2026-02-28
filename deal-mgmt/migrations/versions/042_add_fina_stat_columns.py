"""SI 기업 테이블에 재무정보 컬럼 12개 + 기본정보 기준일자 1개 추가.

금융위 getSummFinaStat_V2 API의 전체 재무 필드(영업이익, 당기순이익,
자산총계, 부채총계 등)와 기준일자/보고서 구분을 사전 적재하여
SI 목록 및 상세 패널에서 즉시 표시할 수 있도록 한다.

기업기본정보(getCorpOutline_V2)의 기준일자(basDt)도 추가한다.

Revision ID: 042
Revises: 041
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "042"
down_revision = "041"
branch_labels = None
depends_on = None

_TABLE = "si_companies"

_COLUMNS: list[tuple[str, sa.types.TypeEngine, dict]] = [
    # ── 재무정보 금액 (getSummFinaStat_V2) ──
    ("operating_profit", sa.Numeric(20, 2), {"comment": "영업이익 (enpBzopPft)"}),
    ("net_income", sa.Numeric(20, 2), {"comment": "당기순이익 (enpCrtmNpf)"}),
    ("total_assets", sa.Numeric(20, 2), {"comment": "자산총계 (enpTastAmt)"}),
    ("total_debt", sa.Numeric(20, 2), {"comment": "부채총계 (enpTdbtAmt)"}),
    ("total_equity", sa.Numeric(20, 2), {"comment": "자본총계 (enpTcptAmt)"}),
    ("capital_amount", sa.Numeric(20, 2), {"comment": "자본금 (enpCptlAmt)"}),
    (
        "debt_ratio",
        sa.Numeric(10, 4),
        {"comment": "부채비율 % (fnclDebtRto)"},
    ),
    (
        "pretax_income",
        sa.Numeric(20, 2),
        {"comment": "법인세차감전순이익 (iclsPalClcAmt)"},
    ),
    # ── 재무정보 메타 ──
    (
        "fina_base_date",
        sa.String(8),
        {"comment": "재무정보 기준일자 YYYYMMDD (basDt)"},
    ),
    (
        "fina_report_code",
        sa.String(5),
        {"comment": "회계보고서 구분코드 (fnclDcd)"},
    ),
    (
        "fina_report_name",
        sa.String(50),
        {"comment": "회계보고서 구분명 (fnclDcdNm)"},
    ),
    (
        "fina_stat_synced_at",
        sa.DateTime(timezone=True),
        {"comment": "재무정보 최종 동기화 시점"},
    ),
    # ── 기업기본정보 메타 (getCorpOutline_V2) ──
    (
        "corp_basic_base_date",
        sa.String(8),
        {"comment": "기본정보 기준일자 YYYYMMDD (basDt)"},
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
