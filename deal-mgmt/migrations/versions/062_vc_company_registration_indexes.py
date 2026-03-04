"""062 — vc_companies 테이블에 법인등록번호·사업자등록번호 인덱스 추가

등록번호 기반 VC 기업 조회 시 114,964건 full-scan 방지.

Revision ID: 062
Revises: 061
"""

from alembic import op

revision = "062"
down_revision = "061"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_vc_companies_corp_reg_no", "vc_companies", ["corp_reg_no"])
    op.create_index("ix_vc_companies_biz_reg_no", "vc_companies", ["biz_reg_no"])


def downgrade() -> None:
    op.drop_index("ix_vc_companies_biz_reg_no", table_name="vc_companies")
    op.drop_index("ix_vc_companies_corp_reg_no", table_name="vc_companies")
