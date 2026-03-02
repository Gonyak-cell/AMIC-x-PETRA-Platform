# Code Review — MA 워크플로우 단계 UI 개선 (13개 관점 통합)

> **Review Date**: 2026-03-02 13:03
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MOU_SIGNED 단계 제거 (9→8단계) + 마일스톤 PDF 업로드 + PipelineFlow 동적 사이징
> **Method**: Review Gates + Quality Gates + 13-Perspective Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) ruff(PASS) build(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(5개 에이전트 호출)
> **Agents**: R2(보안심층) R3(데이터정합성) R4(프로덕션복원력) R5(운영&코드건강성) R6(비즈니스&UX)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2                | P0: 2               |
| Major    | 11    | HIGH: 10 / MEDIUM: 1  | P1: 10 / P2: 1      |
| Moderate | 10    | HIGH: 7 / MEDIUM: 3   | P2: 7 / P3: 3       |
| Minor    | 10    | HIGH: 7 / MEDIUM: 3   | P3: 10              |
| **Total**| **33**| HIGH: **26** / MEDIUM: **7** | P0: **2** / P1: **10** / P2: **8** / P3: **13** |

**Cross-Verification**: Critical 2건 모두 교차 검증 완료 (4/5 에이전트 동일 발견)
**Plan Coverage**: 12/12 항목 구현 완료 (100%)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 기능 차단/데이터 무결성)

#### [P0-1] entity_id UUID 타입 불일치 — 마일스톤 업로드 기능 전체 불동작 — [Critical/HIGH] (점수: 110, 교차검증 4/5)

- **위치**: `MilestoneUploadPopover.tsx:44-45` + `attachments.py:75,133` + `attachment.py:32`
- **카테고리**: 안정성(§4) - 모듈 간 계약
- **13개 관점**: R3(데이터흐름), R4(에러처리), R5(배포안전성), R2(보안)

**근거**:
```python
# attachment.py:32 — DB 모델
entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)

# attachments.py:133 — POST 업로드
parsed_entity_id = _parse_uuid(entity_id, "entity_id") if entity_id else None

# attachments.py:75 — GET 목록조회
parsed_eid = _parse_uuid(entity_id, "entity_id")
```
```typescript
// MilestoneUploadPopover.tsx:44-45 — 프론트엔드
entityId: milestone.milestoneKey,  // "MOU_SIGNED" 또는 "SIGNING" — UUID 아님
```

**영향**: milestoneKey("MOU_SIGNED"/"SIGNING")는 유효한 UUID 형식이 아니므로 `_parse_uuid()`에서 `ValueError` → HTTP 400. 업로드(POST)와 조회(GET) 모두 실패. **마일스톤 업로드 기능이 100% 동작 불가.**

**수정 방향**:
- 옵션 A (권장): `Attachment.entity_id`를 `String(50)`으로 변경 + 마이그레이션 추가
- 옵션 B: `_parse_uuid` 대신 entity_type이 MILESTONE일 때 문자열 허용 분기 추가
- 옵션 C: milestoneKey를 고정 UUID로 변환 (uuid5 namespace)

---

#### [P0-2] MOU_SIGNED 거래에서 workflow_engine KeyError — [Critical/HIGH] (점수: 110, 교차검증 3/5)

- **위치**: `workflow_engine.py:88,130,196`
- **카테고리**: 안정성(§4) - 에러 복원력
- **13개 관점**: R3(데이터흐름), R4(에러처리), R5(배포안전성)

**근거**:
```python
# workflow_engine.py:88 — get_phase_completion
idx = _PHASE_INDEX[txn.phase]  # MOU_SIGNED면 KeyError → 500

# workflow_engine.py:130 — advance_phase
from_idx = _PHASE_INDEX[txn.phase]  # 동일
```

**영향**: 마이그레이션 053이 배포되기 전에 새 코드가 먼저 실행되면, DB에 남아있는 MOU_SIGNED 거래에서 `KeyError` → 500. deploy.yml에서 마이그레이션이 먼저 실행되므로 정상 배포 시에는 발생하지 않으나, 방어 코드 부재.

**수정 방향**: `_PHASE_INDEX.get(txn.phase)` + None 시 `WorkflowError("지원되지 않는 단계입니다")` 반환

---

### P1 — 스프린트 우선 (점수: 60-89, 보안/안정성)

