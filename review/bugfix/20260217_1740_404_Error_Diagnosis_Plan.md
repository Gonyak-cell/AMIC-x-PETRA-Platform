# 404 에러 진단 및 수정 계획

> 작성: 2026-02-17 17:33
> 수정: 2026-02-17 17:40:32
> 카테고리: bugfix
> 심각도: Critical
> 상태: ✅ 수정 완료

## 증상

로그인 성공 후 대시보드 및 KIIS/IM 모듈 페이지에서 404 에러가 반복 발생.
쿠키 인증 수정(samesite lax, refresh 쿠키 읽기) 이후에도 동일 증상 지속.

---

## 진단 결과: 404 가능 원인 3가지

### 원인 1: MSW Service Worker 잔류 (가능성: ★★★★★ 매우 높음)

**근거**:
- `main.tsx:44` — `VITE_DISABLE_MSW`가 미설정이면 MSW 활성화
- `onUnhandledRequest: "bypass"` — 미핸들 요청은 프록시로 통과
- **문제**: MSW Service Worker가 한번 등록되면 브라우저에 영구 캐시됨
- 이전에 MSW가 활성 → 이후 `VITE_DISABLE_MSW=true` 설정 → 하지만 **stale SW가 여전히 요청을 가로채고** 핸들러 없는 요청에 대해 네트워크 에러 또는 404를 반환

**증거**:
- `main.tsx:46-54` — stale SW 해제 로직 있으나, Service Worker 언로드는 비동기이며 캐시된 응답은 즉시 제거되지 않음
- `main.tsx:69` — `worker.start()` 시 새 Service Worker 등록
- 브라우저 Application → Service Workers 탭에 `mockServiceWorker.js` 잔류 가능

**해결 방법**:
```
1. 브라우저 DevTools → Application → Service Workers
2. mockServiceWorker.js가 있으면 "Unregister" 클릭
3. Application → Storage → Clear site data (모든 항목 체크)
4. 브라우저 하드 리프레시 (Ctrl+Shift+R)
5. 페이지 재접속
```

---

### 원인 2: 백엔드 미실행 / Docker 미기동 (가능성: ★★★★☆ 높음)

**근거**:
- Vite 프록시 대상: `localhost:8000` (FDD), `localhost:8001` (KIIS), `localhost:8002` (IM)
- Docker 미실행 시 프록시 대상이 없어 에러 발생
- ECONNREFUSED는 브라우저에서 네트워크 에러 또는 프록시 에러로 표시될 수 있음

**확인 방법**:
```powershell
# Docker 컨테이너 상태 확인
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 기대 출력: fdd-api, kiis-api, im-api 모두 Up 상태
# 포트: 8000, 8001, 8002 매핑 확인

# 개별 백엔드 health check
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

**Docker 미실행 시 해결**:
```bash
docker compose up -d --build
```

**Docker 실행 중이나 백엔드 크래시 시**:
```bash
# 로그 확인
docker logs amic-fdd-api --tail 50
docker logs amic-kiis-api --tail 50
docker logs amic-im-api --tail 50

# 흔한 실패 원인:
# - DB 마이그레이션 미실행
# - 환경변수 누락
# - Python 모듈 import 에러
```

---

### 원인 3: Docker 내부 Vite 프록시 라우팅 실패 (가능성: ★★★☆☆ 보통)

**근거**:
- docker-compose.yml에서 frontend 컨테이너가 Vite 개발 서버 실행
- Vite 프록시 대상이 `localhost:8000/8001/8002`로 하드코딩
- **Docker 컨테이너 내부**에서 `localhost`는 자기 자신이지, 다른 컨테이너가 아님
- 따라서 Docker 내부 Vite에서 프록시는 ECONNREFUSED 발생

**영향 범위**:
- `http://localhost:5173` (Docker frontend 직접 접속) → 프록시 실패
- `http://localhost:3000` (nginx 경유) → 정상 (nginx가 Docker 네트워크 내 서비스명으로 라우팅)

**확인 방법**:
```
현재 어떤 URL로 접속하고 있는가?
- http://localhost:3000 → nginx 경유 (권장)
- http://localhost:5173 → Vite 직접 (Docker 모드에서 프록시 실패)
```

