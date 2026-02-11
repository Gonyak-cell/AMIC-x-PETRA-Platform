---
name: review
description: 최근 변경된 코드를 리뷰합니다.
---
# 코드 리뷰

component-reviewer 서브에이전트를 활용하여 리뷰합니다.

대상: $ARGUMENTS (없으면 git diff로 변경된 파일 전체)

## 리뷰 절차
1. 변경된 파일 목록 확인 (`git diff --name-only`)
2. 각 파일에 대해 component-reviewer 관점에서 검토
3. FDD 모듈 패턴과의 일관성 확인
4. 접근성 이슈 확인
5. TypeScript 타입 안전성 확인
6. 결과를 심각도별로 정리하여 보고
