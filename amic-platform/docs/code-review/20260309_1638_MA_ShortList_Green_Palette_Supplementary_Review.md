# Code Review — MA Short List 녹색 팔레트 + 통합 보충 리뷰

> **Review Date**: 2026-03-09 16:38
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `HEAD~1..HEAD` (커밋 f05850b) — 44개 변경 파일
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review (13관점) + Cross-Verification + Auto-Verification
> **Quality Gates**: tsc(✅ PASS) eslint(✅ PASS) vitest(✅ 178/178 PASS) build(✅ PASS)
> **Review Gates**: Backend(deal-mgmt available) Agent-Filtering(3개 에이전트 호출, R1 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0 | — | — |
| Major | 3 | HIGH: 3 | P0: 2 / P1: 1 |
| Moderate | 5 | HIGH: 1 / MEDIUM: 3 / LOW: 1 | P2: 1 / P3: 4 |
| Minor | 4 | MEDIUM: 1 / LOW: 3 | P3: 4 |
| Info | 1 | — | — |
| **Total** | **13** | HIGH: **4** / MEDIUM: **4** / LOW: **4** / Info: **1** | P0: **2** / P1: **1** / P2: **1** / P3: **8** / Info: **1** |

**FP Prevention**: 가설 17건 검증, 4건 사전 거부 (거부율: 24%)
- 교차 검증 4건 수행 (CONFIRMED: 3, PARTIAL: 1)
- 자동 검증 13건 수행 (FALSE_POSITIVE 제거: 3건)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 4건 하향 조정
- LOW 신뢰도 이슈 4건 하향 조정

---

## Findings

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

#### [SEC-01=R4-02] nda_markups `prev_path` Path Traversal 미방어 — [Major/HIGH] — P0 (점수: 95)

- **파일**: `deal-mgmt/app/routers/nda_markups.py:362-364`
- **교차 검증**: ×2 (보안 에이전트 + R4 에이전트 독립 발견) + review-verifier CONFIRMED
- **증거**:
  ```python
  # line 362-364: NO relative_to() check
  prev_path = Path(prev_markup.file_path)
  reference_text = await run_in_threadpool(
      lambda: redline_engine.extract_paragraphs_text(prev_path.read_bytes())
  )
  ```
  반면 같은 파일의 `base_path`(line 344-347)에는 `relative_to(UPLOAD_DIR.resolve())` 방어 존재.
- **영향**: `prev_markup.file_path`에 `../../etc/passwd` 같은 값이 DB에 저장되면 서버 파일 읽기 가능
- **권장**: `prev_path.resolve().relative_to(UPLOAD_DIR.resolve())` 검증 추가

---

#### [R4-01=R6-02] VDR auto-init retry 무한 루프 가능성 — [Major/HIGH] — P0 (점수: 95)

- **파일**: `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx:85-134`
- **교차 검증**: ×2 (R4 에이전트 + R6 에이전트 독립 발견) + review-verifier CONFIRMED
- **증거**:
  ```tsx
  .catch((err: unknown) => {
      autoInitRef.current = false;        // 재진입 허용
      if (retryCountRef.current >= 3) {
        toast.error("VDR 초기화에 실패했습니다...");
      } else {
        qc.invalidateQueries({            // summary refetch → useEffect 재트리거
          queryKey: ["ma", "transactions", txnId, "vdr"],
        });
      }
  });
  ```
  `retryCountRef`는 `useRef`이므로 컴포넌트 unmount/remount 시 리셋됨 → 탭 전환만으로 재시도 카운터 초기화
- **영향**: 네트워크 불안정 시 빠른 API 호출 루프, 서버 부하
- **권장**: `retryCountRef` 대신 `sessionStorage` 기반 카운터 또는 exponential backoff 적용

---

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)

#### [SEC-02] contract_markups `delete_markup` Path Traversal 미방어 — [Major/HIGH] — P1 (점수: 85)

- **파일**: `deal-mgmt/app/routers/contract_markups.py:246-249`
- **review-verifier**: CONFIRMED
- **증거**:
  ```python
  # line 246-249: NO path validation before unlink
  if markup.file_path:
      file_path = Path(markup.file_path)
      if file_path.exists():
          file_path.unlink()
  ```
  같은 파일의 `download_markup`(line 217-221)에는 경로 검증 존재.
