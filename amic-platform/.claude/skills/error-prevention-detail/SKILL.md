---
name: error-prevention-detail
description: P1~P8 에러 사전 차단 상세 코드 예시 + Review Gate 절차. 코드 작성/리뷰 시 상세 참조 필요할 때 호출.
user-invokable: true
---

# 에러 사전 차단 상세 가이드

> 축약판: `.claude/rules/top5-error-prevention.md` (항상 로딩)
> 이 스킬: 상세 코드 예시 + Review Gate (호출 시에만 로딩)

---

## P1: TypeScript/Python 타입 불일치 — 상세

### 디자인 시스템 Variant 참조 테이블

| 컴포넌트 | 유효 variant | 금지 variant (흔한 실수) | 파일 위치 |
|---------|-------------|----------------------|----------|
| Badge | `"success"` `"warning"` `"error"` `"info"` `"neutral"` | ❌ `"default"`, ❌ `"primary"` | `amic-platform/src/components/ui/Badge.tsx:3` |
| Button | `"primary"` `"secondary"` `"ghost"` `"danger"` `"accent"` `"brand"` | ❌ `"outline"`, ❌ `"default"` | `amic-platform/src/components/ui/Button.tsx:8` |

### Python 타입 힌트 패턴

```python
# ✅ 올바름
field: str | None = None
field: Mapped[str | None] = mapped_column(nullable=True)

# ❌ 금지
field: Optional[str] = None  # from typing import Optional 불필요
field: str = None             # None 가능성 미표시
```

### Review Gate
1. Grep: 변경된 `.tsx`에서 `variant=` 패턴 검색 → 참조 테이블과 대조
2. `enums.py` 변경 시 대응 FE `types/*.ts` 변경 확인
3. `npx tsc -b --noEmit` 통과 확인

---

## P2: 데이터 직렬화/타입 변환 실패 — 상세

### JSONB 저장 시 _json_safe 유틸

```python
# ✅ 올바름
from app.services.audit_service import _sanitize_for_json

data = _sanitize_for_json({
    "amount": Decimal("1234.56"),    # → "1234.56" (str)
    "id": uuid.UUID("..."),          # → "..." (str)
    "status": SomeEnum.ACTIVE,       # → "active" (value)
    "created": datetime.now(),       # → "2026-03-01T..." (isoformat)
})
db_model.json_field = data

# ❌ 금지
db_model.json_field = {"amount": Decimal("1234.56")}
```

참조: `deal-mgmt/app/services/audit_service.py` (`_sanitize_for_json` 함수)

### json.dumps 이중 직렬화 금지

```python
# ✅ dict를 JSONB 컬럼에 직접 할당
model.json_column = {"key": "value"}

# ❌ json.dumps로 문자열화 후 할당
model.json_column = json.dumps({"key": "value"})
```

### 금액 단위 매핑

| 단위 | 값 (KRW) | Python | TypeScript |
|------|---------|--------|------------|
| 억 | 10^8 | `value / 1_0000_0000` | `value / 100_000_000` |
| 조 | 10^12 | `value / 1_0000_0000_0000` | `value / 1_000_000_000_000` |
| 백만 | 10^6 | `value / 100_0000` | `value / 1_000_000` |

### 크로스 DB 타입

```python
# ✅ 크로스 DB 호환
from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB

id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
data: Mapped[dict | None] = mapped_column(
    JSON().with_variant(JSONB, "postgresql"), nullable=True
)

# ❌ PostgreSQL 전용
from sqlalchemy.dialects.postgresql import UUID
id = mapped_column(UUID(as_uuid=True), ...)
data = mapped_column(JSONB, ...)
```

### Review Gate
1. Grep: `mapped_column(JSONB` / `mapped_column(UUID(as_uuid` 패턴 즉시 이슈
2. JSONB 컬럼 할당 경로에서 Decimal/UUID/Enum sanitize 확인
3. 금액 함수에서 나눗셈 상수 매핑 테이블 대조
4. `json.dumps()` → JSONB 컬럼 할당 직전 사용 여부 확인

---

## P3: 환경변수/설정 불일치 — 상세

### 4개 모듈 환경변수 매핑 테이블

| 설정 항목 | FDD | KIIS | IM | MA (deal-mgmt) |
|----------|-----|------|----|----|
| **Config 파일** | `fdd/backend/app/config.py` | `kiis/app/core/config.py` | `im/src/api/config.py` | `deal-mgmt/app/core/config.py` |
| **CORS** | `cors_origins: str` (쉼표) | `ALLOWED_ORIGINS: list[str]` (JSON) | `allowed_origins: list[str]` (alias `CORS_ORIGINS`) | `ALLOWED_ORIGINS: list[str]` (JSON) |
| **JWT Secret** | `jwt_secret: str` (소문자) | `JWT_SECRET: str` (대문자) | `jwt_secret_key: str` (alias `JWT_SECRET`) | `JWT_SECRET: str` (대문자) |
| **DB URL** | `database_url: str` (소문자) | `DATABASE_URL: str` (대문자) | `database_url: str` (소문자) | `DATABASE_URL: str` (대문자) |
| **인증 토글** | `auth_enabled: bool` | `AUTH_ENABLED: bool` | — | `AUTH_ENABLED: bool` |