**해결 방법 A**: nginx 경유 접속 (http://localhost:3000)
**해결 방법 B**: 로컬 `npm run dev` 실행 (Docker 외부, 프록시 정상 작동)

---

## 환경별 권장 실행 방법

| 환경 | 명령어 | 접속 URL | MSW | 비고 |
|------|--------|---------|-----|------|
| **로컬 개발 (Mock)** | `cd amic-platform && npm run dev` | http://localhost:5173 | ✅ 활성 | 백엔드 불필요 |
| **로컬 개발 (실제 API)** | `VITE_DISABLE_MSW=true npm run dev` + Docker | http://localhost:5173 | ❌ | Docker 필수 |
| **Docker 전체** | `docker compose up -d` | http://localhost:3000 | ❌ | nginx 경유 필수 |

---

## 수정 계획 (순서대로)

### Step 0: 즉시 확인 (수정 없이 진단)

```powershell
# 0-1. Service Worker 확인
# 브라우저 DevTools → Application → Service Workers → 잔류 SW 제거

# 0-2. Docker 상태 확인
docker ps

# 0-3. 백엔드 health 확인
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# 0-4. 브라우저 콘솔에서 실제 에러 URL 확인
# DevTools → Network 탭 → 404 반환하는 요청의 Request URL 확인
```

### Step 1: MSW Service Worker 강제 제거

**파일 변경 없음** (브라우저 조작):
1. DevTools → Application → Service Workers → Unregister ALL
2. Application → Storage → Clear site data
3. Ctrl+Shift+R (하드 리프레시)

### Step 2: Vite 프록시에 Docker 네트워크 호환 추가 (선택)

**파일**: `amic-platform/vite.config.ts`

Docker 내부에서도 Vite 프록시가 작동하도록 환경변수 기반 대상 설정:

```typescript
// 현재
"/api/fdd": {
  target: "http://localhost:8000",
  ...
}

// 개선 (환경변수 기반)
"/api/fdd": {
  target: process.env.FDD_API_URL || "http://localhost:8000",
  ...
}
```

Docker 환경에서는 `FDD_API_URL=http://fdd-api:8000` 등으로 설정.

### Step 3: MSW ↔ 실제 API 전환 안전장치 강화

**파일**: `amic-platform/src/main.tsx`

MSW 비활성화 시 Service Worker를 더 적극적으로 제거:

```typescript
// 현재 (46-54줄)
if ("serviceWorker" in navigator) {
  const registrations = await navigator.serviceWorker.getRegistrations();
  for (const reg of registrations) {
    if (reg.active?.scriptURL.includes("mockServiceWorker")) {
      await reg.unregister();
    }
  }
}

// 개선: 모든 캐시도 함께 삭제
if ("serviceWorker" in navigator) {
  const registrations = await navigator.serviceWorker.getRegistrations();
  for (const reg of registrations) {
    await reg.unregister();
  }
  // MSW 관련 캐시 삭제
  const cacheNames = await caches.keys();
  for (const name of cacheNames) {
    await caches.delete(name);
  }
}
```

### Step 4: 개발 서버 시작 시 안내 메시지 추가 (선택)

**파일**: `amic-platform/src/main.tsx`

```typescript
enableMocking().then(() => {
  const isMswActive = !import.meta.env.VITE_DISABLE_MSW;
  if (!isMswActive) {
    console.info(
      "[API] MSW 비활성 → 실제 백엔드 필요\n" +
      "  FDD: http://localhost:8000/health\n" +
      "  KIIS: http://localhost:8001/health\n" +
      "  IM: http://localhost:8002/health"
    );
  }
  // ... render
});
```

---

## 프론트엔드 → 백엔드 URL 매핑 검증 결과

### Vite 프록시 리라이트 규칙
```
/api/fdd/health    → http://localhost:8000/health          (특수 리라이트)
/api/kiis/health   → http://localhost:8001/health          (특수 리라이트)
/api/im/health     → http://localhost:8002/health          (특수 리라이트)
/api/fdd/{path}    → http://localhost:8000/api/v1/{path}   (범용)
/api/kiis/{path}   → http://localhost:8001/api/v1/{path}   (범용)
/api/im/{path}     → http://localhost:8002/api/v1/{path}   (범용)
```

### 핵심 엔드포인트 매핑 (정상 확인)
| 프론트엔드 호출 | 프록시 변환 | 백엔드 라우터 | 존재 |
|----------------|-----------|-------------|------|
| `api.get("/auth/me")` | `GET /api/v1/auth/me` @ FDD | auth.py `/auth` prefix | ✅ |
| `api.post("/auth/login")` | `POST /api/v1/auth/login` @ FDD | auth.py | ✅ |
| `api.post("/auth/refresh")` | `POST /api/v1/auth/refresh` @ FDD | auth.py | ✅ |
| `fddApi.get("/deals")` | `GET /api/v1/deals` @ FDD | deals.py | ✅ |
| `kiisApi.get("/companies")` | `GET /api/v1/companies` @ KIIS | company.py | ✅ |
| `kiisApi.get("/dashboard/summary")` | `GET /api/v1/dashboard/summary` @ KIIS | dashboard.py | ✅ |
| `imApi.get("/documents")` | `GET /api/v1/documents` @ IM | documents.py | ✅ |
| `kiisApi.get("/kofia/funds")` | `GET /api/v1/kofia/funds` @ KIIS | kofia.py | ✅ |
| `kiisApi.get("/reits")` | `GET /api/v1/reits` @ KIIS | reits.py | ✅ |

**URL 매핑 불일치 없음** — 프론트엔드 호출과 백엔드 라우터 모두 정상 매칭됨.

---

## 실제 수정 내역 (2026-02-17 17:40)

### 근본 원인 확정

**nginx 설정에 health 전용 리라이트 누락** + **nginx reload 미실행**

| 요청 | nginx 리라이트 (수정 전) | 실제 백엔드 경로 | 결과 |
|------|------------------------|----------------|------|
| `/api/fdd/health` | `/api/v1/health` ❌ | `/health` | **404** |
| `/api/fdd/notifications` | `/api/v1/notifications` ✅ | `/api/v1/notifications` | **200** |

### 수정 파일

**`nginx/dev.conf`** — 2가지 변경:

1. **health 전용 location 블록 추가** (범용 규칙보다 우선 매칭):
```nginx
location = /api/fdd/health {
    rewrite ^ /health break;
    proxy_pass http://fdd_api;
}
# kiis, im 동일
```

2. **쿠키 전달 헤더 추가** (httpOnly 쿠키 인증 지원):
```nginx
proxy_set_header Cookie $http_cookie;
```

### 수정 후 검증 결과

```
nginx reload 실행: docker exec amic-nginx nginx -s reload

curl http://localhost:3000/api/fdd/health       → 200 ✅ (수정 전 404)
curl http://localhost:3000/api/kiis/health       → 200 ✅ (수정 전 404)
curl http://localhost:3000/api/im/health         → 200 ✅ (수정 전 404)
curl http://localhost:3000/api/kiis/dashboard/summary → 200 ✅ (수정 전 404)
curl http://localhost:3000/api/fdd/notifications → 401 (쿠키 없는 curl, 정상)
```
