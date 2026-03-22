# Code Review — MA Log Unification (보충 통합 리뷰: R2, R9–R13)

> **Review Date**: 2026-03-11 12:47
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 마케팅 로그 + 미팅 로그 통합 — 미수행 6개 관점 보충
> **Method**: Review Gates + Verified Multi-Agent Review + Cross-Verification
> **Review Gates**: Backend(available) Agent-Filtering(3개 에이전트 호출)
> **Prior Reviews**: [1차 11건](20260311_1038_MA_Log_Unification_Code_Review.md), [2차 15건](20260311_1220_MA_Log_Unification_Supplementary_Review.md)

## 리뷰 범위

| 관점 | ID | 이번 리뷰 | 비고 |
|------|-----|----------|------|
| 코드 정합성 | R1 | — | 1차에서 수행 |
| 코드 완전성 | R2 | ✅ | |
| 데이터 무결성 | R3 | — | 2차에서 수행 |
| 복원력/에러 처리 | R4 | — | 2차에서 수행 |
| 운영 안정성 | R5 | — | 2차에서 수행 |
| 비즈니스/UX 정합성 | R6 | — | 2차에서 수행 |
| 보안 | R7 | — | 1차에서 수행 |
| 성능 | R8 | — | 1차에서 수행 |
| 접근성/UX 품질 | R9 | ✅ | |
| 테스트 커버리지 | R10 | ✅ | |
| 문서화/DX | R11 | ✅ | |
| 마이그레이션 안전성 | R12 | ✅ | |
| API 설계 | R13 | ✅ | |

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0 | — | — |
| Major | 0 | — | — |
| Moderate | 4 | HIGH: 4 | P2: 4 |
| Minor | 8 | HIGH: 6 / MEDIUM: 2 | P3: 8 |
| Info | 7 | — | P4: 7 |
| **Total** | **19** | HIGH: **10** / MEDIUM: **2** | P2: **4** / P3: **8** / P4: **7** |

**FP Prevention**: 가설 21건 검증, 2건 사전 거부 (거부율: 10%)
- R13-01: FALSE_POSITIVE — `exclude_unset=True`가 null vs absent 정확히 구분
- R11-02: FALSE_POSITIVE — 호환 레이어 의도적 사용, FE deprecation 마커 불필요

**Cross-Verification**: P2 이슈 5건 중 4건 CONFIRMED, 1건 FALSE_POSITIVE 제거

---

## Findings

### R2 — 코드 완전성 (Code Completeness)

**결과: 전 항목 PASS ✅**

| # | 체크 항목 | 상태 | 검증 근거 |
|---|----------|------|----------|
| 1 | MeetingLog 모델에 `marketing_stage` 컬럼 | ✅ | `meeting_log.py:31` — `Mapped[MarketingStage \| None]` |
| 2 | 스키마 3종(Create/Update/Out)에 필드 추가 | ✅ | `meeting_log.py` schemas — 모두 포함 |
| 3 | 마이그레이션 080 존재 + upgrade/downgrade | ✅ | `080_unify_marketing_meeting_logs.py` |
| 4 | 라우터에 `marketing_stage` 쿼리 파라미터 | ✅ | `meeting_logs.py:59` — `marketing_stage` 필터 |
| 5 | `buyer_marketing.py` 호환 레이어 | ✅ | 기존 API 유지, 내부 meeting_logs 테이블 조회 |
| 6 | FE 타입에 `marketing_stage` 추가 | ✅ | `meeting_log.ts` 인터페이스 |
| 7 | InlineLogInput → useCreateMeetingLog 전환 | ✅ | `InlineLogInput.tsx:8` |
| 8 | MeetingLogForm에 marketing_stage 셀렉트 | ✅ | `MeetingLogForm.tsx` — meeting_phase 조건부 표시 |
| 9 | BuyerMeetingTimeline에 stage 뱃지 | ✅ | `BuyerMeetingTimeline.tsx` — MarketingStageBadge 사용 |
| 10 | auto_advance_buyer_status 호출 | ✅ | `meeting_logs.py:97-101` — marketing_stage 존재 시 호출 |

