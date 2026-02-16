---
name: auto-verify
description: 보통(Moderate) 및 경미(Minor) 이슈 자동 검증. 파일 존재, 라인 번호, 코드 스니펫, 패턴 주장을 자동 검증하여 허위 양성 탐지.
user_invocable: false
arguments: "issues_json"
---

# Auto-Verify 스킬

**작성일**: 2026-02-16 19:21:44
**목적**: 보통(Moderate) 및 경미(Minor) 이슈의 자동 검증으로 검증 범위 100% 달성

---

## 개요

코드 리뷰 오케스트레이터의 Phase 2B에서 호출됩니다.

**검증 대상**: Phase 2(교차 검증)에서 다루지 않는 **Moderate** 및 **Minor** 이슈

**검증 방법**: 4단계 자동 체크로 허위 양성 탐지

---

## 입력 형식

JSON 배열로 이슈 목록을 전달받습니다:

```json
[
  {
    "id": "[m-R1]",
    "severity": "Moderate",
    "file": "src/components/ui/Button.tsx",
    "line": 42,
    "line_range": "40-45",
    "code_snippet": "const handleClick = () => { ... }",
    "claim_type": "exists|missing|wrong_usage",
    "claim_pattern": "error handling",
    "description": "에러 처리 누락"
  }
]
```

---

## 검증 단계

### 1단계: 파일 존재 확인 (25점)

**방법**:
```bash
Glob: {file}
```

**점수**:
- 파일 발견: +25
- 파일 없음: 0 (즉시 **허위 양성** 플래그)

**결과**:
```
✓ 파일 존재: src/components/ui/Button.tsx
```

---

### 2단계: 라인 번호 검증 (25점)

**방법**:
1. Read 도구로 파일의 `{line} ± 10` 범위 읽기
2. 보고된 라인 번호가 `{line} ± 5` 이내에 존재하는지 확인

**점수**:
- 정확 매칭 (±0 라인): +25
- 근접 매칭 (±1~5 라인): +20
- 범위 초과 (±6~10 라인): +10
- 범위 밖 (±10 초과): 0 (허위 양성 플래그)

**결과**:
```
✓ 라인 42 확인됨 (±0 라인)
```

---

### 3단계: 코드 스니펫 매칭 (50점)

**방법**:
1. 보고된 `code_snippet`을 정규화 (공백, 주석 제거)
2. Read한 실제 코드에서 유사 코드 검색
3. 퍼지 매칭 점수 계산 (Levenshtein 거리 기반 유사도)

**퍼지 매칭 알고리즘** (간소화):
- 정확 매칭 (100%): +50
- 높은 유사도 (80-99%): +40
- 중간 유사도 (60-79%): +25
- 낮은 유사도 (<60%): 0 (허위 양성 플래그)

**정규화 규칙**:
- 연속 공백 → 단일 스페이스
- 주석 제거 (`//`, `/**/`)
- 들여쓰기 무시

**결과**:
```
✓ 코드 스니펫 매칭: 92% 유사도
  보고된 코드: const handleClick = () => { ... }
  실제 코드:   const handleClick = () => { onClick?.(); }
```

---

### 4단계: 패턴 주장 검증 (선택적)

**적용 대상**: `claim_type === "missing"` (예: "X가 없다")

**방법**:
```bash
Grep: "{claim_pattern}"
  - path: {file의 디렉터리}
  - output_mode: count
```

**검증 로직**:
- **"X가 없다" 주장** + Grep 0건 → ✓ 주장 정확 (+보너스 10)
- **"X가 없다" 주장** + Grep 1+ 건 → ✗ 반증됨 (즉시 허위 양성 플래그)

**결과**:
```
✓ 패턴 주장 검증: "error handling" Grep 0건 → 부재 확인됨 (+10)
```

---

## 점수 계산 및 판정

**총점**: 1단계(25) + 2단계(25) + 3단계(50) + 4단계(선택적 10) = 최대 110점

**판정 기준**:
- **≥ 75점**: 검증됨 (이슈 유지)
- **< 75점**: 허위 양성 가능성 → 수동 검토 플래그

**예시**:
1. 파일(25) + 라인 정확(25) + 코드 높은 유사도(40) = 90 → ✓ 검증됨
2. 파일(25) + 라인 근접(20) + 코드 중간 유사도(25) = 70 → ✗ 수동 검토
3. 파일(25) + 라인 범위 초과(10) + 코드 낮은 유사도(0) = 35 → ✗ 수동 검토

---

## 출력 형식

각 이슈에 대한 검증 결과를 JSON으로 반환:

```json
{
  "verified": [
    {
      "id": "[m-R1]",
      "score": 90,
      "breakdown": {
        "file_exists": 25,
        "line_match": 25,
        "code_similarity": 40,
        "pattern_claim": 0
      },
      "status": "verified",
      "notes": "라인 42 정확 매칭, 코드 92% 유사도"
    }
  ],
  "flagged": [
    {
      "id": "[m-R2]",
      "score": 45,
      "breakdown": {
        "file_exists": 25,
        "line_match": 20,
        "code_similarity": 0,
        "pattern_claim": 0
      },
      "status": "manual_review_required",
      "reason": "코드 스니펫 불일치 (45% 유사도)",
      "notes": "보고된 코드가 실제 파일에서 발견되지 않음"
    }
  ],
  "summary": {
    "total": 23,
    "verified": 18,
    "flagged": 5,
    "verification_rate": "78%"
  }
}
```

---

## 통합 방법

review-orchestrate/SKILL.md의 Phase 2 뒤에 Phase 2B 삽입:

```markdown
### Phase 2B: Auto-Verification (자동 검증)

Phase 2(교차 검증)는 Critical + Major만 대상이므로, Moderate + Minor 이슈를 자동 검증합니다.

1. Moderate 및 Minor 이슈 목록을 JSON으로 변환
2. auto-verify 스킬 호출:
   ```
   /auto-verify {issues_json}
   ```
3. 검증 결과 처리:
   - `verified`: 이슈 유지
   - `flagged`: "수동 검토 필요" 표시 추가, 우선순위 하향 (P3 → P4)

결과 보고:
- "자동 검증: Moderate 이슈 18/23건 검증됨, 5건 수동 검토 플래그"
```

---

## 성공 지표

- **검증 범위**: 100% (현재 30% → 목표 100%)
- **정확도**: 허위 양성 95% 이상 탐지
- **처리 시간**: 이슈당 평균 <2초

---

## 제한사항

이 스킬은 다음을 검증할 수 없습니다:
- **논리적 오류**: 코드가 존재하지만 잘못 작성됨 (수동 검증 필요)
- **런타임 동작**: 실제 실행 결과 (통합 테스트 필요)
- **백엔드 응답**: API 응답 형식 (실제 백엔드 코드 읽기 필요)

이러한 경우 MEDIUM 이하 신뢰도를 부여하고 수동 검토를 권장합니다.

---

## 롤백 계획

Phase 2B가 오판을 많이 발생시키면:
- review-orchestrate에서 Phase 2B 비활성화
- 다시 Critical + Major만 검증 (Phase 2)으로 복귀

---

**문서 종료** — review-orchestrate에 통합 준비 완료.
