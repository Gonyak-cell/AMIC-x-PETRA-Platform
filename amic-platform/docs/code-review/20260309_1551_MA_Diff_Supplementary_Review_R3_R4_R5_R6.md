# Code Review — MA Diff 보충 리뷰 (R3/R4/R5/R6)

> **Review Date**: 2026-03-09 15:51
> **Reviewer**: Claude Code (review-orchestrate §9 관점 전환 리뷰)
> **Scope**: `git diff HEAD` — 25개 변경 파일 (1차 리뷰 10건 수정 포함)
> **Method**: §9 반복 리뷰 전략 — 1차 리뷰(R1) 미수행 관점 보충
> **적용 라운드**: R3(데이터 정합성) + R4(프로덕션 복원력) + R5(운영 & 코드 건강성) + R6(비즈니스 & UX)
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(PASS 178/178) build(PASS) — 1차 리뷰 검증 유지

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 3     | HIGH: 3                | P1: 3               |
| Moderate | 6     | HIGH: 5 / MEDIUM: 1    | P2: 6               |
| Minor    | 6     | HIGH: 4 / MEDIUM: 2    | P3: 6               |
| **Total**| **15**| HIGH: **12** / MEDIUM: **3** | P1: **3** / P2: **6** / P3: **6** |

**FP Prevention**: 가설 30건 검증, 6건 사전 거부 (거부율: 20%)
- 1차 리뷰 이슈와 중복: 4건 병합
- 의도적 설계로 판정: 2건 거부

---

## Findings

### [R6-001] ShortListSummaryBar 평균 진행률 계산 오류 — [Major/HIGH] — P1 (70)

**파일**: `src/modules/ma/components/buyers/ShortListSummaryBar.tsx:26-38`
**관점**: R6 도메인 로직 / 계산 정확성

```tsx
const avgPct = buyers.length > 0
  ? Math.round(
      buyers.reduce((sum, b) => {
        const stages = stageMap.get(b.id);
        if (!stages) return sum;  // sum에 0 추가
        // ...
      }, 0) / buyers.length,     // 전체 buyers.length로 나눔
    )
  : 0;
```

**문제**: `stageMap`에 데이터가 없는 바이어는 `sum`에 0을 더하지만, 분모는 `buyers.length` 전체를 사용합니다. 10명 중 2명만 스테이지 데이터가 있고 각각 50%라면, 실제 평균은 50%여야 하지만 `(50+50)/10 = 10%`로 표시됩니다.

**영향**: M&A 마케팅 진행 현황 KPI가 실제보다 크게 낮게 표시되어 의사결정에 오해 유발.

**수정 제안**: 분모를 `stageMap`에 데이터가 있는 바이어 수로 변경.

---

### [R3-02] contract_markups/nda_markups — create에서 check_client_deal_access 미호출 — [Major/HIGH] — P1 (70)

**파일**: `deal-mgmt/app/routers/contract_markups.py:72-84`, `nda_markups.py:86-98`
**관점**: R3 데이터 정합성 / API 계약

**문제**: `list_markups`, `get_markup`, `download_markup`, `delete_markup`에서는 모두 `check_client_deal_access(db, txn_id, claims)`를 호출하지만, `create_markup`에서는 호출하지 않습니다. `require_write_access()`가 CLIENT 역할의 쓰기를 차단하므로 즉각적 보안 위험은 없지만, 패턴 불일치로 인해 향후 CLIENT 쓰기 권한 확대 시 타 거래에 마크업 생성 가능한 권한 우회가 발생할 수 있습니다.

`nda_markups.py:86-98`의 `create_nda_markup`도 동일.

---

### [R4-08] rfi_v2 import_excel — 에러/충돌 시 명시적 롤백 없음 — [Major/HIGH] — P1 (70)

**파일**: `deal-mgmt/app/routers/rfi_v2.py:438-463`
**관점**: R4 에러 복원력 / DB 트랜잭션

```python
result = await import_rfi_excel(db, txn_id, file_bytes, ...)
if not result.errors and not result.conflicts:
    await db.commit()
# errors/conflicts 있으면 commit도 rollback도 없음
```

**문제**: `import_rfi_excel` 내부에서 `db.add`/`db.flush`로 부분 데이터가 추가된 후, 에러/충돌이 있으면 세션이 dirty 상태로 남습니다. FastAPI의 `get_db` 구현에 따라 암묵적 롤백이 될 수 있지만 명시적이지 않습니다.

**수정 제안**: `else: await db.rollback()` 추가.

---

### [R4-05] nda_markups — RuntimeError 메시지 HTTP 응답 노출 — [Moderate/HIGH] — P2 (40)

