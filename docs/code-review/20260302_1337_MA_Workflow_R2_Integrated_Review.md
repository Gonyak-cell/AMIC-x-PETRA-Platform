# Code Review — MA Workflow Fix Changes (R2)

> **Review Date**: 2026-03-02 13:37 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `--diff` 변경 파일 14개 + `--backend` (deal-mgmt)
> **Severity Filter**: Critical | Major only
> **Method**: Quality Gates + 5 Parallel Agents + Cross-Verification
> **Quality Gates**: ruff(✓) tsc(✓) build(✓)
> **Agents**: backend-security-reviewer, python-code-reviewer, general-purpose(FE), migration-validator, performance-profiler

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2                | P0: 2                |
| Major    | 14    | HIGH: 9 / MEDIUM: 5   | P1: 9 / P2: 5       |
| **Total**| **16**| HIGH: **11** / MEDIUM: **5** | P0: **2** / P1: **9** / P2: **5** |

**Cross-Verification**: Critical 2건 + Major(HIGH) 9건 직접 Read 확인 완료
**Scope 외 제외**: 3건 (M-01 asyncio.gather, R12-03 mig-041, C-02 spa_analysis 인메모리)

---

## P0 — 즉시 수정 (점수 90+)

---

### [SEC-01] `AttachmentOut` 스키마에 서버 절대 경로 노출 — Critical/HIGH (점수: 100)

- **위치**: `deal-mgmt/app/schemas/attachment.py:18`
- **설명**: `AttachmentOut` 응답 스키마에 `file_path: str` 필드가 포함되어 클라이언트에게 서버 내부 절대 경로(예: `/opt/amic-platform/uploads/attachments/{txn_id}/...`)가 반환됨. OWASP A05:2021 해당.
- **증거**:
  ```python
  class AttachmentOut(BaseModel):
      ...
      file_path: str          # 서버 절대 경로 노출
  ```
  `attachments.py:149`에서 `file_path=str(dest_path)` 저장 → 응답에 그대로 포함.
- **수정**: `file_path` 필드를 `AttachmentOut`에서 제거. 다운로드는 `/attachments/{id}/download` 엔드포인트로만 제공.
- **교차 검증**: 보안 에이전트 + Python 에이전트 동시 발견 (교차 검증됨)

---

### [P-01] 50MB 파일 전체 메모리 적재 후 크기 검사 — Critical/HIGH (점수: 100)

- **위치**: `deal-mgmt/app/routers/attachments.py:115-116`
- **설명**: `content = await file.read()`로 파일 전체를 메모리에 올린 뒤 크기를 검사. 동시 업로드 10건이면 최대 500MB RAM 소비. magic byte 검증과 파일 쓰기도 동일 버퍼 재사용.
- **증거**:
  ```python
  content = await file.read()          # 최대 50MB 단일 버퍼
  if len(content) > MAX_FILE_SIZE:     # 이미 메모리 적재 후 검사
  ```
- **수정**: `file.size` 속성으로 조기 거부 → magic byte는 첫 32바이트만 → 64KB 청크 스트리밍 쓰기.
- **교차 검증**: 성능 에이전트 보고, 코드 직접 확인 CONFIRMED

---

## P1 — 스프린트 우선 (점수 60-89)

---

### [R12-01] Migration 053 `downgrade()` = `raise RuntimeError` 비표준 — Major/HIGH (점수: 80, 3× 교차검증)

- **위치**: `deal-mgmt/migrations/versions/053_remove_mou_signed_phase.py:43-47`
- **설명**: Alembic 표준은 비가역 마이그레이션에 `pass` + 주석 또는 `NotImplementedError` 사용. `RuntimeError`는 마이그레이션 체인 롤백 시 버전 테이블을 오염시킬 수 있음. 046은 SELECT 확인 후 차단하는 안전한 패턴 사용.
- **교차 검증**: 보안 + Python + 마이그레이션 에이전트 3곳에서 동시 지적

---

### [P-04] 파일 삭제 → DB 커밋 원자성 역전 — Major/HIGH (점수: 70)

