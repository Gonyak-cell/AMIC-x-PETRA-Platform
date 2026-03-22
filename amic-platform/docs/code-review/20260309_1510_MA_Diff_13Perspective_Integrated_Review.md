# Code Review — MA Module Diff 13-Perspective Integrated Review

> **Review Date**: 2026-03-09 15:10
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff --name-only HEAD~15` — MA 모듈 최근 변경 파일 (feat/ma-workflow 브랜치)
> **Method**: Review Gates (skip) + Verified Multi-Agent Review + Cross-Verification + Auto-Verification
> **Quality Gates**: skipped (--skip-gates)
> **Agents**: code-reviewer, security-auditor, performance-profiler

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 3     | HIGH: 3               | P0: 1 / P1: 2       |
| Moderate | 6     | HIGH: 4 / MEDIUM: 2   | P2: 6                |
| Minor    | 9     | HIGH: 4 / MEDIUM: 5   | P3: 9                |
| **Total**| **18**| HIGH: **11** / MEDIUM: **7** | P0: **1** / P1: **2** / P2: **6** / P3: **9** |

**FP Prevention**: 가설 25건 검증, 7건 사전 거부 (거부율: 28%) | 교차 검증 4건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 7건 하향 조정
- 교차 검증 확인 1건 (SEC-01/CR-1 → P0 상향)

---

## Findings

### [SEC-01/CR-1] `upload_attachments` 쓰기 권한 누락 — [Major/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/routers/rfi_v2.py:284`
**점수**: 95 (Major 70 × HIGH 1.0 + cross-verify 10 + verifier 15)

**증거**:
```python
# Line 284 — 현재 코드
claims: JWTClaims = Depends(get_jwt_claims),
```

**문제**: 파일 업로드(쓰기 작업)에 읽기 전용 인증(`get_jwt_claims`)만 적용. 같은 파일의 `create_thread`(line 197), `import_excel`(line 442)은 이미 `require_write_access()`로 수정 완료.

**수정 방안**: `Depends(get_jwt_claims)` → `Depends(require_write_access())`

**교차 검증**: security-auditor + code-reviewer 양쪽 독립 확인. 실제 코드 Read로 CONFIRMED.

---

### [CR-2] VDR 자동 초기화 재시도 로직 결함 — [Major/HIGH] — Priority: P1

**파일**: `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx:96-117`
**점수**: 85 (Major 70 × HIGH 1.0 + verifier 15)

**증거**:
```tsx
useEffect(() => {
  if (summary && !summary.initialized && !autoInitRef.current && retryCountRef.current < 3) {
    autoInitRef.current = true;
    retryCountRef.current += 1;
    maApi.post(...)
      .then(() => { qc.invalidateQueries({...}); })
      .catch(() => {
        autoInitRef.current = false;
        // ⚠️ invalidateQueries 미호출 → summary 변하지 않음 → useEffect 재실행 불가
      });
  }
}, [summary, txnId, qc]);
```

**문제**: `.catch()` 경로에서 `autoInitRef.current = false`로 재시도 플래그를 초기화하지만, `summary` 의존성이 변하지 않아 useEffect가 재실행되지 않음. `retryCountRef`는 3까지 증가하도록 설계했지만 실질적으로 1회만 시도.

**수정 방안**: catch에서 `qc.invalidateQueries()`를 호출하거나, 별도 retry state를 useState로 관리하여 의존성 트리거.

**교차 검증**: code-reviewer 보고 + 실제 코드 Read로 CONFIRMED.

---

### [CR-8] BuyerFeedbackSection 메모 상태 동기화 미흡 — [Major/HIGH] — Priority: P1

**파일**: `amic-platform/src/modules/ma/components/buyers/BuyerFeedbackSection.tsx:19`
**점수**: 85 (Major 70 × HIGH 1.0 + verifier 15)

**증거**:
```tsx
const [notes, setNotes] = useState(buyer.notes ?? "");
```

**문제**: `useState(initialValue)`는 마운트 시에만 적용. 부모가 `buyer` prop을 다른 바이어로 변경해도 `notes` state는 이전 바이어의 값을 유지 → blur 저장 시 잘못된 바이어에 덮어쓰기 가능 (데이터 오염).

**수정 방안**: `useEffect`로 `buyer.id` 변경 감지 시 `setNotes(buyer.notes ?? "")` 호출, 또는 `key={buyer.id}` prop으로 컴포넌트 리마운트.

