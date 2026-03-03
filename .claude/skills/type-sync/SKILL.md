---
name: type-sync
description: "BE↔FE 타입 동기화 검증. /type-sync [module]. 예: /type-sync kiis"
user-invocable: true
---

# BE ↔ FE Type Sync Validator

대상: $ARGUMENTS (deal-mgmt / ma / kiis / fdd / im / 미지정=전체)

## Module Path Mapping

| 인자 | BE 스키마 경로 | FE 타입 경로 |
|------|-------------|------------|
| `deal-mgmt` 또는 `ma` | `deal-mgmt/app/schemas/` | `amic-platform/src/modules/ma/types/` |
| `kiis` | `kiis/app/schemas/` | `amic-platform/src/modules/kiis/types/` |
| `fdd` | `fdd/backend/app/schemas/` | `amic-platform/src/modules/fdd/types/` |
| `im` | `im/src/api/schemas/` | `amic-platform/src/modules/im/types/` |

## Type Mapping Rules

| BE (Python) | FE (TypeScript) | 위반 판정 |
|-------------|----------------|---------|
| `uuid.UUID` | `string` | `number` 사용 시 ❌ |
| `Decimal` | `string` | `number` 사용 시 ❌ **P2 위반** |
| `datetime` | `string` (ISO 8601) | `Date` 사용 시 ❌ |
| `Enum(str, Enum)` | union literal type | 값 불일치 시 ❌ **P1 위반** |
| `T \| None` | `T \| null` | `T?` (optional field) 혼동 시 ⚠️ |
| `dict[str, T]` | `Record<string, T>` | `object` 또는 `any` 사용 시 ⚠️ |
| `list[T]` | `T[]` 또는 `Array<T>` | ✅ 양쪽 허용 |
| `int` / `float` | `number` | ✅ (Decimal 제외) |
| `bool` | `boolean` | ✅ |
| `str` | `string` | ✅ |

## Steps

### Step 1: BE Enum 수집

대상 모듈의 schemas/ 디렉토리에서 모든 `.py` 파일을 Glob으로 수집.
각 파일에서 다음 패턴을 Grep:

```
class \w+\(str,\s*Enum\)
```

각 Enum 클래스의 멤버(값)를 Read로 수집하여 목록화.
또한 models/ 디렉토리의 enums.py가 있으면 함께 수집:
- `{module}/app/models/enums.py`
- `{module}/app/models/*.py` 내 Enum 정의

### Step 2: FE 타입 수집

대상 모듈의 FE types/ 디렉토리에서 모든 `.ts` 파일을 Glob으로 수집.
각 파일에서 다음 패턴을 Grep:

```
export type \w+ =
```

union literal의 각 값(`"VALUE1" | "VALUE2"`)을 파싱하여 목록화.

### Step 3: Enum 1:1 대조

BE Enum 이름과 FE type 이름이 동일하거나 유사한 것을 매칭.
매칭 기준:
- 정확히 동일한 이름 (예: `ClosingCategory` ↔ `ClosingCategory`)
- BE snake_case → FE PascalCase 변환 매칭
- 같은 파일 주제 내 유사 이름 (예: `closing.py` ↔ `closing.ts`)

각 매칭 쌍에 대해:
- BE 멤버 값 집합 vs FE 리터럴 값 집합 비교
- 차이가 있으면 ❌ MISMATCH 기록

### Step 4: 응답 스키마 필드 타입 검증

BE의 주요 Response 스키마(이름에 `Out`, `Read`, `Response`, `List` 포함)에서 필드 타입을 Read.
대응하는 FE interface에서 동일 필드명의 타입을 Read.

검증:
- `Decimal` 필드가 FE에서 `number`로 되어 있으면 ❌ P2 위반
- `uuid.UUID` 필드가 FE에서 `string`이 아니면 ❌
- `datetime` 필드가 FE에서 `Date`이면 ❌
- `T | None` 필드가 FE에서 `T?`(optional)이면 ⚠️ 경고

### Step 5: 결과 리포트 출력

아래 형식으로 결과 출력:

```markdown
## Type Sync Report: {module}

### Enum 검증
| BE Enum | FE Type | 상태 | 상세 |
|---------|---------|------|------|

### 타입 매핑 검증
| BE 스키마.필드 | FE 인터페이스.필드 | BE 타입 | FE 타입 | 상태 |
|-------------|----------------|--------|--------|------|

### 요약
- 검증 파일: BE {n}개, FE {n}개
- Enum 검증: ✅ {n}건 일치, ❌ {n}건 불일치
- 필드 타입: ✅ {n}건 정상, ❌ {n}건 위반, ⚠️ {n}건 경고
```

## Notes

- 이 스킬은 읽기 전용 (Read, Grep, Glob만 사용)
- 불일치 발견 시 수정은 하지 않고 리포트만 생성
- 수정이 필요한 경우 사용자에게 보고 후 승인 받아 진행
