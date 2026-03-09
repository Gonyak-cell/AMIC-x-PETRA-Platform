"""076 — DealType enum 변경: MA/PE/RE/IB → SE/BU/ISSUE/HYB/GEN

기존 4가지 딜 타입을 실제 업무에 맞는 5가지로 전면 교체한다.
- SE: 매각 자문 (Sell-side advisory)
- BU: 인수 (Buy-side)
- ISSUE: 신주유치 (New share issuance)
- HYB: 매각+신주유치 (Hybrid)
- GEN: 기타자문 (General advisory)

기존 데이터 매핑: MA→SE, PE→BU, RE→GEN, IB→GEN

Revision ID: 076
Revises: 075
"""

from alembic import op

revision = "076"
down_revision = "075"
branch_labels = None
depends_on = None

OLD_VALUES = ("MA", "PE", "RE", "IB")
NEW_VALUES = ("SE", "BU", "ISSUE", "HYB", "GEN")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # PostgreSQL: ENUM 타입 교체 전략
        # 1) 새 ENUM 타입 생성
        op.execute("CREATE TYPE dealtype_new AS ENUM ('SE', 'BU', 'ISSUE', 'HYB', 'GEN')")
        # 1.5) 기존 DEFAULT 제거 (구 enum 타입에 묶여 있어 타입 변환 차단)
        op.execute("ALTER TABLE transactions ALTER COLUMN deal_type DROP DEFAULT")
        # 2) 기존 데이터를 text로 변환 후 매핑
        op.execute(
            """
            ALTER TABLE transactions
            ALTER COLUMN deal_type TYPE text
            USING deal_type::text
            """
        )
        op.execute("UPDATE transactions SET deal_type = 'SE' WHERE deal_type = 'MA'")
        op.execute("UPDATE transactions SET deal_type = 'BU' WHERE deal_type = 'PE'")
        op.execute("UPDATE transactions SET deal_type = 'GEN' WHERE deal_type = 'RE'")
        op.execute("UPDATE transactions SET deal_type = 'GEN' WHERE deal_type = 'IB'")
        # 3) 새 ENUM 타입으로 컬럼 교체
        op.execute(
            """
            ALTER TABLE transactions
            ALTER COLUMN deal_type TYPE dealtype_new
            USING deal_type::dealtype_new
            """
        )
        # 4) default 값 변경
        op.execute("ALTER TABLE transactions ALTER COLUMN deal_type SET DEFAULT 'SE'")
        # 5) 구 ENUM 타입 삭제 및 이름 변경
        op.execute("DROP TYPE IF EXISTS dealtype")
        op.execute("ALTER TYPE dealtype_new RENAME TO dealtype")
    else:
        # SQLite: VARCHAR 기반이므로 데이터만 변환
        op.execute("UPDATE transactions SET deal_type = 'SE' WHERE deal_type = 'MA'")
        op.execute("UPDATE transactions SET deal_type = 'BU' WHERE deal_type = 'PE'")
        op.execute("UPDATE transactions SET deal_type = 'GEN' WHERE deal_type = 'RE'")
        op.execute("UPDATE transactions SET deal_type = 'GEN' WHERE deal_type = 'IB'")


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # 역변환: SE→MA, BU→PE, ISSUE→MA, HYB→MA, GEN→IB (ISSUE/HYB는 구 체계에 대응 없음)
        op.execute("CREATE TYPE dealtype_old AS ENUM ('MA', 'PE', 'RE', 'IB')")
        op.execute(
            """
            ALTER TABLE transactions
            ALTER COLUMN deal_type TYPE text
            USING deal_type::text
            """
        )
        op.execute("UPDATE transactions SET deal_type = 'MA' WHERE deal_type = 'SE'")
        op.execute("UPDATE transactions SET deal_type = 'PE' WHERE deal_type = 'BU'")
        op.execute("UPDATE transactions SET deal_type = 'MA' WHERE deal_type = 'ISSUE'")
        op.execute("UPDATE transactions SET deal_type = 'MA' WHERE deal_type = 'HYB'")
        op.execute("UPDATE transactions SET deal_type = 'IB' WHERE deal_type = 'GEN'")
        op.execute(
            """
            ALTER TABLE transactions
            ALTER COLUMN deal_type TYPE dealtype_old
            USING deal_type::dealtype_old
            """
        )
        op.execute("ALTER TABLE transactions ALTER COLUMN deal_type SET DEFAULT 'MA'")
        op.execute("DROP TYPE IF EXISTS dealtype")
        op.execute("ALTER TYPE dealtype_old RENAME TO dealtype")
    else:
        # SQLite 역변환
        op.execute("UPDATE transactions SET deal_type = 'MA' WHERE deal_type = 'SE'")
        op.execute("UPDATE transactions SET deal_type = 'PE' WHERE deal_type = 'BU'")
        op.execute("UPDATE transactions SET deal_type = 'MA' WHERE deal_type = 'ISSUE'")
        op.execute("UPDATE transactions SET deal_type = 'MA' WHERE deal_type = 'HYB'")
        op.execute("UPDATE transactions SET deal_type = 'IB' WHERE deal_type = 'GEN'")
