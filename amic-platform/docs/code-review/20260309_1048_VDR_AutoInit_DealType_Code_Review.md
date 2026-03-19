# Code Review — VDR 자동 초기화 + DealType 변경

> **Review Date**: 2026-03-09 10:48
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff HEAD` — 14 files, +69/-87 lines
> **Method**: Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: ruff-check(PASS) ruff-format(PASS) tsc(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(2개 에이전트: python-code-reviewer, code-reviewer)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P0: 1               |
| Major    | 3     | HIGH: 3                | P1: 3               |
| Moderate | 1     | HIGH: 1                | P2: 1               |
| Minor    | 3     | HIGH: 2 / MEDIUM: 1    | P3: 3               |
| **Total**| **8** | HIGH: **7** / MEDIUM: **1** | P0: **1** / P1: **3** / P2: **1** / P3: **3** |

**FP Prevention**: 가설 12건 검증, 1건 사전 거부 (거부율: 8%) | 교차 검증 4건 수행 (1건 FALSE POSITIVE, 1건 DOWNGRADE)

---

## Findings

### P0 — 즉시 수정 (보안/데이터 무결성)

#### [C-01] DealType enum 변경에 대한 Alembic 마이그레이션 누락 — [Critical/HIGH] — Priority: P0 (점수: 100)

**파일**: `deal-mgmt/app/models/enums.py:4-11`, `deal-mgmt/app/models/transaction.py:20`

**문제**: `DealType` enum이 `MA/PE/RE/IB` → `SE/BU/ISSUE/HYB/GEN`으로 완전 교체되었으나, PostgreSQL enum 타입 변경을 위한 Alembic 마이그레이션이 없음. `alembic/versions/` 디렉토리 자체가 존재하지 않음.

프로덕션 DB에 기존 `MA/PE/RE/IB` 값으로 저장된 거래가 있으며, 마이그레이션 없이 배포 시:
- 기존 데이터 SELECT 시 Python enum 역직렬화 실패
- 새 값으로 INSERT 시 `DataError: invalid input value for enum` 발생

**교차 검증**: CONFIRMED — `ls deal-mgmt/alembic/versions/*.py` 결과 0건.

**수정 방향**:
1. Alembic 마이그레이션 생성
2. `upgrade()`: 기존 enum 값 → 신규 값 매핑 (예: MA→SE), ALTER TYPE 실행
3. `downgrade()`: 역변환 포함

---

### P1 — 스프린트 우선 (안정성/정확성)

#### [W-01] 코드명 정규식이 폐기된 DealType 값 검증 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/tests/test_transactions.py:15`

```python
CODE_NAME_PATTERN = re.compile(r"^(MA|PE|RE|IB)\d{2}-[A-Z]{1,3}-\d{2}$")
```

**문제**: 신규 enum `SE/BU/ISSUE/HYB/GEN`으로 생성되는 코드명(`SE26-ALF-01`, `ISSUE26-ALF-01`)을 매칭하지 못하여 테스트 실패.

**교차 검증**: CONFIRMED — Grep으로 해당 라인 확인.

**수정**: `r"^(SE|BU|ISSUE|HYB|GEN)\d{2}-[A-Z]{1,3}-\d{2}$"`

---

#### [W-02] VDR 미초기화 가정 테스트 — 자동 초기화와 충돌 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/tests/test_vdr.py:214-215`, `test_vdr.py:409-410`

```python
# test_vdr.py:214-215
assert data["initialized"] is False   # 이제 True
assert data["total_folders"] == 0     # 이제 11+

# test_vdr.py:409-410
assert item["vdr_initialized"] is False
assert item["total_folders"] == 0
```

**문제**: `create_transaction()`이 VDR 폴더를 자동 생성하므로, fixture로 거래 생성 후 `initialized: False` / `total_folders: 0` 단언이 실패.

**교차 검증**: CONFIRMED — Grep으로 4개 단언 확인.

**수정**: 해당 단언을 `True` / `11`(또는 실제 기본 폴더 수)로 변경. 미초기화 테스트는 별도 fixture(VDR 없이 거래만 INSERT)로 분리.

---

#### [VDR-01] useEffect 자동 초기화 — 에러 핸들링 부재 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx:96-104`

```tsx
useEffect(() => {
  if (summary && !summary.initialized) {
    maApi.post(`/transactions/${txnId}/vdr/init`, {}).then(() => {
      qc.invalidateQueries({
        queryKey: ["ma", "transactions", txnId, "vdr"],
      });
    });
    // .catch() 없음 → Unhandled Promise Rejection
  }
}, [summary, txnId, qc]);
```

**문제**:
1. `.catch()` 없어 네트워크 에러 시 Unhandled Promise Rejection
2. 초기화 실패 시 사용자에게 피드백 없음
3. 실패 후 summary refetch 시 재트리거 → 무한 재시도 가능성

**교차 검증**: CONFIRMED — 코드 직접 확인, `.catch()` 부재.

**수정**:
```tsx
.catch(() => {
  console.error("VDR 자동 초기화 실패");
});
```
+ `useRef` 플래그로 중복 실행 방지 권장.

---

### P2 — 개선 권장 (코드 품질)

#### [VDR-02] useEffect 자동 초기화 — 중복 실행 방지 없음 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/components/vdr/VdrTab.tsx:96-104`

**문제**: React Strict Mode에서 effect 이중 실행, summary refetch마다 재트리거 가능. 백엔드 `init_vdr_folders()`의 TOCTOU 보호로 에러는 발생하지 않지만 불필요한 API 호출.

**수정**: `useRef(false)` 플래그로 진행 중 상태 관리.

---

### P3 — 저우선 (개선 가능)

#### [VDR-03] EngagementDocUpload — 미사용 `refetchFolders` 의존성 — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/components/overview/EngagementDocUpload.tsx:223`

`handleFile` 콜백의 의존성 배열에 `refetchFolders`가 포함되어 있으나 함수 본문에서 사용하지 않음. 불필요한 콜백 재생성 유발.

---

#### [VDR-05] ISSUE 코드 프리뷰 — 5자리 prefix로 포맷 불일치 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `amic-platform/src/modules/ma/pages/CreateTransactionPage.tsx:42-47`

`dealType`이 `"ISSUE"`인 경우 코드명이 `ISSUE26-XXX-??`로 5자리 prefix. 다른 타입(`SE`, `BU`, `HYB`, `GEN`)은 2~3자리. UI 일관성 검토 권장.

---

#### [S-01] create_default_folders() 반환값 미사용 — [Minor/LOW] — Priority: P3 (점수: 6)

**파일**: `deal-mgmt/app/services/transaction_service.py:248`

```python
create_default_folders(db, txn.id)  # 반환값 list[VdrFolder] 무시
```

의도적이라면 문서화 또는 `_ =` 패턴 사용 권장. 동기 함수에서 `AsyncSession.add()` 호출 자체는 SQLAlchemy에서 정상 패턴.

---

## 교차 검증 결과

| Phase 1 ID | Phase 2 판정 | 사유 |
|------------|-------------|------|
| C-01 | CONFIRMED | alembic/versions/ 디렉토리 미존재 확인 |
| C-02 | **FALSE_POSITIVE** (FP-HALLUC) | conftest.py 이미 `"SE"` 사용, Grep 0건 |
| C-03 | **DOWNGRADE** (Critical→Minor) | `AsyncSession.add()`는 동기 메서드, 정상 패턴 |
| W-01 | CONFIRMED | Grep으로 정규식 확인 |
| W-02 | CONFIRMED | Grep으로 4개 단언 확인 |
| VDR-01 | CONFIRMED | .catch() 부재 확인 |

---

## 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | BE: create_default_folders() 헬퍼 추출 | ✅ | vdr_service.py:59-79 |
| 2 | BE: transaction_service.py VDR 자동 생성 | ✅ | transaction_service.py:245-248 |
| 3 | FE: ENGAGEMENT에 vdr 탭 추가 | ✅ | phase.ts:88 |
| 4 | FE: VdrTab 초기화 UI 삭제 + useEffect | ✅ | VdrTab.tsx:96-104, 165-행 삭제 |
| 5 | FE: useInitVdr 훅 삭제 | ✅ | useVdr.ts:62-78 삭제 |
| 6 | FE: EngagementDocUpload initVdr 제거 | ✅ | EngagementDocUpload.tsx:14,71,173-178 |
| 7 | DealType enum 변경 (계획 외) | ⚠️ | 마이그레이션 누락 (C-01) |
| 8 | 테스트 업데이트 | ⚠️ | 코드명 정규식(W-01), VDR 단언(W-02) 미수정 |

---

## Methodology

- Agents: python-code-reviewer (BE), code-reviewer (FE)
- Files scanned: 14
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: Critical + Major 4건 수행 (1건 FP 제거, 1건 하향)
- Backend availability: deal-mgmt(available)
