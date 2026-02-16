---
name: review-test
description: 테스트 품질 리뷰. test-auditor 에이전트로 유닛 테스트 + E2E 테스트 품질 분석.
---
# 테스트 품질 리뷰

review-orchestrate 스킬을 `type=test`로 호출합니다.

대상: $ARGUMENTS (없으면 전체 테스트 파일)

## 사용 에이전트

- **test-auditor**: 유닛 테스트(Vitest/RTL/MSW) + E2E(Playwright) 품질

## 스코프 옵션

```
/review-test                            # 전체 테스트
/review-test --module fdd               # FDD 테스트만
/review-test --files src/test/mocks/    # 특정 테스트 파일
```

## 실행

review-orchestrate 스킬의 실행 파이프라인을 따릅니다.
`.claude/skills/review-orchestrate/SKILL.md` 참조.