---

### R9 — 접근성/UX 품질

#### [R9-01] MeetingLogForm 모달 aria-label 미지정 — [Minor/HIGH] — Priority: P3

- **파일**: `amic-platform/src/modules/ma/components/meetings/MeetingLogForm.tsx`
- **이슈**: 미팅 로그 모달에 `aria-label` 또는 `aria-labelledby`가 없어 스크린 리더가 모달 용도를 식별할 수 없음
- **우선순위 점수**: 20 × 1.0 = 20
- **권장**: `<Dialog>` 또는 모달 wrapper에 `aria-label="미팅 로그 작성"` 추가

#### [R9-03] BuyerMeetingTimeline 빈 상태 메시지 부재 — [Minor/HIGH] — Priority: P3

- **파일**: `amic-platform/src/modules/ma/components/buyers/BuyerMeetingTimeline.tsx`
- **이슈**: 미팅 로그가 0건일 때 빈 화면만 표시. "등록된 미팅 로그가 없습니다" 같은 안내 메시지 없음
- **우선순위 점수**: 20 × 1.0 = 20
- **권장**: `logs.length === 0` 조건에 빈 상태 UI 추가

#### [R9-04] Timeline 로딩 스켈레톤 부재 — [Minor/HIGH] — Priority: P3

- **파일**: `amic-platform/src/modules/ma/components/buyers/BuyerMeetingTimeline.tsx`
- **이슈**: `isLoading` 상태에서 로딩 인디케이터/스켈레톤 없이 빈 화면 표시
- **우선순위 점수**: 20 × 1.0 = 20
- **권장**: `isLoading` 조건에 Skeleton 또는 Spinner 컴포넌트 추가

#### [R9-05] MarketingGridCell → InlineLogInput `onCancel` 미전달 — [Minor/HIGH] — Priority: P3

- **파일**: `amic-platform/src/modules/ma/components/buyers/MarketingGridCell.tsx:67-73`
- **이슈**: `InlineLogInput`은 `onCancel?: () => void` 프롭을 정의하지만, `MarketingGridCell`이 전달하지 않음
- **교차 검증**: CONFIRMED — 단, 부모 `<td>`의 `onKeyDown` 이벤트 버블링으로 Escape가 기능적으로 동작함. 실질적 영향 미미.
- **우선순위 점수**: 20 × 1.0 = 20 (교차 검증에서 심각도 하향)
- **권장**: 명시적으로 `onCancel={() => setShowInput(false)}` 전달 (방어적 코딩)

#### [R9-06] LogListPopover 키보드 내비게이션 — [Minor/MEDIUM] — Priority: P3

- **파일**: `amic-platform/src/modules/ma/components/buyers/LogListPopover.tsx`
- **이슈**: 팝오버 내 로그 목록에서 키보드(Arrow Up/Down)로 항목 간 이동 불가
- **우선순위 점수**: 20 × 0.6 = 12
- **권장**: `role="listbox"` + Arrow key handler 추가 (접근성 개선)

#### [R9-02] InlineLogInput placeholder 안내 개선 — [Info]

- 현재 placeholder "간단히 기록..." → "예: NDA 체결 완료, Teaser 발송" 등 구체적 예시 제공 권장

#### [R9-07] MeetingLogForm 필수 필드 시각적 표시 — [Info]

- 필수 입력 필드(제목, 일자 등)에 `*` 마크나 시각적 강조 없음. UX 개선 권장

---

### R10 — 테스트 커버리지

#### [R10-01] 크로스 딜 매수자 인가 테스트 부재 — [Moderate/HIGH] — Priority: P2

