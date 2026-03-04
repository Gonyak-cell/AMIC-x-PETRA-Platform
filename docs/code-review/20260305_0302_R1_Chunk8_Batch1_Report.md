# 코드 리뷰 리포트: Cross-cutting — 배치 1

- 라운드: 1
- 모듈: Chunk 8 크로스커팅
- 배치: 1 (린트/포맷, 타입 안전성, 의존성)
- 시작: 2026-03-05 02:52
- 종료: 2026-03-05 03:02

## 발견된 이슈

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 | 수정 내용 |
|---|------|-----|------|-----|--------|----------|
| 1 | 린트/포맷 | fdd/backend/app/auth/token.py | - | ruff format 위반 | Low | `ruff format` 적용 |
| 2 | 린트/포맷 | fdd/backend/app/core/log_middleware.py | - | ruff format 위반 | Low | `ruff format` 적용 |
| 3 | 린트/포맷 | fdd/backend/app/core/logging.py | - | ruff format 위반 | Low | `ruff format` 적용 |
| 4 | 린트/포맷 | im/src/api/ (27 files) | - | ruff format 위반 | Low | `ruff format` 적용 |
| 5 | 타입 안전성 | kiis/app/core/exceptions.py | 133 | `register_exception_handlers(app)` — `app: FastAPI` + `-> None` 누락 | Medium | 타입 힌트 추가 |
| 6 | 타입 안전성 | deal-mgmt/app/core/log_middleware.py | 22 | `call_next` 매개변수 타입 누락 | Medium | `call_next: RequestResponseEndpoint` 추가 |
| 7 | 타입 안전성 | fdd/backend/app/core/log_middleware.py | 22 | `call_next` 매개변수 타입 누락 | Medium | `call_next: RequestResponseEndpoint` 추가 |

## 허위 양성 차단 (제1원칙)

| # | 보고된 이슈 | Read 검증 결과 | 판정 |
|---|-----------|-------------|------|
| 1 | deal-mgmt/app/core/contract_styles.py:378 `-> None` 누락 | Read 확인 — 이미 `-> None` 존재 | 허위 양성 |
| 2 | deal-mgmt/app/core/contract_styles.py:445 `-> None` 누락 | Read 확인 — 이미 `-> None` 존재 | 허위 양성 |

## 검증 결과

### 백엔드
- FDD ruff check: ✅ 0건
- FDD ruff format: ✅ 0건
- KIIS ruff check: ✅ 0건
- KIIS ruff format: ✅ 0건
- Deal-Mgmt ruff check: ✅ 0건
- Deal-Mgmt ruff format: ✅ 0건
- IM ruff check: ✅ 0건
- IM ruff format: ✅ 0건

### 프론트엔드
- tsc --noEmit: ✅ 0건

### 의존성
- F401 미사용 import: ✅ 0건 (FDD, KIIS, Deal-Mgmt, IM 모두)

## 에러 카운트

| 관점 | 수정 전 | 수정 후 |
|------|--------|--------|
| 린트/포맷 | 30 files | 0 |
| 타입 안전성 | 3건 | 0 |
| 의존성 | 0건 | 0 |
| 합계 | 33건 | 0 |

## 충족 관점 체크리스트

- [x] 9. 린트/포맷
- [x] 6. 타입 안전성
- [x] 10. 의존성
