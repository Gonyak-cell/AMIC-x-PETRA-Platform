"""협상 워크스페이스 — ContractType BTA/SSA, IssueDecisionStatus, NegotiationIssue 확장, ContractMarkup markup_type.

Revision ID: 030
Revises: 029
"""

import sqlalchemy as sa
from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. ContractType enum에 BTA, SSA 추가
    op.execute("ALTER TYPE contracttype ADD VALUE IF NOT EXISTS 'BTA'")
    op.execute("ALTER TYPE contracttype ADD VALUE IF NOT EXISTS 'SSA'")

    # 2. IssueDecisionStatus enum 생성
    issuedecisionstatus = sa.Enum(
        "PENDING", "CONSIDER_ACCEPTING", "CANNOT_ACCEPT",
        name="issuedecisionstatus",
    )
    issuedecisionstatus.create(op.get_bind(), checkfirst=True)

    # 3. negotiation_issues 테이블 확장
    op.add_column(
        "negotiation_issues",
        sa.Column("contract_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_negotiation_issues_contract_id",
        "negotiation_issues",
        "contracts",
        ["contract_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_negotiation_issues_contract_id", "negotiation_issues", ["contract_id"])

    op.add_column(
        "negotiation_issues",
        sa.Column(
            "decision_status",
            sa.Enum("PENDING", "CONSIDER_ACCEPTING", "CANNOT_ACCEPT", name="issuedecisionstatus"),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.add_column(
        "negotiation_issues",
        sa.Column("linked_issue_ids", sa.dialects.postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "negotiation_issues",
        sa.Column("markup_version_number", sa.Integer, nullable=True),
    )

    # 4. contract_markups 테이블에 markup_type 추가
    op.add_column(
        "contract_markups",
        sa.Column("markup_type", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    # contract_markups
    op.drop_column("contract_markups", "markup_type")

    # negotiation_issues
    op.drop_column("negotiation_issues", "markup_version_number")
    op.drop_column("negotiation_issues", "linked_issue_ids")
    op.drop_column("negotiation_issues", "decision_status")
    op.drop_index("ix_negotiation_issues_contract_id", "negotiation_issues")
    op.drop_constraint("fk_negotiation_issues_contract_id", "negotiation_issues", type_="foreignkey")
    op.drop_column("negotiation_issues", "contract_id")

    # IssueDecisionStatus enum 삭제
    sa.Enum(name="issuedecisionstatus").drop(op.get_bind(), checkfirst=True)

    # ContractType에서 BTA, SSA 제거는 PostgreSQL에서 불가 (ADD VALUE는 비가역적)
