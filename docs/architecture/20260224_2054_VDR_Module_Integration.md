# VDR 모듈 통합 — 사이드바 + Overview 페이지 + 404/500 디버깅

> 작성: 2026-02-24 20:54:00

## 개요

VDR(Virtual Data Room)을 사이드바 독립 모듈로 추가하고, 모든 거래의 VDR 현황을 한눈에 볼 수 있는 Overview 페이지를 구현했다. 이후 발생한 404→500 에러를 체계적으로 디버깅하여 Alembic 마이그레이션 체인 오류를 수정했다.

## 변경 사항

### 1. 프론트엔드 — 사이드바 통합

**ModuleSwitcher** ([ModuleSwitcher.tsx](amic-platform/src/components/layout/ModuleSwitcher.tsx))
- MODULES 배열에 VDR 모듈 추가 (`FolderLock` 아이콘, `/vdr` 경로)
- `getCurrentModule()` 함수에 `/vdr` 경로 매핑 추가

**Sidebar** ([Sidebar.tsx](amic-platform/src/components/layout/Sidebar.tsx))
- `VDR_NAV` 상수 추가: `[{ to: "/vdr", label: "VDR Overview", icon: FolderLock }]`
- `isVdr` 플래그로 VDR 전용 네비게이션 섹션 렌더링

**App.tsx** ([App.tsx](amic-platform/src/App.tsx))
- `VdrRoutes` lazy import + `vdr/*` 라우트 추가 (React.lazy + Suspense)

### 2. 프론트엔드 — VDR 모듈 파일

| 파일 | 역할 |
|------|------|
| `modules/vdr/VdrRoutes.tsx` | VDR 모듈 라우트 정의 |
| `modules/vdr/types/overview.ts` | `VdrOverviewItem` 인터페이스 |
| `modules/vdr/hooks/useVdrOverview.ts` | `maApi.get("/vdr/overview")` 훅 |
| `modules/vdr/pages/VdrOverviewPage.tsx` | PageHero + KPI 3개 + DataTable |

**VDR Overview 페이지 기능**:
- KPI 카드 3개: 전체 거래, VDR 초기화됨, 총 문서
- DataTable: 거래명, 단계, 폴더수, 문서수, 총 용량, 마지막 활동
- 행 클릭 → `/ma/transactions/${id}?tab=vdr` 이동

### 3. 백엔드 — VDR Overview API

| 파일 | 역할 |
|------|------|
| `deal-mgmt/app/routers/vdr_overview.py` | `GET /api/v1/vdr/overview` 엔드포인트 |
| `deal-mgmt/app/services/vdr_service.py` | `get_all_vdr_overviews()` — subquery join으로 N+1 방지 |
| `deal-mgmt/app/schemas/vdr.py` | `VdrOverviewItem` Pydantic 스키마 |
| `deal-mgmt/app/main.py` | `vdr_overview` 라우터 등록 |

### 4. 테스트

[test_vdr.py](deal-mgmt/tests/test_vdr.py) — `TestVdrOverview` 클래스 4개 테스트:
- `test_overview_empty` — 거래 없을 때 빈 배열
- `test_overview_includes_transaction` — 거래 포함 확인
- `test_overview_shows_uninitialized` — VDR 미초기화 거래 표시
- `test_overview_after_init_and_upload` — VDR 초기화 + 파일 업로드 후 통계

## 404/500 디버깅 과정

### 증상
VDR Overview 페이지에서 `GET /api/ma/vdr/overview` 요청 시 404 에러.

### 디버깅 단계

| 단계 | 확인 내용 | 결과 |
|------|----------|------|
| 1 | 프론트 훅 → Vite 프록시 → 백엔드 라우터 코드 체인 | 모두 정상 |
| 2 | `docker compose logs deal-mgmt-api` | `Stopping reloader process [1]` — 컨테이너 중지 |
| 3 | `curl localhost:8003` | exit code 7 (connection refused) |
| 4 | 포트 충돌 확인 | 이전 `deal-mgmt-postgres` 컨테이너가 5436 점유 → 제거 |
| 5 | 컨테이너 재시작 후 curl | 500 Internal Server Error |
| 6 | `docker exec` 내부 Python 직접 테스트 | `UndefinedTableError: relation "vdr_folders" does not exist` |

### 근본 원인

`013_dd_workstream_restructure.py`의 Alembic 마이그레이션 체인 불일치:

```python
# 수정 전 (오류)
down_revision = "012"

# 수정 후 (정상)
down_revision = "012_ralph_phase2"
```

실제 revision 012의 ID는 `"012_ralph_phase2"`인데 `"012"`만 기재되어 Alembic이 체인을 인식하지 못함 → 013/014 마이그레이션 미실행 → VDR 테이블 미생성.

### 해결

1. `down_revision` 수정
2. Docker 컨테이너 재시작
3. `curl http://localhost:8003/api/v1/vdr/overview` → **200 OK**, 3개 거래 정상 반환

## 요청 경로 체인 (최종 확인)

```
Browser → /api/ma/vdr/overview
  → Vite 프록시 (vite.config.ts:79-83)
    → rewrite: /api/ma → /api/v1
    → target: localhost:8003
  → deal-mgmt FastAPI
    → /api/v1/vdr/overview (vdr_overview.router)
    → vdr_service.get_all_vdr_overviews()
  → 200 OK + JSON 배열
```

## 수정 파일 요약

| 파일 | 변경 유형 |
|------|----------|
| `amic-platform/src/components/layout/ModuleSwitcher.tsx` | 수정 |
| `amic-platform/src/components/layout/Sidebar.tsx` | 수정 |
| `amic-platform/src/App.tsx` | 수정 |
| `amic-platform/src/modules/vdr/VdrRoutes.tsx` | 신규 |
| `amic-platform/src/modules/vdr/types/overview.ts` | 신규 |
| `amic-platform/src/modules/vdr/hooks/useVdrOverview.ts` | 신규 |
| `amic-platform/src/modules/vdr/pages/VdrOverviewPage.tsx` | 신규 |
| `deal-mgmt/app/routers/vdr_overview.py` | 신규 |
| `deal-mgmt/app/services/vdr_service.py` | 수정 |
| `deal-mgmt/app/schemas/vdr.py` | 수정 |
| `deal-mgmt/app/main.py` | 수정 |
| `deal-mgmt/tests/test_vdr.py` | 수정 |
| `deal-mgmt/migrations/versions/013_dd_workstream_restructure.py` | 수정 (버그 수정) |
