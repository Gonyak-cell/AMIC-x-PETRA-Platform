# Code Review — MA Workflow (6개 미수행 관점 심층 리뷰)

> **Review Date**: 2026-03-09 15:30 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff HEAD` — 18개 변경 파일
> **Method**: 3-Agent Parallel Review + Cross-Verification
> **Focus**: 관찰 가능성, 배포 안전성, 도메인 로직, 테스트 품질, 의존성, 인지 복잡도
> **Quality Gates**: `--skip-gates` (이전 세션에서 통과 확인됨)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 5     | HIGH: 4 / MEDIUM: 1 | P1: 4 / P2: 1 |
| Moderate | 7     | HIGH: 6 / MEDIUM: 1 | P2: 6 / P3: 1 |
| Minor    | 8     | HIGH: 7 / MEDIUM: 1 | P3: 8 |
| **Total**| **20** | HIGH: **17** / MEDIUM: **3** | P1: **4** / P2: **7** / P3: **9** |

**FP Prevention**: 가설 28건 검증, 8건 사전 거부 (거부율: 29%)
**Cross-Verification**: Major 5건 실제 코드 대조 완료

---

## Findings

### [SEC-D1] contract_markups download_markup — IDOR 취약점 — [Major/HIGH] — Priority: P1 (점수: 85)

**파일**: `deal-mgmt/app/routers/contract_markups.py:184-211`

**문제**: `download_markup` 엔드포인트에서 `_get_contract_or_404(db, txn_id, contract_id)` 호출 누락. `check_client_deal_access`로 URL의 `txn_id`에 대한 사용자 접근만 검증하고, `contract_id`가 해당 `txn_id`에 속하는지 확인하지 않음.

**공격 시나리오**: 자신의 트랜잭션 `txn_id`에 접근 권한이 있는 사용자가 다른 트랜잭션의 `contract_id`와 `markup_id`를 URL에 지정하면 파일 다운로드 가능.

**코드 (현재)**:
```python
async def download_markup(...):
    await check_client_deal_access(db, txn_id, claims)  # txn_id 접근만 검증
    markup = await _get_markup_or_404(db, contract_id, markup_id)  # contract_id ↔ txn_id 미검증
```

**비교 — 동일 파일 내 일관성 불일치**:
- `list_markups` (L41-43): ✅ `get_transaction` + `_get_contract_or_404` 호출
- `get_markup` (L64-66): ✅ `get_transaction` + `_get_contract_or_404` 호출
- `create_markup` (L84-85): ✅ `get_transaction` + `_get_contract_or_404` 호출
- `download_markup` (L192): ❌ 둘 다 누락
- `delete_markup` (L222): ❌ 둘 다 누락

**수정안**:
```python
async def download_markup(...):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_contract_or_404(db, txn_id, contract_id)  # contract ↔ txn 매핑 검증
    markup = await _get_markup_or_404(db, contract_id, markup_id)
```

---

### [SEC-D2] contract_markups delete_markup — IDOR 취약점 — [Major/HIGH] — Priority: P1 (점수: 85)

**파일**: `deal-mgmt/app/routers/contract_markups.py:214-239`

**문제**: SEC-D1과 동일. `delete_markup`에서도 `transaction_service.get_transaction` + `_get_contract_or_404` 누락. 다른 트랜잭션의 계약 마크업 삭제가 가능한 IDOR 취약점.

**코드 (현재)**:
```python
async def delete_markup(...):
    await check_client_deal_access(db, txn_id, claims)  # txn_id만 검증
    markup = await _get_markup_or_404(db, contract_id, markup_id)  # contract ↔ txn 미검증
```

**수정안**:
```python
async def delete_markup(...):
    await transaction_service.get_transaction(db, txn_id)
    await check_client_deal_access(db, txn_id, claims)
    await _get_contract_or_404(db, txn_id, contract_id)
    markup = await _get_markup_or_404(db, contract_id, markup_id)
```

---

### [SEC-D3] nda_markups generate_nda_redline — transaction 존재 검증 누락 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/app/routers/nda_markups.py:269-288`

