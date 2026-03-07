# Code Review — VDR Bridge (Attachment → VDR 자동 연동) 13-Perspective 통합 리뷰

> **Review Date**: 2026-03-07 18:40
> **Reviewer**: Claude Code (review-orchestrate, 13-Perspective)
> **Scope**: `deal-mgmt/app/services/attachment_vdr_bridge.py`, `deal-mgmt/app/routers/attachments.py`, `deal-mgmt/app/services/vdr_service.py`, `deal-mgmt/app/services/vdr_classification_service.py`, `deal-mgmt/app/routers/vdr.py`, `deal-mgmt/app/models/attachment.py`, `deal-mgmt/app/schemas/attachment.py`, `deal-mgmt/migrations/versions/071_attachment_vdr_document_id.py`, `amic-platform/src/modules/ma/types/attachment.ts`, `amic-platform/src/modules/ma/hooks/useAttachments.ts`
> **Method**: 5-Agent Parallel Review (R2–R6, 13 perspectives) + Cross-Verification
> **Prior Review**: R1 기본 리뷰 완료 (C1–N2 수정 적용 후)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P0: 1 |
| Major    | 5     | HIGH: 3 / MEDIUM: 2 / LOW: 0 | P0: 0 / P1: 5 |
| Moderate | 7     | HIGH: 4 / MEDIUM: 3 / LOW: 0 | P2: 7 |
| Minor    | 5     | HIGH: 2 / MEDIUM: 3 / LOW: 0 | P3: 5 |
| **Total**| **18** | HIGH: **10** / MEDIUM: **5** / LOW: **0** | P0: **1** / P1: **5** / P2: **7** / P3: **5** |

**FP Prevention**: 가설 32건 검증, 14건 사전 거부 (거부율: 44%) | 교차 검증 6건 수행 (4-agent 합의 1건, 2-agent 합의 5건)

---

## Findings

### P0 — 즉시 수정 (점수: 90+, 데이터 무결성)

---

#### [C-1] Double Commit → 고아 VDR 문서 — [Critical/HIGH] — Priority: P0

**교차 검증**: 4개 에이전트 합의 (R3, R4, R5, R6) ✅ CONFIRMED

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py` (sync_attachment_to_vdr 함수)

**문제**:
`vdr_service.upload_document()` (`vdr_service.py:265`)가 내부에서 `db.commit()`을 호출하여 VDR 문서를 확정한 후, bridge에서 `attachment.vdr_document_id` 할당 + `db.commit()`을 다시 호출하는 이중 커밋 구조.

두 커밋 사이에서 예외가 발생하면:
1. VDR 문서는 이미 DB에 커밋됨 (롤백 불가)
2. `attachment.vdr_document_id`는 미할당 상태로 남음
3. **고아 VDR 문서**가 생성되어 VDR에 출처 불명 문서가 표시됨
4. 복구 경로 없음 — `ondelete=SET NULL`이므로 FK 무결성은 유지되지만, 논리적 정합성 깨짐

**증거**:
```python
# vdr_service.py:265
await db.commit()  # ← 1차 커밋: VDR 문서 확정

# attachment_vdr_bridge.py (sync 함수 내부)
attachment.vdr_document_id = vdr_doc.id  # ← 이 사이에서 예외 발생 가능
await _record_vdr_sync_audit(db, ...)
await db.commit()  # ← 2차 커밋: attachment에 VDR ID 연결
```

**영향**: 부분 실패 시 VDR에 미연결 문서 누적. 사용자가 VDR에서 출처 알 수 없는 파일을 보게 됨.

**수정 제안**:
- **Option A** (권장): `upload_document()`에 `auto_commit=False` 파라미터 추가하여 bridge에서 단일 커밋으로 통합
- **Option B**: bridge에서 예외 발생 시 VDR 문서를 소프트 삭제하는 보상 트랜잭션 추가
- **Option C** (최소): 고아 문서 감지 + 정리 배치 작업 추가

**우선순위 점수**: 100 × 1.0 + 15 (4-agent 합의) = **115**

---

### P1 — 스프린트 우선 (점수: 60–89, 안정성/정확성)

---

#### [M-1] Rollback 후 Expired Attachment → DetachedInstanceError — [Major/HIGH] — Priority: P1

**교차 검증**: R4 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/routers/attachments.py` (upload_attachment 함수, VDR 연동 실패 처리부)

