---
name: review-infra
description: 인프라/배포 리뷰. infra-auditor 에이전트로 Docker, Nginx, CI/CD, 환경 설정 분석.
---
# 인프라 리뷰

review-orchestrate 스킬을 `type=infra`로 호출합니다.

대상: $ARGUMENTS (없으면 전체 인프라 파일)

## 사용 에이전트

- **infra-auditor**: Docker Compose, Nginx, CI/CD, 환경 변수, 컨테이너 보안

## 스코프 옵션

```
/review-infra                           # 전체 인프라
/review-infra --files nginx/prod.conf   # 특정 설정 파일
/review-infra --diff                    # 변경 파일만
```

## 실행

review-orchestrate 스킬의 실행 파이프라인을 따릅니다.
`.claude/skills/review-orchestrate/SKILL.md` 참조.