**교차 검증**: code-reviewer 보고 + 실제 코드 Read로 CONFIRMED.

---

### [SEC-02] `update_thread` 소유자 검증 미흡 — [Moderate/MEDIUM ⚠️] — Priority: P2

**파일**: `deal-mgmt/app/routers/rfi_v2.py:215-228`
**점수**: 39 (Moderate 40 × MEDIUM 0.6 + verifier 15)

**증거**:
```python
claims: JWTClaims = Depends(require_write_access()),  # ← 역할 기반 검증 O
await check_client_deal_access(db, txn_id, claims)     # ← 거래 접근 검증 O
# ⚠️ thread 소유자 검증 없음 — ANALYST면 모든 thread publish 상태 변경 가능
```

**판정**: DESIGN_RISK — `require_write_access()` 적용 확인됨. 그러나 thread-level 소유자 검증이 없어 같은 거래 내 다른 사용자의 thread를 수정 가능. 현재 소규모 팀 운영 환경에서는 수용 가능하나, 사용자 확대 시 IDOR 위험.

---

### [SEC-03] `get_markup` 트랜잭션 유효성 검증 누락 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/app/routers/contract_markups.py:57-66`
**점수**: 40 (Moderate 40 × HIGH 1.0)

**문제**: `get_markup` 엔드포인트에서 `transaction_service.get_transaction` 호출 없이 직접 markup 조회. 다른 거래의 markup_id를 추측하면 접근 가능.

---

### [SEC-04] `get_nda_markup` 동일 패턴 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/app/routers/nda_markups.py:68-79`
**점수**: 40 (Moderate 40 × HIGH 1.0)

**문제**: SEC-03과 동일한 트랜잭션 유효성 검증 누락 패턴.

---

### [PERF-P1] `_get_contract_or_404` 중복 호출 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/app/routers/contract_markups.py:83, 150`
**점수**: 40 (Moderate 40 × HIGH 1.0)

**문제**: `upload_markup` 함수 내에서 line 83과 line 150에서 동일 contract를 두 번 조회. 첫 번째 조회 결과를 재사용하면 DB 라운드트립 1회 절약.

---

### [CR-6] 테스트 픽스처 실행 순서 의존성 — [Moderate/HIGH] — Priority: P2

**파일**: `deal-mgmt/tests/test_role_access.py`
**점수**: 40 (Moderate 40 × HIGH 1.0)

**문제**: `transaction_id` 픽스처(ADMIN claims)와 `_as_client` 픽스처 간 실행 순서가 pytest 내부 해석에 의존. 명시적 순서 보장 없음.

---

### [SEC-05] NDA redline 경로 순회 위험 — [Moderate/MEDIUM ⚠️] — Priority: P2

**파일**: `deal-mgmt/app/routers/nda_markups.py:306-308`
**점수**: 24 (Moderate 40 × MEDIUM 0.6)

**문제**: `base_markup.file_path`가 DB에서 직접 읽혀 파일 시스템 접근에 사용됨. 경로 순회 방어(path traversal defense) 없음. DB 값이 안전하다는 전제이나, defense-in-depth 관점에서 검증 권장.

---

### [CR-4] FIRecommendModal `indexOf` 참조 동일성 의존 — [Moderate/MEDIUM ⚠️] — Priority: P3

**파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx`
**점수**: 24 (Moderate 40 × MEDIUM 0.6)

**문제**: `results.indexOf(r)` 패턴이 객체 참조 동일성에 의존. 현재 동작하지만 가독성과 안정성이 낮음. `Map` 또는 index 매개변수 사용 권장.

---

### [PERF-P2] `_next_item_number` N+1 패턴 — [Moderate/MEDIUM ⚠️] — Priority: P3

**파일**: `deal-mgmt/app/services/rfi_v2_service.py`
**점수**: 24 (Moderate 40 × MEDIUM 0.6)

**문제**: 배치 생성 시 각 아이템마다 `_next_item_number` 개별 호출 가능성. 현재 사용량에서는 영향 미미하나, 대량 import 시 N+1 쿼리 발생 가능.

---

### [SEC-06] `report_payload` GET에 과도한 쓰기 권한 — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/app/routers/rfi_v2.py:404`
**점수**: 20 (Minor 20 × HIGH 1.0)

