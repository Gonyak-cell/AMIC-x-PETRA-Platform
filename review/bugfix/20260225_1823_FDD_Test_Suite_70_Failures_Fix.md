# FDD 백엔드 테스트 스위트 70건 실패 수정

> 작성: 2026-02-25 18:23:00

## 요약

FDD 백엔드 전체 테스트 실행 시 **70건 실패** (65 failed + 5 errors) → **0 failed, 1439 passed** 달성.

## 근본 원인

### Phase 1: `target_company_name` 필수 필드 누락 (63건 해결)

**원인**: `DealCreate` Pydantic 스키마에 `target_company_name: str = Field(...)` 필수 필드가 추가되었으나, 테스트 SAMPLE_DEAL 딕셔너리에 해당 필드가 누락 → 422 Validation Error.

**확정 근거**:
1. `app/schemas/deal.py:24` — `target_company_name: str = Field(..., min_length=1, max_length=255)` 필수
2. Pydantic 직접 검증: `DealCreate(name='Test', ...)` → `Field required [target_company_name]`
3. `test_uploads.py` 실행 시 422 응답 확인
4. `test_deals.py` 단독 실행 시 동일 422 확인
5. `security/conftest.py` 실행 시 동일 422 확인

**수정 파일 (6곳)**:

| 파일 | 추가 필드 |
|------|----------|
| `tests/test_uploads.py` | `"target_company_name": "Upload Test Corp"` |
| `tests/test_deals.py` | `"target_company_name": "Alpha Corp"` |
| `tests/api/test_vdr.py` | `"target_company_name": "VDR Test Corp"` |
| `tests/test_api_entities.py` | `"target_company_name": "Entity Test Corp"` |
| `tests/test_api_exchange_rates.py` | `"target_company_name": "FX Rate Test Corp"` |
| `tests/security/conftest.py` | `"target_company_name": "Security Test Corp"` + `"base_currency": "KRW"` |

### Phase 2: 코드 진화에 따른 테스트 갱신 (7건 해결)

| # | 파일 | 원인 | 수정 |
|---|------|------|------|
| 1 | `tests/test_deals.py:44` | Deal 목록 API가 페이지네이션 `{items, total, skip, limit}` 반환으로 변경 | `len(resp.json())` → `len(resp.json()["items"])` |
| 2 | `tests/auth/test_auth_api.py:20-23` | 로그인 httpOnly 쿠키 전환 — body에 토큰 대신 `{"message": "로그인 성공"}` 반환 | body 토큰 검증 → 쿠키 + 메시지 검증 |
| 3 | `tests/auth/test_auth_api.py:58-68` | refresh도 쿠키 기반 전환 — `request.cookies.get("refresh_token")` | JSON body 전달 → TestClient 쿠키 자동 전달 |
| 4 | `tests/auth/test_password.py:20-25` | SHA-256 `salt:hash` → bcrypt `$2b$12$...` 전환 | `split(":")` 검증 → `startswith("$2b$")` + `len==60` 검증 |
| 5 | `tests/auth/test_rbac.py:40-47` | VIEWER 권한 2개→4개 확장 (`NOTIFICATION_READ`, `SETTINGS_READ` 추가) | 기대값 set에 2개 권한 추가 |
| 6 | `tests/jobs/test_job_api.py:13-19` | Deal 생성 JSON에 `target_company_name` + `base_currency` 누락 | 두 필드 추가 |
| 7 | `tests/test_industries_api.py:65-70` | ORM 직접 생성 시 날짜 문자열 → SQLite Date 타입 불일치 + `created_by` UUID→String | `date()` 객체 사용 + 이메일 문자열 사용 |

## 검증 결과

```
TESTING=true AUTH_ENABLED=false pytest --tb=short -q
1439 passed, 52 warnings in 154.06s
```

## 심각도

- **Phase 1**: Medium (테스트 전용, 프로덕션 코드 무관)
- **Phase 2**: Medium (테스트와 소스 코드 간 불일치, 프로덕션 코드 정상)
