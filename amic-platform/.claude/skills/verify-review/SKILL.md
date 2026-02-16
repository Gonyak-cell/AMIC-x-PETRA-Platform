---
name: verify-review
description: 코드 리뷰 문서의 허위 양성(할루시네이션) 검증. 리뷰 항목을 실제 소스 코드와 대조하여 정확성 판정.
user_invocable: true
arguments: "[review-file] [issue-ids...]"
---

# 코드 리뷰 검증 (/verify-review)

코드 리뷰 문서의 모든 이슈 항목을 실제 소스 코드와 대조 검증합니다.

## 사용법

```
/verify-review                          # docs/ 내 최근 코드리뷰 파일 자동 탐색
/verify-review code-review.md           # 특정 파일 지정
/verify-review S-C1 S-C4 M-C1           # 특정 이슈 ID만 검증
/verify-review review.md S-C1 M-C1      # 파일 + 특정 항목
```

## 실행 절차

### Step 1: 리뷰 문서 탐색

인자($ARGUMENTS)를 파싱합니다:

- **인자 없음**: `docs/` 디렉터리에서 `*Code_Review*` 또는 `*Review*` 패턴의 최신 `.md` 파일을 Glob으로 탐색
- **파일명 지정**: 해당 파일을 직접 사용 (docs/ 내 검색, 없으면 전체 검색)
- **이슈 ID만**: `S-C1`, `M-C4` 등 `{심각도}-{카테고리}{번호}` 패턴 감지 → 최근 리뷰 파일에서 해당 항목만 검증
- **파일 + 이슈 ID**: 지정 파일에서 지정 항목만 검증

### Step 2: review-verifier 에이전트 실행

Task 도구로 `review-verifier` 에이전트를 호출합니다:

```
subagent_type: general-purpose
prompt: |
  review-verifier 에이전트 역할로 동작하세요.
  .claude/agents/review-verifier.md의 지침을 따릅니다.

  검증 대상: {리뷰 문서 경로}
  검증 범위: {전체 | 특정 이슈 ID 목록}

  반드시 모든 이슈 항목에 대해 Read/Grep/Glob으로 실제 코드를 확인한 뒤
  5단계 판정(정확/허위양성/부분정확/설계리스크/라인불일치)을 부여하세요.
  허위 양성은 6종 원인(FP-IMPL/FP-HALLUC/FP-LINE/FP-LOGIC/FP-CTX/FP-SEV) 분류 필수.
```

### Step 3: 결과 보고서 저장

검증 결과를 `docs/` 디렉터리에 타임스탬프 파일명으로 저장합니다:
- 형식: `docs/YYYYMMDD_HHMM_Review_Verification.md`
- PowerShell로 현재 시간 확인 후 파일명 생성

### Step 4: 요약 출력

사용자에게 아래 요약을 출력합니다:

```
## 검증 완료

- 총 이슈: N건
- 정확: N건 / 허위 양성: N건 / 부분 정확: N건
- 허위 양성율: X%
- 수정 필요 이슈: N건 (P0: N, P1: N, P2: N)
- 보고서: docs/YYYYMMDD_HHMM_Review_Verification.md

⚠️ 수정 작업은 검증된 유효 이슈(정확 + 부분 정확)만 대상으로 진행하세요.
```

## 주의사항

- 검증 없이 코드 리뷰 항목을 수정하지 마세요
- 허위 양성으로 판정된 항목은 수정 대상에서 제외됩니다
- 부분 정확 항목은 수정 심각도를 재조정한 뒤 진행합니다
- 백엔드 코드가 필요한 경우 `Auto FDD/backend/`, `KIIS/`, `IM Module/` 경로를 참조합니다
