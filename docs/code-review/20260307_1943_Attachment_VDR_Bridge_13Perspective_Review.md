# Code Review — Attachment→VDR Bridge 13관점 통합 리뷰

> **Review Date**: 2026-03-07 19:43
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `deal-mgmt/app/services/attachment_vdr_bridge.py`, `deal-mgmt/app/routers/attachments.py`, `deal-mgmt/app/routers/vdr.py`, `deal-mgmt/app/services/vdr_service.py`, `deal-mgmt/app/services/vdr_qa_service.py`, `deal-mgmt/app/schemas/vdr.py`, `amic-platform/src/modules/ma/types/attachment.ts`, `amic-platform/src/modules/ma/types/vdr.ts`, `amic-platform/src/modules/ma/hooks/useAttachments.ts`
> **Method**: 5-Agent Initial Review + 4-Agent Supplementary Review + Cross-Verification
> **Review Gates**: Backend(available) Agent-Filtering(4개 에이전트 호출, 0개 제외)

## 리뷰 범위

### Phase 1 (초기 5-에이전트 리뷰, 별도 문서)
1. Python Code Quality
2. Security
3. Performance
4. Migration Safety
5. FE Type Sync

### Phase 2 (본 보고서 — 추가 8관점)
6. API Design & Contract
7. Backward Compatibility
8. Deployment Safety
9. Error Handling & Recovery
10. Concurrency & Race Conditions
11. Observability & Logging
12. Data Integrity
13. Test Coverage

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0 | — | — |
| Major | 3 | HIGH: 3 | P1: 3 |
| Moderate | 2 | HIGH: 2 | P2: 2 |
| Minor | 3 | HIGH: 1 / MEDIUM: 2 | P2: 1 / P3: 2 |
| **Total** | **8** | HIGH: **6** / MEDIUM: **2** | P1: **3** / P2: **3** / P3: **2** |

**FP Prevention**: 가설 14건 검증, 6건 사전 거부 (거부율: 43%) | 교차 검증 5건 수행

**중복 제거**: E-01=D-1 (blob orphan), E-03=D-4 (init error propagation), API-1=BC-1 (file_path 타입) → 3건 병합

---

## Findings

### [API-2] cost_usd 스키마 non-nullable 위반 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/app/schemas/vdr.py:207`
**증거**:
```python
# schemas/vdr.py:207
cost_usd: float  # non-nullable

# routers/vdr.py:822
cost_usd=result.cost_usd if claims.role == "ADMIN" else None  # None 할당
```

**영향**: non-ADMIN 사용자가 Q&A API 호출 시 Pydantic `ValidationError` 발생 가능. `cost_usd: float`는 `None`을 허용하지 않음.

**수정 제안**: `cost_usd: float | None = None` 으로 변경

**교차 검증**: CONFIRMED — schemas/vdr.py:207 직접 확인, FE 타입(vdr.ts:129)은 이미 `number | null`로 수정 완료.

---

### [E-01/D-1] Bridge except 블록 blob 고아 위험 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/app/services/attachment_vdr_bridge.py:216-223`
**증거**:
```python
except Exception:
    logger.exception(
        "VDR 연동 실패: txn=%s, attachment=%s, file=%s",
        transaction_id, attachment.id, attachment.file_name,
    )
    return None  # blob 정리 없음, rollback 없음
```

**영향**: `auto_commit=False`로 VDR 문서 생성 후 `db.commit()` 실패 시:
- DB에는 VDR 문서 미커밋 (자동 rollback)
- 스토리지에는 blob 파일 잔존 → 고아 blob 누적

**수정 제안**: except 블록에서 `db.rollback()` + blob cleanup (best-effort) 추가

**교차 검증**: CONFIRMED — bridge.py L161, L199의 commit 실패 시 blob 정리 경로 부재 확인.

---

### [C-01] init_vdr_folders TOCTOU 경합 조건 — [Major/HIGH] — Priority: P1 (점수: 70)

**파일**: `deal-mgmt/app/services/vdr_service.py:64-68`
**증거**:
```python
existing = await db.scalar(
    select(func.count()).select_from(VdrFolder)
    .where(VdrFolder.transaction_id == transaction_id)
)
if existing and existing > 0:
    raise ValueError("이 거래의 VDR 폴더가 이미 초기화되어 있습니다.")
# ... INSERT (L70-82)
```

**영향**: 동시 첨부파일 업로드 시 두 요청이 동시에 `existing=0`을 읽고 중복 VDR 폴더 세트 생성 가능.

**수정 제안**: `SELECT ... FOR UPDATE` 또는 unique constraint + `ON CONFLICT` 패턴 사용

**교차 검증**: CONFIRMED — SELECT COUNT → check → INSERT 패턴은 전형적 TOCTOU. 실제 동시 요청 시 발생 가능.

---

### [E-02] Bridge except 블록 rollback 누락 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `deal-mgmt/app/services/attachment_vdr_bridge.py:216-223`
**증거**: E-01/D-1과 동일 위치. `db.rollback()` 호출 없음.

