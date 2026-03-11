# Code Review — MA MeetingType + 미팅 기능 강화 (13관점 통합)

> **Review Date**: 2026-03-11 18:23
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 미팅 기능 강화 — MeetingType enum, 삭제/상세/참석자/유형 기능 (BE 4 + FE 6 = 10개 파일)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) build(PASS)
> **Review Gates**: Backend(available) Agent-Filtering(4개 에이전트 호출, api-auditor 1개 제외)
> **Plan**: `robust-wandering-wolf.md` (마케팅 타임라인 접촉 기록 기능 강화)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P0: 1 |
| Major    | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P1: 1 |
| Moderate | 5     | HIGH: 5 / MEDIUM: 0 / LOW: 0 | P1: 4 / P2: 1 |
| Minor    | 6     | HIGH: 2 / MEDIUM: 3 / LOW: 1 | P2: 2 / P3: 4 |
| Info     | 1     | HIGH: 0 / MEDIUM: 0 / LOW: 1 | P3: 1 |
| **Total**| **14** | HIGH: **9** / MEDIUM: **3** / LOW: **2** | P0: **1** / P1: **5** / P2: **3** / P3: **5** |

**FP Prevention**: 가설 53건 검증, 35건 사전 거부 (거부율: 66%) | 교차 검증 3건 수행 (1건 심각도 하향)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 3건 하향 조정
- LOW 신뢰도 이슈 2건 하향 조정

---

## Findings

### P0 — 즉시 수정 (보안/접근성 필수)

#### [A11Y-01] TimelineMeetingCard: 클릭 가능한 `<div>`에 키보드 접근 불가 — [Critical/HIGH] — Priority: P0 (점수: 100+15=115, verifier 확인)

**위치**: `TimelineMeetingCard.tsx:30-33`

```tsx
<div
  className="... cursor-pointer"
  role="listitem"
  onClick={() => setExpanded((v) => !v)}
>
```

**문제**: `<div>`에 `onClick`만 있고 `tabIndex`, `onKeyDown`, `role="button"`, `aria-expanded`가 모두 없음. 키보드 사용자는 카드 포커스/조작 불가.

**WCAG 위반**: 2.1.1 Keyboard (A), 4.1.2 Name, Role, Value (A)

**교차 검증**: CONFIRMED (verifier 직접 확인)

**권장 수정**:
```tsx
<div
  className="... cursor-pointer"
  role="button"
  tabIndex={0}
  aria-expanded={expanded}
  aria-label={`${log.title} 미팅 상세 ${expanded ? '접기' : '펼치기'}`}
  onClick={() => setExpanded((v) => !v)}
  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded((v) => !v); } }}
>
```

---

### P1 — 스프린트 우선 (안정성/보안/접근성)

#### [SEC-01] list_action_items에서 check_client_deal_access 미호출 — [Major/HIGH] — Priority: P1 (점수: 70+15=85, verifier 확인)

**위치**: `deal-mgmt/app/routers/meeting_logs.py:399-410`

```python
async def list_action_items(
    txn_id: uuid.UUID,
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    claims: JWTClaims = Depends(get_jwt_claims),  # 인증만
):
    await _get_log_or_404(db, txn_id, log_id)  # check_client_deal_access 없음
```

**문제**: 동일 라우터 6개 엔드포인트는 모두 `check_client_deal_access` 호출하지만 이 엔드포인트만 누락. CLIENT 역할 사용자가 비배정 딜의 액션아이템 열람 가능.

**교차 검증**: CONFIRMED (verifier 직접 확인 — 라인 60, 97, 132, 159, 225, 283에서 호출하지만 399에서 누락)

**권장 수정**: 함수 첫 줄에 `await check_client_deal_access(db, txn_id, claims)` 추가.

---

#### [A11Y-03] TimelineMeetingCard: 확장 상태를 스크린리더에 전달하지 않음 — [Moderate/HIGH] — Priority: P1 (점수: 40)

**위치**: `TimelineMeetingCard.tsx:30-34, 64-68`

