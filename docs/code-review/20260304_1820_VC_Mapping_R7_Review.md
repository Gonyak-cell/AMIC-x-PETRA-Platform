# VC/SI Mapping — Round 7 Review

> Round: R7 | Date: 2026-03-04 18:20 | Status: **CONTINUE**
> Quality Gates: ruff(✓) pytest(34/34 ✓) tsc(✓) eslint(✓)
> Fix Criteria: HIGH→FIX | Critical/Major→FIX | else→SKIP
> Perspective: **Edge Cases / Defensive Coding** (런타임 크래시, null/undefined, 범위 초과, 예외 경로)

## Metrics

| Metric | Value |
|--------|-------|
| fix_target_count | 5 |
| skip_count | 8 |
| design_risk_count | 0 |
| fp_removed | 0 |
| oscillation_detected | 0 |

## Fix Target Issues (수정 완료)

### EC-01 [Moderate/HIGH] — asyncio.gather 인덱스 하드코딩
- **파일**: `deal-mgmt/app/services/si_mapping_service.py`
- **수정**: `responses[1:4]`, `responses[4]`, `responses[5]` 하드코딩 → `num_fin_years` 변수 기반 동적 인덱스
- **교차검증**: CONFIRMED — `financial_tasks` 길이 변경 시 인덱스 불일치 런타임 크래시 방지

### EC-02 [Moderate/HIGH] — _extract_amount None.replace() 크래시
- **파일**: `deal-mgmt/app/services/si_mapping_service.py`
- **수정**: `item.get("thstrm_amount", "").replace(",", "")` → `(item.get("thstrm_amount") or "").replace(",", "")`
- **교차검증**: CONFIRMED — DART API가 `{"thstrm_amount": null}` 반환 시 `dict.get(key, default)`는 None 반환 (키 존재), `None.replace()` → AttributeError

### FE-EC-1 [Moderate/HIGH] — company! 비-null 단언 런타임 미보호
- **파일**: `amic-platform/.../SIDetailPanel.tsx`
- **수정**: `company={company!}` → `company && <OverviewTab company={company} ...>` 가드 추가
- **교차검증**: CONFIRMED — TypeScript `!`는 컴파일 타임만, 런타임에서 `company`가 undefined면 OverviewTab 내부에서 크래시

### FE-EC-2 [Minor/HIGH] — RELATION_CONFIG 미정의 키 접근
- **파일**: `amic-platform/.../SICandidateTable.tsx`
- **수정**: `RELATION_CONFIG[c.relation]` → `?? { label: c.relation, badgeCls: "bg-slate-100 text-slate-600" }` 폴백 추가
- **교차검증**: CONFIRMED — 백엔드가 새 relation 타입 추가 시 FE가 undefined.label 크래시 방지

### FE-EC-3 [Minor/HIGH] — bulkAddMutation 에러 미표시
- **파일**: `amic-platform/.../SIMappingPanel.tsx`
- **수정**: 푸터 벌크 추가 버튼 옆에 `bulkAddMutation.isError` 에러 메시지 표시 추가
- **교차검증**: CONFIRMED — `vcMapMutation`과 `mapMutation`은 에러 표시 있으나 `bulkAddMutation`만 누락

## Skipped Issues (스킵)

### EC-03 [Minor/MEDIUM] — financial_tasks 빈 배열 시 responses 인덱스 오류
- **사유**: EC-01 수정으로 `num_fin_years=0`이면 `responses[1:1]` = 빈 리스트 → 안전하게 동작

### EC-04 [Minor/LOW] — _parse_overview 내부 KeyError
- **사유**: `.get()` 패턴으로 안전하게 추출 (이미 방어 코드 존재)

### EC-05 [Minor/LOW] — DART API 타임아웃 미설정
- **사유**: httpx 클라이언트 레벨에서 기본 타임아웃 적용

### EC-06 [Minor/LOW] — corp_code 빈 문자열 전달
- **사유**: `_match_corp_code`가 None 반환 → 이미 early return 처리

### EC-07 [Minor/LOW] — year 범위 오프-바이-원
- **사유**: `range(current_year, current_year - 3, -1)` 정확 (3개년: 현재, -1, -2)

### FE-EC-4 [Minor/MEDIUM] — ValueChainDiagram 빈 배열 렌더링
- **사유**: 컴포넌트 내부에서 빈 배열 체크 → "데이터 없음" 메시지 표시

### FE-EC-5 [Minor/LOW] — KsicSearchInput 빈 응답 처리
- **사유**: React Query가 빈 배열을 정상 처리, suggestions.map() 안전

### FE-EC-6 [Minor/LOW] — SIDetailPanel isLoading 중 탭 전환
- **사유**: 로딩 중 탭 전환은 data가 아직 없어 빈 UI → UX 이슈이나 크래시 아님

## Quality Gates (수정 후 재검증)

| Gate | Status |
|------|--------|
| ruff check | ✓ PASS (0 issues) |
| ruff format | ✓ PASS |
| pytest | ✓ PASS (34/34) |
| tsc --noEmit | ✓ PASS |
| eslint | ✓ PASS |

## Convergence Status

- R4: 10건 → R5: 2건 → R6: 3건 → R7: 5건
- Trend: → 안정 (새 관점에서 소수 발견, 심각도 Moderate/Minor 위주)
- Decision: **CONTINUE** (fix_target > 0, 다음 관점으로 계속)

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `deal-mgmt/app/services/si_mapping_service.py` | num_fin_years 동적 인덱스, None-safe replace |
| `amic-platform/.../SIDetailPanel.tsx` | company! → company && 가드 |
| `amic-platform/.../SICandidateTable.tsx` | RELATION_CONFIG 폴백 |
| `amic-platform/.../SIMappingPanel.tsx` | bulkAddMutation 에러 표시 |