**파일**: `deal-mgmt/app/routers/nda_markups.py:351-355`
**관점**: R4 관찰 가능성 / 보안

```python
except RuntimeError as exc:
    logger.exception("NDA Redline 생성 중 런타임 에러")
    raise HTTPException(status_code=503, detail=f"Redline 생성 실패: {exc}")
```

**문제**: `RuntimeError.message`가 HTTP 응답 `detail`에 그대로 포함됩니다. 내부 파일 경로, 라이브러리 정보 등 민감한 정보가 포함될 수 있습니다. FE의 `extractApiError`는 5xx에서 fallback을 반환하지만, 직접 API 호출(Postman 등) 시 노출됩니다.

---

### [R4-04] contract_markups/nda_markups — VCS 연동 catch 로그 개선 필요 — [Moderate/HIGH] — P2 (40)

**파일**: `deal-mgmt/app/routers/contract_markups.py:149-176`, `nda_markups.py:169-194`
**관점**: R4 관찰 가능성 / 디버깅

```python
except Exception:
    logging.getLogger(__name__).warning("VCS 연동 실패 (계약 마크업)", exc_info=True)
```

**문제**:
1. 로그 레벨이 `warning` — VCS 데이터 정합성 영향을 고려하면 `error`가 적절
2. 에러 컨텍스트(contract_id, txn_id, markup.id 등) 미포함 — 프로덕션 디버깅 어려움

---

### [R6-016] DealSetupWizardPage — 엑셀 업로드 드래그 앤 드롭 미구현 — [Moderate/HIGH] — P2 (40)

**파일**: `src/modules/ma/pages/DealSetupWizardPage.tsx:629-645`
**관점**: R6 UX 일관성

```tsx
<div className="border-2 border-dashed ... cursor-pointer" onClick={...}>
  <p>딜 리스트 엑셀 파일을 드래그하거나 클릭하여 업로드</p>
```

**문제**: UI 텍스트에 "드래그하거나"라고 안내하지만, `onDragOver`/`onDrop` 핸들러가 없어 실제 드래그 앤 드롭은 동작하지 않습니다. 안내 문구와 실제 기능의 불일치.

---

### [R6-008] DealSetupWizardPage — 엑셀 업로드 시 leadEmail 미검증 — [Moderate/HIGH] — P2 (40)

**파일**: `src/modules/ma/pages/DealSetupWizardPage.tsx:393-403`
**관점**: R6 도메인 로직

**문제**: `handleAnalyze`(텍스트 분석)에서는 `if (!leadEmail.trim()) return;` 가드가 있지만, `handleExcelUpload`에서는 `leadEmail` 검증 없이 바로 서버 호출합니다. 이후 `handleConfirm`에서 `leadEmail`이 필요하므로, 빈 값이면 불완전한 거래가 생성될 수 있습니다.

---

### [R6-015] VdrTab — 리사이즈 핸들 키보드 접근 불가 — [Moderate/HIGH] — P2 (40)

**파일**: `src/modules/ma/components/vdr/VdrTab.tsx:292-297`
**관점**: R6 접근성

```tsx
<div className="h-2 ... cursor-row-resize" onMouseDown={handleMouseDown}>
```

**문제**: `<div>`에 `onMouseDown`만 있고, `role`, `tabIndex`, `aria-label`, 키보드 이벤트 핸들러가 없습니다. 키보드 사용자는 이 핸들에 접근하거나 조작할 수 없습니다. `role="separator"` + `aria-valuenow` + 방향키 핸들링이 필요합니다.

---

### [R6-011] DocumentCreateDialog/RevisionUploadDialog — body 스크롤 미차단 — [Moderate/MEDIUM] — P2 (24)

**파일**: `src/modules/ma/components/document-versions/DocumentCreateDialog.tsx:64`, `RevisionUploadDialog.tsx:49`
**관점**: R6 UX

**문제**: 커스텀 오버레이(`fixed inset-0 bg-black/40`)를 사용하지만, `document.body.style.overflow = 'hidden'` 처리가 없어 모달 뒤 배경이 스크롤됩니다. `useFocusTrap`으로 포커스 트랩은 구현했으나 스크롤 차단이 누락.

---

### [R6-012] BuyersTab — DEV_MOCK 모듈이 프로덕션 번들에 포함 — [Minor/HIGH] — P3 (20)

**파일**: `src/modules/ma/tabs/BuyersTab.tsx:23-25, 220-238`
**관점**: R5 성능 / 번들 크기