`aria-expanded` 없이 ChevronUp/Down 아이콘만으로 상태 표시. 스크린리더 사용자 상태 인식 불가.

**WCAG 위반**: 4.1.2 (A), 1.3.1 (A)

> ℹ️ A11Y-01 수정 시 `aria-expanded` 추가로 함께 해결됨.

---

#### [A11Y-04] MeetingLogForm: textarea에 `id`/`htmlFor` 연결 없음 — [Moderate/HIGH] — Priority: P1 (점수: 40)

**위치**: `MeetingLogForm.tsx:211-232`

```tsx
<label className="block text-sm font-medium text-text-dark mb-1">요약</label>
<textarea ... placeholder="미팅 요약" />
```

"요약", "회의록" textarea 2개 모두 `<label>`과 `id`/`htmlFor` 미연결. 같은 파일의 `<Input>` 컴포넌트는 내부에서 자동 연결하지만 native `<textarea>`에는 수동 연결 필요.

---

#### [A11Y-05] MeetingLogForm: 참석자 입력 필드에 aria-label 없음 — [Moderate/HIGH] — Priority: P1 (점수: 40)

**위치**: `MeetingLogForm.tsx:261-278`

```tsx
<input placeholder="이름" ... />  <!-- aria-label 없음 -->
<input placeholder="소속" ... />  <!-- aria-label 없음 -->
```

동적 참석자 행의 이름/소속 input에 접근 가능한 이름 미제공. 비교: `InlineMeetingForm.tsx`의 모든 input은 `aria-label` 명시.

---

#### [A11Y-02] TimelineMeetingCard: 삭제 버튼 터치 타겟 미달 — [Moderate/HIGH] — Priority: P1 (점수: 40)

**위치**: `TimelineMeetingCard.tsx:70-82`

`p-0.5`(2px) + 12px 아이콘 = ~16x16px. WCAG 2.5.8 최소 24x24px 미달. 비교: 같은 뷰의 상세보기 버튼은 `min-w-[44px] min-h-[44px]`.

---

### P2 — 개선 권장 (코드 품질/UX)

#### [SEC-02] 자유 텍스트 필드에 BE max_length 미설정 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**위치**: `deal-mgmt/app/schemas/meeting_log.py:108-109, 132-135`

`minutes`, `summary`, `location` 등에 `max_length` 없음. `title`(max_length=300)은 있으나 나머지 자유 텍스트에는 제한 없어 대용량 데이터 삽입 가능. FE `InlineMeetingForm`은 `maxLength=500` 있으나 `MeetingLogForm` textarea에는 없음.

---

#### [A11Y-06] MeetingLogForm: 참석자 삭제 버튼 aria-label 행 구분 불가 — [Minor/MEDIUM] — Priority: P2 (점수: 12)

**위치**: `MeetingLogForm.tsx:279-285`

모든 삭제 버튼의 `aria-label="참석자 삭제"`가 동일. 동적 구분 필요 (예: `aria-label={`${att.name || `참석자 ${idx+1}`} 삭제`}`).

---

#### [A11Y-07] InlineMeetingForm: "미팅 추가" 버튼 터치 타겟 미달 — [Minor/MEDIUM] — Priority: P2 (점수: 12)

**위치**: `InlineMeetingForm.tsx:77-85`

`py-1`(4px) + 11px 텍스트 ≈ 19px 높이. 24px 최소 기준 미달.

---

### P3 — 저우선 (기술부채/개선 가능)

#### [CR-MEET-01] 마이그레이션 `sa.String(50)` vs 모델 `Enum(MeetingType)` 타입 불일치 — [Minor/HIGH ⚠️] — Priority: P3 (점수: 20, 교차검증→DESIGN_RISK 하향)

**위치**: `deal-mgmt/migrations/versions/081_add_meeting_type.py:22` vs `deal-mgmt/app/models/meeting_log.py:48-52`

