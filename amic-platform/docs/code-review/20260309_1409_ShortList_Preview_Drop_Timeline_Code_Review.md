# Code Review — Short-List Preview (Drop 상태 관리 + 수직 타임라인)

> **Review Date**: 2026-03-09 14:09
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `amic-platform/preview-shortlist-showcase.html` (1050줄, 단일 HTML 프리뷰 파일)
> **Method**: Review Gates + Verified Multi-Agent Review + 13-Perspective Analysis (R2~R6)
> **Quality Gates**: N/A (프리뷰 HTML — tsc/eslint/vitest/build 대상 아님)
> **Review Gates**: Backend(N/A) Agent-Filtering(단일 파일 프론트엔드 프리뷰)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 2     | HIGH: 1 / MEDIUM: 1 | P1: 1 / P2: 1 |
| Moderate | 5     | HIGH: 3 / MEDIUM: 2 | P2: 3 / P3: 2 |
| Minor    | 4     | HIGH: 2 / MEDIUM: 2 | P2: 1 / P3: 3 |
| **Total**| **11** | HIGH: **6** / MEDIUM: **5** | P1: **1** / P2: **5** / P3: **5** |

**FP Prevention**: 가설 15건 검증, 4건 사전 거부 (거부율: 27%)
**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용

## Findings

---

### [M-01] 칸반 다음 단계 날짜 입력에 제출 핸들러 없음 — [Major/HIGH] — Priority: P1

**위치**: `preview-shortlist-showcase.html:700-704`
**카테고리**: R6 비즈니스 로직 정확성

**증거**:
```javascript
// 700-704행
const inp = document.createElement('input');
inp.type = 'date';
inp.placeholder = '날짜 입력';
inp.onclick = function(e) { e.stopPropagation(); };
ni.appendChild(inp);
```

**문제**: 칸반 뷰의 Active 카드에 "다음 단계" 날짜 input이 렌더링되지만, 값을 입력해도 아무 일도 일어나지 않음. onchange/onblur 핸들러가 없어 사용자가 날짜를 선택해도 데이터에 반영되지 않음.

**영향**: 사용자가 기능이 동작한다고 기대하지만 실제로는 데이터 유실. UX 혼란.

**수정 제안**: inp.onchange 핸들러를 추가하여 해당 매수자의 다음 미완료 단계에 날짜를 기록하고 뷰를 재렌더링.

**Self-Challenge**: SC-1(✓ Read 확인) SC-2(✓ 700-704행) SC-3(✓ onchange/onblur 부재 Grep 확인) SC-4(✓) SC-5(✓ 기능 결함)

**우선순위 점수**: 70 x 1.0 = **70** (P1)

---

### [M-02] DOM API와 set-html 혼용 패턴 — [Major/MEDIUM] — Priority: P2

**위치**: `preview-shortlist-showcase.html` 전역 (512, 561, 575, 598, 675, 688, 787, 806, 927, 953행)
**카테고리**: R2 보안 / R5 코드 건강성

**증거**:
```javascript
// 512행 — set-html로 복합 HTML 삽입
right./*set-html*/ = tierHtml(b.tier) + interestHtml(b.tier) + stageDotsHtml(b);

// 대부분의 다른 렌더 코드 — DOM API 사용
const el = document.createElement('div');
el.textContent = '안전한 텍스트';
```

**문제**: 11개 지점에서 element의 HTML 내용을 직접 설정하고, 나머지는 createElement/textContent DOM API를 사용. 패턴이 비일관적. 현재 데이터는 하드코딩이므로 XSS 위험은 LOW이나, 향후 동적 데이터(사용자 입력 등) 연결 시 HTML 직접 설정 지점이 XSS 벡터가 됨.

**영향**: 프리뷰 파일 현재는 낮은 위험. 프로덕션 코드로 전환 시 보안 리스크 상승.

**수정 제안**: SVG 아이콘은 HTML 직접 설정 허용 (정적 상수), Tier/Interest 뱃지는 DOM API로 통일.