- **영향**: DB에 조작된 경로 저장 시 임의 파일 삭제 가능
- **권장**: `file_path.resolve().relative_to(UPLOAD_DIR.resolve())` 검증 추가

---

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

#### [R5-01] FIRecommendModal N+1 API 호출 패턴 — [Moderate/HIGH] — P2 (점수: 40)

- **파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:77-91`
- **증거**: 30명 바이어 추가 시 30회 개별 POST (5건씩 배치이나 bulk API 미사용)
- **영향**: 대량 추가 시 서버 부하, 느린 UX
- **권장**: bulk POST API (`/transactions/{txnId}/buyers/bulk`) 도입

---

### P3 — 저우선 (점수: <30, 개선 가능)

#### [R6-01] DealSetupWizardPage description 빈 문자열 AI 분석 호출 — [Moderate/MEDIUM ⚠️] — P3 (점수: 24)

- **파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx:375-424`
- **증거**: `handleAnalyze`가 `leadEmail.trim()` 체크하나 `description.trim()` 미체크
- **판정**: PARTIAL — 백엔드 Pydantic validation이 빈 문자열 거부 가능 (Major→Moderate 하향)
- **권장**: 프론트엔드에서 `description.trim()` 사전 체크 추가

#### [R4-03] VCS savepoint 상태 불확실성 — [Moderate/MEDIUM ⚠️] — P3 (점수: 24)

- **파일**: `deal-mgmt/app/routers/vdr_analysis.py`
- **증거**: savepoint 롤백 시 후속 작업의 세션 상태 관리 불명확
- **권장**: 명시적 세션 상태 검증 로직 추가

#### [R6-03] 평균 진행률 계산 — stageMap 미등록 바이어 제외 — [Moderate/MEDIUM ⚠️] — P3 (점수: 24)

- **파일**: `amic-platform/src/modules/ma/components/buyers/ShortListSummaryBar.tsx:26-38`
- **증거**: `if (!stages) continue` — stageMap 없는 바이어가 분모에서 제외
- **판정**: DESIGN_RISK — 마케팅 미시작 바이어를 0%로 포함할지는 비즈니스 결정
- **권장**: 사용자 요구사항 확인 후 결정

#### [R6-07] useFocusTrap onClose 리스너 불안정 — [Moderate/MEDIUM ⚠️] — P3 (점수: 24)

- **파일**: `amic-platform/src/modules/ma/hooks/useFocusTrap.ts`
- **증거**: `onClose` 콜백이 `useEffect` deps에 포함되어 매 렌더 재등록 가능
- **권장**: `onClose`를 `useCallback`으로 메모이제이션

#### [R6-08] formatKRW 1억 미만 "원" 단위 미표시 — [Moderate/LOW ⚠️] — P3 (점수: 12)

- **파일**: `amic-platform/src/modules/ma/utils/format.ts:12`
- **증거**: `return ${sign}${Math.round(abs).toLocaleString()}` — 단위 접미사 없음
- **판정**: DESIGN_RISK — M&A 맥락에서 금액 단위(원)는 UI 레이블에서 암묵적
- **권장**: 필요 시 "원" 접미사 추가

#### [R5-02] ShortListOverview stale closure 가능성 — [Minor/MEDIUM ⚠️] — P3 (점수: 12)

- **파일**: `amic-platform/src/modules/ma/components/buyers/ShortListOverview.tsx`
- **증거**: 이벤트 핸들러에서 캡처된 state가 stale할 가능성
- **권장**: `useCallback` deps 검토

#### [R5-03=R6-06] IIFE 날짜 계산 가독성 — [Minor/LOW] — P3 (점수: 6)

- **증거**: 여러 컴포넌트에서 즉시실행함수(IIFE)로 날짜 계산 → 가독성 저하
- **권장**: 유틸 함수 추출

#### [R4-05] Commit 실패 시 파일 정리 레이스 컨디션 — [Minor/LOW] — P3 (점수: 6)

- **파일**: `deal-mgmt/app/routers/` 관련 파일
- **증거**: 파일 업로드 후 DB commit 실패 시 파일 정리 타이밍 불확실
- **권장**: 파일 정리를 finally 블록으로 보장

#### [R6-10] Email validation `@` 단일 체크 — [Minor/LOW] — P3 (점수: 6)

