# JWT httpOnly 쿠키 전환 플랜

> **작성일시**: 2026-02-16 21:52
> **이슈**: [SEC-001] JWT localStorage 저장 (XSS 취약점) — P0
> **목표**: JWT 토큰을 localStorage → httpOnly 쿠키로 전환하여 XSS 공격 방어

---

## 개요

### 현재 문제
- JWT Access Token과 Refresh Token을 localStorage에 저장
- JavaScript에서 `localStorage.getItem()` 호출로 토큰 접근 가능
- **XSS 공격 시 토큰 탈취 → 세션 하이재킹 위험**

### 해결 방안
- 백엔드: Set-Cookie 헤더로 httpOnly + Secure + SameSite=Strict 쿠키 전송
- 프론트엔드: localStorage 제거, 쿠키 자동 첨부 (credentials: 'include')

### 영향 범위
- **백엔드**: FDD, KIIS, IM (3개 모두 수정 필요)
- **프론트엔드**: amic-platform (token-storage.ts, client.ts, useAuth.ts)
- **배포 시**: 모든 기존 세션 무효화 (사용자 재로그인 필요)

---

## Phase 1: 백엔드 수정

### 1.1 FDD 백엔드 (`Auto FDD/backend/app/api/auth.py`)

#### 현재 코드 (42-50줄)
```python
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """사용자 로그인 — JWT 토큰 반환."""
    access, refresh = authenticate_user(db, body.email, body.password)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )
```

#### 수정 후 코드
```python
from fastapi import Response

@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """사용자 로그인 — JWT 토큰을 httpOnly 쿠키로 설정."""
    access, refresh = authenticate_user(db, body.email, body.password)

    # Access Token 쿠키 설정 (15분)
    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )

    # Refresh Token 쿠키 설정 (7일)
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    return {"message": "로그인 성공"}
```

#### /refresh 엔드포인트도 동일하게 수정 (53-61줄)
```python
@router.post("/refresh")
def refresh(
    body: RefreshRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """Access Token 갱신 — 새 토큰을 httpOnly 쿠키로 설정."""
    access, refresh_tok = refresh_tokens(db, body.refresh_token)

    response.set_cookie(
        key="access_token",
        value=access,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.access_token_expire_minutes * 60,
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_tok,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
    )

    return {"message": "토큰 갱신 성공"}
```

#### /logout 엔드포인트 — 쿠키 삭제 추가 (64-82줄)
```python
@router.post("/logout", status_code=204)
def logout(
    current_user: CurrentUser = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    """현재 Access Token을 무효화한다 (로그아웃)."""
    # 쿠키 삭제
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

    if credentials is None:
        return Response(status_code=204)

    payload = decode_access_token(credentials.credentials)
    jti = payload.get("jti")
    if not jti:
        return Response(status_code=204)

    token_exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)
    logout_user(db, current_user.id, jti, token_exp, current_user.email)
    return Response(status_code=204)
```

---

### 1.2 KIIS 백엔드 (`KIIS/app/routers/auth.py`)

#### 현재 코드 (28-36줄)
```python
@router.post("/login", response_model=Token, summary="로그인")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> Token:
    """사용자명과 비밀번호로 로그인하여 JWT 토큰을 발급받는다."""
    access_token, refresh_token = await service.login(db, login_data.username, login_data.password)
    return Token(access_token=access_token, refresh_token=refresh_token)
```

#### 수정 후 코드
```python
from fastapi import Response

@router.post("/login", summary="로그인")
async def login(
    login_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """사용자명과 비밀번호로 로그인하여 JWT 토큰을 httpOnly 쿠키로 설정."""
    access_token, refresh_token = await service.login(db, login_data.username, login_data.password)

    # Access Token 쿠키 설정
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60,  # 15분
    )

    # Refresh Token 쿠키 설정
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7일
    )

    return {"message": "로그인 성공"}
```

#### /refresh 엔드포인트도 동일하게 수정 (39-47줄)

---

### 1.3 IM 백엔드 (`IM Module/auto-im-generator/src/api/routes/auth.py`)

#### 현재 코드 (31-44줄)
```python
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="로그인",
    description="이메일과 비밀번호로 인증하여 JWT 토큰 쌍을 발급받는다.",
)
async def login(
    data: LoginRequest,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """이메일/비밀번호 로그인."""
    service = AuthService(session)
    tokens = await service.login(data.email, data.password)
    return TokenResponse(**tokens)
```