- **위치**: `deal-mgmt/app/routers/attachments.py:208-220`
- **설명**: `file_path.unlink()` (되돌릴 수 없음) 이후 `db.commit()` 실행. commit 실패 시 DB에 레코드 남고 파일은 삭제된 고아 레코드 상태. 업로드(`attachments.py:142-166`)는 올바른 순서(파일→flush→commit).
- **증거**:
  ```python
  file_path.unlink()          # ① 파일 삭제 (비가역)
  await audit_service.record(...)
  await db.delete(attachment)
  await db.commit()           # ② DB 커밋 — ①이 실패하면 불일치
  ```
- **수정**: DB commit 선행 → 파일 삭제 best-effort 후처리.

---

### [R12-04] Migration 054 `downgrade()` milestoneKey 문자열 → UUID 캐스팅 실패 미처리 — Major/HIGH (점수: 70)

- **위치**: `deal-mgmt/migrations/versions/054_attachment_entity_id_string.py:33-38`
- **설명**: downgrade에서 `entity_id::uuid` 캐스팅 실행. milestoneKey 문자열("MOU_SIGNED", "SIGNING")이 존재하면 PostgreSQL `invalid input syntax for type uuid` 오류 발생. 전체 롤백 체인 실패.
- **수정**: SELECT로 문자열 행 존재 여부 확인 → 존재 시 ROLLBACK BLOCKED 패턴 적용.

---

### [SEC-03] `entity_id` 서버사이드 입력 검증 누락 — Major/HIGH (점수: 70)

- **위치**: `deal-mgmt/app/routers/attachments.py:99` (POST), `:68` (GET)
- **설명**: DB 컬럼 `String(50)`이지만 라우터에서 길이·허용 문자 검증 없음. 50자 초과 시 DB truncation/오류, 특수문자 허용.
- **수정**: `re.compile(r'^[A-Z0-9_\-]{1,50}$')` 패턴 검증 추가.

---

### [R11-1] MilestoneUploadPopover: Escape 키 닫기 없음 — Major/HIGH (점수: 70)

- **위치**: `amic-platform/src/modules/ma/components/MilestoneUploadPopover.tsx` (전체)
- **설명**: WCAG 2.1 AA SC 1.4.13 요구: 팝오버는 Escape 키로 닫을 수 있어야 함. 현재 keydown 리스너 없음.
- **수정**: `useEffect`로 `document.addEventListener("keydown", ...)` + Escape 시 `onClose()`.

---

### [R11-2] MilestoneUploadPopover: 포커스 이동·복원 없음 + 외부 클릭 닫기 없음 — Major/HIGH (점수: 70)

- **위치**: `amic-platform/src/modules/ma/components/MilestoneUploadPopover.tsx` (전체)
- **설명**: WCAG SC 2.4.3 (Focus Order) — 팝오버 열림 시 포커스 이동 없음. 닫힘 시 트리거 복원 없음. 외부 클릭으로 닫을 수 없음.
- **수정**: `useEffect` + `ref.focus()` + `mousedown` 외부 클릭 감지.

---

### [R8-1] `useCallback` 의존성에 `upload.mutate` 직접 참조 → 매 렌더 재생성 — Major/HIGH (점수: 70)

- **위치**: `MilestoneUploadPopover.tsx:55`, `:111-112`
- **설명**: TanStack React Query v5의 `mutate`는 매 렌더마다 새 참조. `useCallback` 의존성에 넣으면 사실상 매 렌더마다 재생성되어 메모이제이션 무효화.
- **증거**:
  ```tsx
  [milestone.milestoneKey, milestone.documentLabel, upload.mutate],  // :55
  [milestone.milestoneKey, milestone.documentLabel, existingFile, upload.mutate, deleteMutation.mutate],  // :107-113
  ```
- **수정**: `useRef` 패턴으로 mutation 참조 안정화.

---

### [SEC-02] magic byte 검증에 OLE2/오디오 포맷 미매핑 — Major/HIGH (점수: 70)