**문제**: `import { createDevMockBuyers } from "../constants/devMockBuyers"`는 무조건 실행됩니다. `import.meta.env.DEV ? createDevMockBuyers(txnId) : []`에서 Vite가 프로덕션 빌드 시 `false` 브랜치를 제거하지만, **모듈 import 자체는 남아** 프로덕션 번들에 mock 데이터 모듈이 포함됩니다.

**수정 제안**: dynamic import로 변환: `const mod = await import("../constants/devMockBuyers")`

---

### [R5-01] contract_markups/nda_markups — 50MB 파일 전체 메모리 로드 — [Minor/HIGH] — P3 (20)

**파일**: `deal-mgmt/app/routers/contract_markups.py:89`, `nda_markups.py:110`
**관점**: R5 성능

```python
content = await file.read()  # MAX_FILE_SIZE = 50MB
```

**문제**: 최대 50MB 파일 전체를 메모리에 로드. Azure VM(2 vCPU, 16GB RAM)에서 동시 업로드 수가 적으면 문제없지만, 스트리밍 방식이 더 안전합니다.

---

### [R4-09] contract_markups/nda_markups — DB 커밋 실패 시 고아 파일 — [Minor/MEDIUM] — P3 (12)

**파일**: `deal-mgmt/app/routers/contract_markups.py:121-178`, `nda_markups.py:141-198`
**관점**: R4 에러 복원력

**문제**: 파일이 디스크에 먼저 저장된 후 DB 커밋이 실행됩니다. `db.commit()` 실패 시 디스크의 파일은 삭제되지 않아 고아 파일이 남습니다.

---

### [R6-004] BUYER_STATUS_OPTIONS — "전체" 빈값 옵션 누락 — [Minor/HIGH] — P3 (20)

**파일**: `src/modules/ma/constants/buyer.ts:96-114`
**관점**: R6 UX

**문제**: `BUYER_TYPE_OPTIONS`와 `BUYER_TIER_OPTIONS`에는 `{ value: "", label: "전체" }` 옵션이 있지만, `BUYER_STATUS_OPTIONS`에는 없습니다. Status 필터를 초기 상태로 되돌릴 수 없습니다.

---

### [R6-009] DealSetupWizardPage — 프로젝트명 한영 변환 안내 부족 — [Minor/HIGH] — P3 (20)

**파일**: `src/modules/ma/pages/DealSetupWizardPage.tsx:136-141`
**관점**: R6 UX

```tsx
const applyProjectName = (raw: string) => {
  const converted = koreanToEnglish(raw);
  // ...
};
```

**문제**: 한글 입력 시 영문 키보드 매핑으로 자동 변환되는 동작에 대한 UI 안내가 부족합니다. "삼성" → "Tlaqjd" 변환이 사용자에게 혼란을 줄 수 있습니다.

---

### [R6-013] DealSetupWizardPage — 이메일 형식 검증 누락 — [Minor/MEDIUM] — P3 (12)

**파일**: `src/modules/ma/pages/DealSetupWizardPage.tsx:144-150`
**관점**: R6 UX / 도메인 로직

**문제**: `canSubmit`에서 `form.lead_advisor_email.trim()` 만 체크하여 빈 문자열만 방지합니다. "abc" 같은 유효하지 않은 이메일도 제출 가능합니다. `type="email"`이 있지만 브라우저 기본 검증에만 의존합니다.

---

## 거부된 이슈 (6건)

| 가설 | 거부 사유 |
|------|---------|
| useDealSetup onError 누락 | FP-CTX: 1차 리뷰 API-06에서 이중 토스트 방지를 위해 의도적으로 제거. 호출 측에서 처리 |
| DocumentCreateDialog/RevisionUploadDialog onError 미처리 | FP-IMPL: 훅 레벨 onError가 toast.error 처리. 컴포넌트 레벨 처리는 선택 사항 |
| VdrTab 프로덕션 로그/재시도 리셋 | 1차 리뷰 ISS-3에서 이미 백오프 추가됨. 탭 전환 재시도 리셋은 의도된 동작(3회 전역 제한 필요 시 별도 설계) |
| useTransactions err.message 패턴 불일치 | 범위 외: useTransactions.ts는 이번 diff에 포함되지 않음 |
| R3-01/R6-006 estimated_deal_value 타입 불일치 | FP-IMPL: `TransactionCreate.estimated_deal_value`는 `string | undefined`로, `e.target.value`(string)과 일치. AITab의 confirm은 preview 데이터를 별도 구조로 전송하여 경로가 다름 |
| FIRecommendModal 부분 성공 배치 단위 정보 | 범위 축소: 실질적 사용자 영향 낮음 (성공/실패 총 건수는 표시됨) |

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)

