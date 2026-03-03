# Deep Scan Before Fix (수정 전 파급 범위 분석)

> **핵심**: 눈앞의 에러만 고치지 않는다. 같은 원인에서 파생된 숨겨진 에러까지 찾아서 한 번에 수정한다.

## 적용 시점

사용자가 다음을 요청할 때 **자동 적용**:
- 버그 수정, 에러 해결, 문제 해결, 테스트 실패 수정
- CI 실패 수정, 린트 에러 수정
- "안 된다", "에러가 난다", "고쳐", "수정해" 등의 요청

**기존 RCV 규칙(`bugfix-root-cause-verification.md`)의 Gate 3 이후에 실행한다.**

## 절대 금지

- 실패한 **하나의 파일/테스트만** 보고 수정하는 것
- "이 파일만 고치면 될 것이다"라는 가정
- 모듈 전체 검증 없이 수정 완료 선언

## 필수 절차: Blast Radius Analysis (파급 범위 분석)

근본 원인을 확정한 후(RCV Gate 2), **수정 코드를 작성하기 전에** 반드시:

### Step 1: 심볼 참조 탐색

수정 대상 파일에서 변경되는 **함수명, 클래스명, 상수명, 스키마 필드명**을 특정하고,
같은 모듈 내에서 해당 심볼을 참조하는 **모든 파일**을 `Grep`으로 탐색한다.

```
예시: DocumentCreate 스키마에 필드 추가 시
→ Grep "DocumentCreate" im/ → 참조 파일 N개 발견
→ 각 파일에서 해당 필드 사용 여부 확인
```

### Step 2: 테스트 파일 교차 확인

수정 대상이 **모델/스키마/서비스** 파일이면, 관련 테스트 파일을 반드시 확인한다:
- `app/models/*.py` 수정 → `tests/` 디렉토리에서 해당 모델 참조 탐색
- `app/schemas/*.py` 수정 → 테스트의 mock 데이터가 새 스키마와 일치하는지 확인
- `app/services/*.py` 수정 → 해당 서비스를 호출하는 테스트 확인

### Step 3: 모듈 전체 사전 검증

수정 계획을 세운 후, **수정 전에** 모듈 전체 상태를 확인한다:

```bash
# Python 모듈 (fdd, kiis, im, deal-mgmt)
cd {모듈} && python -m ruff check . 2>&1 | head -20

# 테스트 수집 확인 (실행 없이 테스트 목록만)
cd {모듈} && python -m pytest --co -q -o "addopts=" 2>&1 | tail -5
```

**이미 존재하는 에러가 발견되면**, 현재 수정 대상과 함께 한 번에 해결 계획을 세운다.

### Step 4: 수정 후 전체 검증

모든 수정을 완료한 후, 수정한 파일이 속한 **모듈 전체**를 검증한다:

```bash
# 린트 (0건 필수)
cd {모듈} && python -m ruff check . && python -m ruff format --check .

# 테스트 (전체 통과 필수)
cd {모듈} && python -m pytest tests/ -v --tb=short -o "addopts=" 2>&1
```

## Blast Radius 체크리스트

수정 전 다음 항목을 모두 확인한다:

- [ ] 변경되는 심볼(함수/클래스/상수)을 참조하는 **다른 파일** 목록 확인
- [ ] 해당 심볼을 **import하는 파일** 목록 확인
- [ ] 관련 **테스트 파일**에서 mock 데이터가 최신 스키마와 일치하는지 확인
- [ ] 모듈 전체 **ruff check** 사전 실행 → 기존 숨겨진 린트 에러 발견
- [ ] 모듈 전체 **pytest --co** → 테스트 수집 가능 여부 확인

## 실제 Cascade 사례와 Deep Scan 적용

### 사례 1: 스키마 변경 → 7개 테스트 파일 연쇄 실패 (70201d5)

**기존**: DocumentCreate에 필드 추가 → 테스트 1개 실패 → 수정 → 다음 테스트 실패 → 반복 7회

**Deep Scan 적용 시**:
1. DocumentCreate 변경 확정
2. `Grep "DocumentCreate" im/tests/` → 7개 파일 발견
3. 7개 파일 모두에서 mock 데이터 확인 → 한 번에 전부 수정
4. pytest 전체 실행 → 한 번에 통과

### 사례 2: Python 3.11 호환성 → 3개 연속 CI fix 커밋

**기존**: PEP 695 문법 에러 → 수정 → ruff E741 발견 → 수정 → tsc 에러 발견 → 수정

**Deep Scan 적용 시**:
1. Python 버전 호환성 문제 확정
2. `Grep "type.*\[" im/` → PEP 695 문법 사용처 전수 탐색
3. `ruff check im/` → 기존 숨겨진 린트 에러 사전 발견
4. 모든 문제를 한 커밋에서 해결

## "하나만 고치면 될 것이다" 위반 감지 신호

다음을 생각하거나 쓰려 한다면 **STOP — Blast Radius Analysis로 돌아가기**:

- "이 파일만 수정하면 된다"
- "다른 파일은 영향 없을 것이다"
- "테스트는 나중에 확인하면 된다"
- "ruff는 자동 포맷이 잡아줄 것이다"
- "이 에러만 고치면 CI 통과할 것이다"

## 관련 규칙

- `bugfix-root-cause-verification.md` — RCV Gate 1~3 (원인 확정)
- `python-ci-standards.md` — ruff/타입힌트 강행 규정
- `top5-error-prevention.md` — P1~P9 에러 방지 체크리스트
- `ci-regression-prevention.md` — CI 회귀 방지 8개 Guard