- **위치**: `deal-mgmt/app/routers/attachments.py:226-236`
- **설명**: `.doc`/`.xls`/`.ppt`(OLE2), `.txt`/`.csv`, 오디오 확장자에 대해 매직 바이트 검증 없음. 해당 확장자를 붙인 다른 형식의 파일 업로드 가능.
- **수정**: OLE2 서명(`b"\xD0\xCF\x11\xE0..."`) 추가, 텍스트 파일은 널 바이트 검사.

---

### [P-02] `_check_risk_compliance_gate` ORM 객체 전체 로드 (건수만 필요) — Major/HIGH (점수: 70)

- **위치**: `deal-mgmt/app/services/workflow_engine.py:289-307`
- **설명**: `scalars().all()`로 조건 맞는 모든 RiskItem/ComplianceItem ORM 객체를 메모리에 적재. 실제 필요한 것은 건수(`len()`)뿐.
- **수정**: `func.count()` 또는 `exists()` 쿼리로 교체.

---

## P2 — 개선 권장 (점수 30-59)

---

### [R12-02] Migration 053 DDL/DML 실행 순서 역전 — Major/MEDIUM (점수: 42)

- **위치**: `deal-mgmt/migrations/versions/053_remove_mou_signed_phase.py:29-36`
- **설명**: DML(UPDATE) 먼저 실행 → `autocommit_block`이 현재 트랜잭션 커밋 → DDL 실행. DDL 실패 시 UPDATE는 이미 커밋됨. `IF NOT EXISTS`로 실패 가능성 낮으나 046 패턴(DDL 먼저)과 불일치.
- **수정**: DDL을 DML 이전으로 순서 변경.

---

### [R7-1] `MilestoneUploadPopover` props에서 `PhaseMilestone` union narrowing 없음 — Major/MEDIUM (점수: 42)

- **위치**: `MilestoneUploadPopover.tsx:17`, `:51-52`
- **설명**: `milestone: PhaseMilestone` (union)로 선언. `DisplayOnlyMilestone`에서 `milestoneKey`는 `undefined`. 실질적으로 `uploadable=true`일 때만 호출되므로 런타임 안전하나, 타입 수준 보장 없음.
- **수정**: props 타입을 `UploadableMilestone`으로 좁히기.

---

### [R11-3] 비-uploadable 마일스톤 상태를 색상만으로 구분 (WCAG 1.4.1) — Major/MEDIUM (점수: 42)

- **위치**: `PipelineFlow.tsx:196-203`
- **설명**: 비-uploadable 마일스톤의 done/not-done 상태를 `bg-accent` vs `bg-white`로만 구분. 2×2px 원에 아이콘 없음.
- **수정**: done 상태 시 체크마크 아이콘 또는 시각적 패턴 추가.

---

### [P-05] 프론트엔드 파일 교체: 2단계 API 호출 비원자적 — Major/MEDIUM (점수: 42)

- **위치**: `MilestoneUploadPopover.tsx:91-104`
- **설명**: 업로드 성공 → 삭제 2단계. 네트워크 단절 시 두 파일 공존. `invalidateQueries` 2회 연속 실행.
- **수정**: 백엔드 replace API 또는 프론트엔드 invalidation 1회 통합.

---

### [C-01] `audit_service.record` entity_id UUID 전용 — 설계 리스크 — Major/MEDIUM (점수: 42)

- **위치**: `deal-mgmt/app/services/audit_service.py:88`
- **설명**: 시그니처가 `entity_id: uuid.UUID`로 고정. 현재 `attachment.id` (UUID)를 전달하므로 동작하지만, 향후 문자열 entity에 대한 감사 로그 확장 시 타입 오류 발생.
- **수정**: `entity_id: uuid.UUID | str`로 시그니처 일반화 또는 `str(attachment.id)` 명시적 변환.

---

## Scope 외 제외 사항

