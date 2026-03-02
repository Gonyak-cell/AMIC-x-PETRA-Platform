# SPA 계약서 역분석 시스템 — 에러 로그 정리 + 코드 리뷰 프롬프트

> 작성: 2026-03-02 12:10 KST
> 소스: `logs/errors.jsonl` (SPA/계약서 관련 24건)
> 기간: 2026-02-27 ~ 2026-03-02

---

## 1. 에러 로그 정리 (24건, 빈도순)

### 카테고리 분포

| 카테고리 | 건수 | 비율 |
|---------|------|------|
| test | 13건 | 54% |
| lint | 9건 | 38% |
| other | 2건 | 8% |

---

### 에러 패턴별 상세

#### E1. ruff check 에러 (10건, 42%) — **최다 빈도**

| 발생 시각 | 대상 파일 | 에러 내용 |
|----------|----------|----------|
| 03-01 01:05 | `app/routers/consortium.py` 등 | 미사용 import (F401: `Query`, `status`) |
| 03-01 21:35 | `app/models/contract_clause.py` 등 | 2건 에러 (상세 미포함) |
| 03-01 23:13 | `app/services/contract_generation_service.py` | UP041: `asyncio.TimeoutError` → `TimeoutError` 교체 필요 |
| 03-01 23:39 | `app/schemas/contract*.py` | 5건 에러 → 1건으로 감소 반복 |
| 03-01 23:58 | `app/services/contract_generation_service.py` | F401: Jinja2 미사용 import (`BaseLoader`, `StrictUndefined` 등) |
| 03-02 01:20 | `app/services/contract_generation_service.py` | 1건 에러 |
| 03-02 01:39 | `app/ + tests/test_contract*` | 1건 에러 |
| 03-02 10:36 | `app/schemas/spa_analysis.py` | B017: `pytest.raises`에 `match=` 누락 |

**패턴 요약**:
- `contract_generation_service.py`: 반복적 린트 실패 (UP041 asyncio.TimeoutError, F401 미사용 import)
- `spa_analysis.py` 스키마/테스트: B017 pytest.raises match 누락
- 수정 → 재검증 사이클이 3~4회 반복되는 패턴

#### E2. ruff format 위반 (4건, 17%)

| 발생 시각 | 대상 파일 |
|----------|----------|
| 03-01 01:05 | `buyer_marketing.py`, `buyers.py` |
| 03-01 21:35 | `contract_clause.py`, `template_variable.py`, `contract_generation.py`, `contract_export_service.py` |
| 03-01 23:13 | `contract_generation.py` |
| 03-01 23:39 | `contract_generation.py`, `seed_contract_templates.py` |

**패턴 요약**: 계약서 관련 모델/라우터/서비스 4개 파일이 포맷 미적용 상태로 반복 감지

#### E3. pytest-cov 인자 미인식 (3건, 13%)

```
ERROR: unrecognized arguments: --cov=app --cov-report=xml --cov-fail-under=60
```

| 발생 시각 | 대상 |
|----------|------|
| 03-01 21:38, 23:39, 23:58 | `tests/test_contract_generation.py` |

**원인**: `pytest-cov` 패키지 미설치 상태에서 `--cov` 옵션 사용

#### E4. F401 미사용 import (1건)

```
F401: `.exceptions.DataOverflowError` imported but unused
```

**파일**: `app/pptx/template*.py` 계열

#### E5. UP041 asyncio.TimeoutError (1건)

```python
# 현재 (위반)
except asyncio.TimeoutError:
# 올바른 패턴
except TimeoutError:
```

**파일**: `app/services/contract_generation_service.py:151`

#### E6. 파일 미존재 (1건)

**시각**: 02-27 12:22
**원인**: 잘못된 파일 경로 참조

#### E7. B017 pytest.raises match 누락 (1건)

```python
# 현재 (위반) — test_spa_analysis.py:36, 72
with pytest.raises(Exception, match="ensure this value has at least 100 characters|at least 100"):
```

**파일**: `tests/test_spa_analysis.py`

---

## 2. 핵심 위험 요약

| 우선순위 | 위험 | 영향 | 대상 파일 |
|---------|------|------|----------|
| **P0** | ruff check/format 미통과 | CI 실패 | `contract_generation_service.py`, `contract_clause.py`, `template_variable.py` |
| **P1** | UP041 asyncio.TimeoutError | CI 린트 실패 | `contract_generation_service.py:151` |
| **P1** | F401 미사용 import | CI 린트 실패 | `contract_generation_service.py` (Jinja2 관련) |
| **P2** | pytest-cov 미설치 | 커버리지 측정 불가 | `pyproject.toml` dev 의존성 |
| **P2** | B017 pytest.raises | 린트 경고 | `test_spa_analysis.py` |
| **P3** | ruff format 미적용 | CI 실패 | 4개 파일 |

---

## 3. 코드 리뷰 프롬프트

아래 프롬프트를 새 세션에서 사용하여 SPA 역분석 시스템 전체를 한꺼번에 리뷰할 수 있습니다.

---

### 프롬프트 시작