### .env CORS 값 형식

```bash
# FDD — str 타입 (쉼표 구분)
FDD_CORS_ORIGINS=https://ap-platform.kr,http://52.231.69.38

# KIIS, IM, MA — list[str] 타입 (JSON 배열)
KIIS_ALLOWED_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]
IM_CORS_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]
MA_ALLOWED_ORIGINS=["https://ap-platform.kr","http://52.231.69.38"]
```

### Review Gate
1. `config.py` 변경 → 매핑 테이블과 필드명/타입 일관성 대조
2. FDD만 `str`(쉼표), 나머지 `list[str]`(JSON) — 혼용 금지
3. JWT_SECRET 4개 모듈 동일 환경변수명 확인
4. 하드코딩 시크릿 여부 확인

---

## P4: 마이그레이션/스키마 누락 — 상세

### 마이그레이션 체인 검증

```bash
cd {모듈} && python -m alembic heads       # head 1개여야 정상
cd {모듈} && python -m alembic history --verbose | head -20
```

### Review Gate
1. `git diff`에서 `app/models/` 변경 → `migrations/versions/` 대응 확인
2. `downgrade()` 실제 rollback SQL 포함 확인
3. 새 모델 → `models/__init__.py` import 확인
4. 마이그레이션 내 `UUID(as_uuid=True)` / `JSONB` 직접 사용 Grep

---

## P5: 보안/권한 데코레이터 누락 — 상세

### 모듈별 인증 패턴 참조 테이블

| 모듈 | 인증 함수 | import 경로 | 사용 패턴 |
|------|----------|------------|----------|
| FDD | `get_current_user` | `from app.auth.jwt_handler import get_current_user` | `current_user = Depends(get_current_user)` |
| KIIS | `get_current_active_user` | `from app.core.dependencies import get_current_active_user` | `current_user: User = Depends(get_current_active_user)` |
| IM | `get_current_user` | `from src.api.auth import get_current_user` | `current_user = Depends(get_current_user)` |
| MA | `get_jwt_claims` | `from app.core.security import get_jwt_claims` | `claims: JWTClaims = Depends(get_jwt_claims)` |

### Review Gate
1. `@router.` 함수에 인증 Depends 확인 (health/public만 예외)
2. JWT_SECRET 기본값이 빈 문자열인지 확인
3. 새 라우터 vs 기존 라우터 인증 패턴 비교

---

## P6: Ruff 린트 — 상세

### 주요 위반 코드

| 코드 | 의미 | 방지법 |
|------|------|-------|
| **B017** | `pytest.raises`에 `match=` 미사용 | `pytest.raises(ValueError, match="expected msg")` |
| **M105** | 미사용 모듈 수준 변수 | 선언 즉시 사용처 확인 |
| **F401** | import 후 미사용 | 사용하지 않으면 즉시 삭제 |

```python
# ❌ B017
with pytest.raises(ValueError):
    some_function()

# ✅
with pytest.raises(ValueError, match="invalid input"):
    some_function()
```

### Review Gate
1. `ruff check` 0건 확인
2. 새 import → 코드에서 실제 참조 Grep 확인
3. `pytest.raises` → `match=` 인자 확인

---

## P7: 의존성 누락 — 상세

### 최근 누락 패키지

| 패키지 | 모듈 | 용도 |
|--------|------|------|
| `pandas` | deal-mgmt | 시드 스크립트 |
| `olefile` | deal-mgmt | HWP 파싱 |
| `chardet` | deal-mgmt | 인코딩 감지 |
| `fakeredis` | kiis | Redis 모킹 |

### Review Gate
1. 새 import → `pyproject.toml` 등록 확인
2. C 확장 의존성 → Dockerfile 빌드 도구 필요 여부

---

## P8: 인코딩/경로 — 상세

```python
# ✅ pathlib
from pathlib import Path
base = Path(__file__).resolve().parent
data_file = base / "data" / "input.csv"

# ❌ 하드코딩
data_file = "C:\\Users\\data\\input.csv"

# ✅ UTF-8 명시
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# ❌ 인코딩 미지정
with open(filepath, "r") as f:
    content = f.read()
```

### Review Gate
1. `open(` → `encoding=` 인자 확인 (바이너리 제외)
2. `C:\\`, `/Users/`, `/opt/` 절대 경로 Grep
3. `pathlib.Path` 또는 `os.path` 사용 확인