| # | ID | 심각도/신뢰도 | 관점 | 파일 | 이슈 요약 | 점수 |
|---|-----|-------------|------|------|---------|------|
| 3 | S-01 | Major/HIGH | R2 보안 | `attachments.py:96` | upload_attachment에 `check_client_deal_access` 누락 — 딜 격리 위반 | 70 |
| 4 | S-02 | Major/HIGH | R2 보안 | `attachments.py:116,142` | 서버 MIME 타입 검증 없음 — 확장자만 검증, 매직 바이트 미확인 | 70 |
| 5 | S-03 | Major/HIGH | R2 보안 | `attachments.py:86` | 파일 업로드 Rate Limiting 미적용 — DoS 가능 | 70 |
| 6 | M-01 | Major/HIGH | R4+R6 복원력 | `MilestoneUploadPopover.tsx:62-68` | handleReplace 삭제-업로드 비원자성 — 법적 문서 유실 위험 | 80 |
| 7 | C-03 | Major/HIGH | R5 운영 | `MilestoneUploadPopover.tsx:27-31` | 상위에서 이미 조회한 마일스톤 첨부파일을 중복 API 호출 | 70 |
| 8 | P-01 | Major/HIGH | R5 성능 | `MilestoneUploadPopover.tsx:49` | useCallback 의존성에 upload 뮤테이션 객체 — stale closure 위험 | 70 |
| 9 | T-01 | Major/HIGH | R6 테스트 | `test_workflow.py:194-200` | 멀티 전진 테스트가 CLOSING/POST_CLOSING 미포함 | 70 |
| 10 | T-02 | Major/HIGH | R6 테스트 | (미존재) | 마일스톤 업로드 기능 테스트 전무 (FE/BE 모두) | 70 |
| 11 | A-01 | Major/HIGH | R6 접근성 | `PipelineFlow.tsx:149-200` | MilestoneMarker aria-label 누락 | 70 |
| 12 | A-02 | Major/HIGH | R6 접근성 | `MilestoneUploadPopover.tsx:124-160` | 드래그앤드롭 영역 키보드/스크린리더 접근성 부재 | 70 |

---

### P2 — 개선 권장 (점수: 30-59, 코드 품질/UX)

| # | ID | 심각도/신뢰도 | 관점 | 파일 | 이슈 요약 | 점수 |
|---|-----|-------------|------|------|---------|------|
| 13 | M-03 | Major/MEDIUM ⚠️ | R4 복원력 | `useAttachments.ts:80-82` | onError에서 에러 상세 미전달 — 디버깅 불가 | 42 |
| 14 | I-02 | Major/MEDIUM ⚠️ | R3 데이터 | `053_remove_mou_signed_phase.py:22-34` | Race condition — 마이그레이션 중 신규 MOU_SIGNED 삽입 가능 | 42 |
| 15 | I-03 | Moderate/HIGH | R3 데이터 | `053_remove_mou_signed_phase.py:37-44` | downgrade() RuntimeError — 046 패턴과 비대칭 | 40 |
| 16 | MOD-01 | Moderate/HIGH | R4 복원력 | `exceptions.py:104-112` | WorkflowError 핸들러에 request_id 미포함 | 40 |
| 17 | P-02 | Moderate/HIGH | R5 성능 | `PipelineFlow.tsx:52-54` | PHASE_MILESTONES.find() 매 렌더링 실행 — useMemo 권장 | 40 |
| 18 | A-09 | Moderate/HIGH | R6 접근성 | `PipelineFlow.tsx:59-62` | Phase 버튼 aria-label/aria-current 부재 | 40 |
| 19 | A-06 | Moderate/HIGH | R6 UX | `MilestoneUploadPopover.tsx:38-41` | PDF 외 파일 드래그 시 사용자 피드백 없이 무시 | 40 |
| 20 | D-05 | Moderate/HIGH | R6 도메인 | `TransactionWorkspacePage.tsx` | MOU_SIGNED deprecated enum — FE에서 자동 매핑 방어 로직 부재 | 40 |

---

### P3 — 저우선 (점수: <30, 개선 가능)

