# Code Review — Deal Setup AI Agent + VDR Prompt Guard

> **Review Date**: 2026-03-06 23:54 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 신규 BE 4파일 + FE 3파일 + 수정 BE 2파일 + FE 1파일
> **Method**: Quality Gates + 3-Agent Parallel Review + Cross-Verification
> **Quality Gates**: tsc(PASS) ruff-check(PASS after fix) ruff-format(PASS)

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Critical | 1     | HIGH: 1    | P0: 1    |
| Major    | 4     | HIGH: 4    | P1: 4    |
| Moderate | 4     | HIGH: 3 / MEDIUM: 1 | P2: 4 |
| Minor    | 5     | HIGH: 3 / MEDIUM: 2 | P3: 5 |
| **Total**| **14**| HIGH: **11** / MEDIUM: **3** | P0: **1** / P1: **4** / P2: **4** / P3: **5** |

**Quality Gate Fix**: `main.py`에서 `deal_setup` import 누락 발견 — 즉시 수정 완료 (ruff F821)

---

## P0 — 즉시 수정 (재무 데이터 정확성)

### [C-1] estimated_deal_value float 사용 — Critical/HIGH (점수: 100)

**파일**: `deal-mgmt/app/schemas/deal_setup.py:43`
**교차 검증**: BE Python + Security 에이전트 동시 발견

```python
estimated_deal_value: float | None = None  # float 사용
```

기존 `TransactionCreate` 스키마는 `Decimal | None`, DB 컬럼은 `Numeric(20,2)`. 서비스에서 `Decimal(str(...))` 변환하지만 JSON 직렬화 중간 단계에서 부동소수점 오차 유입 가능.

**수정**: `float` -> `Decimal`으로 변경. FE도 `number` -> `string`으로 동기화.

---

## P1 — 스프린트 우선 (안정성/보안)

### [M-1] 에러 응답에 예외 객체 직접 노출 — Major/HIGH (점수: 70)

**파일**: `deal-mgmt/app/routers/deal_setup.py:54-57, 88-91`
**교차 검증**: BE Python + Security 에이전트 동시 발견

```python
detail=f"AI 분석에 실패했습니다: {exc}"  # exc 직접 노출
```

LLM API 키, 내부 경로 등이 클라이언트에 노출될 수 있음.

**수정**: 고정 문자열 사용, 상세 오류는 `logger.exception`으로만 기록.

### [M-2] BuyerTier `NOT_TARGET` FE 타입 누락 — Major/HIGH (점수: 70)

**파일**: `amic-platform/src/modules/ma/types/dealSetup.ts:34`

```typescript
export type BuyerTier = "TIER_1" | "TIER_2" | "TIER_3" | null;
// BE enum에 "NOT_TARGET" 존재 (enums.py:97)
```

AI가 `NOT_TARGET`을 반환하면 FE 타입 안전성 깨짐.

**수정**: `"NOT_TARGET"` 추가.

### [M-3] Confirm 스키마에 리스트 크기 제한 없음 — Major/HIGH (점수: 70)

**파일**: `deal-mgmt/app/schemas/deal_setup.py` (DealSetupConfirm)

`dd_checklist`, `timeline`, `buyer_candidates` 리스트에 `max_length` 미설정. 공격자가 수천 개 항목을 INSERT 가능.

**수정**: `Field(..., max_length=50/30/20)` 추가.

### [M-4] 엑셀 경로 프롬프트 인젝션 사전 필터 없음 — Major/HIGH (점수: 70)

**파일**: `deal-mgmt/app/services/deal_setup_service.py:75`

엑셀 셀에 `Ignore previous instructions` 등을 삽입 가능. VDR Q&A는 `_validate_question()`이 있으나 deal_setup에는 없음.

**수정**: deal_setup_service에도 입력 사전 검증 추가 또는 프롬프트에 `<excel_data>` 구분자 사용.

---

## P2 — 개선 권장 (코드 품질)

### [m-1] event_type str — Enum 미검증 — Moderate/HIGH (점수: 40)

**파일**: `deal-mgmt/app/schemas/deal_setup.py:63`

`event_type: str`로 자유 문자열. DD 체크리스트의 `workstream`은 Enum으로 검증되는 것과 불일치.

### [m-2] 인메모리 대화 히스토리 메모리 누수 — Moderate/HIGH (점수: 40)

**파일**: `deal-mgmt/app/services/vdr_qa_service.py:33` (기존 코드)

`_conversation_store`에 TTL/maxsize 없음. 장시간 운영 시 메모리 증가.

### [m-3] _generate_code_name private 함수 직접 import — Moderate/HIGH (점수: 40)

**파일**: `deal-mgmt/app/services/deal_setup_service.py:123`

`_` 접두사 private 함수를 외부 모듈에서 import. 리팩토링 시 파손 위험.

### [m-4] useCallback 의존성 배열 비효율 — Moderate/MEDIUM (점수: 24)

**파일**: `amic-platform/src/modules/ma/pages/DealSetupWizardPage.tsx:389-421`

`useMutation` 반환 객체가 매 렌더마다 새 참조 -> `useCallback` 메모이제이션 무효화. 성능 영향은 미미하나 의도와 불일치.

---

## P3 — 저우선 (개선 가능)

### [L-1] 드래그 앤 드롭 미구현 — Minor/HIGH

**파일**: `DealSetupWizardPage.tsx:633-649` — UI 텍스트에 "드래그하거나"라고 안내하지만 `onDrop` 핸들러 없음.

### [L-2] CreateTransactionPage.tsx 데드 코드 — Minor/HIGH

MaRoutes에서 더 이상 참조하지 않는 파일이 잔존. 의도적 보존이면 주석 명시.

### [L-3] Button loading + 내부 Loader2 이중 표시 — Minor/MEDIUM

**파일**: `DealSetupWizardPage.tsx:665-686` — `loading` prop과 children 내 `Loader2` 동시 사용.

### [L-4] AI 분석 에러 시 인라인 메시지 부재 — Minor/MEDIUM

Toast만 표시. `isError` 상태 활용한 인라인 에러 메시지 추가 권장.

### [L-5] LLM 재시도 시 비용 추적 부정확 — Minor/HIGH

**파일**: `deal_setup_service.py:79-108` — 재시도 실패 시 비용이 로그에 기록되지 않음.

---

## Passed Checks

- [x] 모든 엔드포인트에 `require_write_access()` 인증 적용
- [x] SQL 인젝션 없음 (SQLAlchemy ORM 사용)
- [x] 하드코딩된 시크릿/API 키 없음
- [x] 파일 업로드 검증 (확장자 + 10MB 크기 제한)
- [x] N+1 쿼리 없음 (벌크 INSERT 패턴)
- [x] XSS 방어 (dangerouslySetInnerHTML 미사용)
- [x] Pydantic Enum 검증 (DealType, TransactionSide, DDWorkstream, BuyerType)
- [x] UI variant 유효 (Badge, Button, Tabs 컴포넌트)
- [x] VDR 프롬프트 가드 이중 방어 (_validate_question + _sanitize_answer)
- [x] async/await 일관 사용
- [x] 타입 힌트 완전성
- [x] ruff check / tsc --noEmit 통과

## Methodology

- **Agents**: python-code-reviewer, backend-security-reviewer, superpowers:code-reviewer
- **Files scanned**: 10 (BE 6 + FE 4)
- **Protocol**: Verified Claim Protocol v1.1
- **Cross-verification**: Critical + Major (5건 중 2건 교차 확인됨)
- **False Positives removed**: 0건
- **Duplicates merged**: 3건 (에러 노출, event_type, 메모리 누수)