**문제**:
VDR 연동 중 예외 발생 → `db.rollback()` 호출 → SQLAlchemy async session이 모든 ORM 객체를 expire → 이후 `AttachmentOut.model_validate(attachment)` 호출 시 expired 속성 접근 → `DetachedInstanceError` 또는 `MissingGreenlet`.

```python
except Exception:
    await db.rollback()  # ← attachment 객체 expire
    logger.warning(...)
result = AttachmentOut.model_validate(attachment)  # ← expired 속성 접근 시 에러
```

**수정 제안**: rollback 전에 `attachment` 속성을 dict로 미리 추출하거나, rollback 후 `await db.refresh(attachment)` 호출.

**우선순위 점수**: 70 × 1.0 = **70**

---

#### [M-2] Bridge 테스트 부재 — [Major/HIGH] — Priority: P1

**교차 검증**: R6 단독 발견, CONFIRMED

**위치**: `deal-mgmt/tests/` (부재)

**문제**: 핵심 비즈니스 로직인 `attachment_vdr_bridge.py`에 대한 단위/통합 테스트가 전무. 정상 경로, 실패 경로, VDR 미초기화 케이스 등 테스트 필요.

**수정 제안**: `deal-mgmt/tests/test_attachment_vdr_bridge.py` 신규 생성. 최소 케이스:
1. 정상 1차 심사 통과
2. 1차 미통과 → 2차 심사 트리거
3. VDR 미초기화 → 자동 초기화
4. best-effort 실패 → `None` 반환

**우선순위 점수**: 70 × 1.0 = **70**

---

#### [M-3] `classification_score` 의미 혼동 — [Major/MEDIUM] — Priority: P1

**교차 검증**: R6 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py`

**문제**: `VdrSyncResult.classification_score`에 `score_document()`의 반환값(0–100 점수)을 할당하지만, `VdrSyncInfo` 스키마에서 사용자에게 노출 시 "분류 점수"로 해석됨. 실제로는 "1차 심사 점수"이며, 2차 심사(LLM) 결과와 무관.

**수정 제안**: 필드명을 `primary_score` 또는 `routing_score`로 변경하여 의미 명확화.

**우선순위 점수**: 70 × 0.6 = **42** → MEDIUM 신뢰도 하향으로 P1 하한

---

#### [M-4] `check_vdr_write_permission` 위치 부적절 — [Major/MEDIUM] — Priority: P1

**교차 검증**: R5, R6 2개 에이전트 합의

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py`

**문제**: 순수 함수(`check_vdr_write_permission`)가 bridge 서비스 모듈에 위치하나, VDR 권한 검사는 VDR 서비스의 책임. bridge가 아닌 라우터에서도 재사용 가능해야 함.

**수정 제안**: `vdr_service.py` 또는 별도 `vdr_permissions.py`로 이동.

**우선순위 점수**: 70 × 0.6 + 10 (2-agent) = **52** → P1 하한

---

#### [M-5] `file_path` 경로 순회 검증 미비 — [Major/HIGH] — Priority: P1

**교차 검증**: R2 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py` (sync_attachment_to_vdr 파라미터)

**문제**: `file_path: Path` 파라미터가 호출자(라우터)에서 `dest_path`로 전달되며, 라우터에서 이미 `UPLOAD_DIR / secure_filename(...)` 패턴으로 구성되므로 실질적 위험은 낮음. 그러나 bridge 함수 자체에는 경로가 기대 디렉토리 내에 있는지 검증하는 로직이 없음.

**수정 제안**: bridge 함수 진입 시 `file_path.resolve().is_relative_to(UPLOAD_DIR)` 단언 추가 (방어적 프로그래밍).

**우선순위 점수**: 70 × 1.0 = **70**

---

### P2 — 개선 권장 (점수: 30–59, 코드 품질)

---

#### [m-1] 50MB 파일 메모리 이중 적재 — [Moderate/HIGH] — Priority: P2

**교차 검증**: R2, R5 2개 에이전트 합의

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py` (sync_attachment_to_vdr 내 `file_path.read_bytes()`)