#### 수정 후 코드
```python
from fastapi import Response

@router.post(
    "/login",
    summary="로그인",
    description="이메일과 비밀번호로 인증하여 JWT 토큰을 httpOnly 쿠키로 설정.",
)
async def login(
    data: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """이메일/비밀번호 로그인."""
    service = AuthService(session)
    tokens = await service.login(data.email, data.password)

    # Access Token 쿠키 설정
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=15 * 60,  # 15분
    )

    # Refresh Token 쿠키 설정
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=7 * 24 * 60 * 60,  # 7일
    )

    return {"message": "로그인 성공"}
```

---

### 1.4 백엔드 CORS 설정 수정

**각 백엔드 CORS 설정에 `credentials=True` 추가 필요**

#### FDD (`Auto FDD/backend/app/main.py`)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,  # ✅ 추가
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### KIIS, IM도 동일하게 `allow_credentials=True` 추가

---

## Phase 2: 프론트엔드 수정

### 2.1 token-storage.ts 제거

**파일 삭제**: `amic-platform/src/lib/token-storage.ts`

쿠키는 브라우저가 자동 관리하므로 더 이상 필요 없음.

---

### 2.2 client.ts 수정 (`amic-platform/src/api/client.ts`)

#### 현재 코드 (1-104줄) — 주요 변경사항

**1. import 제거** (라인 2-7)
```typescript
// ❌ 제거
import {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
} from "@/lib/token-storage";
```

**2. Request Interceptor 수정** (라인 24-31)
```typescript
// ❌ 현재 코드
instance.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ✅ 수정 후 — Authorization 헤더 제거 (쿠키 자동 첨부)
instance.interceptors.request.use((config) => {
  // 쿠키는 브라우저가 자동으로 첨부하므로 별도 처리 불필요
  return config;
});
```

**3. Response Interceptor 수정** (라인 33-89)
```typescript
// ❌ 현재 코드 (51-56줄)
const refresh = getRefreshToken();
if (!refresh) {
  clearTokens();
  emitForceLogout();
  return Promise.reject(error);
}

// ✅ 수정 후
// Refresh Token도 쿠키로 자동 전송되므로 getRefreshToken() 불필요
// 백엔드가 쿠키를 읽어서 처리

// ❌ 현재 코드 (59-72줄) — setTokens 제거
refreshPromise = axios
  .post<{ access_token: string; refresh_token: string }>(
    REFRESH_URL,
    { refresh_token: refresh },  // ❌ body에서 제거
  )
  .then(({ data }) => {
    setTokens(data.access_token, data.refresh_token);  // ❌ 제거
    return data.access_token;
  })

// ✅ 수정 후
refreshPromise = axios
  .post<{ message: string }>(
    REFRESH_URL,
    {},  // ✅ body 비우기 (쿠키로 전송됨)
    { withCredentials: true }  // ✅ 쿠키 전송 활성화
  )
  .then(() => {
    // ✅ 토큰 저장 불필요 (쿠키 자동 갱신)
    return true;
  })

// ❌ 현재 코드 (78-84줄)
const is401 = axios.isAxiosError(refreshErr) && refreshErr.response?.status === 401;
if (is401) {
  clearTokens();  // ❌ 제거
  emitForceLogout();
}

// ✅ 수정 후
const is401 = axios.isAxiosError(refreshErr) && refreshErr.response?.status === 401;
if (is401) {
  emitForceLogout();  // ✅ clearTokens() 제거 (쿠키는 백엔드에서 삭제)
}
```

**4. createApiClient 수정** (라인 92-99)
```typescript
export function createApiClient(baseURL: string): AxiosInstance {
  const instance = axios.create({
    baseURL,
    timeout: 30_000,
    headers: { "Content-Type": "application/json" },
    withCredentials: true,  // ✅ 추가 — 쿠키 전송 활성화
  });
  return applyAuthInterceptors(instance);
}
```

---

### 2.3 useAuth.ts 수정 (`amic-platform/src/hooks/useAuth.ts`)

#### 현재 코드
```typescript
import { clearTokens } from "@/lib/token-storage";

// logout 함수
const logout = useCallback(async () => {
  try {
    await api.post("/auth/logout");
  } finally {
    clearTokens();  // ❌ 제거
    queryClient.clear();
    navigate("/login");
  }
}, [navigate, queryClient]);
```