프로젝트 CI Guard 2 규칙에 의한 의도적 `sa.String(50)` 사용. SQLite CI 호환을 위한 설계 결정이나, 모델의 `Enum(MeetingType)`과 불일치하는 기술부채. 다른 마이그레이션(079, 080)도 동일 패턴 사용 확인.

---

#### [TC-01] MeetingLogUpdate FE에 `attachments` 필드 누락 — [Minor/HIGH] — Priority: P3 (점수: 20)

**위치**: `meeting_log.ts:152-168` vs `meeting_log.py:131-149`

BE `MeetingLogUpdate`에 `attachments: list[dict] | None` 있으나 FE에 없음. 현재 attachments UI 미구현이므로 즉시 영향 없음.

---

#### [TC-02] MeetingLogForm meeting_type null→"MEETING" fallback — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**위치**: `MeetingLogForm.tsx:44-45`

`existing?.meeting_type ?? "MEETING"` — DB에 null인 기존 로그 수정 시 "MEETING"으로 의도치 않게 변경될 수 있음.

---

#### [SEC-04] MeetingLogUpdate에서 marketing_stage 변경 시 phase 검증 부재 — [Minor/MEDIUM] — Priority: P3 (점수: 12)

**위치**: `meeting_log.py:131-149`

Create에는 `@model_validator`로 `meeting_phase=MARKETING`일 때만 `marketing_stage` 허용하지만 Update에는 검증 없음.

---

#### [SEC-03] window.confirm 삭제 확인 — [Minor/HIGH] — Priority: P3 (점수: 20)

**위치**: `TimelineMeetingCard.tsx:74`

네이티브 `window.confirm` 사용. Modal 컴포넌트 기반 확인 다이얼로그로 교체 권장 (일관성).

---

#### [TC-03] MeetingLogForm 상태 변수 `string` 타입 — [Info/LOW] — Priority: P3 (점수: 6)

**위치**: `MeetingLogForm.tsx:41-47`

`useState<string>` + `as MeetingType` 캐스팅. Select 컴포넌트 제약으로 인한 것이며, UI에서 유효값만 선택 가능하여 실질 위험 없음.

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|-----------|
| 1 | BE: MeetingType enum 추가 | ✅ | `enums.py:541-549` — 6개 값 |
| 2 | BE: meeting_log 모델에 meeting_type 컬럼 | ✅ | `meeting_log.py:48-52` — nullable=True |
| 3 | BE: 3개 스키마에 meeting_type 필드 | ✅ | `schemas/meeting_log.py:75,106,137` |
| 4 | BE: Alembic 081 마이그레이션 | ✅ | `081_add_meeting_type.py` — String(50), downgrade 구현 |
| 5 | FE: MeetingType 타입 + 상수 | ✅ | `meeting_log.ts` + `meeting.ts` — 6개 값 BE 완전 동기화 |
| 6 | FE: TimelineMeetingCard 삭제+상세+유형뱃지 | ✅ | 삭제(70-82), 확장패널(90-116), 유형뱃지(44-48) |
| 7 | FE: MarketingTimelineView 삭제훅 연결 | ✅ | `useDeleteMeetingLog` + props 전달 |
| 8 | FE: InlineMeetingForm 유형+참석자 | ✅ | meetingType 드롭다운(130-140) + attendeesInput(156-167) |
| 9 | FE: MeetingLogForm 유형+참석자 동적폼 | ✅ | 3-column grid(177-196) + 참석자 폼(236-291) |
| 10 | 용어 변경 제거 (Step 5) | ✅ | 사용자 지시에 따라 제거됨 |

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | §1 타입 정합성 자동 검증됨 |
| eslint | ✅ PASS | §1 코드 정합성 자동 검증됨 |
| ruff check | ✅ PASS | §1 BE 코드 정합성 자동 검증됨 |
| vite build | ✅ PASS | §2 빌드 완전성 자동 검증됨 |

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
1. [A11Y-01] [Critical/HIGH]: TimelineMeetingCard 키보드 접근 불가 — `TimelineMeetingCard.tsx:30` (점수: 115)

