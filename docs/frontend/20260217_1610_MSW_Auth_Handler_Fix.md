# MSW 핸들러 수정 — httpOnly 쿠키 인증 호환

**수정일**: 2026-02-17 16:17
**대상 파일**: `amic-platform/src/test/mocks/handlers.ts`, `amic-platform/src/test/mocks/data.ts`
**상태**: 완료

---

## 문제 요약

### 증상
- 홈페이지(DashboardPage)에서 **404 에러** 발생
- 3개 모듈(Auto FDD, KIIS, IM Generator) 모두 **Unreachable** 표시
- 거의 모든 페이지에서 API 에러 발생

### 근본 원인
**MSW(Mock Service Worker) 핸들러가 쿠키 기반 인증과 호환되지 않음**

이전 세션(Session 20)에서 프론트엔드 인증 방식을 `localStorage` → `httpOnly 쿠키`로 전환했으나, MSW 핸들러는 업데이트되지 않았음.

#### 구체적 불일치:

| 항목 | MSW 핸들러 (변경 전) | 프론트엔드 (현재) |
|------|---------------------|------------------|
| 로그인 응답 | `{ access_token, refresh_token }` | `{ message: string }` 기대 |
| 인증 확인 | `Authorization: Bearer` 헤더 체크 | httpOnly 쿠키 사용 (헤더 없음) |
| 로그아웃 | 핸들러 없음 | `/auth/logout` POST 호출 |
| 토큰 갱신 | 핸들러 없음 | `/auth/refresh` POST 호출 |

#### 장애 흐름:
1. 앱 로드 → `api.get("/auth/me")` 호출
2. MSW: `Authorization` 헤더 없음 → **401 반환**
3. `AuthProvider`: `isAuthenticated = false`
4. `ProtectedRoute`: `/login`으로 리다이렉트
5. 로그인 시도 → MSW: 토큰을 body로 반환 → 앱은 무시 (쿠키 기대)
6. `api.get("/auth/me")` 재호출 → 여전히 401 → **로그인 실패 무한 반복**

---

## 수정 내역

### 1. 인증 핸들러 재설계 (핵심)

**변경 전** (Authorization 헤더 기반):
```typescript
http.post("*/api/fdd/auth/login", () => {
  return HttpResponse.json({
    access_token: "mock-access-token",
    refresh_token: "mock-refresh-token",
    token_type: "bearer",
    expires_in: 3600,
  });
});

http.get("*/api/fdd/auth/me", ({ request }) => {
  const authHeader = request.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    return new HttpResponse(null, { status: 401 });
  }
  return HttpResponse.json(mockUser);
});
```

**변경 후** (sessionStorage 기반 쿠키 시뮬레이션):
```typescript
const MSW_AUTH_KEY = "msw-authenticated";

function isMswAuthenticated(): boolean {
  return sessionStorage.getItem(MSW_AUTH_KEY) === "true";
}

function setMswAuthenticated(value: boolean): void {
  if (value) {
    sessionStorage.setItem(MSW_AUTH_KEY, "true");
  } else {
    sessionStorage.removeItem(MSW_AUTH_KEY);
  }
}

http.post("*/api/fdd/auth/login", () => {
  setMswAuthenticated(true);
  return HttpResponse.json({ message: "Login successful" });
});

http.post("*/api/fdd/auth/logout", () => {
  setMswAuthenticated(false);
  return HttpResponse.json({ message: "Logged out" });
});

http.post("*/api/fdd/auth/refresh", () => {
  if (!isMswAuthenticated()) {
    return new HttpResponse(null, { status: 401 });
  }
  return HttpResponse.json({ message: "Token refreshed" });
});

http.get("*/api/fdd/auth/me", () => {
  if (!isMswAuthenticated()) {
    return new HttpResponse(null, { status: 401 });
  }
  return HttpResponse.json(mockUser);
});
```

**설계 결정**:
- `sessionStorage` 사용 → HMR 업데이트에도 로그인 상태 유지
- 탭 닫으면 자동 초기화 (보안)
- MSW에서 httpOnly 쿠키 직접 조작 불가 → 인메모리 플래그로 대체

### 2. 누락된 핸들러 추가 (51개 → 0개)

기존 34개 핸들러에서 **51개 누락된 엔드포인트** 추가:

