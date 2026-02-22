---
paths:
  - "fdd/**/tests/**/*.py"
  - "kiis/**/tests/**/*.py"
  - "im/**/tests/**/*.py"
---
# Backend Testing Rules

## Test File Structure
```
{module}/tests/
├── test_api_{resource}.py      # API endpoint tests
├── test_service_{name}.py      # Service layer tests
├── test_{engine}_engine.py     # Engine unit tests (FDD)
├── conftest.py                 # Shared fixtures
└── test_data/                  # Test fixtures data
```

## Naming Convention
```python
def test_{action}_{condition}_{expected_result}():
    ...

# Examples
def test_create_document_without_corp_code_succeeds():
def test_calculate_ebitda_with_zero_revenue_returns_zero():
def test_search_funds_returns_paginated_results():
```

## Async Test Pattern (KIIS / IM)
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_list_funds(async_client: AsyncClient):
    response = await async_client.get("/api/v1/kofia/funds?fund_name=삼성")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
```

## Sync Test Pattern (FDD)
```python
import pytest
from decimal import Decimal

def test_calculate_ebitda_basic():
    accounts = {"revenue": Decimal("-1000000"), "cogs": Decimal("600000")}
    result = calculate_reported_ebitda(accounts)
    assert result == Decimal("400000")
```

## Fixture Best Practices
```python
# conftest.py — transaction rollback isolation
@pytest.fixture
async def db_session():
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()
```

## Common Pitfalls
1. **Date columns**: Use `date(2025, 12, 31)`, NOT `"2025-12-31"` string
2. **Money**: Use `Decimal("1000")`, NOT `1000` or `1000.0`
3. **UUID reference**: Call `db.flush()` / `await session.flush()` before accessing `.id`
4. **No `time.sleep()`** — use `asyncio.sleep()` or mock time
5. **No shared mutable state** between tests
6. **No hardcoded URLs** — use fixtures or env vars

## External API Mocking
```python
# Use pytest-httpx for async HTTP mocking
@pytest.fixture
def mock_dart_api(httpx_mock):
    httpx_mock.add_response(
        url="https://opendart.fss.or.kr/api/company.json",
        json={"status": "000", "corp_name": "삼성전자"}
    )
```

## Running Tests
```bash
# FDD
cd fdd/backend && python -m pytest tests/ -v --tb=short

# KIIS
cd kiis && uv run pytest tests/ -v --tb=short

# IM
cd im && python -m pytest tests/ -v --tb=short
```

## Coverage Goals
- Overall: 80%+
- Engines/Services: 90%+ (critical business logic)
- API: 70%+ (happy path + error cases)