| ID | 에이전트 | 이유 |
|----|---------|------|
| M-01 | Python | `ralph/generators/ldd/*.py` — diff 외 파일 |
| R12-03 | Migration | `migrations/041` — diff 외 파일 (선행 이슈) |
| C-02 | Python | `spa_analysis_service.py` 인메모리 세션 — diff 내 파일이나 이번 변경과 무관한 기존 아키텍처 이슈 |
| R3-01 | Migration | MOU_SIGNED fallback — 의도적 설계 (`WorkflowError`로 방어 처리 확인됨) |
| P-03 | Performance | `risk_items` 복합 인덱스 — diff 외 파일 (migration 006, risk_item.py) |

---

## Priority Matrix

### P0 — 즉시 수정 (2건)
1. [SEC-01] [Critical/HIGH]: AttachmentOut file_path 서버 경로 노출 — schemas/attachment.py (100)
2. [P-01] [Critical/HIGH]: 50MB 파일 전체 메모리 적재 — routers/attachments.py (100)

### P1 — 스프린트 우선 (9건)
1. [R12-01] [Major/HIGH ★교차검증]: 053 downgrade RuntimeError 비표준 — 053 migration (80)
2. [P-04] [Major/HIGH]: 파일 삭제-DB 커밋 원자성 역전 — routers/attachments.py (70)
3. [R12-04] [Major/HIGH]: 054 downgrade milestoneKey 캐스팅 실패 — 054 migration (70)
4. [SEC-03] [Major/HIGH]: entity_id 입력 검증 누락 — routers/attachments.py (70)
5. [R11-1] [Major/HIGH]: Escape 키 닫기 없음 — MilestoneUploadPopover.tsx (70)
6. [R11-2] [Major/HIGH]: 포커스 이동/외부 클릭 닫기 없음 — MilestoneUploadPopover.tsx (70)
7. [R8-1] [Major/HIGH]: useCallback 의존성 불안정 — MilestoneUploadPopover.tsx (70)
8. [SEC-02] [Major/HIGH]: magic byte OLE2 등 미매핑 — routers/attachments.py (70)
9. [P-02] [Major/HIGH]: ORM 전체 로드 → func.count 교체 — workflow_engine.py (70)

### P2 — 개선 권장 (5건)
1. [R12-02] [Major/MEDIUM ⚠️]: 053 DDL/DML 순서 역전 — 053 migration (42)
2. [R7-1] [Major/MEDIUM ⚠️]: PhaseMilestone union narrowing 누락 — MilestoneUploadPopover.tsx (42)
3. [R11-3] [Major/MEDIUM ⚠️]: 비-uploadable 마일스톤 색상만 구분 — PipelineFlow.tsx (42)
4. [P-05] [Major/MEDIUM ⚠️]: 파일 교체 2단계 비원자적 — MilestoneUploadPopover.tsx (42)
5. [C-01] [Major/MEDIUM ⚠️]: audit_service entity_id UUID 전용 — audit_service.py (42)

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, general-purpose(FE/A11y), migration-validator, performance-profiler
- **Files scanned**: 14
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 2건 + Major/HIGH 9건 직접 Read 확인
- **Backend availability**: deal-mgmt(✓)

## 검증 투명성

### 검증 통계
- 에이전트 보고 총 이슈: 23건 (중복 포함)
- 교차 검증 후 병합: 3건 (R12-01=SEC-04=M-02)
- Scope 외 제외: 5건
- 최종 보고: 16건

### 제외 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| Scope 외 파일 | 3 | M-01(ralph), R12-03(mig-041), P-03(mig-006) |
| 기존 아키텍처 | 1 | C-02(spa 인메모리 세션) |
| 의도적 설계 | 1 | R3-01(MOU_SIGNED WorkflowError 방어) |
| 중복 병합 | 3 | R12-01=SEC-04=M-02 (downgrade RuntimeError) |

---

## 이전 리뷰(R1) 대비 진행 현황

**R1 리뷰(20260302_1303)에서 33건 발견 → 전부 수정 완료.**

R2 리뷰에서 발견된 16건은:
- **신규 이슈**: 10건 (R11-1/2, R8-1, R7-1, SEC-03, R12-04, R12-02, P-05, R11-3, C-01)
- **기존 미발견**: 6건 (SEC-01, P-01, P-04, R12-01, SEC-02, P-02)
