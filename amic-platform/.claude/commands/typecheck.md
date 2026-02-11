---
name: typecheck
description: TypeScript 타입 체크를 실행하고 에러를 분석합니다.
---
# TypeScript 타입 체크

1. `npx tsc --noEmit` 실행
2. 에러가 있으면 각 에러를 분석:
   - 에러 위치 (파일:라인)
   - 원인 분석
   - 수정 방안 제시
3. 에러가 없으면 "타입 체크 통과" 보고

대상: $ARGUMENTS (특정 파일 경로 지정 가능, 미지정 시 전체)
