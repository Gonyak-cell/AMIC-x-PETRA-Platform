# 인증 아키텍처 수정 — 쿠키 기반 크로스 백엔드 인증

> 작성: 2026-02-17 17:16
> 수정: 2026-02-17 17:27:04
> 카테고리: security
> 심각도: Critical (P0)

## Context

### 문제
로그인 후 대시보드 및 KIIS/IM 모듈 페이지에서 404/401 에러가 반복 발생한다.

### 근본 원인
인증 아키텍처 불일치 — FDD 로그인이 httpOnly 쿠키로 JWT를 설정하지만, 3개 백엔드 모두 Authorization: Bearer 헤더에서만 토큰을 읽는다. httpOnly 쿠키는 JS에서 접근 불가하므로 프론트엔드가 Authorization 헤더를 설정할 수 없다.

| 구분 | 현재 상태 | 결과 |
|------|----------|------|
| FDD 로그인 | httpOnly 쿠키 설정 (access_token, refresh_token) | 쿠키 저장됨 |
| FDD API | HTTPBearer → Authorization 헤더만 읽음, auth_enabled=True | 401 |
| KIIS API | OAuth2PasswordBearer → Authorization 헤더만 읽음 | 401 |
| IM API | OAuth2PasswordBearer → Authorization 헤더만 읽음 | 401 |
| FDD refresh | body: RefreshRequest (refresh_token 필수) | 프론트엔드 빈 body → 422 |
| 쿠키 flags | secure=True, samesite="strict" 고정 | localhost HTTP 호환 문제 |

### JWT 시크릿 공유 (docker-compose.yml 확인 완료)
3개 백엔드 모두 `JWT_SECRET=dev-shared-jwt-secret-change-in-production` 공유 → 크로스 백엔드 토큰 검증 가능

### 에러 흐름 (예: 대시보드 로딩 시)
1. AuthProvider → `api.get("/auth/me")` → FDD → 401 (Authorization 헤더 없음)
2. 401 인터셉터 → `axios.post("/api/fdd/auth/refresh", {})` → 빈 body → FDD 422
3. refresh 실패 → AuthProvider catch → `isAuthenticated: false` → 로그인 페이지 이동
4. 로그인 후 쿠키 설정 → 대시보드 이동 → 동일 반복 (쿠키 있지만 Authorization 헤더 미설정)

## 수정 계획

### Step 1: FDD 백엔드 — 쿠키 인증 폴백 ✅
- `fdd/backend/app/auth/dependencies.py` — ✅ 완료 (Request 추가, 쿠키 폴백)
- `fdd/backend/app/api/auth.py` — ✅ 완료 (samesite lax)
  - refresh는 이미 쿠키 읽기, secure는 이미 조건부 (`_cookie_secure`)
  - samesite "strict" → "lax" (login 2곳 + refresh 2곳)

### Step 2: KIIS 백엔드 — 쿠키 인증 폴백 ✅
- `kiis/app/core/security.py` — ✅ 완료 (Request, `get_jwt_claims` + `get_current_user` 쿠키 폴백)
- `kiis/app/routers/auth.py` — ✅ 완료
  - `Request`, `HTTPException` import 추가
  - refresh: `TokenRefresh` body → `request.cookies.get("refresh_token")` 변경
  - samesite "strict" → "lax" (login 2곳 + refresh 2곳)

### Step 3: IM 백엔드 — 쿠키 인증 폴백 ✅
- `im/src/api/dependencies.py` — ✅ 완료 (Request 추가, 쿠키 폴백)
- `im/src/api/routes/auth.py` — ✅ 완료
  - `os`, `Request` import 추가
  - `_is_production`, `_cookie_secure` 변수 추가
  - login: `secure=True` → `_cookie_secure`, samesite "strict" → "lax"
  - refresh: `RefreshRequest` body → `request.cookies.get("refresh_token")` 변경
  - refresh: `secure=True` → `_cookie_secure`, samesite "strict" → "lax"

**프론트엔드 변경 없음** (쿠키 + withCredentials 이미 설정됨)

## 수정 파일 요약

| # | 파일 | 변경 | 상태 |
|---|------|------|------|
| 1 | `fdd/backend/app/auth/dependencies.py` | Request 추가, 쿠키 폴백 | ✅ 완료 (이전 세션) |
| 2 | `fdd/backend/app/api/auth.py` | samesite "strict" → "lax" (4곳) | ✅ 완료 (2026-02-17 17:27) |
| 3 | `kiis/app/core/security.py` | Request 추가, `get_jwt_claims` + `get_current_user` 쿠키 폴백 | ✅ 완료 (이전 세션) |
| 4 | `kiis/app/routers/auth.py` | refresh 쿠키 읽기, samesite "strict" → "lax" (4곳), Request/HTTPException import | ✅ 완료 (2026-02-17 17:27) |
| 5 | `im/src/api/dependencies.py` | Request 추가, 쿠키 폴백 | ✅ 완료 (이전 세션) |
| 6 | `im/src/api/routes/auth.py` | refresh 쿠키 읽기, `_is_production`/`_cookie_secure` 추가, secure 조건부, samesite "strict" → "lax" (4곳) | ✅ 완료 (2026-02-17 17:27) |

## 검증 방법

### 1단계: Docker 재빌드
```bash
docker compose down && docker compose up -d --build fdd-api kiis-api im-api
```

### 2단계: curl 테스트
```bash
# FDD 로그인 → 쿠키 획득
curl -v -c cookies.txt http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.com","password":"test1234"}'

# 쿠키로 FDD 인증 (핵심 테스트)
curl -b cookies.txt http://localhost:8000/api/v1/deals

# 쿠키로 KIIS 크로스 인증
curl -b cookies.txt http://localhost:8001/api/v1/alerts/unread-count

# 쿠키로 IM 크로스 인증
curl -b cookies.txt http://localhost:8002/api/v1/documents

# 쿠키로 refresh (빈 body)
curl -b cookies.txt -c cookies.txt -X POST http://localhost:8000/api/v1/auth/refresh
```

### 3단계: 브라우저 테스트
1. 서비스 워커 클리어: DevTools → Application → Service Workers → Unregister
2. 브라우저 캐시 클리어 (Ctrl+Shift+Delete)
3. `npm run dev` 실행
4. 로그인 → 대시보드 에러 없음 확인
5. KIIS 모듈 → IM 모듈 이동 → 에러 없음 확인
