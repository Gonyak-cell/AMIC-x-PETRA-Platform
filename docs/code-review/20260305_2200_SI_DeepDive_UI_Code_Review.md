# Code Review — SI 매핑 모달 GSAP 애니메이션 + 딥다이브 UI 활성화

> **Review Date**: 2026-03-05 22:00 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `c64f261` — SIMappingPanel.tsx, VcMappingResult.tsx
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(✅) eslint(✅) vitest 178 tests(✅) build(✅)
> **Review Gates**: Backend(available) Agent-Filtering(5개 에이전트 호출, 8개 제외)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P0: 1                |
| Major    | 2     | HIGH: 1 / MEDIUM: 1    | P1: 1 / P2: 1        |
| Moderate | 3     | HIGH: 1 / MEDIUM: 2    | P2: 1 / P3: 2        |
| Minor    | 2     | HIGH: 1 / MEDIUM: 1    | P3: 2                |
| **Total**| **8** | HIGH: **4** / MEDIUM: **3** / LOW: **1** (제거됨) | P0: **1** / P1: **1** / P2: **2** / P3: **4** |

**FP Prevention**: 가설 15건 검증, 7건 사전 거부 (거부율: 47%) | 교차 검증 3건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 3건 하향 조정 (Major→P2, Moderate→P3)
- LOW 신뢰도 이슈 1건 제거 (GSAP null target — FP)

---

## Findings

### [R3-C1] VcChainCompany.id(int) → deep-dive API(uuid.UUID) 타입 불일치 — [Critical/HIGH] — Priority: P0

- **위치**: `VcMappingResult.tsx:48`, `SIMappingPanel.tsx:240`
- **에이전트**: R3 데이터 무결성
- **교차 검증**: ✅ CONFIRMED (review-verifier)

**증거**:
```typescript
// VcMappingResult.tsx:48 — VcChainCompany.id는 number (Integer PK)
onClick={() => onCompanyClick(String(company.id))}
// → String(12345) → "12345"

// si_mapping.ts:101 — 타입 정의
export interface VcChainCompany {
  id: number;  // ← Integer PK (vc_companies 테이블)
  ...
}

// useSIMapping.ts:72 — API 호출
const { data } = await maApi.get<DeepDiveResponse>(
  `/si-mapping/companies/${companyId}/deep-dive`,
);
// → /si-mapping/companies/12345/deep-dive

// deal-mgmt/app/routers/si_mapping.py:161 — 백엔드 파라미터
async def get_deep_dive(
    company_id: uuid.UUID,  // ← UUID 기대 → "12345" 파싱 실패 → 422
    ...
```

**영향**: 기업명 클릭 시 **100% 실패** (422 Unprocessable Entity). 딥다이브 기능이 VC 매핑 결과에서 완전히 작동 불가.

**근본 원인**: `vc_companies` 테이블(Integer PK)과 `si_companies` 테이블(UUID PK)이 서로 다른 PK 체계를 사용하며, deep-dive API는 `si_companies`의 UUID를 기대. VC 매핑 결과의 기업은 `vc_companies`이므로 deep-dive API와 호환되지 않음.

**수정 방안 (택 1)**:
1. VC 기업 전용 deep-dive 엔드포인트 추가 (`/vc-mapping/companies/{vc_id}/deep-dive`, Integer 파라미터)
2. VC 기업 → SI 기업 매칭 후 SI 기업 UUID로 deep-dive 호출
3. deep-dive API를 compound lookup으로 변경 (기업명 + 등록번호 기반)

---

### [R6-M1] `<div role="dialog">` 사용 — 네이티브 `<dialog>` 패턴과 불일치 — [Major/HIGH] — Priority: P1

- **위치**: `SIMappingPanel.tsx:150-157`
- **에이전트**: R6 비즈니스 & UX
- **교차 검증**: ✅ CONFIRMED → DESIGN_RISK

**증거**:
```tsx
// SIMappingPanel.tsx:150-157 — <div> 사용
<div ref={panelRef} className="fixed inset-0 z-50 ..."
  role="dialog" aria-modal="true" aria-labelledby={titleId}>

// 비교: Modal.tsx, SlidePanel.tsx — <dialog> 사용
<dialog ref={dialogRef} ... onCancel={(e) => { e.preventDefault(); handleClose(); }}>
```

**영향**:
- 스크린 리더가 모달 뒤 콘텐츠를 탐색할 수 있음 (background `inert` 미적용)
- 수동 focus trap + Escape 핸들러로 기능적 보완은 됨
- SIDetailPanel(`<dialog>` top layer)과 SIMappingPanel(`<div>` z-index) 간 스태킹 모델 불일치

**판정**: DESIGN_RISK — 현재 기능적으로 동작하나, Modal.tsx/SlidePanel.tsx 패턴과의 일관성 부족. 향후 `<dialog>` 전환 권장.

---

### [R6-M2] 백드롭 `<div>` 접근성 역할 부재 — [Major/MEDIUM ⚠️] — Priority: P2

