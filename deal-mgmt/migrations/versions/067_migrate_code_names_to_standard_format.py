"""067 — 기존 거래 코드명을 표준 형식(MA26-XXX-NN)으로 마이그레이션

명명 원칙: {거래타입}{연도2자리}-{프로젝트명첫3자대문자}-{연도내순번2자리}
예시: MA26-EDW-01

대상 거래 (4건):
  EDWARD       → MA26-EDW-01  (Project Edward, 롯데에코웰(주))
  Project Spicy → MA26-SPI-02  (Project Spicy, 해들촌)
  NEXT         → MA26-NEX-03  (Project Next, 주식회사 엔엑스쓰리게임즈)
  TITAN        → MA26-TIT-04  (Project Titan, (주)타이탄컴퍼니)

Revision ID: 067
Revises: 066
Create Date: 2026-03-05
"""

from alembic import op

revision = "067"
down_revision = "066"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE transactions SET code_name = 'MA26-EDW-01' WHERE code_name = 'EDWARD'")
    op.execute("UPDATE transactions SET code_name = 'MA26-SPI-02' WHERE code_name = 'Project Spicy'")
    op.execute("UPDATE transactions SET code_name = 'MA26-NEX-03' WHERE code_name = 'NEXT'")
    op.execute("UPDATE transactions SET code_name = 'MA26-TIT-04' WHERE code_name = 'TITAN'")


def downgrade() -> None:
    op.execute("UPDATE transactions SET code_name = 'EDWARD' WHERE code_name = 'MA26-EDW-01'")
    op.execute("UPDATE transactions SET code_name = 'Project Spicy' WHERE code_name = 'MA26-SPI-02'")
    op.execute("UPDATE transactions SET code_name = 'NEXT' WHERE code_name = 'MA26-NEX-03'")
    op.execute("UPDATE transactions SET code_name = 'TITAN' WHERE code_name = 'MA26-TIT-04'")
