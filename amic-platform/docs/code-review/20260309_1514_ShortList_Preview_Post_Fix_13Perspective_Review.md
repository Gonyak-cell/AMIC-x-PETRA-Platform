# Code Review — ShortList Preview Post-Fix 13 Perspective Review

> **Review Date**: 2026-03-09 15:14
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `amic-platform/preview-shortlist-showcase.html` (1140줄, standalone vanilla HTML/CSS/JS)
> **Method**: Review Gates + Verified Multi-Agent Review + Cross-Verification
> **Strategy**: Strategy 2 (Post-Fix Verification) + Strategy 1 (Perspective Shift — 13개 관점 통합)
> **Quality Gates**: N/A (standalone HTML, 빌드 시스템 없음)
> **Review Gates**: Backend(N/A — standalone preview) Agent-Filtering(2개 에이전트 호출)

---

## 이전 리뷰 수정 확인 (11/11 완료)

| 이전 이슈 | 심각도 | 수정 상태 | 검증 근거 |
|-----------|--------|----------|----------|
| M-01: kanban onchange 클로저 | Major | 수정됨 | 라인 776-778: IIFE 패턴 |
| M-02: DOM API 전환 | Major | 수정됨 | 라인 390-422: createElement + textContent |
| m-01: ARIA 속성 누락 | Moderate | 수정됨 | 라인 234-291: 16개 ARIA 속성 |
| m-02: 불필요한 렌더링 | Moderate | 수정됨 | 라인 1102, 1117-1121: currentView + renderCurrentView() |
| m-03: Drop 뱃지 중복 | Moderate | 수정됨 | 라인 427-432: appendDropBadge() 선언 |
| m-04: 날짜 유효성 검증 | Moderate | 수정됨 | 라인 485-492: min/max 범위 검증 |
| m-05: !important 남용 | Moderate | 수정됨 | CSS 전체 !important 0건 |
| L-01: 반응형 미지원 | Minor | 수정됨 | 라인 210-225: @media 쿼리 |
| L-02: 에러 핸들링 | Minor | 수정됨 | 라인 477, 497: try/catch |
| L-03: getSorted() 중복 | Minor | 수정됨 | 라인 1123-1131: 1회 호출 후 전달 |
| L-04: 로그 삭제 기능 | Minor | 수정됨 | 라인 501-506: deleteCustomLog() |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0 | — | — |
| Major | 0 | — | — |
| Moderate | 4 | HIGH: 4 | P2: 4 |
| Minor | 3 | HIGH: 1 / MEDIUM: 1 / LOW: 1 | P3: 3 |
| **Total** | **7** | HIGH: **5** / MEDIUM: **1** / LOW: **1** | P2: **4** / P3: **3** |

**FP Prevention**: 가설 22건 검증, 15건 사전 거부 (거부율: 68%) | 교차 검증 1건 수행

---

## Findings

### [m-R1] addCustomLog의 빈 catch 블록 — [Moderate/HIGH] — Priority: P2

> 교차 검증됨: Agent 1 (R4) + Agent 2 (R5) 동일 이슈 발견

- **파일**: `preview-shortlist-showcase.html:497`
- **우선순위**: P2 (점수: 50 = 40x1.0 + 10 교차검증)
- **Self-Challenge**: SC-1(V) SC-2(V) SC-3(V) SC-4(V) SC-5(V) SC-6(V)
- **증거**:
  ```javascript
  } catch (e) { }
  ```
- **이슈**: L-02 수정에서 try/catch를 추가했으나 catch 블록이 비어있어 모든 예외를 무시한다.
- **영향**: 로그 추가 실패 시 사용자에게 무반응, 디버깅 불가.
- **수정안**:
  ```javascript
  } catch (e) { console.error('addCustomLog error:', e); }
  ```

---

### [m-X1] 타임라인 로그 입력 폼 aria-label 누락 — [Moderate/HIGH] — Priority: P2

- **파일**: `preview-shortlist-showcase.html:939-952`
- **우선순위**: P2 (점수: 40 = 40x1.0)
- **Self-Challenge**: SC-1(V) SC-2(V) SC-3(V) SC-4(V) SC-5(V) SC-6(V)
- **증거**:
  ```javascript
  const dateInp = document.createElement('input');
  dateInp.type = 'date';
  dateInp.id = 'log-date-' + b.id;
  // aria-label 없음
  ```
- **이슈**: m-01에서 주요 UI에 ARIA를 추가했으나 폼 입력에 누락. WCAG 2.1 1.3.1 미충족.
- **수정안**: `dateInp.setAttribute('aria-label', '활동 날짜')`, `textInp.setAttribute('aria-label', '활동 내용')`

---

### [m-X2] 칸반 date input aria-label 누락 — [Moderate/HIGH] — Priority: P2

- **파일**: `preview-shortlist-showcase.html:773`
- **우선순위**: P2 (점수: 40 = 40x1.0)
- **Self-Challenge**: SC-1(V) SC-2(V) SC-3(V) SC-4(V) SC-5(V) SC-6(V)
- **증거**:
  ```javascript
  const inp = document.createElement('input');
  inp.type = 'date';
  inp.placeholder = '날짜 입력';
  // aria-label 없음
  ```
