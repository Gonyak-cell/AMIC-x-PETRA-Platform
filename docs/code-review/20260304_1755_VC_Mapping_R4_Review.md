# VC/SI Mapping — Round 4 Review

> Round: R4 | Date: 2026-03-04 17:55 | Status: **CONTINUE**
> Quality Gates: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> Fix Criteria: HIGH→FIX | Critical/Major→FIX | else→SKIP

## Metrics

| Metric | Value |
|--------|-------|
| fix_target_count | 10 |
| skip_count | 1 |
| design_risk_count | 3 |
| fp_removed | 0 |
| oscillation_detected | 0 |

## Fix Target Issues (수정 완료)

### BE-R1 [Major/HIGH] — httpx 클라이언트 셧다운 누락
- **파일**: `deal-mgmt/app/main.py`
- **수정**: lifespan shutdown에 `close_kiis_dart_client()` 호출 추가
- **교차검증**: CONFIRMED

### FE-R01 [Major/HIGH] — Tailwind border-l-6 무효 유틸리티
- **파일**: `amic-platform/src/modules/ma/components/si-mapping/ValueChainDiagram.tsx`
- **수정**: `border-l-6` → `border-l-[6px]` (2개소)
- **교차검증**: CONFIRMED

### BE-R3 [Moderate/HIGH] — get_deep_dive CompanyNotFoundError 미처리
- **파일**: `deal-mgmt/app/routers/si_mapping.py`
- **수정**: `except CompanyNotFoundError` 분기 추가 → 404 반환

### BE-R4 [Moderate/HIGH] — bulk_add 감사 로그 설명 부족
- **파일**: `deal-mgmt/app/services/si_mapping_service.py`
- **수정**: 감사 로그 best-effort 정책 설명 주석 추가
- **교차검증**: PARTIAL (R3에서 try-except 추가됨, 주석만 필요)

### FE-R02 [Moderate/HIGH] — SIMappingPanel 배경 클릭 이벤트 전파
- **파일**: `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx`
- **수정**: `onClick={onClose}` → `onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}`
  - `stopPropagation` 패턴 제거 (SIDetailPanel 이벤트 버블링 차단 방지)

### FE-R05 [Moderate/HIGH] — KsicSearchInput 키보드 내비게이션 미구현
- **파일**: `amic-platform/src/modules/ma/components/si-mapping/KsicSearchInput.tsx`
- **수정**: ArrowDown/ArrowUp/Enter/Escape 키보드 내비게이션 + 하이라이트 인덱스 추가

### BE-R5 [Minor/HIGH] — 테스트 파일 조직 안내 docstring
- **파일**: `deal-mgmt/tests/test_si_mapping.py`
- **수정**: SI/VC 매핑 커버리지 + 분할 가이드 docstring 확장

### BE-R6 [Minor/HIGH] — _strip_reg_col 타입 힌트 부정확
- **파일**: `deal-mgmt/app/services/si_mapping_service.py`
- **수정**: `col: object → col: Any`, `# type: ignore[return]` 제거

### BE-R7 [Minor/HIGH] — search_ksic 변수 섀도잉
- **파일**: `deal-mgmt/app/services/si_mapping_service.py`
- **수정**: 매개변수와 동명 변수 `q` → `trimmed`/`stmt` 분리

### FE-R03 [Minor/HIGH] — BuyersTab 불필요한 타입 캐스트
- **파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx`
- **수정**: `as BuyerCandidateUpdate & { is_short_listed: boolean }` 캐스트 제거
  - `BuyerCandidateUpdate`에 `is_short_listed?: boolean` 이미 포함
  - 미사용 `BuyerCandidateUpdate` import도 제거

## Skipped Issues (스킵)

### FE-R06 [Minor/HIGH] — VcMappingResult 탭 전환 시 selectedIds 리셋
- **사유**: 의도적 UX 설계 (탭 전환 시 선택 초기화는 사용자 혼란 방지)

## Design Risk (기술부채)

### BE-R2 [Moderate/HIGH] — VC mapping N+1 쿼리 패턴
- **사유**: 현재 트래픽으로 성능 영향 미미, DB 쿼리 구조 변경 필요

### FE-R04 [Moderate/MEDIUM] — SIMappingPanel focus trap + dialog 충돌 가능성
- **사유**: focus trap 직접 구현 vs Headless UI 라이브러리 도입 — 아키텍처 결정 필요

### FE-R07 [Minor/MEDIUM] — BuyersTab Suspense fallback 모달 스타일 없음
- **사유**: 시각적 개선사항, 기능 영향 없음

## Quality Gates (수정 후 재검증)

| Gate | Status |
|------|--------|
| ruff check | ✓ PASS (0 issues) |
| ruff format | ✓ PASS (302 files formatted) |
| pytest | ✓ PASS (34/34) |
| tsc --noEmit | ✓ PASS |
| eslint | ✓ PASS |

## Convergence Status

- R3: 34건 → R4: 10건
- Trend: ↓ 감소 (71% 감소)
- Decision: **CONTINUE** (fix_target > 0)

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `deal-mgmt/app/main.py` | close_kiis_dart_client 셧다운 호출 추가 |
| `deal-mgmt/app/services/si_mapping_service.py` | Any import, 변수명, 타입 힌트, 주석 |
| `deal-mgmt/app/routers/si_mapping.py` | CompanyNotFoundError → 404 분기 |
| `deal-mgmt/tests/test_si_mapping.py` | docstring 확장 |
| `amic-platform/.../ValueChainDiagram.tsx` | border-l-[6px] |
| `amic-platform/.../SIMappingPanel.tsx` | currentTarget 배경 클릭 |
| `amic-platform/.../KsicSearchInput.tsx` | 키보드 내비게이션 |
| `amic-platform/.../BuyersTab.tsx` | 불필요 캐스트/import 제거 |