**문제**: `generate_nda_redline`에서 `transaction_service.get_transaction(db, txn_id)` 누락. `_get_nda_or_404`가 `NDA.transaction_id == txn_id`를 검증하므로 IDOR 위험은 낮지만, 존재하지 않는 txn_id에 대해 "NDA를 찾을 수 없습니다" 에러가 반환되어 에러 메시지가 부정확함.

**비교 — nda_markups 내 일관성**:
- `list_nda_markups` (L50): ✅ `transaction_service.get_transaction`
- `get_nda_markup` (L76): ✅ `transaction_service.get_transaction`
- `create_nda_markup` (L99): ✅ `transaction_service.get_transaction`
- `download_nda_markup` (L212): ❌ 누락
- `delete_nda_markup` (L246): ❌ 누락
- `generate_nda_redline` (L285): ❌ 누락

**참고**: `_get_nda_or_404`가 `NDA.transaction_id == txn_id`를 체크하므로 SEC-D1/D2보다 위험도 낮음. 주로 **일관성** 문제.

---

### [SEC-D4] nda_markups current_file_path 경로 탐색 방어 불일치 — [Major/MEDIUM] — Priority: P2 (점수: 42)

**파일**: `deal-mgmt/app/routers/nda_markups.py:297-298 vs 310-312`

**문제**: `generate_nda_redline`에서 `base_path`에는 `resolve().relative_to(UPLOAD_DIR.resolve())` 방어(L310-312)가 있지만, `current_file_path`(L297)에는 동일한 방어 없음. DB에서 온 값이므로 실질적 위험은 낮으나 방어 패턴 일관성 차원에서 추가 권장.

**코드**:
```python
current_file_path = Path(current_markup.file_path)  # ← 경로 탐색 방어 없음
current_bytes = await run_in_threadpool(current_file_path.read_bytes)
# ...
base_path = Path(base_markup.file_path)
base_path.resolve().relative_to(UPLOAD_DIR.resolve())  # ← 방어 있음
```

---

### [DOM-1] DealSetupWizardPage formatKRW 중복 정의 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx:77-84`

**문제**: 로컬 `formatKRW` 함수가 정의되어 있으나, `@/modules/ma/utils/format`에 공유 버전 존재. 두 구현의 로직이 다르며(로컬: number만, 공유: string|number), BuyerFeedbackSection은 공유 버전 사용. 금액 표시 일관성 위험.

---

### [DOM-2] DealSetupWizardPage estimated_deal_value 타입 불일치 — [Moderate/MEDIUM] — Priority: P3 (점수: 24)

**파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx:307-309`

**문제**: `Input type="number"`의 `e.target.value`는 항상 문자열. `set("estimated_deal_value", e.target.value)`로 문자열이 저장되어 `formatKRW(txn.estimated_deal_value)`에서 타입 불일치 가능성.

---

### [OBS-1] DealSetupWizardPage onError 에러 상세 누락 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx:395, 406, 424`

**문제**: 3개 mutation의 `onError`에서 에러 객체를 무시하고 고정 문자열만 표시. 같은 diff의 다른 파일(`BuyerFeedbackSection`, `useSIMapping`)에서는 `extractApiError(err, "...")` 패턴 사용. 패턴 불일치.

---

### [OBS-2] VdrTab catch 에러 객체 미수집 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx:110`

**문제**: `.catch(() => ...)` 에서 에러 객체를 받지 않아 디버깅 추적 불가.

---

### [OBS-3] contract_markups VCS except 블록 내 import — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `deal-mgmt/app/routers/contract_markups.py:174-177`

**문제**: `except` 블록 안에서 `import logging`. `nda_markups.py`에서는 파일 상단 `logger = logging.getLogger(__name__)` 패턴 사용. 모듈 간 불일치.

---

### [OBS-4] useVdr onError 패턴 불일치 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/hooks/useVdr.ts:203-204`

**문제**: `onError: () => toast.error("문서 수정에 실패했습니다.")` — 다른 훅의 `extractApiError` 패턴과 불일치.

---

### [DEPLOY-1] rfi_v2 권한 변경 회귀 위험 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `deal-mgmt/app/routers/rfi_v2.py:197, 284, 442`

