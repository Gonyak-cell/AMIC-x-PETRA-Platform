---
name: new-api
description: "FastAPI 엔드포인트 스캐폴딩. 사용법: /new-api {module} {resource-name}. 예: /new-api kiis reputation-scores"
user-invocable: true
disable-model-invocation: true
---

# New API Endpoint Scaffolding (Monorepo)

인자: $ARGUMENTS
(첫 번째 단어 = 모듈명, 두 번째 = 리소스명)

## Module Directory Structures
| Module | Routers | Schemas | Services | Tests |
|--------|---------|---------|----------|-------|
| fdd | `fdd/backend/app/api/` | `fdd/backend/app/schemas/` | `fdd/backend/app/services/` | `fdd/backend/tests/` |
| kiis | `kiis/app/routers/` | `kiis/app/schemas/` | `kiis/app/services/` | `kiis/tests/` |
| im | `im/src/api/routes/` | `im/src/api/schemas/` | `im/src/api/services/` | `im/tests/` |

## Steps

1. **기존 패턴 확인**:
   - 해당 모듈의 기존 라우터/스키마/서비스 파일 구조 확인
   - 네이밍 패턴 파악

2. **생성할 파일**:
   - `{routers_dir}/{resource}.py` — CRUD 라우터
   - `{schemas_dir}/{resource}.py` — Request/Response 스키마
   - `{services_dir}/{resource}_service.py` — 비즈니스 로직
   - `{tests_dir}/test_{resource}.py` — 테스트

3. **라우터 패턴**:
   ```python
   router = APIRouter(prefix="/{resource}", tags=["{resource}"])
   # GET /, GET /{id}, POST /, PUT /{id}, DELETE /{id}
   ```

4. **라우터 등록**: 해당 모듈의 main.py에 import 추가

## Conventions
- URL: kebab-case (`/reputation-scores`)
- 파일명: snake_case (`reputation_scores.py`)
- 모든 리스트 API에 페이지네이션 필수 (skip/limit)
- Pydantic v2 ConfigDict 사용
- 금액 필드: Decimal → str (JSON)
