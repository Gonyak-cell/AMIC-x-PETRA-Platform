# Code Review — Short List 사이드바 토글

> **Review Date**: 2026-03-09 23:07
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `amic-platform/preview-shortlist-showcase.html` — 사이드바 접기/펼치기 기능
> **Method**: Review Gates + 13-Perspective Verified Multi-Agent Review + Cross-Verification + Auto-Fix
> **Quality Gates**: N/A (standalone HTML preview)
> **Review Gates**: Backend(unavailable — standalone) Agent-Filtering(code-reviewer + a11y-auditor)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 1     | HIGH: 1 | P1: 1 |
| Moderate | 3     | HIGH: 3 | P2: 3 |
| Minor    | 2     | HIGH: 1 / MEDIUM: 1 | P3: 2 |
| **Total**| **6** | HIGH: **5** / MEDIUM: **1** | P1: **1** / P2: **3** / P3: **2** |

**FP Prevention**: 가설 14건 검증, 8건 사전 거부 (거부율: 57%) | 교차 검증 1건 수행

## Findings

### [M-R1] 모바일 반응형에서 사이드바 접힘 시 레이아웃 깨짐 — [Major/HIGH] — Priority: P1

- **파일**: `preview-shortlist-showcase.html:15`, `line 225-227`
- **에이전트**: code-reviewer
- **우선순위**: P1 (점수: 70) — 심각도 70 × 신뢰도 1.0
- **검증 추적**:
  1. ✓ Read: `.sidebar.collapsed { width: 48px }` specificity 0-2-0
  2. ✓ Read: `@media(max-width:768px) .sidebar { width: 100% }` specificity 0-1-0
  3. ✓ CSS Specificity 분석: collapsed가 media query를 항상 덮어씀
  4. ✓ SC-1(✓) SC-2(✓) SC-3(✓) SC-5(✓) SC-6(✓)
- **이슈**: 768px 이하 모바일에서 `flex-direction: column`으로 전환되지만, `.sidebar.collapsed`의 `width: 48px`이 더 높은 specificity로 우선 적용되어 레이아웃 깨짐.
- **수정**: `.sidebar.collapsed` 모바일 오버라이드 추가 (`width: 100%; max-height: 48px`)
- **수정 상태**: ✅ 자동 수정 완료

### [m-R2] 접힌 콘텐츠에 opacity transition 없음 — [Moderate/HIGH] — Priority: P2

- **파일**: `preview-shortlist-showcase.html:16-18`
- **에이전트**: code-reviewer
- **우선순위**: P2 (점수: 40) — 심각도 40 × 신뢰도 1.0
- **이슈**: 사이드바 너비는 0.2s ease 애니메이션, 내부 콘텐츠는 opacity: 0으로 즉시 사라짐. 비대칭.
- **수정**: `transition: opacity 0.15s ease` 추가
- **수정 상태**: ✅ 자동 수정 완료

### [m-R3] CSS 들여쓰기 불일치 — [Moderate/HIGH] — Priority: P2

- **파일**: `preview-shortlist-showcase.html:21`
- **에이전트**: code-reviewer
- **우선순위**: P2 (점수: 40)
- **이슈**: Sidebar Toggle 섹션만 0-space indent, 나머지 모든 CSS는 2-space indent.
- **수정 상태**: ✅ 자동 수정 완료

### [m-R4] var/const/let 혼용 — [Moderate/HIGH] — Priority: P2

- **파일**: `preview-shortlist-showcase.html:411+`
- **에이전트**: code-reviewer
- **우선순위**: P2 (점수: 40)
- **이슈**: 초기 헬퍼 함수는 `var`, 렌더링 함수는 `const/let` 사용. 15개 이상 인스턴스.
- **수정**: 모든 `var` → `const`/`let` 통일 (총 0건 남음)
- **수정 상태**: ✅ 자동 수정 완료

### [L-X1] 토글 버튼 키보드 포커스 링 없음 — [Minor/HIGH] — Priority: P3