- **파일**: `deal-mgmt/tests/test_meeting_logs.py`
- **이슈**: 모든 테스트가 단일 `transaction_id` 픽스처 사용. Deal A의 매수자가 Deal B에 미팅 로그를 생성할 수 없음을 검증하는 테스트 없음
- **교차 검증**: CONFIRMED
- **우선순위 점수**: 40 × 1.0 = 40
- **권장**: `test_create_meeting_log_cross_deal_forbidden()` 추가

#### [R10-02] auto_advance_buyer_status 통합 테스트 부재 — [Moderate/HIGH] — Priority: P2

- **파일**: `deal-mgmt/tests/test_meeting_logs.py`
- **이슈**: 미팅 로그 생성 시 `marketing_stage`가 있으면 `auto_advance_buyer_status`가 호출되는데, 이 통합 경로를 검증하는 테스트 없음
- **우선순위 점수**: 40 × 1.0 = 40
- **권장**: `test_create_meeting_log_with_marketing_stage_advances_buyer()` 추가

#### [R10-03] marketing_stage 필터 조회 테스트 부재 — [Minor/HIGH] — Priority: P3

- **파일**: `deal-mgmt/tests/test_meeting_logs.py`
- **이슈**: 목록 API의 `marketing_stage` 쿼리 파라미터 필터링 검증 테스트 없음
- **우선순위 점수**: 20 × 1.0 = 20
- **권장**: `test_list_meeting_logs_filter_by_marketing_stage()` 추가

#### [R10-04] 마이그레이션 080 데이터 무결성 테스트 — [Info]

- 마이그레이션 후 `buyer_marketing_logs` 건수 = `meeting_logs`의 `marketing_stage IS NOT NULL` 건수 검증 스크립트 권장

#### [R10-05] MeetingLogUpdate partial update 테스트 — [Info]

- `marketing_stage`만 PATCH 시 다른 필드 미변경 확인 테스트 권장

---

### R11 — 문서화/DX

#### [R11-01] 스키마 Field description 부재 — [Minor/HIGH] — Priority: P3

- **파일**: `deal-mgmt/app/schemas/meeting_log.py`
- **이슈**: `MeetingLogCreate`, `MeetingLogUpdate`의 필드에 `Field(description="...")` 미지정. Swagger/OpenAPI 자동 문서에 필드 설명 표시 안 됨
- **우선순위 점수**: 20 × 1.0 = 20
- **권장**: 주요 필드에 `Field(description="마케팅 단계 (MARKETING phase에서만 사용)")` 등 추가

#### ~~[R11-02] useMarketingLogs 훅 deprecated 미표시~~ — FALSE_POSITIVE

- **교차 검증**: 호환 레이어를 의도적으로 사용하는 활성 소비자. FE에서 deprecation 마커 불필요. 엔드포인트 URL도 올바르게 사용 중.

---

### R12 — 마이그레이션 안전성

#### [R12-01] Row-by-row INSERT 성능 — [Moderate/HIGH] — Priority: P2

- **파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py:74-116`
- **이슈**: `fetchall()` 후 Python `for` 루프로 개별 INSERT 실행. 대량 데이터(1000건+) 시 마이그레이션 소요 시간 급증
- **교차 검증**: CONFIRMED — UUID 생성 + 제목 변환이 per-row 로직이라 순수 `INSERT...SELECT` 불가. 단, PostgreSQL의 `gen_random_uuid()` + `concat()` 활용 시 단일 문으로 변환 가능
- **우선순위 점수**: 40 × 1.0 = 40
- **권장**: PostgreSQL 경로에서 `INSERT INTO meeting_logs SELECT gen_random_uuid(), ... FROM buyer_marketing_logs` 패턴으로 변환. 또는 `executemany()` 배치 활용

#### [R12-02] downgrade()에서 marketing_stage 데이터 보존 미고려 — [Minor/HIGH] — Priority: P3

- **파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`
- **이슈**: downgrade 시 `marketing_stage` 컬럼만 제거하고, 해당 데이터를 `buyer_marketing_logs`로 복원하지 않음. 주석으로 명시 권장
- **우선순위 점수**: 20 × 1.0 = 20
- **권장**: downgrade 함수에 "데이터 복원 불가" 주석 추가

