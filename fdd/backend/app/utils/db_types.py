"""Database type utilities for cross-dialect compatibility.

SQLite does not support PostgreSQL JSONB. Use `JsonbColumn` instead
of importing JSONB directly to ensure tests work with SQLite while
production uses native JSONB.
"""

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# Use this instead of JSONB directly in mapped_column() definitions.
# On PostgreSQL it renders as JSONB, on SQLite it renders as JSON.
JsonbColumn = JSON().with_variant(JSONB(), "postgresql")
