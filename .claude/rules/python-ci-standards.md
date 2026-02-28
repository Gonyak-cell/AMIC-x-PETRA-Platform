# Python CI 강행 규정 (최우선 적용)

> **핵심**: 이 규칙은 모든 Python 코드 작성 시 최우선으로 적용된다.
> CI 파이프라인 검증 기준을 위반한 코드는 오답으로 간주한다.

## 적용 시점

**모든 Python 코드 작성/수정 시 자동 적용.**
기능 개발, 리팩토링, 버그 수정, 테스트 등 어떤 작업이든 동일하게 적용된다.

## 역할

복잡한 논리 연산(문서 비교 대조, 재무 데이터 파싱 등)을 수행하는 Python 애플리케이션을 개발하는 **시니어 엔지니어**.
기능적 완전성뿐만 아니라 아래 CI 검증 기준을 100% 통과해야 한다.

---

## 강행 규정 1: 린팅 및 포맷팅 (Ruff 강제 적용)

- 모든 코드는 PEP 8을 엄수한다.
- `ruff check` 및 `ruff format` 실행 시 **경고(Warning)도 에러(Error)도 0건**이어야 한다.
- 불필요한 import는 **엄격히 금지**한다.
- 미사용 변수는 **즉시 제거**한다.

### 코드 작성 후 필수 검증

```bash
# 모듈 디렉토리에서 실행
cd {모듈} && python -m ruff check . && python -m ruff format --check .
```

위 명령어에서 **1건이라도 경고/에러가 발생하면 수정 후 재검증**한다.

---

## 강행 규정 2: 실행 환경 및 의존성

- **Python 3.10** 환경의 **Linux(Ubuntu) 컨테이너**에서 실행됨을 전제로 작성한다.
- 특정 OS(Windows/Mac)에 종속적인 파일 경로 표기를 **금지**한다:
  - ❌ 역슬래시(`\`) 사용 금지
  - ❌ 하드코딩된 절대 경로 금지 (예: `C:\Users\...`, `/Users/...`)
- 반드시 `pathlib` 또는 `os.path` 모듈을 사용하여 **환경 독립적**으로 작성한다:

```python
# ✅ 올바른 패턴
from pathlib import Path

base_dir = Path(__file__).resolve().parent
data_file = base_dir / "db" / "data.csv"

# ❌ 금지 패턴
data_file = "C:\\Users\\data\\db\\data.csv"
data_file = "/opt/app/db/data.csv"
```

---

## 강행 규정 3: 타입 힌팅 (Type Hinting)

- 모든 함수와 메서드 선언부에 **매개변수와 반환값**의 타입 힌트를 기재한다.
- CI 파이프라인의 정적 분석 통과 목적.

```python
# ✅ 올바른 패턴
def calculate_total(items: list[Decimal], tax_rate: Decimal) -> Decimal:
    ...

def find_matching_codes(
    source: pd.DataFrame,
    target_codes: set[str],
) -> dict[str, list[str]]:
    ...

async def get_transactions(
    db: AsyncSession,
    fund_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[TransactionResponse]:
    ...

# ❌ 금지 패턴 — 타입 힌트 누락
def calculate_total(items, tax_rate):
    ...
```

---

## 위반 감지 신호

다음을 쓰거나 생각하려 한다면 **STOP — 이 규칙으로 돌아가기**:
- 타입 힌트 없이 함수를 작성하려 함
- `\`를 포함한 파일 경로를 하드코딩하려 함
- `import` 후 해당 모듈/함수를 사용하지 않음
- 변수를 할당 후 참조하지 않음
- ruff 검증 없이 코드를 최종 제출하려 함

## 관련 규칙

- `.claude/rules/python-style.md` — 네이밍, 스키마, 에러 처리 등 상세 스타일
- `.claude/rules/ci-regression-prevention.md` — CI 회귀 방지 (SQLAlchemy, pyproject.toml 등)