### P1 — 스프린트 우선 (점수: 60-89)
1. [SEC-01] [Major/HIGH]: list_action_items 권한 검증 누락 — `meeting_logs.py:399` (점수: 85)
2. [A11Y-03] [Moderate/HIGH]: 확장 상태 aria-expanded 누락 — `TimelineMeetingCard.tsx` (점수: 40)
3. [A11Y-04] [Moderate/HIGH]: textarea label 연결 누락 — `MeetingLogForm.tsx:211` (점수: 40)
4. [A11Y-05] [Moderate/HIGH]: 참석자 input aria-label 누락 — `MeetingLogForm.tsx:261` (점수: 40)
5. [A11Y-02] [Moderate/HIGH]: 삭제 버튼 터치 타겟 16px — `TimelineMeetingCard.tsx:70` (점수: 40)

### P2 — 개선 권장 (점수: 30-59)
1. [SEC-02] [Moderate/HIGH]: BE 자유 텍스트 max_length 미설정 — `meeting_log.py` (점수: 40)
2. [A11Y-06] [Minor/MEDIUM]: 참석자 삭제 버튼 동적 label — `MeetingLogForm.tsx:283` (점수: 12)
3. [A11Y-07] [Minor/MEDIUM]: 미팅 추가 버튼 터치 타겟 — `InlineMeetingForm.tsx:77` (점수: 12)

### P3 — 저우선 (점수: <30)
1. [CR-MEET-01] [Minor/HIGH ⚠️]: 마이그레이션 String vs Enum 기술부채 (점수: 20, DESIGN_RISK)
2. [TC-01] [Minor/HIGH]: FE attachments 필드 누락 (점수: 20)
3. [SEC-03] [Minor/HIGH]: window.confirm → Modal 교체 (점수: 20)
4. [TC-02] [Minor/MEDIUM]: null→"MEETING" fallback (점수: 12)
5. [SEC-04] [Minor/MEDIUM]: Update phase 검증 부재 (점수: 12)

---

## Methodology

- **Agents**: code-reviewer, type-checker, security-auditor, a11y-auditor
- **Excluded Agents**: api-auditor (리뷰 대상에 라우터 신규 생성 없음)
- **Files scanned**: 10개 (FE 6, BE 4)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 1 + Major 1 + Important 1 = 3건 검증 (2건 CONFIRMED, 1건 DESIGN_RISK)
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 53건
- 거부된 가설 (사전 제거): 35건
- 보고된 이슈: 14건 (+ SEC-05 데이터품질 미보고)
- 거부율: 66%

### 에이전트별 가설 검증 현황

| 에이전트 | 검증 가설 | 보고 이슈 | 거부 가설 |
|---------|----------|----------|----------|
| code-reviewer | 12 | 2 | 9 |
| type-checker | 12 | 3 | 9 |
| security-auditor | 14 | 5 | 9 |
| a11y-auditor | 15 | 7 | 8 |

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 25 | BE↔FE enum 6개 값 완벽 일치, Modal 포커스트랩 구현 확인 |
| 의도적 설계 | 4 | CI Guard 2 String(50) 사용, MEETING_TYPE_LABEL 분리 |
| 이미 구현됨 | 3 | InlineMeetingForm aria-label, Modal aria-labelledby |
| 범위 외 | 2 | CORS 앱 레벨 관리, JWT 환경변수 로드 |
| 오판 | 1 | InlineMeetingForm select 캐스팅 안전성 |

---

## 잘 된 점

1. **BE↔FE 타입 동기화 완벽**: MeetingType 6개 값 양쪽 완전 일치
2. **N+1 쿼리 방지**: 트랜잭션 전체 미팅 1회 fetch + `useMemo` 그룹핑
3. **마이그레이션 downgrade 구현**: 롤백 가능한 마이그레이션
4. **에러 상태 UI 처리**: `isError`, `isPending` 상태 모두 사용자에게 표시
5. **InlineMeetingForm 접근성 우수**: 모든 input에 `aria-label`, `maxLength`, Escape 키 처리
