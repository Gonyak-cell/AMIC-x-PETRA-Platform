---
name: tdd
description: 기능 구현이나 버그 수정 시, 구현 코드 작성 전에 사용. RED-GREEN-IMPROVE 사이클.
---

# Test-Driven Development (TDD)

> 출처: [obra/superpowers](https://github.com/obra/superpowers) — 프로젝트에 맞게 적용

## 핵심 원칙

```
실패하는 테스트 없이 프로덕션 코드 작성 금지
```

테스트 전에 코드를 작성했다면? 삭제하고 다시 시작.

## 사용 시점

**항상:**
- 새 기능
- 버그 수정
- 리팩터링
- 동작 변경

**예외 (사용자에게 확인 후):**
- 일회성 프로토타입
- 생성된 코드 (Alembic 마이그레이션 등)
- 설정 파일

## RED-GREEN-IMPROVE 사이클

### RED — 실패하는 테스트 작성

하나의 최소 테스트로 원하는 동작 정의.

**Python 예시 (pytest):**
```python
def test_rejects_empty_transaction_name():
    with pytest.raises(ValueError, match="거래명은 필수"):
        create_transaction(name="")
```

**TypeScript 예시 (Vitest):**
```typescript
test('rejects empty transaction name', () => {
  expect(() => createTransaction({ name: '' })).toThrow('거래명은 필수');
});
```

**요구사항:**
- 하나의 동작만
- 명확한 이름
- 실제 코드 (모킹은 불가피할 때만)

### RED 검증 — 실패 확인

**필수. 절대 건너뛰지 않기.**

```bash
# 백엔드
pytest tests/test_transactions.py::test_rejects_empty_transaction_name -v

# 프론트엔드
npx vitest run src/modules/ma/__tests__/transactions.test.ts
```

확인:
- 테스트 실패 (에러가 아님)
- 실패 메시지가 예상대로
- 기능 부재 때문에 실패 (오타 아님)

### GREEN — 최소 코드

테스트를 통과하는 가장 간단한 코드 작성.

```python
# Good: 딱 통과할 만큼만
def create_transaction(name: str) -> Transaction:
    if not name.strip():
        raise ValueError("거래명은 필수")
    return Transaction(name=name)
```

```python
# Bad: 과도한 설계 (YAGNI)
def create_transaction(
    name: str,
    validator: Optional[Callable] = None,
    hooks: Optional[List[Hook]] = None,
) -> Transaction:
    ...
```

테스트 이상으로 기능 추가, 리팩터링, "개선" 금지.

### GREEN 검증 — 통과 확인

**필수.**
- 테스트 통과 확인
- 다른 테스트도 여전히 통과 확인
- 경고, 에러 없이 깨끗한 출력

### IMPROVE — 정리

그린 이후에만:
- 중복 제거
- 이름 개선
- 헬퍼 추출

테스트 그린 유지. 동작 추가 금지.

## 좋은 테스트 기준

| 품질 | Good | Bad |
|------|------|-----|
| **최소** | 하나만. 이름에 "and"? 분리. | `test_validates_email_and_domain_and_whitespace` |
| **명확** | 이름이 동작 설명 | `test_test1` |
| **의도 표현** | 원하는 API 시연 | 코드가 무엇을 해야 하는지 불분명 |

## 흔한 합리화

| 핑계 | 현실 |
|------|------|
| "너무 단순해서 테스트 불필요" | 단순한 코드도 깨진다. 테스트 30초면 된다. |
| "나중에 테스트 추가" | 즉시 통과하는 테스트는 아무것도 증명 안 함. |
| "먼저 탐색해야 함" | 좋다. 탐색 후 버리고 TDD로 시작. |
| "TDD가 느리게 만든다" | TDD가 디버깅보다 빠르다. |
| "수동으로 이미 테스트함" | 수동 ≠ 체계적. 기록 없고 재실행 불가. |

## 위험 신호 — 멈추고 다시 시작

- 테스트 전에 코드 작성
- 구현 후 테스트 추가
- 테스트가 즉시 통과
- 테스트가 왜 실패했는지 설명 불가
- "이번만 한 번" 합리화

**모두 의미: 코드 삭제. TDD로 다시 시작.**

## 검증 체크리스트

작업 완료 표시 전:

- [ ] 모든 새 함수/메서드에 테스트 있음
- [ ] 각 테스트가 구현 전 실패하는 것 확인
- [ ] 각 테스트가 예상 이유(기능 부재)로 실패
- [ ] 각 테스트를 통과하는 최소 코드 작성
- [ ] 모든 테스트 통과
- [ ] 깨끗한 출력 (에러, 경고 없음)
- [ ] 실제 코드 사용 (모킹은 불가피할 때만)
- [ ] 엣지 케이스와 에러 커버
