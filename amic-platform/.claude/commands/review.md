---
name: review
description: 코드 리뷰를 수행합니다. Verified Claim Protocol 적용. code-reviewer 에이전트 활용.
---
# 코드 리뷰

code-reviewer 에이전트를 활용하여 Verified Claim Protocol 기반 리뷰를 수행합니다.

대상: $ARGUMENTS (없으면 git diff로 변경된 파일 전체)

## 스코프 파싱

인자($ARGUMENTS)를 분석합니다:

- **인자 없음**: `git diff --name-only HEAD`로 변경된 `.ts`, `.tsx` 파일 전체
- **`--diff [branch]`**: 지정 브랜치 대비 변경 파일 (`git diff --name-only [branch]...HEAD`)
- **`--module fdd|kiis|im|platform`**: 해당 모듈 디렉터리로 스코프 제한
- **`--files path1 path2 ...`**: 특정 파일만 리뷰
- **파일 경로 직접 지정**: `src/modules/fdd/hooks/useDeals.ts` 등

## 리뷰 절차

### Phase 0: 대상 파일 확인
1. 스코프에 따라 대상 파일 목록 확정
2. 파일이 없으면 "리뷰 대상 파일이 없습니다" 안내

### Phase 1: Verified Review
Task 도구로 `code-reviewer` 에이전트를 호출합니다:

```
subagent_type: general-purpose
prompt: |
  code-reviewer 에이전트 역할로 동작하세요.
  .claude/agents/code-reviewer.md의 지침과
  .claude/rules/verified-claim-protocol.md의 프로토콜을 따릅니다.

  리뷰 대상 파일: {파일 목록}

  모든 이슈에 대해 반드시:
  1. Read로 실제 코드를 확인한 뒤 클레임
  2. 증거(실제 코드 스니펫) 첨부
  3. 신뢰도 점수 (HIGH/MEDIUM/LOW) 부여
  4. 가설이 반증되면 보고하지 않기

  출력은 Verified Claim Protocol 표준 형식을 따릅니다.
```

### Phase 2: 결과 정리
1. 심각도별 분류: Critical > Major > Moderate > Minor
2. 우선순위 할당: P0(즉시) > P1(우선) > P2(개선) > P3(저우선)
3. 검증 투명성 섹션 포함 (가설 검증/거부 카운트)

## 출력 요약

```
## 리뷰 완료

- 대상 파일: N개
- 발견 이슈: N건 (Critical: N, Major: N, Moderate: N, Minor: N)
- 검증 투명성: 가설 N건 검증, N건 거부
- 수정 필요: N건 (P0: N, P1: N, P2: N)
```