**문제**: 읽기 전용 GET 엔드포인트에 `require_write_access()` 적용. 읽기만 하는 사용자도 접근 불가.

---

### [SEC-07] RevisionUploadDialog 파일 확장자 서버사이드 검증 미흡 — [Minor/MEDIUM] — Priority: P3

**파일**: `amic-platform/src/modules/ma/components/document-versions/RevisionUploadDialog.tsx`
**점수**: 12 (Minor 20 × MEDIUM 0.6)

**문제**: `accept` 속성에 `.csv` 포함. 서버사이드 확장자 검증은 별도 확인 필요.

---

### [CR-3] DealSetupWizardPage 인지 복잡도 — [Minor/HIGH] — Priority: P3

**파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx`
**점수**: 20 (Minor 20 × HIGH 1.0)

**문제**: 701줄, AITab ~325줄. 컴포넌트 분리 권장.

---

### [CR-5] Markup 라우터 파일 메모리 적재 — [Minor/MEDIUM] — Priority: P3

**파일**: `deal-mgmt/app/routers/contract_markups.py`, `nda_markups.py`
**점수**: 12 (Minor 20 × MEDIUM 0.6)

**문제**: 대용량 파일을 한 번에 메모리에 로드. 현재 파일 크기에서는 문제 없으나, 수백 MB 문서 처리 시 OOM 위험.

---

### [CR-7] Dialog backdrop 클릭 닫기 미구현 — [Minor/MEDIUM] — Priority: P3

**파일**: `amic-platform/src/modules/ma/components/document-versions/DocumentCreateDialog.tsx`, `RevisionUploadDialog.tsx`
**점수**: 12 (Minor 20 × MEDIUM 0.6)

**문제**: 모달 외부(backdrop) 클릭으로 닫기 불가. Escape 키만 동작. UX 관례와 불일치.

---

### [PERF-P3] 배치 리프레시 루프 — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/app/routers/rfi_v2.py`
**점수**: 20 (Minor 20 × HIGH 1.0)

**문제**: 배치 작업 후 개별 객체 refresh 루프. 현재 소규모 데이터에서는 영향 없음.

---

### [PERF-P4] Savepoint lazy import — [Minor/HIGH] — Priority: P3

**파일**: `deal-mgmt/app/routers/contract_markups.py`, `nda_markups.py`
**점수**: 20 (Minor 20 × HIGH 1.0)

**문제**: savepoint 관련 로깅에서 lazy import 패턴. 성능 영향은 미미.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)
1. [SEC-01/CR-1] [Major/HIGH]: upload_attachments 쓰기 권한 누락 — rfi_v2.py:284 (점수: 95, 교차 검증됨)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)
1. [CR-2] [Major/HIGH]: VDR 자동 초기화 재시도 로직 결함 — VdrTab.tsx:96-117 (점수: 85)
2. [CR-8] [Major/HIGH]: BuyerFeedbackSection 메모 상태 동기화 미흡 — BuyerFeedbackSection.tsx:19 (점수: 85)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [SEC-03] [Moderate/HIGH]: get_markup 트랜잭션 검증 누락 — contract_markups.py:57 (점수: 40)
2. [SEC-04] [Moderate/HIGH]: get_nda_markup 동일 패턴 — nda_markups.py:68 (점수: 40)
3. [PERF-P1] [Moderate/HIGH]: _get_contract_or_404 중복 호출 — contract_markups.py (점수: 40)
4. [CR-6] [Moderate/HIGH]: 테스트 픽스처 순서 의존성 — test_role_access.py (점수: 40)
5. [SEC-02] [Moderate/MEDIUM ⚠️]: update_thread 소유자 검증 — rfi_v2.py:215 (점수: 39, DESIGN_RISK)
6. [SEC-05] [Moderate/MEDIUM ⚠️]: NDA redline 경로 순회 — nda_markups.py:306 (점수: 24)

