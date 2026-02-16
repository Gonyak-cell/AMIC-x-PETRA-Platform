# Auto FDD 로컬 구동 검증 보고서

> 작성일: 2026-02-10
> Sprint: 13 (Track A — A1: 로컬 구동 검증)
> 상태: PENDING EXECUTION

---

## 검증 항목 및 결과

### 1. Docker Compose 구동 + DB 마이그레이션

| 항목 | 명령어 | 결과 | 비고 |
|------|--------|------|------|
| Docker Compose 기동 | `make up` | ⬜ PENDING | db:5433, backend:8000, pptx:3100, frontend:5173 |
| DB 마이그레이션 | `make migrate` | ⬜ PENDING | Alembic 001~005 적용 |
| 서비스 상태 확인 | `docker compose ps` | ⬜ PENDING | 4서비스 running/healthy |
| Alembic 버전 확인 | `alembic current` | ⬜ PENDING | head (005번) |

**성공 기준:** 4서비스 모두 running/healthy, `alembic current` → head

---

### 2. 브라우저 접속 확인

| 항목 | URL | 결과 | 비고 |
|------|-----|------|------|
| 프론트엔드 접속 | http://localhost:5173 | ⬜ PENDING | 로그인 페이지 표시 |
| 콘솔 에러 | F12 Console | ⬜ PENDING | 에러 0건 |

**성공 기준:** 로그인 페이지 정상 로드, F12 콘솔 에러 0건

---

### 3. 전체 워크플로 수동 테스트

| 단계 | 작업 | 예상 결과 | 결과 | 비고 |
|------|------|-----------|------|------|
| 1 | Admin 계정 생성 | 계정 생성 성공 | ⬜ PENDING | |
| 2 | 로그인 | 딜 리스트 페이지 표시 | ⬜ PENDING | |
| 3 | 딜 생성 (DealSetupWizard) | 딜 상세 + WorkflowStepper | ⬜ PENDING | |
| 4 | TB/GL 업로드 → 인제스트 | 업로드 성공 (< 5초) | ⬜ PENDING | |
| 5 | 계정 매핑 → Tie-out | 매핑 완료 + Tie-out 통과 | ⬜ PENDING | |
| 6 | QoE 분석 실행 | Adjusted EBITDA 결과 표시 | ⬜ PENDING | |
| 7 | NWC/Net Debt 분석 실행 | 분류 + 계산 결과 표시 | ⬜ PENDING | |
| 8 | PPT 보고서 생성 → 다운로드 | .pptx 파일 다운로드 성공 | ⬜ PENDING | |

**성공 기준:** 8단계 전체 PASS

---

### 4. E2E 스모크 테스트

| 항목 | 명령어 | 결과 | 비고 |
|------|--------|------|------|
| E2E 실행 | `cd e2e && npm install && npm test` | ⬜ PENDING | Playwright 39 시나리오 |

**성공 기준:** 전체 통과 (minor accessibility warnings 허용)

---

### 5. API 헬스체크

| 엔드포인트 | 예상 응답 | 결과 | 비고 |
|-----------|-----------|------|------|
| `GET /api/v1/health` | 200 OK | ⬜ PENDING | |
| `GET /api/v1/deals` | 200 (인증 후) | ⬜ PENDING | |

---

### 6. 성능 기본 확인

| 항목 | 기준 | 결과 | 비고 |
|------|------|------|------|
| 페이지 로드 (LCP) | < 3초 | ⬜ PENDING | |
| API 응답 시간 | < 500ms (P95) | ⬜ PENDING | |
| 메모리 사용량 | < 512MB (backend) | ⬜ PENDING | |

---

## 종합 결과

| 카테고리 | 항목 수 | PASS | FAIL | 결과 |
|---------|---------|------|------|------|
| Docker/DB | 4 | - | - | ⬜ |
| 브라우저 | 2 | - | - | ⬜ |
| 워크플로 | 8 | - | - | ⬜ |
| E2E | 1 | - | - | ⬜ |
| API | 2 | - | - | ⬜ |
| 성능 | 3 | - | - | ⬜ |
| **합계** | **20** | **-** | **-** | **⬜ PENDING** |

---

## 발견된 이슈

| # | 심각도 | 설명 | GitHub Issue | 상태 |
|---|--------|------|-------------|------|
| - | - | (검증 실행 후 기록) | - | - |

---

## 검증 실행 절차

```bash
# 1. Docker Compose 기동
make up
make migrate
docker compose ps

# 2. 브라우저 접속
# http://localhost:5173 → F12 콘솔 확인

# 3. 수동 워크플로 테스트
# 위 8단계 순차 실행

# 4. E2E 테스트
cd e2e && npm install && npm test

# 5. API 헬스체크
curl http://localhost:8000/api/v1/health

# 6. 성능 확인
# 브라우저 DevTools → Performance 탭
```

---

*문서 끝*