**Self-Challenge**: SC-1(✓) SC-2(✓ 11개 지점 확인) SC-3(△ 현재 데이터 하드코딩으로 실제 XSS 불가) SC-5(✓ 패턴 비일관) → 신뢰도 MEDIUM으로 하향

**우선순위 점수**: 70 x 0.6 = **42** (P2)

---

### [m-01] 접근성(a11y) 요소 전무 — [Moderate/HIGH] — Priority: P2

**위치**: `preview-shortlist-showcase.html` 전역
**카테고리**: R6 접근성

**증거**: aria- 속성 0건, role= 속성 0건 (Grep 확인).
- 사이드바 마스터 리스트: button 사용은 적절하나, aria-selected 없음
- 뷰 탭 전환: aria-controls, role="tablist" 없음
- Drop/복구 토글: 상태 변경 시 aria-live 알림 없음
- 타임라인: role="list" / role="listitem" 없음

**영향**: 스크린 리더 사용자가 뷰 전환, Drop 상태, 타임라인 이벤트를 인지 불가.

**Self-Challenge**: SC-1(✓ Grep 확인) SC-3(✓ aria-/role= 0건 확인) SC-5(✓ 접근성 표준 위반)

**우선순위 점수**: 40 x 1.0 = **40** (P2)

---

### [m-02] renderAll()이 보이지 않는 뷰까지 전체 렌더링 — [Moderate/HIGH] — Priority: P2

**위치**: `preview-shortlist-showcase.html:1032-1042`
**카테고리**: R5 성능

**증거**:
```javascript
// 1032-1042행 (renderAll)
function renderAll() {
  renderSummary();
  renderMasterList();
  renderGrid();
  renderKanban();
  renderTimeline();
  if (selectedBuyerId) {
    var b = BUYERS.find(function(x){ return x.id === selectedBuyerId; });
    if (b) renderDetail(b);
  }
}
```

**문제**: 뷰 탭 전환으로 한 번에 하나의 뷰만 보이지만 (display:none 처리), renderAll()은 Grid/Kanban/Timeline 3개 뷰를 매번 전체 렌더링. 매수자 8명 기준 현재 성능 문제는 없으나, 데이터 증가 시 불필요한 DOM 조작 발생.

**영향**: 현재 규모(8명)에서는 체감 성능 차이 없음. 50명+ 시 DOM 렌더링 병목 가능.

**Self-Challenge**: SC-1(✓) SC-2(✓ 1032-1042행) SC-3(△ 8명 규모에서 성능 문제 미발생) → 신뢰도 유지 (구조적 이슈)

**우선순위 점수**: 40 x 1.0 = **40** (P2)

---

### [m-03] 긴 함수 (50줄 초과 4개) — [Moderate/HIGH] — Priority: P2

**위치**: renderGrid(82줄), renderKanban(121줄), renderTimeline(143줄), renderDetail(133줄)
**카테고리**: R5 인지 복잡도

**증거**:

| 함수 | 시작행 | 종료행 | 줄 수 |
|------|--------|--------|-------|
| renderGrid | 522 | 604 | 82 |
| renderKanban | 609 | 730 | 121 |
| renderTimeline | 735 | 878 | 143 |
| renderDetail | 883 | 1016 | 133 |

**문제**: 단일 파일 바닐라 JS에서 4개 함수가 50줄을 크게 초과. 렌더링 + 이벤트 바인딩 + 데이터 변환이 한 함수에 혼재.

**영향**: 유지보수 시 특정 렌더링 로직 수정 위치 파악 어려움. 코드 리뷰 부담 증가.

**수정 제안**: 프리뷰 파일 특성상 즉시 분리 필요는 낮으나, 프로덕션 전환 시 createTimelineCard(), createKanbanCard() 등으로 헬퍼 추출 권장.

**Self-Challenge**: SC-1(✓) SC-3(△ 프리뷰 파일이라 강한 규칙 적용 불필요) SC-5(✓ 구조적 개선점)

**우선순위 점수**: 40 x 1.0 = **40** (P2)

---

