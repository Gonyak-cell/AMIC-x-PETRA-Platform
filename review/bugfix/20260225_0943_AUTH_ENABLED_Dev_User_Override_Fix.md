# AUTH_ENABLED=false로 인한 로그인 사용자 덮어쓰기 버그 수정

> **수정일**: 2026-02-25 09:43
> **심각도**: Critical
> **카테고리**: bugfix / auth
> **상태**: ✅ 완료

## 증상

- `jwsuh@amic.kr`로 로그인해도 항상 `system@autofdd.dev` (autofdddev) 계정으로 표시됨
- 로그인 POST 요청 자체는 성공하지만, 이후 사용자 정보 조회 시 dev 계정 반환

## 근본 원인

**위치**: `docker-compose.yml` 라인 58, 113, 196, 247

`docker-compose.yml`에서 4개 백엔드 모두 `AUTH_ENABLED: "false"`로 설정되어 있어, JWT 토큰 검증을 건너뛰고 하드코딩된 dev 사용자를 반환함.

### 버그 재현 흐름

```
1. POST /auth/login {email: "jwsuh@amic.kr"} → FDD가 JWT 쿠키 정상 발급 ✅
2. GET /auth/me (쿠키 전송) → get_current_user() 호출
3. AUTH_ENABLED=False → JWT 검증 스킵 → _DEV_USER 반환 ❌
4. DB에서 UUID 00000000... 조회 → 없음 → dev 모드 폴백 응답
5. 프론트엔드에 system@autofdd.dev 표시
```

### 확정 근거

| # | 근거 | 내용 |
|---|------|------|
| 1 | 설정 파일 직접 확인 | `docker-compose.yml:58` — `AUTH_ENABLED: "false"` |
| 2 | FDD 인증 우회 코드 | `fdd/backend/app/auth/dependencies.py:57-58` — `if not settings.auth_enabled: return _DEV_USER` |
| 3 | /me 엔드포인트 폴백 | `fdd/backend/app/api/auth.py:184-200` — DB에 dev user 없으면 dev 폴백 응답 |
| 4 | deal-mgmt 동일 패턴 | `deal-mgmt/app/core/security.py:50-51` — `_DEV_CLAIMS` 반환 |
| 5 | 4개 백엔드 전부 동일 | `kiis/app/core/security.py:110`, `im/src/api/dependencies.py:65-66` |

## 수정 내용

### `docker-compose.yml` (4곳)

```diff
# fdd-api (라인 58)
-      AUTH_ENABLED: "false"
+      AUTH_ENABLED: "true"

# kiis-api (라인 113)
-      AUTH_ENABLED: "false"
+      AUTH_ENABLED: "true"

# deal-mgmt-api (라인 196)
-      AUTH_ENABLED: "false"
+      AUTH_ENABLED: "true"

# im-api (라인 247)
-      AUTH_ENABLED: "false"
+      AUTH_ENABLED: "true"
```

## 검증

1. `docker compose up -d` — 4개 API 컨테이너 Recreated 확인
2. 브라우저에서 `jwsuh@amic.kr` / `1111`로 로그인 → "서지원" 표시 확인 ✅

## 영향 범위

- **변경 파일**: `docker-compose.yml` 1개
- **영향 서비스**: fdd-api, kiis-api, deal-mgmt-api, im-api (4개 전부)
- **사이드 이펙트**: 모든 API 요청에 유효한 JWT 토큰 필요 (시드 사용자 DB 등록 필수)