#### 수정 후
```typescript
// ❌ import 제거
// import { clearTokens } from "@/lib/token-storage";

// logout 함수
const logout = useCallback(async () => {
  try {
    await api.post("/auth/logout");
  } finally {
    // ✅ clearTokens() 제거 (백엔드가 쿠키 삭제)
    queryClient.clear();
    navigate("/login");
  }
}, [navigate, queryClient]);
```

---

### 2.4 AuthProvider.tsx 수정 (로그인 응답 처리)

#### 파일 위치
`amic-platform/src/components/auth/AuthProvider.tsx`

#### 현재 코드 (예상)
```typescript
import { setTokens } from "@/lib/token-storage";

const login = async (email: string, password: string) => {
  const { data } = await api.post("/auth/login", { email, password });
  setTokens(data.access_token, data.refresh_token);  // ❌ 제거
  // ...
};
```

#### 수정 후
```typescript
// ❌ import 제거
// import { setTokens } from "@/lib/token-storage";

const login = async (email: string, password: string) => {
  const { data } = await api.post("/auth/login", { email, password });
  // ✅ setTokens() 제거 (쿠키 자동 설정됨)
  // data는 { message: "로그인 성공" } 형태
};
```

---

## Phase 3: 테스트 계획

### 3.1 로컬 테스트

#### 백엔드 테스트
```bash
# 1. FDD 백엔드 실행
cd "Auto FDD/backend"
uvicorn app.main:app --reload

# 2. KIIS 백엔드 실행
cd KIIS
uvicorn app.main:app --reload --port 8001

# 3. IM 백엔드 실행
cd "IM Module/auto-im-generator"
uvicorn src.api.main:app --reload --port 8002
```

#### 프론트엔드 테스트
```bash
cd amic-platform
npm run dev
```

#### 쿠키 확인 (Chrome DevTools)
1. Application 탭 → Cookies → http://localhost:5173
2. `access_token`, `refresh_token` 확인
3. HttpOnly, Secure, SameSite 플래그 확인

---

### 3.2 기능 테스트

| 기능 | 테스트 방법 | 예상 결과 |
|------|-----------|----------|
| **로그인** | 이메일/비밀번호 입력 | 쿠키 2개 설정 (access_token, refresh_token) |
| **로그아웃** | 로그아웃 버튼 클릭 | 쿠키 2개 삭제 |
| **토큰 갱신** | Access Token 만료 대기 (15분) | 자동 갱신, 새 쿠키 설정 |
| **401 재시도** | 만료된 토큰으로 API 호출 | Refresh 후 재시도 성공 |
| **새로고침** | F5 새로고침 | 로그인 유지 (쿠키 존재) |
| **XSS 방어** | `document.cookie` 확인 | 토큰 보이지 않음 (HttpOnly) |

---

### 3.3 CORS 테스트

#### 개발 환경
- 프론트엔드: `http://localhost:5173`
- 백엔드 CORS 설정: `http://localhost:5173` 허용 확인

#### 프로덕션 환경
- 프론트엔드: `https://platform.example.com`
- 백엔드 CORS 설정: `CORS_ORIGINS` 환경변수 확인

---

## Phase 4: 배포 체크리스트

### 4.1 백엔드 배포 전

- [ ] **환경변수 확인**: `CORS_ORIGINS` 설정 (프로덕션 도메인)
- [ ] **HTTPS 설정**: `Secure` 플래그 동작 확인
- [ ] **테스트 코드 수정**: 로그인 응답 형식 변경 (`TokenResponse` → `{ message }`)

### 4.2 프론트엔드 배포 전

- [ ] **TypeScript 컴파일**: `npx tsc --noEmit` 통과 확인
- [ ] **Build 확인**: `npm run build` 성공
- [ ] **E2E 테스트**: Playwright 로그인/로그아웃 시나리오

### 4.3 배포 순서

**⚠️ 중요: 백엔드를 먼저 배포해야 함**

1. **백엔드 배포** (FDD, KIIS, IM 순차 또는 동시)
   - 쿠키 설정 코드 배포
   - CORS `allow_credentials=True` 배포
2. **프론트엔드 배포**
   - token-storage.ts 제거
   - client.ts 수정 (withCredentials: true)
3. **배포 공지**
   - 모든 사용자 재로그인 필요 (기존 세션 무효화)

---

## Phase 5: 롤백 계획

