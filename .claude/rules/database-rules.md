---
paths:
  - "fdd/**/models/**/*.py"
  - "fdd/**/alembic/**/*.py"
  - "kiis/**/models/**/*.py"
  - "kiis/**/migrations/**/*.py"
  - "im/**/models/**/*.py"
  - "im/**/alembic/**/*.py"
---
# Database Rules (백엔드 통합)

## Schema Conventions
| Target | Convention | Example |
|--------|-----------|---------|
| Table names | snake_case plural | `documents`, `fund_prices`, `journal_entries` |
| Column names | snake_case | `created_at`, `corp_code`, `data_source` |
| Primary keys | `id` (UUID) | `id: Mapped[UUID]` |
| Foreign keys | `{table}_id` | `document_id`, `deal_id` |

## Sync Model Pattern (FDD)
```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import UUID, uuid4

class Deal(Base):
    __tablename__ = "deals"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
```

## Async Model Pattern (KIIS / IM)
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_company(session: AsyncSession, corp_code: str) -> Company | None:
    stmt = select(Company).where(Company.corp_code == corp_code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
```

## Money Columns — CRITICAL
```python
from sqlalchemy import Numeric
from decimal import Decimal

amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
```
**NEVER use Float, REAL, or INTEGER for monetary values.**

## N+1 Query Prevention
```python
from sqlalchemy.orm import selectinload, joinedload

# GOOD — Eager loading
stmt = select(Deal).options(selectinload(Deal.snapshots))

# BAD — N+1 query
deals = session.execute(select(Deal)).scalars().all()
for deal in deals:
    snapshots = deal.snapshots  # Lazy load per iteration!
```

## Alembic Migrations
- All models must be imported in the module's `__init__.py` for autogenerate
- Never modify existing migrations in production
- Test round-trip: upgrade → downgrade → upgrade
- Migration paths:
  - FDD: `fdd/backend/alembic/versions/`
  - KIIS: `kiis/migrations/versions/`
  - IM: `im/alembic/versions/`

## Enum Columns
```python
import enum
from sqlalchemy import Enum as SQLEnum

class DataSource(str, enum.Enum):
    DART = "DART"
    MANUAL = "MANUAL"
    EXCEL = "EXCEL"

data_source: Mapped[DataSource] = mapped_column(
    SQLEnum(DataSource), default=DataSource.DART
)
```

## Query Patterns
```python
# Use select() instead of legacy query()
from sqlalchemy import select

stmt = select(Fund).where(Fund.fund_type == "stock").offset(skip).limit(limit)
```