- **위치**: `SIMappingPanel.tsx:159-164`
- **에이전트**: R6 비즈니스 & UX
- **교차 검증**: ⚠️ PARTIAL — 기존 SlidePanel.tsx와 동일 패턴

**증거**:
```tsx
// SIMappingPanel.tsx:159-164
<div ref={backdropRef} className="fixed inset-0 bg-amic-900/70 ..."
  style={{ opacity: 0 }} onClick={handleClose} />
// role, aria-label, tabIndex 없음

// SlidePanel.tsx:119-124 — 동일 패턴 (기존 코드)
<div ref={backdropRef} className="fixed inset-0 bg-amic-900/70 ..."
  style={{ opacity: 0 }} onClick={handleClose} />
```

**판정**: PARTIAL — 기존 코드베이스 패턴과 동일. 단독 수정보다 일괄 `<dialog>` 전환 시 함께 해결 권장.

⚠️ 이 Major 이슈는 MEDIUM 신뢰도로 인해 P2로 분류되었습니다. (기존 패턴과 동일하여 이 커밋 단독 수정 대상이 아님)

---

### [R4-M2] bulkAddMutation stale 에러 메시지 — [Moderate/HIGH] — Priority: P2

- **위치**: `VcMappingResult.tsx:332-351`
- **에이전트**: R4 프로덕션 복원력
- **교차 검증**: ✅ CONFIRMED (auto-verify)

**증거**:
```tsx
// VcMappingResult.tsx:247-249 — 탭 전환 시 selectedIds 초기화
onClick={() => {
  setActiveTab(key);
  setSelectedIds(new Set());  // ← 에러 영역 숨김 (opacity-0)
}}
// 하지만 bulkAddMutation.isError는 리셋되지 않음
// → 다시 항목 선택 시 이전 실패의 에러 메시지 재표시
```

**영향**: 탭 전환 후 새 항목 선택 시 stale 에러 메시지가 나타나 사용자 혼란 유발. 새 `mutate()` 호출 시 자동 리셋되므로 기능적 영향은 낮음.

**수정 제안**: 탭 전환 시 `bulkAddMutation.reset()` 호출 추가.

---

### [R6-M4] 기업명 버튼 시각적 어포던스 부족 — [Moderate/MEDIUM ⚠️] — Priority: P3

- **위치**: `VcMappingResult.tsx:46-52`
- **에이전트**: R6 비즈니스 & UX

**증거**:
```tsx
// VcMappingResult.tsx:49
className="text-left text-accent hover:underline"
// 기본 상태에서 underline 없음 → 터치 기기에서 클릭 가능 여부 인지 어려움
```

**영향**: 터치 기기 사용자/색각 이상 사용자가 클릭 가능 여부 인지 어려울 수 있으나, 테이블 내 파란색 텍스트는 일반적 UI 컨벤션이므로 실사용 영향 낮음.

**수정 제안**: `className="text-left text-accent underline decoration-accent/30 underline-offset-2 hover:decoration-accent"` 로 기본 underline 추가.

⚠️ MEDIUM 신뢰도로 인해 P3으로 분류되었습니다.

---

### [R4-M1] vcMapMutation 에러 피드백 — 복구 안내 부재 — [Moderate/MEDIUM ⚠️] — Priority: P3

- **위치**: `SIMappingPanel.tsx:218-234`
- **에이전트**: R4 프로덕션 복원력

**증거**:
```tsx
// SIMappingPanel.tsx:230-234
{vcMapMutation.isError && (
  <p role="alert" className="mt-2 text-sm text-red-600">
    {vcMapMutation.error.message}  // ← 에러 메시지만, 복구 안내 없음
  </p>
)}
```

**영향**: 토스트 + 인라인 이중 피드백이 제공되며, 버튼이 여전히 보여 재시도 가능. 기능적 복원력 양호. 네트워크 장애 시 구체적 복구 안내("네트워크 연결을 확인하세요") 없음.

**수정 제안**: 선택적 개선 — "잠시 후 다시 시도해 주세요" 안내 추가.

⚠️ MEDIUM 신뢰도로 인해 P3으로 분류되었습니다.

---

### [R5-m1] 인라인 화살표 함수 memo 무효화 — [Minor/HIGH] — Priority: P3

- **위치**: `SIMappingPanel.tsx:240`
- **에이전트**: R5 운영 & 코드 건강성

**증거**:
```tsx
// SIMappingPanel.tsx:240
onCompanyClick={(id) => setDeepDiveId(id)}
// → 매 렌더링마다 새 참조 생성
// → memo(ChainPanelCard), memo(CompanyRow) 무효화

// React state setter는 안정적 참조이므로 직접 전달 가능:
onCompanyClick={setDeepDiveId}
```

**영향**: 실질적 성능 영향은 낮음 (VC 매핑 결과 목록은 일반적으로 수십 건). 코드 간결성 개선 가능.

**수정 제안**: `onCompanyClick={setDeepDiveId}` 로 직접 전달.

---

### [R6-m1] ARIA tabs 키보드 탐색 패턴 불일치 — [Minor/MEDIUM ⚠️] — Priority: P3