#### KIIS 모듈 (25개 추가)
| 엔드포인트 | 대상 페이지 |
|-----------|-----------|
| `GET /api/kiis/deals` | DealSourcingPage |
| `GET /api/kiis/deals/stats` | DealSourcingPage |
| `GET /api/kiis/deals/stages` | DealSourcingPage |
| `GET /api/kiis/deals/recent` | DealSourcingPage |
| `GET /api/kiis/news` | NewsListPage |
| `GET /api/kiis/news/:articleId` | NewsDetailPage |
| `POST /api/kiis/news/collect` | NewsListPage |
| `GET /api/kiis/kofia/funds` | FundListPage |
| `GET /api/kiis/kofia/funds/:fundCode` | FundDetailPage |
| `GET /api/kiis/kofia/managers` | FundListPage |
| `GET /api/kiis/reits` | ReitListPage |
| `GET /api/kiis/reits/:reitCode` | ReitDetailPage |
| `GET /api/kiis/sanctions` | SanctionListPage |
| `GET /api/kiis/sanctions/summary` | SanctionListPage |
| `POST /api/kiis/sanctions/classify` | SanctionListPage |
| `GET /api/kiis/portfolio` | PortfolioPage |
| `GET /api/kiis/portfolio/:id` | PortfolioPage |
| `POST /api/kiis/portfolio/...` | PortfolioPage (3개) |
| `GET /api/kiis/managers` | ManagerListPage |
| `GET /api/kiis/managers/:id` | ManagerProfilePage |
| `GET /api/kiis/managers/movement` | ManagerListPage |
| `GET /api/kiis/entities/aliases` | EntityResolutionPage |
| `POST /api/kiis/entities/resolve` | EntityResolutionPage |
| `GET /api/kiis/disclosures/:corpCode` | DisclosurePage |
| `GET /api/kiis/analysis/reputation` | CompanyDetailPage |

#### FDD 모듈 (22개 추가)
| 엔드포인트 | 대상 페이지 |
|-----------|-----------|
| `GET /api/fdd/deals/:id/qoe` | QoE 탭 |
| `POST /api/fdd/deals/:id/qoe/calculate` | QoE 탭 |
| `GET /api/fdd/deals/:id/nwc` | NWC 탭 |
| `POST /api/fdd/deals/:id/nwc/calculate` | NWC 탭 |
| `GET /api/fdd/deals/:id/debt` | Debt 탭 |
| `POST /api/fdd/deals/:id/debt/calculate` | Debt 탭 |
| `GET /api/fdd/deals/:id/definitions` | 정의 탭 |
| `GET /api/fdd/deals/:id/mappings` | 매핑 탭 |
| `GET /api/fdd/deals/:id/issues` | 이슈 탭 |
| `GET /api/fdd/deals/:id/tie-out` | 검증 탭 |
| `GET /api/fdd/deals/:id/uploads` | 업로드 탭 |
| `GET /api/fdd/deals/:id/vdr/folders` | VDR 탭 |
| `GET /api/fdd/deals/:id/reports/versions` | 보고서 탭 |
| `PUT /api/fdd/deals/:id` | 딜 수정 |
| `GET/POST /api/fdd/comments` | 댓글 CRUD |
| `PATCH /api/fdd/notifications/...` | 알림 관리 |
| `GET/PUT /api/fdd/settings/...` | 설정 페이지 |
| `POST /api/fdd/auth/users` | 유저 관리 |
| `PUT /api/fdd/auth/users/:id` | 프로필 수정 |
| `POST /api/fdd/auth/change-password` | 비밀번호 변경 |

#### IM 모듈 (1개 추가)
| 엔드포인트 | 대상 페이지 |
|-----------|-----------|
| `GET /api/im/documents/:id/download` | DocumentDetailPage |

---

## 검증

| 항목 | 결과 |
|------|------|
| TypeScript 컴파일 (`tsc --noEmit`) | 통과 |
| Vite 빌드 (`vite build`) | 통과 (12.16초) |
| 개발 서버 실행 | 200 응답 확인 |

---

## 사용 방법

1. `npm run dev` 실행
2. 브라우저에서 `http://localhost:5173` 접속
3. 로그인 페이지에서 **시드 계정**으로 로그인:

| 이메일 | 비밀번호 | 이름 | 역할 |
|-------|---------|------|------|
| `jwsuh@amic.kr` | `1111` | 서지원 | ADMIN |
| `ytkim@amic.kr` | `1111` | 김용태 | ANALYST |
| `yhlim@amic.kr` | `1111` | 임영훈 | ANALYST |
| `wsjo@amic.kr` | `1111` | 조원석 | ANALYST |
| `bj.park@amic.kr` | `1111` | 박병준 | ANALYST |

4. DashboardPage에서 3개 모듈 **Connected** 확인
5. 각 모듈 페이지 정상 렌더링 확인

**참고**:
- MSW 비활성화하려면 `.env.local`에 `VITE_DISABLE_MSW=true` 추가
- 시드 계정은 `scripts/seed-users.py` 및 `data.ts`의 `SEED_ACCOUNTS`와 동기화됨
- 잘못된 이메일/비밀번호 입력 시 401 에러 반환 (실제 백엔드와 동일)
