"""Restructure DDWorkstream enum: FDD/LDD/TDD sub-categories.

Revision ID: 013
Revises: 012_ralph_phase2
"""

from alembic import op

revision = "013"
down_revision = "012_ralph_phase2"

OLD_VALUES = [
    "FINANCIAL", "LEGAL", "TAX", "COMMERCIAL",
    "IT", "HR", "ENVIRONMENTAL", "INSURANCE", "OTHER",
]

NEW_VALUES = [
    # FDD
    "FDD_FINANCIAL_STATEMENTS", "FDD_REVENUE", "FDD_WORKING_CAPITAL",
    "FDD_DEBT_CASH", "FDD_PROJECTIONS",
    # LDD
    "LDD_CORPORATE", "LDD_PERMITS", "LDD_CONTRACTS", "LDD_ASSETS",
    "LDD_LABOR", "LDD_LITIGATION", "LDD_IP", "LDD_INSURANCE", "LDD_ENVIRONMENT",
    # TDD
    "TDD_CORPORATE_TAX", "TDD_VAT", "TDD_TRANSFER_PRICING",
    "TDD_WITHHOLDING", "TDD_TAX_INCENTIVES",
    # Other
    "OTHER",
]

# Best-effort mapping for any existing rows
MIGRATION_MAP = {
    "FINANCIAL": "FDD_FINANCIAL_STATEMENTS",
    "LEGAL": "LDD_CORPORATE",
    "TAX": "TDD_CORPORATE_TAX",
    "COMMERCIAL": "OTHER",
    "IT": "OTHER",
    "HR": "LDD_LABOR",
    "ENVIRONMENTAL": "LDD_ENVIRONMENT",
    "INSURANCE": "LDD_INSURANCE",
}


def upgrade() -> None:
    # 1. Add a temporary text column
    op.execute("ALTER TABLE dd_checklists ADD COLUMN _ws_tmp TEXT")
    op.execute("UPDATE dd_checklists SET _ws_tmp = workstream::TEXT")

    # 2. Drop the workstream column (which depends on the old enum)
    op.execute("ALTER TABLE dd_checklists ALTER COLUMN workstream DROP DEFAULT")
    op.execute("ALTER TABLE dd_checklists ALTER COLUMN workstream TYPE TEXT USING workstream::TEXT")

    # 3. Drop old enum and create new one
    op.execute("DROP TYPE IF EXISTS ddworkstream")
    enum_vals = ", ".join(f"'{v}'" for v in NEW_VALUES)
    op.execute(f"CREATE TYPE ddworkstream AS ENUM ({enum_vals})")

    # 4. Migrate existing data
    for old_val, new_val in MIGRATION_MAP.items():
        op.execute(
            f"UPDATE dd_checklists SET _ws_tmp = '{new_val}' WHERE _ws_tmp = '{old_val}'"
        )

    # 5. Convert column back to enum
    op.execute(
        "ALTER TABLE dd_checklists "
        "ALTER COLUMN workstream TYPE ddworkstream USING _ws_tmp::ddworkstream"
    )
    op.execute("ALTER TABLE dd_checklists DROP COLUMN _ws_tmp")


def downgrade() -> None:
    op.execute("ALTER TABLE dd_checklists ADD COLUMN _ws_tmp TEXT")
    op.execute("UPDATE dd_checklists SET _ws_tmp = workstream::TEXT")
    op.execute("ALTER TABLE dd_checklists ALTER COLUMN workstream TYPE TEXT USING workstream::TEXT")

    op.execute("DROP TYPE IF EXISTS ddworkstream")
    enum_vals = ", ".join(f"'{v}'" for v in OLD_VALUES)
    op.execute(f"CREATE TYPE ddworkstream AS ENUM ({enum_vals})")

    # Reverse mapping
    reverse_map = {
        "FDD_FINANCIAL_STATEMENTS": "FINANCIAL", "FDD_REVENUE": "FINANCIAL",
        "FDD_WORKING_CAPITAL": "FINANCIAL", "FDD_DEBT_CASH": "FINANCIAL",
        "FDD_PROJECTIONS": "FINANCIAL",
        "LDD_CORPORATE": "LEGAL", "LDD_PERMITS": "LEGAL", "LDD_CONTRACTS": "LEGAL",
        "LDD_ASSETS": "LEGAL", "LDD_LABOR": "HR", "LDD_LITIGATION": "LEGAL",
        "LDD_IP": "LEGAL", "LDD_INSURANCE": "INSURANCE", "LDD_ENVIRONMENT": "ENVIRONMENTAL",
        "TDD_CORPORATE_TAX": "TAX", "TDD_VAT": "TAX", "TDD_TRANSFER_PRICING": "TAX",
        "TDD_WITHHOLDING": "TAX", "TDD_TAX_INCENTIVES": "TAX",
    }
    for new_val, old_val in reverse_map.items():
        op.execute(
            f"UPDATE dd_checklists SET _ws_tmp = '{old_val}' WHERE _ws_tmp = '{new_val}'"
        )

    op.execute(
        "ALTER TABLE dd_checklists "
        "ALTER COLUMN workstream TYPE ddworkstream USING _ws_tmp::ddworkstream"
    )
    op.execute("ALTER TABLE dd_checklists DROP COLUMN _ws_tmp")