#### [R12-03] SQLite 경로 enum 문자열 처리 — [Info]

- SQLite는 native enum 미지원. 문자열로 저장 시 대소문자 불일치 가능. 현재 코드는 올바르게 처리 중

#### [R12-04] 마이그레이션 인덱스 네이밍 — [Info]

- `ix_meeting_logs_buyer_stage` 인덱스명이 프로젝트 네이밍 규칙(`ix_{table}_{col1}_{col2}`)과 일치하는지 확인 권장

#### [R12-05] 원본 테이블 보존 문서화 — [Info]

- `buyer_marketing_logs` 테이블을 의도적으로 보존하는 이유를 마이그레이션 파일 docstring에 명시 권장

#### [R12-06] batch_size 파라미터 미활용 — [Minor/MEDIUM] — Priority: P3

- **파일**: `deal-mgmt/migrations/versions/080_unify_marketing_meeting_logs.py`
- **이슈**: 대량 마이그레이션 시 메모리 관리를 위한 `fetchmany(batch_size)` 미사용
- **우선순위 점수**: 20 × 0.6 = 12
- **권장**: `fetchmany(500)` + `while` 루프 패턴으로 변경

---

### R13 — API 설계

#### [R13-03] meeting_phase / marketing_stage 교차 검증 누락 — [Moderate/HIGH] — Priority: P2

- **파일**: `deal-mgmt/app/schemas/meeting_log.py:96-114` (`MeetingLogCreate`)
- **이슈**: `meeting_phase=NEGOTIATION`에 `marketing_stage=LOI_RECEIVED`를 보내도 Pydantic 스키마가 수용. 비즈니스 규칙상 `marketing_stage`는 `meeting_phase=MARKETING`일 때만 유효
- **교차 검증**: CONFIRMED
- **우선순위 점수**: 40 × 1.0 = 40
- **권장**: `@model_validator(mode="after")`로 `meeting_phase != MARKETING → marketing_stage must be None` 검증 추가

#### ~~[R13-01] PATCH null vs absent 혼동 위험~~ — FALSE_POSITIVE

- Pydantic `exclude_unset=True`가 JSON `null`(= "set to None")과 필드 미전송(= "not set")을 정확히 구분. 의도된 동작.

#### [R13-06] 호환 레이어 응답 형식 차이 — [Minor/MEDIUM] — Priority: P3

- **파일**: `deal-mgmt/app/routers/buyer_marketing.py`
- **이슈**: 호환 레이어의 응답이 원래 `BuyerMarketingLogOut`이 아닌 `MeetingLogOut` 기반. 필드명/구조 차이가 기존 FE 소비자에 영향 줄 수 있음
- **우선순위 점수**: 20 × 0.6 = 12
- **권장**: 호환 레이어에서 응답을 `BuyerMarketingLogOut` 형식으로 매핑하는 어댑터 추가, 또는 FE 훅이 새 형식을 직접 소비하도록 전환

---

## Priority Matrix

### P2 — 개선 권장 (점수: 40, 코드 품질/테스트 갭)

| # | ID | Severity/Confidence | Summary | Score |
|---|-----|---------------------|---------|-------|
| 1 | R13-03 | Moderate/HIGH | meeting_phase↔marketing_stage 교차 검증 누락 — `MeetingLogCreate` | 40 |
| 2 | R10-01 | Moderate/HIGH | 크로스 딜 매수자 인가 테스트 부재 | 40 |
| 3 | R10-02 | Moderate/HIGH | auto_advance 통합 테스트 부재 | 40 |
| 4 | R12-01 | Moderate/HIGH | 마이그레이션 080 row-by-row INSERT 성능 | 40 |