**문제**: `create_thread`, `upload_attachments`, `import_excel`의 `get_jwt_claims` → `require_write_access()` 권한 강화. 기존에 CLIENT 역할 사용자가 이 기능을 사용했다면 403 발생. `test_role_access.py`에 이 엔드포인트들의 CLIENT 접근 테스트 없어 회귀 탐지 불가.

---

### [DEPLOY-2] VdrTab 자동 초기화 remount 시 재시도 리셋 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx:99-121`

**문제**: `retryCountRef`가 `useRef(0)`이므로 컴포넌트 remount 시 0으로 리셋. 서버 VDR 초기화가 계속 실패하면 탭 전환마다 3회 재시도가 반복됨.

---

### [TEST-1] test_role_access 엔드포인트 커버리지 부족 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/tests/test_role_access.py`

**문제**: 현재 3개 엔드포인트만 CLIENT 차단 테스트. 누락:
- CONTRACT MARKUP: POST/DELETE (`require_write_access` 사용)
- NDA MARKUP: POST/DELETE
- RFI: POST/PATCH/DELETE items, POST attachments
- VDR: 문서 업로드/삭제

---

### [TEST-2] 프론트엔드 테스트 부재 — [Moderate/HIGH] — Priority: P2 (점수: 40)

14개 변경 컴포넌트 중 테스트 파일 1개만 존재 (`utils/__tests__/format.test.ts`). BuyersTab(526줄, 9개 상태), FIRecommendModal(비동기 bulk 로직) 등 복잡 컴포넌트 테스트 부재.

---

### [CC-1] BuyersTab God Component — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx` (526줄)

**문제**: useState 9개, useMemo 7개, 8개 이상 책임. Long List/Short List 렌더링, 필터링, SI 매핑 모달, FI 추천 모달, 상세 패널, 뷰 모드 전환 등 단일 컴포넌트에 집중.

---

### [CC-2] DealSetupWizardPage 3컴포넌트 단일 파일 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx` (701줄)

**문제**: `DealSetupWizardPage`, `ManualTab` (240줄), `AITab` (326줄) 3개 컴포넌트가 단일 파일에 집중.

---

### [CC-3] nda_markups generate_nda_redline 과다 길이 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `deal-mgmt/app/routers/nda_markups.py:269-388` (120줄)

**문제**: 권한 검증 → 파일 읽기 → 참조 버전 결정(3분기) → LLM 호출 → 파일 저장 → DB 업데이트 → 응답 반환 7단계를 단일 함수에서 수행.

---

### [CC-4] contract_markups create_markup 과다 길이 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `deal-mgmt/app/routers/contract_markups.py:71-181` (110줄)

**문제**: 파일 검증 → 버전 번호 결정 → 파일 저장 → DB 생성 → 감사 기록 → VCS 연동(savepoint) → 커밋 7단계 수행.

---

### [DEP-1] os.path vs pathlib 혼용 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `deal-mgmt/app/routers/rfi_v2.py:5, 294`

**문제**: `os.path.splitext()` 사용. 같은 프로젝트 `contract_markups.py`, `nda_markups.py`에서는 `Path().suffix.lower()` 사용. `python-ci-standards.md` 강행 규정 2 위반.

---

### [DEP-2] document_version_service import 패턴 불일치 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `contract_markups.py:20` vs `nda_markups.py:172`

**문제**: contract_markups에서는 모듈-레벨 import, nda_markups에서는 함수 내 지연 import. 불일치.

---

### [STALE-1] BuyerFeedbackSection useState stale closure — (기존 CR-8 미수정)

**파일**: `amic-platform/src/modules/ma/components/buyers/BuyerFeedbackSection.tsx:20`

**상태**: 이전 세션에서 수정했으나 외부 수정으로 되돌려짐. `useEffect` 동기화 블록 부재.

```tsx
const [notes, setNotes] = useState(buyer.notes ?? "");  // buyer.id 변경 시 동기화 안 됨
```