- **파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx`
- **증거**: 이메일 유효성을 `includes("@")`만으로 검증
- **권장**: RFC 5322 기반 정규식 또는 `z.string().email()` 사용

---

### Info — 설계 결정 (참고용)

#### [R5-04=R6-04] Badge variant 바이패스 — className 직접 스타일링 — [Info]

- **파일**: `amic-platform/src/modules/ma/components/buyers/BuyerTierBadge.tsx`
- **증거**: Badge의 `variant` prop 대신 `className`으로 녹색 계열 직접 지정
- **판정**: 의도적 설계 결정 (Short List 탭 녹색 팔레트 통일 — 플랜 `pure-watching-kettle.md` Step 3)
- **액션**: 없음

---

## Priority Matrix

### P0 — 즉시 수정 (2건)
1. [SEC-01=R4-02] [Major/HIGH]: nda_markups prev_path Path Traversal — `nda_markups.py:362` (점수: 95)
2. [R4-01=R6-02] [Major/HIGH]: VDR auto-init retry 무한 루프 — `VdrTab.tsx:85` (점수: 95)

### P1 — 스프린트 우선 (1건)
1. [SEC-02] [Major/HIGH]: contract_markups delete_markup Path Traversal — `contract_markups.py:246` (점수: 85)

### P2 — 개선 권장 (1건)
1. [R5-01] [Moderate/HIGH]: FIRecommendModal N+1 API — `FIRecommendModal.tsx:77` (점수: 40)

### P3 — 저우선 (8건)
1. [R6-01] [Moderate/MEDIUM ⚠️]: description 미검증 AI 호출 — `DealSetupWizardPage.tsx:375` (점수: 24)
2. [R4-03] [Moderate/MEDIUM ⚠️]: VCS savepoint 상태 — `vdr_analysis.py` (점수: 24)
3. [R6-03] [Moderate/MEDIUM ⚠️]: 평균 진행률 분모 편향 — `ShortListSummaryBar.tsx:26` (점수: 24)
4. [R6-07] [Moderate/MEDIUM ⚠️]: useFocusTrap onClose 재등록 — `useFocusTrap.ts` (점수: 24)
5. [R6-08] [Moderate/LOW ⚠️]: formatKRW "원" 미표시 — `format.ts:12` (점수: 12)
6. [R5-02] [Minor/MEDIUM ⚠️]: stale closure — `ShortListOverview.tsx` (점수: 12)
7. [R5-03=R6-06] [Minor/LOW]: IIFE 날짜 가독성 (점수: 6)
8. [R4-05] [Minor/LOW]: commit 실패 파일 정리 (점수: 6)
9. [R6-10] [Minor/LOW]: email `@` 단일 체크 (점수: 6)

### Info (1건)
1. [R5-04=R6-04] Badge variant 바이패스 — 설계 결정

---

## Methodology

- **Agents**: security-auditor (R2), data-integrity (R3), error-handling (R4), performance (R5), domain-logic (R6)
- **Excluded Agents**: R1 (기본 정합성/완전성 — 이전 리뷰에서 완료)
- **Files scanned**: 44개 (HEAD~1..HEAD diff)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Major 4건 중 CONFIRMED 3건, PARTIAL 1건 (→Moderate 하향)
- **Auto-verification**: Moderate+Minor 13건 중 FALSE_POSITIVE 3건 제거
- **Backend availability**: deal-mgmt(available), FDD(unavailable), KIIS(unavailable), IM(unavailable)

## 검증 투명성

### 검증 통계
- 검증한 가설: 17건
- 거부된 가설 (사전 제거): 4건
- 보고된 이슈: 13건
- 거부율: 24%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 (FALSE_POSITIVE) | 3 | SEC-03: `extractApiError` 이미 사용 중, R4-04: `onError` 존재, R6-09: `onCancel` prop 없음 |
| Self-Challenge 기각 | 1 | R6-01: Major→Moderate (백엔드 validation 가능) |

### 에이전트별 허위 양성율

| 에이전트 | 보고 | FP 제거 | FP율 |
|----------|------|---------|------|
| R2+R3 (보안+데이터) | 3 | 1 (SEC-03) | 33% |
| R4+R5 (에러+성능) | 7 | 1 (R4-04) | 14% |
| R6 (도메인+가독성) | 7 | 1 (R6-09) | 14% |