```
SPA 계약서 역분석 시스템 전체 코드 리뷰를 진행해주세요.

## 리뷰 대상 파일 (10개)

### 백엔드 (Python, deal-mgmt/)
1. `deal-mgmt/app/routers/spa_analysis.py` — API 엔드포인트 (3개 Step)
2. `deal-mgmt/app/schemas/spa_analysis.py` — Pydantic 스키마
3. `deal-mgmt/app/services/spa_analysis_service.py` — LLM 호출 + 분석 로직 핵심
4. `deal-mgmt/tests/test_spa_analysis.py` — 테스트 (50+ 케이스)

### 프론트엔드 (TypeScript/React, amic-platform/src/modules/docs/)
5. `pages/SpaAnalysisPage.tsx` — 진입 페이지
6. `components/SpaAnalysisWizard.tsx` — 4단계 위저드 UI
7. `components/SpaTextInput.tsx` — Step 0 텍스트 입력
8. `components/AnalysisReviewPanel.tsx` — Step 1/2 리뷰 패널
9. `hooks/useSpaAnalysis.ts` — API 훅 (React Query)
10. `types/spa_analysis.ts` — TypeScript 타입 정의

### 관련 기존 파일 (계약서 생성 시스템과의 연동 확인)
11. `deal-mgmt/app/routers/contract_generation.py`
12. `deal-mgmt/app/services/contract_generation_service.py`
13. `deal-mgmt/app/models/contract.py` (ContractTemplate, ContractClause, TemplateVariable)

## 실제 에러 로그 기반 집중 점검 항목

아래는 개발 중 실제 발생한 24건의 에러 로그에서 도출한 반복 패턴입니다. 리뷰 시 이 항목들을 **최우선으로** 확인해주세요:

### [P0] ruff check/format 통과 여부
- `contract_generation_service.py`: UP041 (`asyncio.TimeoutError` → `TimeoutError`), F401 (미사용 Jinja2 import)
- `contract_clause.py`, `template_variable.py`: ruff format 미적용
- `spa_analysis.py` 스키마: 린트 에러 존재 여부
- **검증**: 각 파일에 대해 `ruff check` + `ruff format --check` 제로 에러 확인

### [P1] pytest-cov 의존성
- `pytest-cov`가 `pyproject.toml`의 `[project.optional-dependencies] dev` 에 등록되어 있는지 확인
- `--cov` 옵션 사용하는 pytest 설정이 있다면 의존성과 일치하는지 확인

### [P2] B017 pytest.raises match= 누락
- `test_spa_analysis.py`에서 `pytest.raises(Exception)` 사용 시 `match=` 인자 유무
- ruff B017 규칙 준수 여부

## 일반 리뷰 항목

### 백엔드 (Python)
1. **보안**: 인증 Depends 주입 여부 (deal-mgmt: `get_jwt_claims`), Rate Limiting 우회 가능성
2. **LLM 프롬프트**: 프롬프트 인젝션 방지, JSON 파싱 실패 처리, 비용 제한 ($5/세션)
3. **세션 관리**: 인메모리 세션의 TTL(30분) 적정성, 멀티워커 환경 세션 유실 처리
4. **타입 힌팅**: 모든 함수에 매개변수/반환값 타입 힌트 존재 여부
5. **크로스 DB 호환**: `Uuid` + `JSON().with_variant(JSONB, "postgresql")` 패턴 준수 (SQLite CI 호환)
6. **에러 처리**: Step 간 실패 시 롤백/재시도 로직, LLM 응답 파싱 실패 핸들링
7. **데이터 직렬화**: Decimal/UUID/Enum → JSON 변환 시 `_sanitize_for_json()` 거치는지

### 프론트엔드 (TypeScript/React)
1. **타입 일치**: Python Pydantic 스키마 ↔ TypeScript 타입 리터럴 정확히 대응하는지
2. **에러 처리**: 429(Rate Limit), 503(LLM 불가), 422(검증 실패) 각각 적절한 사용자 메시지
3. **XSS 방지**: SafeHtml 컴포넌트의 sanitize 로직 (script/style/event handler 제거)
4. **접근성**: aria 속성, 포커스 관리, 키보드 네비게이션
5. **상태 관리**: Step 간 전환 시 데이터 유실 방지, 뒤로 가기 처리

### 아키텍처
1. **계약서 생성 시스템 연동**: Step 3에서 DB 저장한 템플릿이 `ContractGeneratorPage`에서 정상 로드되는지
2. **모델 관계**: ContractTemplate → ContractClause (1:N), ContractTemplate → TemplateVariable (1:N) FK 정합성
3. **중복 제거**: variable_key, clause_order 유니크 제약 적용 여부

## 출력 형식

리뷰 결과를 아래 형식으로 정리해주세요:

### 요약
- 전체 파일 수, 발견 이슈 수, 심각도별 분포

### 이슈 목록 (심각도순)
| # | 심각도 | 파일:라인 | 이슈 | 수정 제안 |
|---|--------|----------|------|----------|

### ruff 검증 결과
각 Python 파일에 대해 `ruff check` + `ruff format --check` 실행 결과

### BE-FE 타입 일치 검증
Python Enum/리터럴 ↔ TypeScript 타입 대조표
```

### 프롬프트 끝

---

## 4. 파일 경로 빠른 참조

```
# 백엔드
deal-mgmt/app/routers/spa_analysis.py
deal-mgmt/app/schemas/spa_analysis.py
deal-mgmt/app/services/spa_analysis_service.py
deal-mgmt/tests/test_spa_analysis.py

# 프론트엔드
amic-platform/src/modules/docs/pages/SpaAnalysisPage.tsx
amic-platform/src/modules/docs/components/SpaAnalysisWizard.tsx
amic-platform/src/modules/docs/components/SpaTextInput.tsx
amic-platform/src/modules/docs/components/AnalysisReviewPanel.tsx
amic-platform/src/modules/docs/hooks/useSpaAnalysis.ts
amic-platform/src/modules/docs/types/spa_analysis.ts

# 관련 기존 파일
deal-mgmt/app/routers/contract_generation.py
deal-mgmt/app/services/contract_generation_service.py
deal-mgmt/app/models/contract.py
```