### [m-04] 수동 로그 날짜 입력 검증 없음 — [Moderate/MEDIUM] — Priority: P3

**위치**: `preview-shortlist-showcase.html:413-424`
**카테고리**: R3 데이터 정합성

**증거**:
```javascript
// 418행
const date = dateInput.value;
const content = contentInput.value.trim();
if (!date || !content) return;
buyer.custom_logs.push({ date: date, content: content });
```

**문제**: input type="date"의 값을 검증 없이 그대로 저장. 브라우저가 기본 날짜 형식 검증을 수행하나, 미래 날짜(2099년 등)나 과거 날짜(1900년 등) 제한 없음. 비즈니스 맥락에서 M&A 마케팅 활동 로그에 비합리적 날짜 입력 가능.

**Self-Challenge**: SC-1(✓) SC-3(△ input type="date" 자체가 형식 검증 수행) → MEDIUM

**우선순위 점수**: 40 x 0.6 = **24** (P3)

---

### [m-05] .is-dropped에 !important 사용 — [Moderate/MEDIUM] — Priority: P3

**위치**: `preview-shortlist-showcase.html:66`
**카테고리**: R5 코드 건강성

**증거**:
```css
.is-dropped { opacity: 0.55; filter: grayscale(100%); background-color: #f9fafb !important; }
```

**문제**: background-color에 !important 사용. CSS 특이성(specificity) 충돌을 강제로 해결하는 패턴으로, 향후 스타일 오버라이드 어려움.

**Self-Challenge**: SC-1(✓) SC-3(△ 단일 파일 프리뷰에서 실질적 문제 낮음) → MEDIUM

**우선순위 점수**: 40 x 0.6 = **24** (P3)

---

### [L-01] 반응형 디자인 없음 — [Minor/HIGH] — Priority: P2

**위치**: `preview-shortlist-showcase.html` CSS 전역
**카테고리**: R6 UX

**증거**: @media 쿼리 0건 (Grep 확인). 사이드바 width: 280px 고정, 메인 영역 flex: 1.

**문제**: 모바일/태블릿에서 사이드바가 화면을 과도하게 차지. 1024px 미만에서 레이아웃 깨짐 예상.

**영향**: 프리뷰 파일이므로 주로 데스크톱에서 확인. 프로덕션 전환 시 반드시 대응 필요.

**Self-Challenge**: SC-1(✓) SC-3(✓ @media 0건 확인)

**우선순위 점수**: 20 x 1.0 = **20** (P2 경계, 프리뷰 특성 고려 P3에 가까움)

---

### [L-02] 에러 핸들링 없음 — [Minor/MEDIUM] — Priority: P3

**위치**: `preview-shortlist-showcase.html` 전역
**카테고리**: R4 에러 처리

**증거**: try/catch 0건 (Grep 확인). toggleDropStatus, addCustomLog 등 상태 변경 함수에 에러 핸들링 없음.

**문제**: DOM 요소를 getElementById로 조회 후 null 체크 없이 .value 접근 (416-417행). 요소가 없으면 TypeError 발생 가능.

**Self-Challenge**: SC-1(✓) SC-3(△ 정상 렌더링 경로에서 항상 요소 존재) → MEDIUM

**우선순위 점수**: 20 x 0.6 = **12** (P3)

---

### [L-03] getSorted() 중복 호출 — [Minor/HIGH] — Priority: P3

**위치**: `preview-shortlist-showcase.html:481, 523`
**카테고리**: R5 성능

**증거**: getSorted() 호출 — renderMasterList(481행), renderGrid(523행). renderAll() 실행 시 정렬 연산 2회 반복.

**문제**: 8명 배열 정렬이므로 성능 영향 무시 수준이나, 구조적으로 renderAll() 상단에서 한 번 정렬 후 전달이 깔끔.

**Self-Challenge**: SC-1(✓) SC-3(△ O(n log n) x 2, n=8 → 무시 가능)

**우선순위 점수**: 20 x 1.0 = **20** (P3)

---