**문제**: 라우터에서 파일을 디스크에 저장한 후, bridge에서 `read_bytes()`로 전체를 메모리에 다시 읽음. 50MB 제한이므로 단일 요청은 수용 가능하나, 동시 업로드 시 메모리 압박.

**수정 제안**: 파일 경로만 VDR 서비스에 전달하여 스트리밍 처리하거나, 동시 업로드 수를 rate limiter와 연동.

**우선순위 점수**: 40 × 1.0 + 10 (2-agent) = **50**

---

#### [m-2] `vdr_document_id` 인덱스 누락 — [Moderate/HIGH] — Priority: P2

**교차 검증**: R5 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/models/attachment.py`, `deal-mgmt/migrations/versions/071_attachment_vdr_document_id.py`

**문제**: `vdr_document_id` FK 컬럼에 `index=True`가 없음. VDR 문서 기준으로 연결된 attachment를 조회하는 역방향 쿼리 성능 저하.

**수정 제안**: `mapped_column(..., index=True)` + 마이그레이션에 `op.create_index` 추가.

**우선순위 점수**: 40 × 1.0 = **40**

---

#### [m-3] `import asyncio` 함수 내부 배치 — [Moderate/HIGH] — Priority: P2

**교차 검증**: R4, R6 2개 에이전트 합의

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py`

**문제**: `import asyncio`가 `sync_attachment_to_vdr()` 함수 내부에 있음. 표준 라이브러리 import는 모듈 최상단에 배치해야 함.

**수정 제안**: 모듈 최상단으로 이동.

**우선순위 점수**: 40 × 1.0 + 10 (2-agent) = **50**

---

#### [m-4] 2차 심사 로그에 `transaction_id` 누락 — [Moderate/MEDIUM] — Priority: P2

**교차 검증**: R4 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/services/vdr_classification_service.py` (run_secondary_classification 내부 except 블록)

**문제**: 내부 except 로그에 `transaction_id`가 포함되지 않아, 프로덕션에서 어떤 거래의 분류가 실패했는지 추적 어려움.

**수정 제안**: `logger.exception("2차 심사 실패: txn=%s, doc=%s", transaction_id, document_id, ...)`

**우선순위 점수**: 40 × 0.6 = **24** → P2 하한

---

#### [m-5] N+1 `db.refresh(attachment)` — [Moderate/MEDIUM] — Priority: P2

**교차 검증**: R5 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/routers/attachments.py`

**문제**: attachment 커밋 후 `db.refresh(attachment)` 호출 + VDR 연동 후 다시 `model_validate` — 불필요한 DB 왕복 가능.

**수정 제안**: VDR 연동 후 한 번만 refresh하거나 필요한 속성만 로드.

**우선순위 점수**: 40 × 0.6 = **24**

---

#### [m-6] `_resolve_folder_by_category` 중복 함수 — [Moderate/MEDIUM] — Priority: P2

**교차 검증**: R5 단독 발견, CONFIRMED

**위치**: `deal-mgmt/app/services/vdr_classification_service.py`

**문제**: `_resolve_folder_by_category`가 `vdr_service.resolve_folder_by_category`와 기능 중복. 두 함수가 동일한 로직을 다른 위치에서 구현.

**수정 제안**: classification_service에서 `vdr_service.resolve_folder_by_category` 재사용.

**우선순위 점수**: 40 × 0.6 = **24**

---

#### [m-7] `useDeleteAttachment` VDR 캐시 미무효화 — [Moderate/HIGH] — Priority: P2

**교차 검증**: R6 단독 발견, CONFIRMED

**위치**: `amic-platform/src/modules/ma/hooks/useAttachments.ts` (useDeleteAttachment onSuccess)

**문제**: 업로드 시에는 VDR 캐시를 무효화하지만, 삭제 시에는 VDR 캐시를 무효화하지 않음. FK `ondelete=SET NULL`로 VDR 문서 자체는 유지되지만, UI 정합성을 위해 무효화 필요.

**수정 제안**: `useDeleteAttachment`의 `onSuccess`에 VDR 쿼리키 무효화 추가.