### 5.1 백엔드 롤백

**증상**: 로그인 후 쿠키가 설정되지 않음

**조치**:
```bash
# 이전 버전으로 롤백
git revert <commit-hash>
docker-compose restart
```

### 5.2 프론트엔드 롤백

**증상**: API 호출 시 401 Unauthorized 연속 발생

**조치**:
```bash
# 이전 버전으로 롤백
git revert <commit-hash>
npm run build
# 재배포
```

---

## Phase 6: 보안 강화 (선택사항)

### 6.1 CSRF 방어

httpOnly 쿠키 사용 시 CSRF 공격 가능성 증가.

**해결 방법**: CSRF 토큰 추가
```python
# 백엔드
from fastapi_csrf_protect import CsrfProtect

@router.post("/login")
def login(response: Response, csrf_protect: CsrfProtect = Depends()):
    csrf_token = csrf_protect.generate_csrf()
    response.set_cookie(key="csrf_token", value=csrf_token)
    # ...
```

```typescript
// 프론트엔드
axios.defaults.headers.common['X-CSRF-Token'] = getCsrfToken();
```

### 6.2 Content Security Policy (CSP)

XSS 공격 추가 방어

**nginx 설정**:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline';";
```

---

## 참고 자료

### 관련 이슈
- [SEC-001] JWT localStorage 저장 (XSS 취약점) — P0
- [m-A4] 토큰 리프레시 경로 FDD 하드코딩 — P2

### 관련 파일
- **백엔드**: `Auto FDD/backend/app/api/auth.py`, `KIIS/app/routers/auth.py`, `IM Module/.../routes/auth.py`
- **프론트엔드**: `amic-platform/src/lib/token-storage.ts`, `amic-platform/src/api/client.ts`, `amic-platform/src/hooks/useAuth.ts`
- **리포트**: `docs/20260216_2055_Full_Code_Review.md`

### 외부 문서
- [OWASP XSS Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html)
- [MDN: Using HTTP cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [FastAPI Response Cookies](https://fastapi.tiangolo.com/advanced/response-cookies/)

---

## Phase 7: 실행 완료 (2026-02-16 22:05)

### ✅ 백엔드 수정 완료

**FDD 백엔드** (`Auto FDD/backend/`)
- ✅ `app/api/auth.py` — login, refresh, logout 쿠키 설정 완료
- ✅ `app/main.py` — `allow_credentials=True` 이미 설정됨

**KIIS 백엔드** (`KIIS/`)
- ✅ `app/routers/auth.py` — login, refresh 쿠키 설정 + logout 엔드포인트 추가
- ✅ `app/main.py` — `allow_credentials=True` 이미 설정됨

**IM 백엔드** (`IM Module/auto-im-generator/`)
- ✅ `src/api/routes/auth.py` — login, refresh, logout 쿠키 설정 완료
- ✅ `src/api/middleware/cors.py` — `allow_credentials=True` 이미 설정됨

### ✅ 프론트엔드 수정 완료

**프론트엔드** (`amic-platform/src/`)
- ✅ `lib/token-storage.ts` — 파일 삭제
- ✅ `api/client.ts` — withCredentials 추가, 인터셉터 수정
- ✅ `hooks/useAuth.ts` — clearTokens 제거, logout API 호출 추가
- ✅ `components/auth/AuthProvider.tsx` — 토큰 관리 로직 제거

### ✅ TypeScript 컴파일 확인

```bash
npx tsc --noEmit
# ✅ 에러 없음
```

### 다음 단계

**로컬 테스트 필요**:
1. 백엔드 3개 실행 (FDD, KIIS, IM)
2. 프론트엔드 실행 (`npm run dev`)
3. 로그인/로그아웃/토큰 갱신 기능 테스트
4. Chrome DevTools → Application → Cookies 확인
   - `access_token`, `refresh_token` 쿠키 존재 확인
   - HttpOnly, Secure, SameSite 플래그 확인

**프로덕션 배포 전**:
1. 환경변수 `CORS_ORIGINS` 설정 확인
2. HTTPS 도메인 설정 확인 (Secure 플래그 동작)
3. 사용자 공지: "보안 강화를 위해 재로그인이 필요합니다"

---

**작성자**: Claude Code (review-orchestrate)
**최종 업데이트**: 2026-02-16 22:05
**상태**: ✅ Phase 1-2 구현 완료 — 로컬 테스트 대기