**완화 요소**: 호출자(`attachments.py:275`)에서 2차 방어로 `await db.rollback()` 수행.
```python
# attachments.py:275
except Exception:
    await db.rollback()
    logger.warning("VDR 연동 실패: ...")
```

**교차 검증**: PARTIAL — bridge 자체에 rollback 없으나, caller가 2차 방어 제공. 방어적 프로그래밍 관점에서 bridge 내부에도 추가 권장.

---

### [API-1/BC-1] FE Attachment 타입에 file_path 잔존 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/types/attachment.ts:16`
**증거**:
```typescript
export interface Attachment {
  // ...
  file_path: string;  // BE에서 SEC-01으로 제거됨
  // ...
}
```

**영향**: BE가 `file_path`를 응답에서 제거했으므로 FE 타입과 실제 API 응답 불일치. 현재 FE 컴포넌트에서 `attachment.file_path`를 직접 사용하는 곳은 Grep으로 확인되지 않아 런타임 영향은 없음.

**수정 제안**: FE 타입에서 `file_path` 제거 또는 `file_path?: string` (optional)으로 변경

**교차 검증**: PARTIAL — 타입 불일치는 실재하나 런타임 에러 경로 없음. Major→Moderate 하향.

---

### [O-01] Bridge 서비스 로깅 상세도 부족 — [Minor/HIGH] — Priority: P2 (점수: 20)

**파일**: `deal-mgmt/app/services/attachment_vdr_bridge.py:216-223`
**증거**: except 블록에서 `logger.exception()`으로 스택 트레이스는 기록하나, VDR 문서 ID, 폴더 ID 등 디버깅에 필요한 컨텍스트 부재.

**수정 제안**: 로그에 `vdr_document_id`, `folder_id`, `classification_status` 등 추가

---

### [T-01] Bridge 서비스 테스트 커버리지 50% — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/tests/test_attachment_vdr_bridge.py`
**증거**: 5개 테스트 존재. 누락 시나리오: folder=None fallback, 중복 파일명, audit 인자 검증, commit/rollback 검증.

**수정 제안**: 누락 브랜치에 대한 테스트 추가 (특히 commit 실패 → rollback 경로)

---

### [D-02] vdr_qa_service InMemory 대화 저장소 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:54-57`
**증거**:
```python
_conversation_store: OrderedDict[str, list[dict]] = OrderedDict()
```

**영향**: multi-worker uvicorn 배포 시 워커 간 대화 상태 공유 불가. 현재 단일 워커로 운영 중이면 즉시 영향 없음.

**수정 제안**: Redis 또는 DB 기반 대화 저장소로 전환 (multi-worker 전환 시)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)
없음

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)
1. [API-2] [Major/HIGH]: cost_usd non-nullable 스키마 위반 — schemas/vdr.py (점수: 70)
2. [E-01/D-1] [Major/HIGH]: blob 고아 위험 (bridge except) — attachment_vdr_bridge.py (점수: 70)
3. [C-01] [Major/HIGH]: init_vdr_folders TOCTOU 경합 — vdr_service.py (점수: 70)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)
1. [E-02] [Moderate/HIGH]: bridge rollback 누락 (caller 방어 존재) — attachment_vdr_bridge.py (점수: 40)
2. [API-1/BC-1] [Moderate/HIGH]: FE file_path 타입 잔존 — attachment.ts (점수: 40)
3. [O-01] [Minor/HIGH]: 로깅 컨텍스트 부족 — attachment_vdr_bridge.py (점수: 20)

### P3 — 저우선 (점수: <30, 개선 가능)
1. [T-01] [Minor/MEDIUM]: 테스트 커버리지 50% — test_attachment_vdr_bridge.py (점수: 12)
2. [D-02] [Minor/MEDIUM]: InMemory 대화 저장소 — vdr_qa_service.py (점수: 12)

---

## Methodology

- **Phase 1 Agents**: Python Code Quality, Security, Performance, Migration Safety, FE Type Sync
- **Phase 2 Agents (본 리뷰)**: API/BC Agent, Error/Deployment Agent, Concurrency/Observability Agent, Test/Data Agent
- **Excluded Agents**: 없음
- **Files scanned**: 9개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Major+ 5건 수행 (CONFIRMED: 3, PARTIAL: 2, FALSE_POSITIVE: 0)
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 6건
- 보고된 이슈: 8건
- 거부율: 43%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 2 | "에러 핸들링 없음" → caller에서 처리 확인 |
| 중복 | 3 | E-01=D-1, E-03=D-4, API-1=BC-1 병합 |
| 범위 외 | 1 | 기존 vdr_service 로직 (bridge 범위 아님) |

---

## 수정 우선순위 권장

1. **API-2** (가장 쉬움): `schemas/vdr.py:207`에서 `cost_usd: float | None = None` 변경 — 1줄 수정
2. **E-01/E-02** (함께 수정): bridge except 블록에 `db.rollback()` + blob cleanup 추가
3. **C-01** (설계 변경 필요): init_vdr_folders에 SELECT FOR UPDATE 또는 unique constraint 도입
4. **API-1/BC-1**: FE attachment 타입에서 `file_path` optional 처리