### [L-04] 상태 변경 Undo 불가 — [Minor/MEDIUM] — Priority: P3

**위치**: `preview-shortlist-showcase.html:405-410, 413-424`
**카테고리**: R6 UX

**증거**: toggleDropStatus는 ACTIVE/DROPPED 토글이므로 자체 복구 가능. 그러나 addCustomLog는 push()로 추가 후 삭제 UI 없음.

**문제**: 수동 로그를 잘못 추가하면 삭제할 방법이 없음. 페이지 새로고침으로만 초기화 가능.

**Self-Challenge**: SC-1(✓) SC-3(△ 프리뷰 파일 — 데이터 영속화 없음, 새로고침으로 리셋)

**우선순위 점수**: 20 x 0.6 = **12** (P3)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
없음

### P1 — 스프린트 우선 (점수: 60-89)
1. [M-01] [Major/HIGH]: 칸반 다음 단계 날짜 입력에 제출 핸들러 없음 — :700-704 (점수: 70)

### P2 — 개선 권장 (점수: 30-59)
1. [M-02] [Major/MEDIUM]: DOM API와 HTML 직접 설정 혼용 — 전역 11개 지점 (점수: 42, 신뢰도 하향)
2. [m-01] [Moderate/HIGH]: 접근성(a11y) 요소 전무 — 전역 (점수: 40)
3. [m-02] [Moderate/HIGH]: renderAll()이 보이지 않는 뷰까지 전체 렌더링 — :1032-1042 (점수: 40)
4. [m-03] [Moderate/HIGH]: 긴 함수 50줄 초과 4개 — 전역 (점수: 40)
5. [L-01] [Minor/HIGH]: 반응형 디자인 없음 — CSS 전역 (점수: 20)

### P3 — 저우선 (점수: 30 미만)
1. [m-04] [Moderate/MEDIUM]: 수동 로그 날짜 입력 검증 없음 — :418 (점수: 24)
2. [m-05] [Moderate/MEDIUM]: .is-dropped에 !important 사용 — :66 (점수: 24)
3. [L-03] [Minor/HIGH]: getSorted() 중복 호출 — :481, 523 (점수: 20)
4. [L-02] [Minor/MEDIUM]: 에러 핸들링 없음 — 전역 (점수: 12)
5. [L-04] [Minor/MEDIUM]: 상태 변경 Undo 불가 — :413-424 (점수: 12)

---

## 계획 대비 구현 검증 (section 6)

> 플랜 파일: `.claude/plans/dynamic-booping-perlis.md`

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | 데이터 모델에 status, custom_logs 추가 | ✅ | :280-352 — b7, b8에 DROPPED, 모든 매수자 custom_logs: [] |
| 2 | Drop/복구 토글 UI | ✅ | :405-410 toggleDropStatus() + :995-1010 상세 패널 버튼 |
| 3 | 정렬 함수 getSorted() | ✅ | :395-402 — DROPPED 하단 + completedCount 내림차순 |
| 4 | CSS 추가 (Drop, 타임라인, 로그 폼) | ✅ | :66-202 — .is-dropped, .v-timeline, .log-form 등 |
| 5 | 그리드 뷰 Drop 처리 | ✅ | :522-604 — .is-dropped 클래스 + [Drop] 뱃지 |
| 6 | 사이드바 Drop 처리 | ✅ | :480-517 — getSorted() + Drop 뱃지 |
| 7 | 칸반 뷰 Drop 처리 | ✅ | :609-730 — Active→Divider→Dropped 순서, Drop 카드 다음 단계 미렌더 |
| 8 | 타임라인 수직형 전면 개편 | ✅ | :735-878 — Drop 필터링 + 수직 타임라인 + 이벤트 수집 |
| 9 | 수동 로그 기능 addCustomLog() | ✅ | :413-425 — 날짜+내용 입력, push, 폼 초기화, 재렌더 |
| 10 | Summary Bar 동적 업데이트 | ✅ | :430-475 renderSummary() — Active 기준 통계 |

**결과**: 플랜 10개 항목 중 **10개 완전 구현** (100%)

