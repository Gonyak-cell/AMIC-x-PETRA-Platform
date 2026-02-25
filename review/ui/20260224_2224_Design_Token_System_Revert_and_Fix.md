# 디자인 토큰 시스템 되돌리기 + 미정의 토큰 수정

> 작성: 2026-02-24 22:24:00

## 요약

CSS custom properties(`:root` 변수) 기반 디자인 토큰 시스템을 도입했으나, 적용 결과가 시각적으로 불만족스러워 전체 롤백 후 실제 문제(미정의 토큰 6종)만 hex로 해결.

## 도입한 시스템

| 단계 | 작업 | 변경 규모 |
|------|------|----------|
| Phase 0 | `:root` CSS 변수 65줄 + `.dark` 블록 + tailwind 토큰 13종 추가 | 2개 파일 |
| Phase 1 | UI 컴포넌트 19개 `bg-white` → `bg-surface` 등 | 19개 파일 |
| Phase 2 | 레이아웃 + 모듈 페이지 하드코딩 색상 일괄 전환 | ~65개 파일, 202건 |
| Phase 3 | gradient hex → CSS 변수 전환 | 1개 파일 |
| Phase 4 | TokenShowcasePage 신규 생성 | 1개 파일 |

## 롤백 사유 — 왜 안 맞았는가

### 1. 색상 뉘앙스 손실 (Many-to-One 매핑)
```
bg-blue-50  (#EFF6FF) ──┐
bg-blue-100 (#DBEAFE) ──┤── bg-info-light (단일 값)
bg-blue-200 (#BFDBFE) ──┘
```
서로 다른 강도의 색상이 하나로 평탄화 → 시각적 깊이감 상실

### 2. Tailwind v3 비호환
CSS 변수 기반 색상에 opacity modifier 불가 (`bg-surface/50` 작동 안 함).
하이브리드 전략(hex+CSS 변수 혼재)이 오히려 개발 혼란 야기.

### 3. 불필요한 추상화
`bg-white → bg-surface → var(--surface) → #FFFFFF`: 다크모드 미활성 상태에서 3단계 간접 참조는 순수 오버헤드.

### 4. 일괄 전환 리스크
~350건 일괄 변경으로 개별 변경의 시각적 영향 확인 불가, 롤백도 복잡.

### 5. Tailwind 생태계 직관성 상실
`bg-blue-50`은 모든 Tailwind 개발자가 아는 색상. `bg-info-light`는 커스텀 학습 비용 발생.

## 롤백 작업 내역

| 작업 | 방법 | 건수 |
|------|------|------|
| `TokenShowcasePage.tsx` 삭제 | 파일 삭제 | 1개 |
| `App.tsx` 라우트 제거 | Edit (import + route) | 2건 |
| `bg-surface` → `bg-white` 되돌리기 | Python 스크립트 | 119건 / 53개 파일 |
| tracked 파일 git checkout | `git checkout --` | 34개 파일 |
| 시맨틱 토큰 수동 되돌리기 | Python 스크립트 | 6건 / 3개 파일 |
| `:root` CSS 변수 블록 제거 | Edit | 90줄 제거 |
| `.dark` 블록 제거 | Edit | 포함 |
| gradient hex 원복 | Edit | 4건 |
| `tailwind.config.js` 시맨틱 토큰 제거 | Edit | 13종 + `darkMode: "class"` |

## 실제 수정 — 미정의 토큰 6종 hex 추가

롤백 후에도 코드에서 사용 중이지만 tailwind.config.js에 미정의된 토큰이 있어 투명 렌더링 문제 발생. hex 값으로 해결.

**파일**: `amic-platform/tailwind.config.js`

```js
"positive-light": "#E8F8ED",   // 41건 — QualityDashboard, LDDReportsTab 등
"negative-light": "#FEF2F2",   // ~20건 — QualityDashboard, ErrorBoundary 등
"caution-light": "#FFFBEB",    // ~15건 — QualityDashboard, SentimentIndicator
"info-light": "#EFF6FF",       // ~10건 — QualityDashboard, Badge, workflow
"accent-hover": "#1FAA52",     // ~3건 — Button.tsx hover 상태
"solid-green": "#1C8F57",      // ~2건 — Button.tsx brand variant gradient
```

## 교훈 — 향후 도입 시 주의사항

| 항목 | 권장 |
|------|------|
| 도입 시점 | Tailwind v4 마이그레이션 시 (CSS 변수 네이티브 지원) |
| 전환 방식 | 일괄 전환 금지. 컴포넌트 단위로 점진적 전환 + 시각 테스트 |
| 색상 매핑 | 1:1 매핑 원칙 (Many-to-One 금지) |
| 다크모드 | 비즈니스 요구 확정 후에만 인프라 추가 |

## 상태

- **롤백**: ✅ 완료 (빌드 통과)
- **미정의 토큰 수정**: ✅ 완료 (6종 hex 추가)
