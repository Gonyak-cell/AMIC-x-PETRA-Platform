---
name: review-security
description: 보안 집중 코드 리뷰. security-auditor + api-auditor 에이전트 활용.
---
# 보안 코드 리뷰

review-orchestrate 스킬을 `type=security`로 호출합니다.

대상: $ARGUMENTS (없으면 전체 코드베이스)

## 사용 에이전트

- **security-auditor**: 인증, 입력 검증, LLM 보안, CORS, 시크릿, 데이터 보호
- **api-auditor**: FE-BE 통합 보안 (토큰 흐름, 프록시 설정)

## 스코프 옵션

```
/review-security                        # FE 전체 + 공통 설정
/review-security --backend              # FE + BE 모두 (권장)
/review-security --module kiis --backend  # KIIS 모듈 FE+BE
/review-security --diff                 # 변경 파일만
```

## 실행

review-orchestrate 스킬의 실행 파이프라인을 따릅니다.
`.claude/skills/review-orchestrate/SKILL.md` 참조.