1. [R6-001] [Major/HIGH]: ShortListSummaryBar 평균 진행률 계산 오류 — `ShortListSummaryBar.tsx` (70)
2. [R3-02] [Major/HIGH]: create_markup 접근 제어 누락 — `contract_markups.py`, `nda_markups.py` (70)
3. [R4-08] [Major/HIGH]: import_excel 에러 시 명시적 롤백 없음 — `rfi_v2.py` (70)

### P2 — 개선 권장 (점수: 30-59)

1. [R4-05] [Moderate/HIGH]: RuntimeError 메시지 HTTP 응답 노출 — `nda_markups.py` (40)
2. [R4-04] [Moderate/HIGH]: VCS 연동 catch 로그 개선 — `contract_markups.py`, `nda_markups.py` (40)
3. [R6-016] [Moderate/HIGH]: 엑셀 드래그 앤 드롭 미구현 — `DealSetupWizardPage.tsx` (40)
4. [R6-008] [Moderate/HIGH]: 엑셀 업로드 시 leadEmail 미검증 — `DealSetupWizardPage.tsx` (40)
5. [R6-015] [Moderate/HIGH]: 리사이즈 핸들 키보드 접근 불가 — `VdrTab.tsx` (40)
6. [R6-011] [Moderate/MEDIUM]: body 스크롤 미차단 — `DocumentCreateDialog.tsx`, `RevisionUploadDialog.tsx` (24)

### P3 — 저우선 (점수: <30)

1. [R6-012] [Minor/HIGH]: DEV_MOCK 프로덕션 번들 포함 — `BuyersTab.tsx` (20)
2. [R5-01] [Minor/HIGH]: 50MB 파일 전체 메모리 로드 — `contract_markups.py`, `nda_markups.py` (20)
3. [R6-004] [Minor/HIGH]: Status 필터 "전체" 옵션 누락 — `buyer.ts` (20)
4. [R6-009] [Minor/HIGH]: 프로젝트명 한영 변환 안내 부족 — `DealSetupWizardPage.tsx` (20)
5. [R4-09] [Minor/MEDIUM]: DB 커밋 실패 시 고아 파일 — `contract_markups.py`, `nda_markups.py` (12)
6. [R6-013] [Minor/MEDIUM]: 이메일 형식 검증 누락 — `DealSetupWizardPage.tsx` (12)

---

## 1차 리뷰 + 보충 리뷰 통합 현황

| 라운드 | 관점 | 1차 리뷰 | 보충 리뷰 | 상태 |
|--------|------|---------|---------|------|
| R1 | 기본 §0~§8 | 10건 발견, 10건 수정 완료 | — | ✅ |
| R2 | 보안 심층 + 위협 모델링 | 1차에서 security-auditor 수행 | R3-02 (접근 제어 불일치) | ✅ |
| R3 | 데이터 정합성 + API 계약 | 1차에서 api-auditor 수행 | R3-02, R4-08 | ✅ |
| R4 | 프로덕션 복원력 + 관찰 가능성 | 부분 수행 (ISS-3) | R4-04, R4-05, R4-08, R4-09 | ✅ |
| R5 | 성능 + 배포 안전성 + 의존성 | 미수행 | R5-01, R6-012 | ✅ |
| R6 | 비즈니스 + 테스트 + 인지 복잡도 + 접근성 | 1차에서 a11y-auditor 수행 | R6-001~R6-016 | ✅ |

**13개 관점 모두 커버 완료.**

---

## Methodology

- **Agents**: 3개 병렬 에이전트 (R4 전담, R6 전담, R3+R5 전담)
- **Files scanned**: 25개 (diff 범위 전체 + 관련 import 파일)
- **Protocol**: Verified Claim Protocol v1.1 + §9 관점 전환 리뷰
- **1차 리뷰 참조**: `20260309_1529_MA_Diff_Full_Code_Review.md` (10건 수정 완료)

## 검증 투명성

### 검증 통계
- 검증한 가설: 30건 (R4: 10건, R6: 16건, R3+R5: 9건, 중복 5건)
- 거부된 가설: 6건
- 중복 병합: 4건
- 보고된 이슈: 15건
- 거부율: 20%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| FP-CTX (의도적 설계) | 2 | useDealSetup onError: 1차 API-06 수정에 의한 의도적 제거 |
| FP-IMPL (구현 이해 부족) | 2 | 훅 레벨 onError가 처리, estimated_deal_value 타입 경로 분리 |
| 범위 외 | 2 | useTransactions.ts (diff 미포함), 배치 단위 정보 (영향 미미) |