**우선순위 점수**: 40 × 1.0 = **40**

---

### P3 — 저우선 (점수: <30, 개선 가능)

---

#### [L-1] FE 오디오 확장자 미동기화 — [Minor/MEDIUM] — Priority: P3

**교차 검증**: R3, R6 2개 에이전트 합의

**위치**: `amic-platform/src/modules/ma/types/attachment.ts` (ATTACHMENT_CONSTRAINTS.ALLOWED_EXTENSIONS)

**문제**: BE는 `.mp3`, `.wav`, `.m4a`, `.ogg`, `.aac`, `.wma` 오디오 확장자를 허용하지만, FE `ALLOWED_EXTENSIONS`에는 누락. FE에서 오디오 파일 선택이 차단됨.

**수정 제안**: FE 상수에 오디오 확장자 추가.

**우선순위 점수**: 20 × 0.6 + 10 (2-agent) = **22**

---

#### [L-2] `score_document` 이중 호출 가능성 — [Minor/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py`

**문제**: `score_document()`과 `auto_route()` 내부에서 동일한 스코어링 로직이 중복 실행될 가능성. 현재 `auto_route`가 `scores`를 파라미터로 받으므로 실질적 중복은 없으나, API 변경 시 위험.

**우선순위 점수**: 20 × 0.6 = **12**

---

#### [L-3] 세마포어 매직 넘버 — [Minor/MEDIUM] — Priority: P3

**위치**: `deal-mgmt/app/services/vdr_classification_service.py` (`_classification_semaphore = asyncio.Semaphore(5)`)

**문제**: 동시 LLM 호출 제한 `5`가 상수로 추출되지 않음.

**수정 제안**: `MAX_CONCURRENT_CLASSIFICATIONS = 5` 상수 정의.

**우선순위 점수**: 20 × 0.6 = **12**

---

#### [L-4] 로그에 `file_name` 미포함 — [Minor/HIGH] — Priority: P3

**위치**: `deal-mgmt/app/services/attachment_vdr_bridge.py` (exception 로그)

**문제**: `logger.exception("VDR 연동 실패: txn=%s, attachment=%s", ...)` — 파일명이 없어 디버깅 시 어떤 파일에서 실패했는지 추적 어려움.

**수정 제안**: `attachment.original_filename` 추가.

**우선순위 점수**: 20 × 1.0 = **20**

---

#### [L-5] Non-CLIENT/Non-ADMIN 트랜잭션 접근 갭 (기존 이슈) — [Minor/HIGH] — Priority: P3

**교차 검증**: R2 단독 발견, CONFIRMED (기존 코드 이슈, 본 PR 범위 외)

**위치**: `deal-mgmt/app/routers/attachments.py` (기존 권한 체크 로직)

**문제**: `CLIENT` 역할이 아닌 사용자가 자신의 트랜잭션이 아닌 다른 트랜잭션의 attachment에 접근 가능한 갭. 본 PR에서 도입된 것이 아닌 기존 이슈.

**우선순위 점수**: 20 × 1.0 = **20** (범위 외이므로 정보 제공용)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
1. [C-1] [Critical/HIGH]: Double Commit → 고아 VDR 문서 — attachment_vdr_bridge.py (점수: 115, 4-agent 합의)

### P1 — 스프린트 우선 (점수: 60–89)
1. [M-1] [Major/HIGH]: Rollback 후 Expired Attachment → DetachedInstanceError — attachments.py (점수: 70)
2. [M-2] [Major/HIGH]: Bridge 테스트 부재 — tests/ (점수: 70)
3. [M-5] [Major/HIGH]: file_path 경로 순회 검증 미비 — attachment_vdr_bridge.py (점수: 70)
4. [M-3] [Major/MEDIUM ⚠️]: classification_score 의미 혼동 — attachment_vdr_bridge.py (점수: 42, 신뢰도 하향)
5. [M-4] [Major/MEDIUM]: check_vdr_write_permission 위치 부적절 — attachment_vdr_bridge.py (점수: 52, 2-agent 합의)