### P3 — 저우선 (점수: <30, 개선 가능)
1. [CR-4] [Moderate/MEDIUM ⚠️]: indexOf 참조 의존 — FIRecommendModal.tsx (점수: 24)
2. [PERF-P2] [Moderate/MEDIUM ⚠️]: N+1 _next_item_number — rfi_v2_service.py (점수: 24)
3. [SEC-06] [Minor/HIGH]: GET에 과도한 쓰기 권한 — rfi_v2.py:404 (점수: 20)
4. [CR-3] [Minor/HIGH]: 인지 복잡도 701줄 — DealSetupWizardPage.tsx (점수: 20)
5. [PERF-P3] [Minor/HIGH]: 배치 리프레시 루프 — rfi_v2.py (점수: 20)
6. [PERF-P4] [Minor/HIGH]: Savepoint lazy import — contract/nda_markups.py (점수: 20)
7. [SEC-07] [Minor/MEDIUM]: 파일 확장자 서버 검증 — RevisionUploadDialog.tsx (점수: 12)
8. [CR-5] [Minor/MEDIUM]: 파일 메모리 적재 — contract/nda_markups.py (점수: 12)
9. [CR-7] [Minor/MEDIUM]: Backdrop 클릭 닫기 — DocumentCreateDialog/RevisionUploadDialog (점수: 12)

---

## 13개 리뷰 관점 커버리지

| # | 관점 | 커버리지 | 주요 발견 |
|---|------|---------|---------|
| 1 | 보안 | ✅ 심층 | SEC-01~07 (7건) |
| 2 | 위협 모델링 | ✅ | SEC-02 IDOR, SEC-05 경로 순회 |
| 3 | 데이터 흐름 | ✅ | CR-8 stale state, P2 직렬화 (기수정) |
| 4 | API 계약 | ✅ | SEC-03/04 트랜잭션 검증, SEC-06 권한 수준 |
| 5 | 에러 처리 | ✅ | CR-2 재시도 로직, Imp-6 onError (기수정) |
| 6 | 관찰 가능성 | ⚠️ 경미 | 로깅 패턴은 기존 수준 유지 |
| 7 | 성능 | ✅ | PERF-P1~P4 (4건) |
| 8 | 배포 안전성 | ✅ | savepoint 패턴 (기수정), 마이그레이션 정합성 |
| 9 | 의존성 | ✅ | import 정합성 확인 완료 |
| 10 | 도메인 로직 | ✅ | 자문 유형, 거래 설정 플로우 검증 |
| 11 | 테스트 품질 | ✅ | CR-6 픽스처 격리 |
| 12 | 인지 복잡도 | ✅ | CR-3 DealSetupWizardPage 701줄 |
| 13 | 접근성 & UX | ✅ | CR-7 backdrop, SI footer (기수정) |

**커버리지**: 13/13 관점 수행 완료 (12 심층 + 1 경미)

---

## Methodology

- **Agents**: code-reviewer, security-auditor (backend-security-reviewer), performance-profiler
- **Excluded Agents**: type-checker (tsc skip-gates), a11y-auditor (프론트 변경 소규모)
- **Files scanned**: 15+ 파일 (diff 기반)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 4건 수행 (CONFIRMED: 3, DESIGN_RISK: 1)
- **Backend availability**: deal-mgmt (available), FDD/KIIS/IM (not in scope)

## 검증 투명성

### 검증 통계
- 검증한 가설: 25건
- 거부된 가설 (사전 제거): 7건
- 보고된 이슈: 18건
- 거부율: 28%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | SEC-02 "require_write_access 미사용" → Read로 사용 확인 |
| 이미 수정됨 | 2 | DealSetupWizardPage onError 이미 추가됨 |
| 중복 | 1 | CR-1 = SEC-01 동일 이슈 |
| 신뢰도 불충분 | 1 | 증거 약함 (LOW 미만) |

### 이전 세션 수정 완료 이슈 (참고)

| ID | 내용 | 상태 |
|----|------|------|
| Critical-2 | test_role_access.py 리소스 누수 | ✅ 수정 완료 |
| Imp-1 | DocumentCreateDialog 에러 UI | ✅ 수정 완료 |
| Imp-2 | RevisionUploadDialog 에러 UI | ✅ 수정 완료 |
| Imp-3 | VdrTab 재시도 제한 | ✅ 수정 완료 (CR-2에서 로직 결함 추가 발견) |
| Imp-5 | useVdr 캐시 무효화 | ✅ 수정 완료 |
| Imp-6 | DealSetupWizardPage onError | ✅ 수정 완료 |
| Imp-7/8 | contract/nda_markups savepoint | ✅ 수정 완료 |
| Imp-9/10 | rfi_v2 RBAC 강화 | ✅ 수정 완료 (SEC-01에서 누락 1건 추가 발견) |
