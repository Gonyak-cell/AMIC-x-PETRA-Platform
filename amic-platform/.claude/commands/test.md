---
name: test
description: 테스트를 실행하고 결과를 분석합니다.
---
# 테스트 실행

- 전체: `npm run test`
- 특정: `npx vitest run $ARGUMENTS`
- 커버리지: `npx vitest run --coverage`

실패 시 원인을 분석하고 수정 방안을 제시합니다.

## 보고 형식
- Total: passed / failed / skipped
- 실패 시: 파일명, 테스트명, 근본 원인, 수정 제안
