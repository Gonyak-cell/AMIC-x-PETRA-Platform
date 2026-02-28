---
paths:
  - "fdd/**/*.py"
  - "kiis/**/*.py"
  - "im/**/*.py"
  - "deal-mgmt/**/*.py"
---
# Python Style Guide (백엔드 통합)

## Naming Conventions
| Target | Convention | Example |
|--------|-----------|---------|
| Files, functions, variables | snake_case | `kofia_service.py`, `calculate_ebitda()` |
| Classes | PascalCase | `DocumentService`, `FundListResponse` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `CACHE_TTL` |
| Private | Leading underscore | `_helper_func()`, `_internal_var` |

## Type Hints (Required)
```python
from decimal import Decimal
from collections.abc import Sequence

# Use X | None instead of Optional[X]
def get_company(corp_code: str | None = None) -> CompanyResponse | None:
    ...

# Generic type hints for collections
def calculate_total(items: Sequence[Decimal]) -> Decimal:
    ...
```

## SQLAlchemy Models (2.0 Style)
```python
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID, uuid4

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

## Pydantic Schemas (v2)
```python
from pydantic import BaseModel, ConfigDict

class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
```

## Imports Order (ruff handles)
1. Standard library
2. Third-party
3. Local application

## Error Handling
```python
# Never bare except
try:
    ...
except ValueError as e:
    logger.error("Validation failed", exc_info=True)
    raise HTTPException(status_code=422, detail=str(e)) from e
```

## Docstrings
- Required for public functions
- Google style format
- Include type info in signature, not docstring

```python
def process_data(input_data: dict[str, Any]) -> ProcessedResult:
    """Process input data and return structured result.

    Args:
        input_data: Raw data dictionary from upload.

    Returns:
        Processed and validated result.

    Raises:
        HTTPException: If validation fails.
    """
```

## Prohibited Patterns
- `from module import *` — wildcard imports
- `except:` or `except Exception:` without re-raise
- `float` for monetary values (use `Decimal`)
- Mutable default arguments (`def f(items=[])`)
