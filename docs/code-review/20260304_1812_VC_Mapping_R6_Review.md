# VC/SI Mapping — Round 6 Review

> Round: R6 | Date: 2026-03-04 18:12 | Status: **CONTINUE**
> Quality Gates: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> Fix Criteria: HIGH→FIX | Critical/Major→FIX | else→SKIP
> Perspective: **Deep Concurrency / Performance** (N+1, race condition, memory, async patterns, rendering)

## Metrics

| Metric | Value |
|--------|-------|
| fix_target_count | 3 |
| skip_count | 4 |
| design_risk_count | 3 |
| fp_removed | 1 |
| oscillation_detected | 1 |

## Fix Target Issues (수정 완료)

### SI-06 [Minor/HIGH] — close_kiis_dart_client 중복 호출
- **파일**: `deal-mgmt/app/main.py`
- **수정**: lifespan shutdown에서 직접 `close_kiis_dart_client()` 호출 제거 (R4에서 추가했으나 `close_all_clients()`에서 이미 호출)
- **교차검증**: CONFIRMED — dependencies.py:99-105에서 동일 함수 호출 확인

### W-2 [Minor/HIGH] — corporateInfo IIFE 매 렌더 실행
- **파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx`
- **수정**: IIFE 패턴 → `useMemo([txn?.corporate_info])` 전환
- **교차검증**: CONFIRMED — txn 미변경 시 불필요한 in 연산자 체크 방지

### W-3 [Moderate/HIGH] — SICandidateTable 필터 카운트 반복 계산
- **파일**: `amic-platform/src/modules/ma/components/si-mapping/SICandidateTable.tsx`
- **수정**: 인라인 `candidates.filter().length` (3회) → `useMemo` `relationCounts` 사전 계산
- **교차검증**: CONFIRMED — 렌더당 O(3n) → O(n) 단일 순회

## Skipped Issues (스킵)

### SI-02 [Minor/HIGH] — InMemoryRateLimiter race condition
- **사유**: 단일 워커에서 asyncio GIL 보호. R5 I-06 Redis 전환과 동일 범주

### SI-04 [Minor/HIGH] — DART 검색 직렬 API 호출
- **사유**: corp_code 의존성으로 구조적 직렬 필수. 온디맨드 단건 호출이라 체감 영향 미미

### S-1 [Minor/MEDIUM] — useKsicSearch staleTime 미설정
- **사유**: 기능 정상 동작. KSIC 검색은 디바운스(300ms)로 이미 요청 최적화

### S-2 [Minor/MEDIUM] — SIDetailPanel onClose 인라인
- **사유**: deepDiveId=null 시 렌더 안됨. 체감 없음

## Design Risk (기술부채)

### SI-01 [Major/HIGH] — VC 매핑 업종별 N+1 쿼리 (진동 2회차)
- **사유**: R4 BE-R2에서도 등장 (2회차 → DESIGN_RISK 확정)
- **해결 방향**: ROW_NUMBER() 윈도우 함수 배치 쿼리 전환 (DB 구조 변경)

### SI-03 [Moderate/HIGH] — 5,000건 SICompany 인메모리 로딩
- **사유**: 프로세스 레벨 TTL 캐시 도입 필요 (스탈 데이터 관리 정책 결정 필요)

### W-1 [Moderate/HIGH] — buyerColumns 매 렌더 재생성
- **사유**: `updateBuyer` 참조가 매 렌더 변경 → useMemo 단순 적용 무효. 체크박스를 별도 컴포넌트로 추출하는 구조 변경 필요

## False Positive (제거됨)

### SI-05 — 전방/후방 쿼리 병렬화
- **사유**: FP-IMPL — AsyncSession 단일 커넥션 공유로 동일 세션 내 asyncio.gather 안전하지 않음

## Quality Gates (수정 후 재검증)

| Gate | Status |
|------|--------|
| ruff check | ✓ PASS (0 issues) |
| ruff format | ✓ PASS |
| pytest | ✓ PASS (34/34) |
| tsc --noEmit | ✓ PASS |
| eslint | ✓ PASS |

## Convergence Status

- R3: 34건 → R4: 10건 → R5: 2건 → R6: 3건
- Trend: → 안정 (R5 2건 → R6 3건, 새 관점에서 소폭 증가)
- Decision: **CONTINUE** (fix_target > 0, R7 edge cases 관점으로 계속)

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `deal-mgmt/app/main.py` | 중복 close_kiis_dart_client 호출 제거 |
| `amic-platform/.../BuyersTab.tsx` | useMemo import 추가, corporateInfo useMemo 전환 |
| `amic-platform/.../SICandidateTable.tsx` | relationCounts useMemo 추가, 인라인 filter 제거 |