### P3 — 저우선 (점수: 12–20, 개선 가능)

| # | ID | Severity/Confidence | Summary | Score |
|---|-----|---------------------|---------|-------|
| 1 | R9-01 | Minor/HIGH | MeetingLogForm 모달 aria-label 미지정 | 20 |
| 2 | R9-03 | Minor/HIGH | BuyerMeetingTimeline 빈 상태 메시지 부재 | 20 |
| 3 | R9-04 | Minor/HIGH | Timeline 로딩 스켈레톤 부재 | 20 |
| 4 | R9-05 | Minor/HIGH | MarketingGridCell → InlineLogInput onCancel 미전달 | 20 |
| 5 | R10-03 | Minor/HIGH | marketing_stage 필터 조회 테스트 부재 | 20 |
| 6 | R11-01 | Minor/HIGH | 스키마 Field description 부재 | 20 |
| 7 | R12-02 | Minor/HIGH | downgrade() 데이터 복원 미고려 | 20 |
| 8 | R9-06 | Minor/MEDIUM | LogListPopover 키보드 내비게이션 | 12 |

### P4 — 참고 (Info)

| # | ID | Summary |
|---|-----|---------|
| 1 | R9-02 | InlineLogInput placeholder 안내 개선 |
| 2 | R9-07 | MeetingLogForm 필수 필드 시각적 표시 |
| 3 | R10-04 | 마이그레이션 080 데이터 무결성 테스트 |
| 4 | R10-05 | MeetingLogUpdate partial update 테스트 |
| 5 | R12-03 | SQLite enum 문자열 처리 |
| 6 | R12-04 | 마이그레이션 인덱스 네이밍 |
| 7 | R12-05 | 원본 테이블 보존 문서화 |

---

## Methodology

- **Agents**: Agent 1 (R2+R9), Agent 2 (R10+R11), Agent 3 (R12+R13) — 3개 병렬
- **Excluded Agents**: security-auditor, perf-auditor (1차 리뷰에서 수행)
- **Files scanned**: BE 5개 (meeting_log model/schema/router, buyer_marketing router, migration 080) + FE 7개 (타입, 훅, 컴포넌트 5종)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: P2 이슈 5건 대상, 4건 CONFIRMED, 1건 FP 제거

## 검증 투명성

### 검증 통계
- 검증한 가설: 21건
- 거부된 가설 (사전 제거): 2건
- 보고된 이슈: 19건 (Moderate 4 + Minor 8 + Info 7)
- 거부율: 10%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | R13-01: `exclude_unset=True`가 null/absent 정확히 구분 → Grep/Read 확인 |
| 설계 의도 | 1 | R11-02: 호환 레이어 의도적 사용 → 코드 주석 + BE deprecated 플래그 확인 |

---

## 3차 리뷰 통합 총괄

| 리뷰 | 날짜 | 관점 | 이슈 수 | 수정 완료 |
|------|------|------|---------|---------|
| 1차 | 03-11 10:38 | R1, R7, R8 + 코드 품질 | 11건 | 11건 ✅ |
| 2차 | 03-11 12:20 | R3, R4+R5, R6 | 15건 (Major 5, Moderate 5, Minor 5) | 10건 ✅ (Moderate까지) |
| **3차 (본 리뷰)** | **03-11 12:47** | **R2, R9–R13** | **19건 (Moderate 4, Minor 8, Info 7)** | **미수정** |
| **합계** | | **R1–R13 전체** | **45건** | **21건 수정 완료** |

> **결론**: 13개 관점 전체 리뷰 완료. Critical/Major 이슈 없음. P2 이슈 4건은 테스트 갭(R10-01, R10-02) + API 검증(R13-03) + 마이그레이션 성능(R12-01)으로, 현재 프로덕션 안정성에 즉각적 영향 없으나 중기적 개선 권장.