---

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. [SEC-D1] [Major/HIGH]: contract_markups download_markup IDOR (점수: 85)
2. [SEC-D2] [Major/HIGH]: contract_markups delete_markup IDOR (점수: 85)
3. [SEC-D3] [Major/HIGH]: nda_markups generate_nda_redline 일관성 (점수: 70)
4. [TEST-1] [Major/HIGH]: test_role_access 엔드포인트 커버리지 부족 (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. [SEC-D4] [Major/MEDIUM ⚠️]: nda_markups current_file_path 방어 불일치 (점수: 42)
2. [DOM-1] [Moderate/HIGH]: formatKRW 중복 정의 (점수: 40)
3. [OBS-1] [Moderate/HIGH]: DealSetupWizardPage onError 에러 상세 누락 (점수: 40)
4. [OBS-2] [Moderate/HIGH]: VdrTab catch 에러 미수집 (점수: 40)
5. [DEPLOY-1] [Moderate/HIGH]: rfi_v2 권한 변경 회귀 위험 (점수: 40)
6. [DEPLOY-2] [Moderate/HIGH]: VdrTab remount 재시도 리셋 (점수: 40)
7. [TEST-2] [Moderate/HIGH]: 프론트엔드 테스트 부재 (점수: 40)

### P3 — 저우선 (점수: <30)
1. [DOM-2] [Moderate/MEDIUM ⚠️]: estimated_deal_value 타입 불일치 (점수: 24)
2. [CC-1] [Moderate/HIGH]: BuyersTab God Component (점수: 20 — 리팩토링)
3. [OBS-3] [Minor/HIGH]: except 내 import (점수: 20)
4. [OBS-4] [Minor/HIGH]: useVdr onError 패턴 불일치 (점수: 20)
5. [CC-2] [Minor/HIGH]: DealSetupWizardPage 701줄 단일 파일 (점수: 20)
6. [CC-3] [Minor/HIGH]: nda_markups 120줄 핸들러 (점수: 20)
7. [CC-4] [Minor/HIGH]: contract_markups 110줄 핸들러 (점수: 20)
8. [DEP-1] [Minor/HIGH]: os.path vs pathlib 혼용 (점수: 20)
9. [DEP-2] [Minor/HIGH]: import 패턴 불일치 (점수: 20)

---

## 이전 리뷰(13관점) 대비 신규 발견

| 관점 | 이전 커버리지 | 이번 심층 리뷰 | 신규 이슈 |
|------|------------|-------------|---------|
| 관찰 가능성 | ⚠️ 경미 | ✅ 심층 | OBS-1~4 (4건) |
| 배포 안전성 | ⚠️ 경미 | ✅ 심층 | DEPLOY-1~2 (2건) |
| 의존성 | ⚠️ 경미 | ✅ 심층 | DEP-1~2 (2건) |
| 도메인 로직 | ⚠️ 경미 | ✅ 심층 | DOM-1~2 (2건) |
| 테스트 품질 | ⚠️ 경미 | ✅ 심층 | TEST-1~2 (2건) |
| 인지 복잡도 | ⚠️ 경미 | ✅ 심층 | CC-1~4 (4건) |
| 보안 | ✅ 심층 | ✅ 보강 | SEC-D1~4 (4건 신규 IDOR) |

---

## Methodology

- **Agents**: 관찰가능성+배포안전성, 도메인로직+테스트품질, 의존성+인지복잡도 (3개 병렬)
- **Files scanned**: 18개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Major 5건 실제 코드 대조 완료

## 검증 투명성

### 검증 통계
- 검증한 가설: 28건
- 거부된 가설 (사전 제거): 8건
- 보고된 이슈: 20건
- 거부율: 29%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 3 | VdrTab `_get_nda_or_404`가 txn 매핑 검증 중 |
| 범위 외 | 2 | 변경되지 않은 기존 코드 |
| 이미 수정됨 | 1 | download_markup 경로 탐색 방어 이미 존재 |
| 오판 | 1 | DEV_MOCK_BUYERS 프로덕션 가드 실제 동작 확인 |
| 중복 | 1 | VdrTab 재시도 이슈 2개 에이전트 중복 보고 |
