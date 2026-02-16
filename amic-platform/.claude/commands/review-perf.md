---
name: review-perf
description: 성능/번들 최적화 리뷰. perf-auditor 에이전트로 번들, 렌더링, 네트워크, CSS 분석.
---
# 성능 리뷰

review-orchestrate 스킬을 `type=perf`로 호출합니다.

대상: $ARGUMENTS (없으면 전체 코드베이스)

## 사용 에이전트

- **perf-auditor**: 번들 크기, 렌더링 성능, 네트워크 최적화, CSS, Vite 설정

## 스코프 옵션

```
/review-perf                            # 전체
/review-perf --module kiis              # KIIS 모듈 (18개 정적 import 이슈 등)
/review-perf --diff                     # 변경 파일만
```

## 실행

review-orchestrate 스킬의 실행 파이프라인을 따릅니다.
`.claude/skills/review-orchestrate/SKILL.md` 참조.