### P2 — 개선 권장 (점수: 30–59)
1. [m-1] [Moderate/HIGH]: 50MB 파일 메모리 이중 적재 — attachment_vdr_bridge.py (점수: 50, 2-agent 합의)
2. [m-3] [Moderate/HIGH]: import asyncio 함수 내부 배치 — attachment_vdr_bridge.py (점수: 50, 2-agent 합의)
3. [m-2] [Moderate/HIGH]: vdr_document_id 인덱스 누락 — attachment.py (점수: 40)
4. [m-7] [Moderate/HIGH]: useDeleteAttachment VDR 캐시 미무효화 — useAttachments.ts (점수: 40)
5. [m-4] [Moderate/MEDIUM]: 2차 심사 로그 transaction_id 누락 — vdr_classification_service.py (점수: 24)
6. [m-5] [Moderate/MEDIUM]: N+1 db.refresh — attachments.py (점수: 24)
7. [m-6] [Moderate/MEDIUM]: _resolve_folder_by_category 중복 — vdr_classification_service.py (점수: 24)

### P3 — 저우선 (점수: <30)
1. [L-1] [Minor/MEDIUM]: FE 오디오 확장자 미동기화 — attachment.ts (점수: 22, 2-agent 합의)
2. [L-4] [Minor/HIGH]: 로그에 file_name 미포함 — attachment_vdr_bridge.py (점수: 20)
3. [L-5] [Minor/HIGH]: Non-CLIENT 접근 갭 (기존) — attachments.py (점수: 20, 범위 외)
4. [L-2] [Minor/MEDIUM]: score_document 이중 호출 가능성 — attachment_vdr_bridge.py (점수: 12)
5. [L-3] [Minor/MEDIUM]: 세마포어 매직 넘버 — vdr_classification_service.py (점수: 12)

---

## Methodology

- **Agents**: R2 (Security+STRIDE), R3 (Data Integrity+API Contract), R4 (Error Handling+Observability), R5 (Performance+Deploy+Dependencies), R6 (Domain+Tests+Readability)
- **Prior**: R1 (Basic Review) — C1~N2 수정 적용 완료
- **Files scanned**: 10개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 1건 (4-agent 합의), Major 1건 (2-agent 합의)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 32건
- 거부된 가설 (사전 제거): 14건
- 보고된 이슈: 18건
- 거부율: 44%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 5 | "rate limiter 없음" → InMemoryRateLimiter 확인 |
| 범위 외 | 3 | 기존 VDR 서비스 구조 문제 (본 PR 외) |
| 이미 수정됨 | 2 | R1 리뷰에서 M1/M2/W1/W2로 수정 완료 |
| 오판 | 2 | 코드 로직 오독 (auto_route 파라미터 분석 오류) |
| 중복 | 2 | 다른 에이전트가 동일 이슈 보고 (병합 처리) |

### 교차 검증 상세

| 이슈 ID | 합의 에이전트 | 판정 |
|---------|-------------|------|
| C-1 | R3, R4, R5, R6 (4개) | ✅ CONFIRMED — vdr_service.py:265 커밋 확인 |
| m-1 | R2, R5 (2개) | ✅ CONFIRMED — read_bytes() 전체 로드 확인 |
| m-3 | R4, R6 (2개) | ✅ CONFIRMED — 함수 내 import 확인 |
| M-4 | R5, R6 (2개) | ✅ CONFIRMED — 순수 함수 위치 부적절 |
| L-1 | R3, R6 (2개) | ✅ CONFIRMED — BE/FE 확장자 목록 불일치 확인 |

---

## 수정 권장 순서

1. **C-1** (P0): `upload_document` 트랜잭션 통합 — 고아 문서 방지
2. **M-1** (P1): rollback 후 attachment 안전 처리
3. **M-5** (P1): file_path 경로 검증 추가
4. **M-2** (P1): bridge 테스트 작성
5. **m-3** (P2): import asyncio 위치 수정 + m-2 인덱스 추가 + m-7 캐시 무효화 — 한 번에 처리 가능
6. 나머지 P2/P3 — 후속 스프린트

---

*Generated by Claude Code — review-orchestrate 13-Perspective Pipeline*
*Protocol: Verified Claim Protocol v1.1*
