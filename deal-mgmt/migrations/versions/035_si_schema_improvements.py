"""SI 매핑 스키마 개선: io_sectors 마스터, ksic_classifications, 유니크 제약, FK, 복합 인덱스, 유발계수 테이블.

Revision ID: 035
Revises: 034
"""

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. io_sectors 마스터 테이블 생성 ──────────────────
    op.create_table(
        "io_sectors",
        sa.Column("code", sa.String(20), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
    )

    # ── 2. 기존 테이블 중복 제거 (유니크 제약 추가 전 필수) ──
    op.execute(
        sa.text(
            "DELETE FROM ksic_io_mappings WHERE id NOT IN ("
            "  SELECT MIN(id) FROM ksic_io_mappings GROUP BY io_code, ksic_code"
            ")"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM io_transactions WHERE id NOT IN ("
            "  SELECT MIN(id) FROM io_transactions"
            "  GROUP BY source_io_code, target_io_code"
            ")"
        )
    )

    # ── 3. 유니크 제약 추가 ───────────────────────────────
    op.create_unique_constraint(
        "uq_ksic_io_mapping", "ksic_io_mappings", ["io_code", "ksic_code"]
    )
    op.create_unique_constraint(
        "uq_io_txn_src_tgt", "io_transactions", ["source_io_code", "target_io_code"]
    )

    # ── 4. FK 추가 (batch_alter_table — SQLite 호환) ──────
    with op.batch_alter_table("io_transactions") as batch_op:
        batch_op.create_foreign_key(
            "fk_io_txn_source", "io_sectors", ["source_io_code"], ["code"]
        )
        batch_op.create_foreign_key(
            "fk_io_txn_target", "io_sectors", ["target_io_code"], ["code"]
        )

    with op.batch_alter_table("ksic_io_mappings") as batch_op:
        batch_op.create_foreign_key(
            "fk_ksic_io_code", "io_sectors", ["io_code"], ["code"]
        )

    # ── 5. 복합 인덱스 추가 (쿼리 패턴 최적화) ────────────
    # backward chain: WHERE target_io_code IN (...) GROUP BY source_io_code
    op.create_index(
        "ix_io_txn_tgt_src", "io_transactions", ["target_io_code", "source_io_code"]
    )
    # KSIC→IO 브릿지: WHERE ksic_code IN (...) → io_code
    op.create_index(
        "ix_ksic_io_ksic_io", "ksic_io_mappings", ["ksic_code", "io_code"]
    )

    # ── 6. 유발계수 테이블 2종 생성 ───────────────────────
    op.create_table(
        "io_production_inducements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_io_code",
            sa.String(20),
            sa.ForeignKey("io_sectors.code"),
            nullable=False,
        ),
        sa.Column(
            "target_io_code",
            sa.String(20),
            sa.ForeignKey("io_sectors.code"),
            nullable=False,
        ),
        sa.Column("coefficient", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint(
            "source_io_code", "target_io_code", name="uq_prod_ind_src_tgt"
        ),
    )
    op.create_index(
        "ix_prod_ind_source", "io_production_inducements", ["source_io_code"]
    )
    op.create_index(
        "ix_prod_ind_target", "io_production_inducements", ["target_io_code"]
    )

    op.create_table(
        "io_value_added_inducements",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_io_code",
            sa.String(20),
            sa.ForeignKey("io_sectors.code"),
            nullable=False,
        ),
        sa.Column(
            "target_io_code",
            sa.String(20),
            sa.ForeignKey("io_sectors.code"),
            nullable=False,
        ),
        sa.Column("coefficient", sa.Numeric(20, 10), nullable=False),
        sa.UniqueConstraint(
            "source_io_code", "target_io_code", name="uq_va_ind_src_tgt"
        ),
    )
    op.create_index(
        "ix_va_ind_source", "io_value_added_inducements", ["source_io_code"]
    )
    op.create_index(
        "ix_va_ind_target", "io_value_added_inducements", ["target_io_code"]
    )

    # ── 7. KSIC 산업분류 참조 테이블 (4계층, 305행) ──────────
    op.create_table(
        "ksic_classifications",
        sa.Column("basic_code", sa.String(10), primary_key=True),
        sa.Column("basic_name", sa.String(200), nullable=False),
        sa.Column("sub_code", sa.String(10), nullable=True),
        sa.Column("sub_name", sa.String(200), nullable=True),
        sa.Column("mid_code", sa.String(10), nullable=True),
        sa.Column("mid_name", sa.String(200), nullable=True),
        sa.Column("large_code", sa.String(10), nullable=True),
        sa.Column("large_name", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    # KSIC 분류 테이블 삭제
    op.drop_table("ksic_classifications")

    # 유발계수 테이블 삭제
    op.drop_index("ix_va_ind_target", table_name="io_value_added_inducements")
    op.drop_index("ix_va_ind_source", table_name="io_value_added_inducements")
    op.drop_table("io_value_added_inducements")

    op.drop_index("ix_prod_ind_target", table_name="io_production_inducements")
    op.drop_index("ix_prod_ind_source", table_name="io_production_inducements")
    op.drop_table("io_production_inducements")

    # 복합 인덱스 삭제
    op.drop_index("ix_ksic_io_ksic_io", table_name="ksic_io_mappings")
    op.drop_index("ix_io_txn_tgt_src", table_name="io_transactions")

    # FK 삭제
    with op.batch_alter_table("ksic_io_mappings") as batch_op:
        batch_op.drop_constraint("fk_ksic_io_code", type_="foreignkey")

    with op.batch_alter_table("io_transactions") as batch_op:
        batch_op.drop_constraint("fk_io_txn_target", type_="foreignkey")
        batch_op.drop_constraint("fk_io_txn_source", type_="foreignkey")

    # 유니크 제약 삭제
    with op.batch_alter_table("io_transactions") as batch_op:
        batch_op.drop_constraint("uq_io_txn_src_tgt", type_="unique")

    with op.batch_alter_table("ksic_io_mappings") as batch_op:
        batch_op.drop_constraint("uq_ksic_io_mapping", type_="unique")

    # io_sectors 삭제
    op.drop_table("io_sectors")
