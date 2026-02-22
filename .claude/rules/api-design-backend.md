---
paths:
  - "fdd/**/api/**/*.py"
  - "fdd/**/routers/**/*.py"
  - "kiis/**/routers/**/*.py"
  - "im/**/routes/**/*.py"
  - "fdd/**/schemas/**/*.py"
  - "kiis/**/schemas/**/*.py"
  - "im/**/schemas/**/*.py"
---
# Backend API Design Rules

## URL Conventions
```
GET    /api/v1/{resource}                # List
POST   /api/v1/{resource}                # Create
GET    /api/v1/{resource}/{id}           # Get one
PUT    /api/v1/{resource}/{id}           # Update
DELETE /api/v1/{resource}/{id}           # Delete

# Nested resources
GET    /api/v1/deals/{deal_id}/qoe       # Deal's QoE
POST   /api/v1/documents/{id}/regenerate # Action (kebab-case)
```

## Module Port Mapping
| Module | Port | Prefix |
|--------|------|--------|
| FDD | 8000 | `/api/v1/` |
| KIIS | 8001 | `/api/v1/` |
| IM | 8002 | `/api/v1/` |

## Router Pattern
```python
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/funds", tags=["funds"])

@router.get("/")
async def list_funds(
    skip: int = 0,
    limit: int = Query(default=20, le=100),
) -> PaginatedResponse[FundResponse]:
    ...
```

## Route Order (CRITICAL)
```python
# Static routes BEFORE dynamic routes
@router.get("/gp")              # First — static
@router.get("/{fund_code}")     # Second — dynamic
# Otherwise "gp" gets parsed as fund_code
```

## Response Schemas
```python
from pydantic import BaseModel, ConfigDict

class FundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    fund_name: str
    nav: str  # Decimal as string in JSON
```

## Error Responses
```python
# Use HTTPException with clear messages
raise HTTPException(
    status_code=404,
    detail=f"Fund {fund_code} not found"
)

# Korean error messages for user-facing APIs
raise HTTPException(
    status_code=422,
    detail="유효하지 않은 기업코드입니다."
)
```

## Pagination
```python
@router.get("/")
async def list_items(
    skip: int = 0,
    limit: int = Query(default=20, le=100),
) -> PaginatedResponse[ItemResponse]:
    ...
```
- Default: `limit=20`, Max: `limit=100`
- All list APIs must have pagination

## File Upload
```python
from fastapi import UploadFile, Form

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    document_id: str = Form(...),
):
    # Validate extension and size before processing
    ...
```

## Dependency Injection
```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```