- **파일**: `preview-shortlist-showcase.html:22-23`
- **에이전트**: a11y-auditor
- **우선순위**: P3 (점수: 20) — 심각도 20 × 신뢰도 1.0
- **이슈**: `:hover` 스타일만 있고 `:focus-visible` 없음. WCAG 2.1 AA 위반.
- **수정**: `.sidebar-toggle:focus-visible` 스타일 추가
- **수정 상태**: ✅ 자동 수정 완료

### [L-R5] 토글 버튼 모바일 위치 문제 — [Minor/MEDIUM] — Priority: P3

- **파일**: `preview-shortlist-showcase.html:22`
- **에이전트**: code-reviewer
- **우선순위**: P3 (점수: 12) — 심각도 20 × 신뢰도 0.6
- **이슈**: `right: -14px` 모바일에서 부적절한 위치.
- **수정**: 모바일 미디어쿼리에 `right: 16px` 오버라이드 추가
- **수정 상태**: ✅ 자동 수정 완료

## §6 계획 대비 구현 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|----------|
| 1 | `.sidebar` transition 추가 | ✅ | line 14: `transition: width 0.2s ease` |
| 2 | `.sidebar.collapsed` { width: 48px } | ✅ | line 15 |
| 3 | 접힌 상태 텍스트 숨김 | ✅ | lines 16-18 |
| 4 | 토글 버튼 스타일 | ✅ | lines 22-26 |
| 5 | `.main` flex:1 자동 대응 | ✅ | line 19 |
| 6 | toggleSidebar() JS 함수 | ✅ | lines 318-320 |
| 7 | 접힘/펼침 화살표 방향 | ✅ | line 26 rotate(180deg) |

**구현율**: 7/7 (100%)

## Priority Matrix

### P1 — 스프린트 우선 (점수: 60-89)
1. [M-R1] [Major/HIGH]: 모바일 반응형 사이드바 접힘 레이아웃 깨짐 (점수: 70) ✅ 수정됨

### P2 — 개선 권장 (점수: 30-59)
1. [m-R2] [Moderate/HIGH]: opacity transition 없음 (점수: 40) ✅ 수정됨
2. [m-R3] [Moderate/HIGH]: CSS 들여쓰기 불일치 (점수: 40) ✅ 수정됨
3. [m-R4] [Moderate/HIGH]: var/const/let 혼용 (점수: 40) ✅ 수정됨

### P3 — 저우선 (점수: <30)
1. [L-X1] [Minor/HIGH]: 키보드 포커스 링 없음 (점수: 20) ✅ 수정됨
2. [L-R5] [Minor/MEDIUM ⚠️]: 모바일 토글 위치 (점수: 12) ✅ 수정됨

## Methodology

- Agents: code-reviewer, a11y-auditor
- Excluded Agents: api-auditor(범위외), security-auditor(standalone), type-checker(no TS), test-auditor(no tests), perf-auditor(8건 mock data), infra-auditor(no infra)
- Files scanned: 1
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- Cross-verification: Major 1건 → CONFIRMED (CSS specificity)
- 13-Perspective Coverage: §1정합성(✓) §2완전성(✓) §3품질(✓) §4안정성(✓) R2보안(N/A-standalone) R3데이터(N/A) R4복원력(N/A) R5운영(✓) R6비즈니스&UX(✓) 접근성(✓) 성능(N/A-8items) 배포(N/A) 의존성(N/A)

## 검증 투명성

### 검증 통계
- 검증한 가설: 14건
- 거부된 가설 (사전 제거): 8건
- 보고된 이슈: 6건
- 거부율: 57%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| SC 기각 | 3 | innerHTML XSS → SC-3: 정적 SVG만 사용, 사용자 입력 없음 |
| 범위 외 | 3 | 백엔드 연동, API 계약, DB → standalone HTML |
| 반증됨 | 1 | 1024px 반응형 collapsed 충돌 → specificity로 정상 동작 확인 |
| 오판 | 1 | mock 이메일 PII → preview 파일 명백한 가짜 데이터 |
