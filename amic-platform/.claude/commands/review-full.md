---
name: review-full
description: 멀티 에이전트 전체 코드 리뷰. Quality Gates + 5개 에이전트 병렬 + 교차 검증.
---
# 전체 코드 리뷰 (Multi-Agent)

review-orchestrate 스킬을 `type=full`로 호출합니다.

대상: $ARGUMENTS (없으면 전체 코드베이스)

## 사용 에이전트

- **code-reviewer**: 패턴, 상태 관리, 에러 처리, 접근성, 타입, 성능, UX
- **type-checker**: TypeScript strict 모드 준수, any 감지, 제네릭
- **api-auditor**: FE-BE 통합, 프록시, 인증, 타입 일치
- **security-auditor**: 보안 (인증, 입력 검증, CORS, 시크릿)
- **a11y-auditor**: WCAG 2.1 접근성

## 파이프라인

1. **Phase 0**: Quality Gates (tsc + eslint + vitest + build)
2. **Phase 1**: 5개 에이전트 병렬 Verified Review
3. **Phase 2**: Critical/Major 이슈 교차 검증
4. **Phase 3**: 리포트 병합, 중복 제거, 우선순위 할당

## 스코프 옵션

```
/review-full                           # 전체 코드베이스
/review-full --module kiis             # KIIS 모듈만
/review-full --diff                    # git diff 변경 파일
/review-full --module fdd --backend    # FDD FE+BE
/review-full --skip-gates              # Quality Gates 건너뛰기
```

## 실행

review-orchestrate 스킬의 실행 파이프라인을 따릅니다.
`.claude/skills/review-orchestrate/SKILL.md` 참조.
