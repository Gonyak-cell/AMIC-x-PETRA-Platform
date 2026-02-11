---
name: build-check
description: 빌드 전 전체 점검 (format + lint + typecheck + build)을 실행합니다.
---
# 빌드 전 점검

다음 항목을 순서대로 검사하고 결과를 보고:

## 1단계: 코드 품질
- `npm run format:check` — Prettier 포매팅 확인
- `npm run lint` — ESLint (--max-warnings 0)

## 2단계: 타입 체크
- `npx tsc --noEmit` — TypeScript strict 체크

## 3단계: 빌드
- `npm run build` — Vite 프로덕션 빌드

## 4단계: 최종 보고
```
=== 빌드 준비 점검 결과 ===
[ ] Prettier: PASS/FAIL
[ ] ESLint: PASS/FAIL
[ ] TypeScript: PASS/FAIL
[ ] Vite Build: PASS/FAIL
빌드 가능 여부: YES/NO
```
