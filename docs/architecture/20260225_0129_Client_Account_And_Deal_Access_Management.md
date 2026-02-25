# CLIENT 계정 생성 수정 + 딜 접근 관리 기능

> 작성: 2026-02-25 01:29:00

## 개요

CLIENT 역할 사용자 계정 생성 시 API 에러(500) 해결 및 사용자 관리 페이지에서 딜 접근 권한을 직접 설정하는 기능 추가.

---

## 1. 버그 수정: CLIENT 계정 생성 API 에러

### 근본 원인

3가지 문제가 복합적으로 작용:

1. **마이그레이션 체인 불일치**: `013_add_user_title.py`의 `down_revision = "012"` → 실제 revision ID는 `"012_deal_classify"`
2. **마이그레이션 자동 실행 미지원**: FDD 백엔드에 lifespan 기반 alembic 자동 마이그레이션 없음 (deal-mgmt만 있었음)
3. **컬럼 중복**: seed 스크립트(`scripts/seed-users.py`)가 `title` 컬럼을 이미 추가 → 마이그레이션 013이 `DuplicateColumn` 에러

### 수정 내용

| 파일 | 변경 |
|------|------|
| `fdd/backend/app/main.py` | lifespan + `_run_alembic_upgrade()` 추가 (deal-mgmt 패턴) |
| `fdd/backend/alembic/versions/013_add_user_title.py` | `down_revision` 수정 (`"012"` → `"012_deal_classify"`) + idempotent 처리 |
| DB 직접 실행 | `ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'CLIENT'` + `alembic stamp 014` |

### 결과

- `GET /health` → `{"migration_ok": true}`
- CLIENT 역할 사용자 생성 가능

---

## 2. 신규 기능: 사용자 관리 페이지에서 딜 접근 관리

### 변경 전

- `ClientDealAssignments` 컴포넌트가 **읽기 전용**
- "Go to M&A → Transaction Workspace → Client Access to assign deals" 안내만 표시
- 딜 배정/해제하려면 각 거래 워크스페이스로 이동해야 함

### 변경 후

- **거래 Select 드롭다운**: 모든 활성 거래 목록에서 이미 배정된 딜 자동 필터링
- **배정 버튼**: 선택한 거래에 CLIENT 사용자 즉시 배정
- **해제 버튼**: 각 배정 딜 행에 삭제 아이콘으로 즉시 해제
- 모든 작업에 toast 알림 + 자동 목록 갱신

### 수정 파일

| 파일 | 변경 |
|------|------|
| `deal-mgmt/app/schemas/deal_client.py` | `ClientDealSummary`에 `id: uuid.UUID` 필드 추가 |
| `deal-mgmt/app/routers/deal_clients.py` | `/deal-clients/by-email` 응답에 `dc.id` 포함 |
| `amic-platform/src/hooks/useClientDeals.ts` | `id` 타입 추가, `useAdminAssignDeal`, `useAdminUnassignDeal` 훅 추가 |
| `amic-platform/src/pages/admin/UserManagementPage.tsx` | `ClientDealAssignments` 대화형 개선 |

---

## 검증

- TypeScript 타입 체크: 통과
- deal-mgmt pytest: 382/382 통과
- FDD health: `migration_ok: true`
- DB userrole enum: `{ADMIN,MANAGER,ANALYST,VIEWER,CLIENT}`