---

## 13개 리뷰 관점 심층 분석 (section 9)

### R2 — 보안 심층 + 위협 모델링

| 관점 | 결과 |
|------|------|
| XSS 벡터 | HTML 직접 설정 11개 지점 — 모두 하드코딩 상수/SVG (현재 안전). [M-02] 참조 |
| CSRF | N/A — 서버 통신 없음, 클라이언트 전용 |
| 데이터 노출 | BUYERS 배열에 담당자명/연락처 하드코딩 — 프리뷰 전용, 프로덕션 전환 시 제거 필요 |
| CSP | @import url() 외부 폰트 로드 — CSP 헤더 미설정 시 차단 가능성 |

### R3 — 데이터 흐름 및 무결성

| 관점 | 결과 |
|------|------|
| 상태 일관성 | BUYERS 배열 직접 변이(mutation) — 모든 render 함수가 동일 소스 참조, 일관성 유지 |
| 날짜 정합성 | custom_logs 날짜 미검증 [m-04]. stages 날짜는 하드코딩이라 안전 |
| API 계약 | N/A — 백엔드 통신 없음 |

### R4 — 에러 처리 + 관찰 가능성

| 관점 | 결과 |
|------|------|
| try-catch | 0건 [L-02]. getElementById 반환값 null 체크 없음 |
| 로깅 | console.log/warn/error 0건. 디버깅 시 상태 추적 어려움 |
| 실패 모드 | 렌더 함수 내부 에러 시 해당 뷰 전체 미렌더링 (부분 실패 복구 없음) |

### R5 — 성능 + 코드 건강성

| 관점 | 결과 |
|------|------|
| DOM 재사용 | 매 renderAll() 시 전체 DOM 삭제 후 재생성 — Virtual DOM 없는 환경에서 비효율 [m-02] |
| getSorted() 중복 | 2회/cycle [L-03] |
| 보이지 않는 뷰 렌더링 | 3개 뷰 모두 렌더링 [m-02] |
| CSS 특이성 | !important 1건 [m-05] |
| 함수 크기 | 50줄 초과 4개 [m-03] |

### R6 — 비즈니스 로직 + UX + 접근성

| 관점 | 결과 |
|------|------|
| Drop 비즈니스 로직 | 그리드/칸반/사이드바 = 시각적 감쇠, 타임라인 = 완전 제외. 뷰별 목적에 부합 |
| 칸반 다음 단계 | 날짜 입력 핸들러 미구현 [M-01] — 기능 결함 |
| 접근성 | aria-/role= 0건 [m-01] |
| 반응형 | @media 0건 [L-01] |
| Undo | 수동 로그 삭제 불가 [L-04] |
| 도메인 적합성 | M&A 마케팅 프로세스 단계(NDA→미팅→IOI→LOI→최종) 반영 정확 |

---

## Methodology

- **Agents**: code-reviewer (단일 에이전트, 프리뷰 HTML 단일 파일)
- **Excluded Agents**: type-checker, api-auditor, security-auditor (범위-에이전트 필터링 — 프리뷰 HTML은 빌드/API/백엔드 대상 아님)
- **Files scanned**: 1 (preview-shortlist-showcase.html, 1050줄)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major = 2건 대상, self-challenge 적용
- **Backend availability**: N/A (프리뷰 파일, 백엔드 없음)

## 검증 투명성

### 검증 통계
- 검증한 가설: 15건
- 거부된 가설 (사전 제거): 4건
- 보고된 이슈: 11건
- 거부율: 27%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 1 | "이벤트 리스너 누수" — 매 렌더 시 DOM 전체 교체로 자동 해제 |
| 범위 외 | 1 | "모듈 번들링 필요" — 프리뷰 HTML은 번들링 대상 아님 |
| 설계 의도 | 1 | "BUYERS 직접 변이 위험" — 프리뷰 파일의 의도적 단순화 |
| 중복 | 1 | "타임라인 Drop 미표시" — 요구사항의 의도적 설계 (기능 아님) |
