---
paths:
  - "fdd/**/*.py"
  - "kiis/**/*.py"
  - "im/**/*.py"
---
# Financial Conventions (금액 처리 규칙)

## CRITICAL Rules
- ALL monetary values: `Decimal` (Python) or `string` (JSON/TypeScript). **NEVER `float`.**
- DB columns: `NUMERIC(18,4)` — no exceptions.
- KRW: zero decimal places. FX rates: up to 4 decimal places.
- Rounding: always explicit via `quantize(ROUND_HALF_UP)`, never implicit.
- Tests: use `Decimal("123.4567")` not `123.4567`.

## Code Patterns
```python
from decimal import Decimal, ROUND_HALF_UP

Q4 = Decimal("0.0001")
Q0 = Decimal("1")

# Float → Decimal (반드시 str 경유)
amount = Decimal(str(value)).quantize(Q4, rounding=ROUND_HALF_UP)

# KRW 정수 처리
krw_amount = amount.quantize(Q0, rounding=ROUND_HALF_UP)
```

## JSON Serialization
```python
# Pydantic 모델에서 Decimal → str
class MoneyResponse(BaseModel):
    amount: str  # NOT Decimal, NOT float
```

## Unit Display (한국어)
| 범위 | 단위 | 예시 |
|------|------|------|
| < 10억 | 백만원 | 950백만원 |
| 10억 ~ 1조 | 억원 | 1,250억원 |
| >= 1조 | 조원 | 1.5조원 |

## Financial Statement Types
- CFS (연결재무제표): Consolidated — 기본 사용
- OFS (별도재무제표): Separate — CFS 없을 때만
- 두 유형 혼합 연산 금지

## Database Columns
```python
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
```