- **수정안**: `inp.setAttribute('aria-label', STAGE_LABELS[nextStage] + ' 날짜 입력')`

---

### [m-X3] 로그 삭제 버튼 aria-label 누락 — [Moderate/HIGH] — Priority: P2

- **파일**: `preview-shortlist-showcase.html:900-907`
- **우선순위**: P2 (점수: 40 = 40x1.0)
- **Self-Challenge**: SC-1(V) SC-2(V) SC-3(V) SC-4(V) SC-5(V) SC-6(V)
- **증거**:
  ```javascript
  delBtn.textContent = 'x';
  delBtn.title = '로그 삭제';
  // title만 있고 aria-label 없음 — createArrowBtn(라인 440)은 aria-label 적용됨
  ```
- **수정안**: `delBtn.setAttribute('aria-label', '로그 삭제')`

---

### [L-R1] SVG string replace 패턴 — [Minor/HIGH] — Priority: P3

- **파일**: `preview-shortlist-showcase.html:442, 655, 1030`
- **우선순위**: P3 (점수: 20 = 20x1.0)
- **증거**:
  ```javascript
  // 라인 1030 — string replace로 스타일 주입
  circle.innerHTML = checkSvg().replace('class="check-svg"',
    'class="check-svg" style="width:14px;height:14px"');
  ```
- **이슈**: 정적 SVG이므로 XSS 위험 없음. 단 replace 체인이 checkSvg() 형식 변경에 취약.
- **수정안**: `checkSvg(size)` 파라미터 추가 또는 CSS 클래스 분리.

---

### [L-R2] CDN @import SRI 미적용 — [Minor/MEDIUM] — Priority: P3

- **파일**: `preview-shortlist-showcase.html:8`
- **우선순위**: P3 (점수: 12 = 20x0.6)
- **이슈**: CSS @import는 SRI hash 미지원. 프리뷰 파일이므로 실질적 위험 없음.

---

### [L-R3] switchView null 방어 없음 — [Minor/LOW] — Priority: P3

- **파일**: `preview-shortlist-showcase.html:1104-1115`
- **우선순위**: P3 (점수: 6 = 20x0.3)
- **이슈**: inline onclick에서만 호출되어 실질적 발생 불가.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
없음.

### P1 — 스프린트 우선 (점수: 60-89)
없음.

### P2 — 개선 권장 (점수: 30-59)
1. [m-R1] 빈 catch 블록 (점수: 50, 교차 검증됨)
2. [m-X1] 타임라인 폼 aria-label 누락 (점수: 40)
3. [m-X2] 칸반 date input aria-label (점수: 40)
4. [m-X3] 삭제 버튼 aria-label (점수: 40)

### P3 — 저우선 (점수: <30)
1. [L-R1] SVG string replace (점수: 20)
2. [L-R2] CDN SRI (점수: 12)
3. [L-R3] switchView null 방어 (점수: 6)

---

## Methodology

- **Agents**: code-reviewer x2 (R2/R3/R4 + R5/R6)
- **Excluded Agents**: api-auditor(N/A), type-checker(N/A), test-auditor(N/A), infra-auditor(N/A)
- **Files scanned**: 1개 (1140줄)
- **Protocol**: Verified Claim Protocol v1.1
- **Cross-verification**: 1건 (m-R1 silent catch)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 22건
- 거부된 가설 (사전 제거): 15건
- 보고된 이슈: 7건
- 거부율: 68%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 4 | getSorted()가 .slice() 사용 확인, 색상 대비 AA 충족 |
| Self-Challenge 기각 | 5 | var/const 혼용, function/arrow 혼용 — SC-5 프리뷰 의도된 패턴 |
| 이미 수정됨 | 2 | kanban 클로저, DOM API 전환 |
| 오판 | 2 | kanban/timeline 다른 정렬 로직, textContent 성능 무의미 |
| 범위 외 | 2 | immutable 패턴, 로그 UUID — 프로덕션 전환 시 해결 |

---

## 리뷰 적용 관점 매핑 (13개 관점)

| 관점 | 적용 | 결과 |
|------|------|------|
| R2-1 Security (XSS) | O | Minor 1건 (정적 SVG) |
| R2-2 Threat modeling | O | Minor 1건 (CDN SRI) |
| R3-1 Data flow | O | 이슈 없음 |
| R3-2 API contracts | N/A | standalone |
| R4-1 Error handling | O | Moderate 1건 (silent catch) |
| R4-2 Observability | N/A | 프리뷰 |
| R5-1 Performance | O | 이슈 없음 |
| R5-2 Deployment | N/A | standalone |
| R5-3 Dependencies | O | Minor 1건 |
| R6-1 Domain logic | O | 이슈 없음 |
| R6-2 Test quality | N/A | 프리뷰 |
| R6-3 Cognitive complexity | O | 양호 |
| R6-4 Accessibility | O | Moderate 3건 (aria-label) |

**적용**: 9/13 관점 (4건 N/A)