| # | ID | 심각도/신뢰도 | 관점 | 이슈 요약 | 점수 |
|---|-----|-------------|------|---------|------|
| 21 | MOD-03 | Moderate/MEDIUM | R4 | 파일 저장 후 DB 실패 시 고아 파일 | 24 |
| 22 | I-04 | Moderate/MEDIUM | R3 | MOU_SIGNED enum 잔존 — 향후 재활성화 위험 | 24 |
| 23 | A-05 | Moderate/MEDIUM | R6 | 팝오버 absolute 위치 — 뷰포트 이탈 가능성 | 24 |
| 24 | A-04 | Major/HIGH | R6 | 마일스톤 마커 터치 영역 44px 미달 (WCAG AA 24px 충족) | 20* |
| 25 | S-08 | Minor/HIGH | R2 | RuntimeError가 Alembic 롤백 CLI 차단 | 20 |
| 26 | S-09 | Minor/HIGH | R2 | WorkflowError에 내부 리스크 제목 노출 | 20 |
| 27 | MIN-02 | Minor/MEDIUM | R4 | MOU_SIGNED 전환 시도 거부 테스트 없음 | 12 |
| 28 | MIN-01 | Minor/MEDIUM | R4 | 클라이언트 파일 크기 검증 없음 (50MB 서버 거부) | 12 |
| 29 | A-07 | Minor/HIGH | R6 | 팝오버 닫기 버튼 aria-label 누락 | 20 |
| 30 | P-03 | Minor/HIGH | R5 | useDynamicSizing의 useMemo 빈 의존성 — 효과 없음 | 20 |
| 31 | C-02 | Minor/MEDIUM | R6 | MilestoneMarker 조건부 렌더링 6경로 분기 | 12 |
| 32 | C-05 | Minor/HIGH | R6 | PhaseMilestone 조건부 필수 필드 — discriminated union 권장 | 20 |
| 33 | A-08 | Minor/MEDIUM | R6 | 반응형 소형 화면 대응 미흡 (11요소 일렬 배치) | 12 |

\* A-04: Apple HIG/Material 44px 미달이나 WCAG AA 24px 충족. 기능상 영향 낮아 P3 분류.

---

## §6 최초 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | Alembic 마이그레이션 (MOU_SIGNED → MAIN_DUE_DILIGENCE) | ✅ | `migrations/053_remove_mou_signed_phase.py` (번호 052→053 변경) |
| 2 | AttachmentEntityType에 MILESTONE 추가 | ✅ | `enums.py:770` |
| 3 | 워크플로우 엔진 _PHASE_ORDER에서 MOU_SIGNED 제거 | ✅ | `workflow_engine.py:37-46` 8단계 |
| 4 | 워크플로우 라우터 독스트링 "8단계" 수정 | ✅ | `workflow.py:1` |
| 5 | 테스트 업데이트 (MOU_SIGNED 제거) | ✅ | `test_workflow.py`, `e2e_docker.py` |
| 6 | PHASE_CONFIG에서 MOU_SIGNED 제거 + order 재번호 | ✅ | `constants.ts:761-818` |
| 7 | PHASE_TAB_MAP, PHASE_VISIBLE_TABS deprecated 처리 | ✅ | `constants.ts:821-851` |
| 8 | PHASE_MILESTONES 확장 (uploadable, documentLabel, milestoneKey) | ✅ | `constants.ts:875-902` |
| 9 | PipelineFlow 동적 사이징 + 마일스톤 클릭 | ✅ | `PipelineFlow.tsx:20-202` |
| 10 | MilestoneUploadPopover 신규 생성 | ✅ | `MilestoneUploadPopover.tsx:1-166` |
| 11 | TransactionWorkspacePage 마일스톤 연동 | ✅ | `TransactionWorkspacePage.tsx:477-497` |
| 12 | TypeScript 타입 MOU_SIGNED 유지 (deprecated 주석) | ✅ | `transaction.ts:8` |

**구현율: 12/12 (100%)**

---

## §7 품질 게이트 상태

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | §1 타입 [자동 검증됨] |
| ruff check + format | ✅ PASS | §1 린트 [자동 검증됨] |
| vite build | ✅ PASS | §2 빌드 [자동 검증됨] |

---

## Methodology

- **Agents**: R2(backend-security-reviewer), R3(migration-validator), R4(python-code-reviewer), R5(performance-profiler), R6(general-purpose)
- **Files scanned**: 17 (FE 9 + BE 8)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 2건 → 2건 CONFIRMED (4/5, 3/5 에이전트)
- **13 Perspectives**: 보안, 위협모델링, 데이터흐름, API계약, 에러처리, 관찰가능성, 성능, 배포안전성, 의존성, 도메인로직, 테스트품질, 인지복잡도, 접근성