- **위치**: `VcMappingResult.tsx:238-260`
- **에이전트**: R6 비즈니스 & UX

**증거**: 모든 탭 버튼이 `tabIndex={0}`(기본값)으로 설정되어 Tab 키로 3개 탭 모두 순회. ARIA Authoring Practices는 비활성 탭에 `tabIndex={-1}` + 좌우 화살표 탐색 권장.

**판정**: **기존 코드** — 이 커밋의 변경분이 아님. 향후 일괄 개선 과제.

⚠️ MEDIUM 신뢰도 + 기존 코드로 인해 P3으로 분류되었습니다.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 데이터 무결성)
1. [R3-C1] [Critical/HIGH]: VcChainCompany.id(int) → deep-dive API(uuid.UUID) 타입 불일치 — VcMappingResult.tsx (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89, UX 일관성)
1. [R6-M1] [Major/HIGH → DESIGN_RISK]: `<div role="dialog">` vs `<dialog>` 패턴 불일치 — SIMappingPanel.tsx (점수: 70)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [R6-M2] [Major/MEDIUM ⚠️]: 백드롭 접근성 역할 부재 — SIMappingPanel.tsx (점수: 42, 기존 패턴과 동일)
2. [R4-M2] [Moderate/HIGH]: bulkAddMutation stale 에러 메시지 — VcMappingResult.tsx (점수: 40)

### P3 — 저우선 (점수: <30, 개선 가능)
1. [R6-M4] [Moderate/MEDIUM ⚠️]: 기업명 버튼 시각적 어포던스 — VcMappingResult.tsx (점수: 24)
2. [R4-M1] [Moderate/MEDIUM ⚠️]: vcMapMutation 에러 복구 안내 — SIMappingPanel.tsx (점수: 24)
3. [R5-m1] [Minor/HIGH]: 인라인 화살표 함수 memo 무효화 — SIMappingPanel.tsx (점수: 20)
4. [R6-m1] [Minor/MEDIUM ⚠️]: ARIA tabs 키보드 탐색 — VcMappingResult.tsx (점수: 12, 기존 코드)

---

## 계획 대비 구현 검증 (§6)

플랜 파일: `C:\Users\서지원\.claude\plans\tidy-shimmying-church.md`

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | VcMappingResultProps에 onCompanyClick 추가 | ✅ | VcMappingResult.tsx:19 |
| 2 | CompanyRow에 기업명 클릭 트리거 추가 | ✅ | VcMappingResult.tsx:44-56 |
| 3 | ChainPanelCard에 콜백 전달 | ✅ | VcMappingResult.tsx:70-79, 143-150 |
| 4 | 경쟁사 CompanyRow에도 전달 | ✅ | VcMappingResult.tsx:296-303 |
| 5 | VcMappingResult에 setDeepDiveId 연결 | ✅ | SIMappingPanel.tsx:240 |
| 6 | Escape 핸들러 수정 (SlidePanel 위임) | ✅ | SIMappingPanel.tsx:96-106 |
| 7 | z-index 충돌 없음 확인 | ✅ | dialog top layer — 검증 완료 |
| 8 | **VcChainCompany.id 타입 호환성** | ❌ | VcChainCompany.id(int) ≠ deep-dive API(uuid.UUID) |

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | §1 정합성 — 자동 검증됨 |
| eslint | ✅ PASS | §1 정합성 — 자동 검증됨 |
| vitest (178 tests) | ✅ PASS | §2 완전성 — 자동 검증됨 |
| vite build | ✅ PASS | §2 완전성 — 자동 검증됨 |

---

## Methodology

- **Agents**: R2(보안), R3(데이터무결성), R4(프로덕션복원력), R5(운영&코드건강성), R6(비즈니스&UX)
- **Excluded Agents**: R2-BE(백엔드보안), API감사, 인프라, 성능, 테스트, a11y전용, 타입체커, 마이그레이션
- **Files scanned**: 2개 (SIMappingPanel.tsx, VcMappingResult.tsx) + 의존 파일 7개 (si_mapping.ts, useSIMapping.ts, SIDetailPanel.tsx, SlidePanel.tsx, Modal.tsx, gsap.ts, si_mapping.py)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 1건 + Major 2건 = 3건 수행
- **Backend availability**: deal-mgmt(available) FDD(N/A) KIIS(N/A) IM(N/A)

## 검증 투명성

### 검증 통계
- 검증한 가설: 15건
- 거부된 가설 (사전 제거): 7건
- 보고된 이슈: 8건
- 거부율: 47%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 정상 동작 확인 | 3 | isClosingRef 이중호출 방지, Escape 위임 타이밍, Escape 키 위임 패턴 |
| 범위 외 | 2 | prefers-reduced-motion(전역 설정), handleBulkAdd useCallback(불필요) |
| 신뢰도 불충분 | 1 | GSAP null 타겟(LOW → GSAP v3에서 안전 처리) |
| 관찰/정보 | 1 | MAX_BULK 클라이언트 가드(Info 등급, 적절한 구현) |
