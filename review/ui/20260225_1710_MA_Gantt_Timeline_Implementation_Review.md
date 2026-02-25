# M&A 딜 전용 간트 타임라인 — 구현 리뷰

> 2026-02-25 17:10 작성

## 구현 요약

사이드바 "타임라인" 탭을 단순 활동 로그에서 **딜 전용 간트 타임라인**으로 교체.

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `deal-mgmt/app/schemas/timeline.py` | `PhaseBar`, `GanttMilestone`, `GanttResponse` 스키마 추가 |
| `deal-mgmt/app/routers/timeline.py` | `GET /transactions/{txn_id}/timeline/gantt` 엔드포인트 추가 |
| `amic-platform/src/modules/ma/components/GanttTimeline.tsx` | **신규** — 간트 차트 컴포넌트 |
| `amic-platform/src/modules/ma/types/timeline.ts` | `GanttPhaseBar`, `GanttMilestone`, `GanttResponse` 타입 추가 |
| `amic-platform/src/modules/ma/hooks/useTransactions.ts` | `useGanttTimeline` hook 추가 |
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` | timeline 탭 content를 GanttTimeline + 접을 수 있는 활동 로그로 교체 |

### 기능

- 7개 phase를 수평 바로 시각화 (완료=green, 진행 중=blue+pulse, 예정=gray)
- 오늘 날짜 파란 세로선 + 목표완료일 빨간 점선
- 마일스톤 다이아몬드 마커 (DOCUMENT_SIGNED, DEADLINE, CUSTOM, MEETING)
- 호버 시 툴팁 (phase 기간, 소요일수)
- 하단 7칸 그리드로 phase별 소요일수 요약
- 기존 활동 로그를 접을 수 있는 `<details>` 섹션으로 유지

---

## 코드 리뷰 결과

### PASS

| 항목 | 검증 결과 |
|------|----------|
| **라우트 충돌** | `/gantt`은 FastAPI에서 `/{event_id}` 앞에 매칭됨 ✅ |
| **PHASE_TRANSITION 파싱** | `workflow_engine.py:156`의 `f"{from_phase.value} → {to_phase.value}"` = `timeline.py:134`의 `split(" → ")` 정확히 일치 ✅ |
| **백엔드/프론트엔드 타입 일치** | PhaseBar, GanttMilestone, GanttResponse 구조 동일 ✅ |
| **txn.created_at 안전성** | TimestampMixin 필수 필드 ✅ |
| **txn.phase Enum 안전성** | TransactionPhase 필수 Enum, 디폴트 idx=0 폴백 ✅ |
| **import/hook 체인** | `useGanttTimeline` → `GanttTimeline` → `TransactionWorkspacePage` 연결 정상 ✅ |
| **탭 접근 경로** | 사이드바 Tools (MA_TOOLS_NAV) + CLOSING phase 탭 모두 접근 가능 ✅ |
| **Tailwind `text-negative`** | `negative: "#BC2C1A"` 정의됨 → `text-negative` 유효 ✅ |
| **Tailwind `text-text-muted`** | `"text-muted": "#9CA3AF"` 정의됨 → `text-text-muted` 유효 ✅ |
| **tsc --noEmit** | 에러 없음 ✅ |
| **vite build** | 빌드 성공 (17.25s) ✅ |

### FAIL → 수정 완료

| 문제 | 수정 내용 |
|------|----------|
| **타입 중복 정의 (P1)** | `GanttTimeline.tsx`에서 자체 `PhaseBar`/`GanttMilestone`/`GanttData` 삭제 → `timeline.ts`에서 `GanttResponse`/`GanttPhaseBar`/`GanttMilestone` import |
| **`text-text-primary` 미정의 (P2)** | `GanttTimeline.tsx:192`의 `text-text-primary` → `text-text-dark`로 변경 (tailwind.config.js에 정의된 색상) |

### 허위 리뷰 검증

초기 자동 리뷰에서 다음이 **CRITICAL**로 잘못 리포트됨:

| 잘못 리포트된 항목 | 실제 검증 결과 |
|-------------------|---------------|
| `text-negative` 미정의 | `negative: "#BC2C1A"` 정의됨 → Tailwind이 `text-negative` 생성 ✅ |
| `text-text-muted` 미정의 | `"text-muted": "#9CA3AF"` 정의됨 → `text-text-muted` 유효 ✅ |
| `text-text-primary` 미정의 | 실제 미정의이나, 코드베이스 전체 49곳(11파일)에서 사용 중인 **기존 이슈** — GanttTimeline 고유 문제가 아님 |

---

## 아키텍처 노트

### 백엔드 데이터 소스
- Phase 시작일: `DealTimeline` 테이블의 `PHASE_TRANSITION` 이벤트 `event_date`에서 역산
- ENGAGEMENT 시작일: `transaction.created_at`
- 현재 phase: 종료일 없음 (진행 중)
- 향후 phase: start/end 모두 null (예정)

### 프론트엔드 레이아웃
- 커스텀 HTML/CSS 기반 (recharts 미사용 — 간트 차트에 부적합)
- 퍼센트 기반 위치 계산 (`toX = dayOffset / totalDays * 100%`)
- 최소 700px 너비, 수평 스크롤 지원
