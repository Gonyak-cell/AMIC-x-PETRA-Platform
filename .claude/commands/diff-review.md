---
name: diff-review
description: "Codex CLI(GPT-5.4, xhigh)로 코드 변경 diff 리뷰. 사용법: /diff-review [uncommitted|branch <base>|commit <sha>]"
---

# Diff 리뷰 — Codex CLI (GPT-5.4, reasoning: xhigh)

Codex CLI 내장 `exec review` 서브커맨드를 사용하여 코드 변경사항을 리뷰한다.

## 모드 (3가지)

`$ARGUMENTS` 파싱:
- **인자 없음 또는 `uncommitted`**: staged + unstaged + untracked 변경사항 리뷰
- **`branch <base>`**: 특정 브랜치 대비 변경사항 리뷰 (예: `branch master`, `branch develop`)
- **`commit <sha>`**: 특정 커밋의 변경사항 리뷰 (예: `commit abc123`)

## 실행 순서

### 1. 현재 변경 상태 확인

```bash
git status --short
```

변경사항이 없으면 "리뷰할 변경사항이 없습니다." 안내 후 종료.

### 2. Codex exec review 실행

인자에 따라 아래 중 하나를 Bash 도구로 실행한다 (**timeout: 300000**):

**uncommitted 모드** (기본):
```bash
npx @openai/codex exec review \
  --uncommitted \
  --full-auto \
  --ephemeral \
  -o "/tmp/codex-diff-review.md"
```

**branch 모드**:
```bash
npx @openai/codex exec review \
  --base {브랜치명} \
  --full-auto \
  --ephemeral \
  -o "/tmp/codex-diff-review.md"
```

**commit 모드**:
```bash
npx @openai/codex exec review \
  --commit {커밋SHA} \
  --full-auto \
  --ephemeral \
  -o "/tmp/codex-diff-review.md"
```

### 3. 결과 출력

`/tmp/codex-diff-review.md` 파일을 Read로 읽는다.

**반드시 Codex 리뷰 원문을 그대로 사용자에게 출력한다** (요약/편집/생략 없이 전문 표시).

원문 출력 후, 핵심 포인트를 한글로 간략 요약한다:
```
### Codex Diff 리뷰 요약 (한글)
- 핵심 이슈 1: ...
- 핵심 이슈 2: ...
- 전체 평가: ...
```

### 4. 수정 제안

심각한 이슈가 발견되면 수정을 제안한다.
Codex 원문 코멘트를 인용하여 수정 근거를 제시한다:
```
- [Codex 코멘트] "Potential SQL injection in query parameter"
  → 해당 쿼리에 파라미터 바인딩 적용 제안
```
