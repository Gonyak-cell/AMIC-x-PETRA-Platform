# KIIS GP 페이지 — AUM 숫자 잘림 + 502 에러 수정

> 작성: 2026-02-25 15:24

## 요약

KIIS GP & Funds 페이지에서 두 가지 문제를 수정:
1. **502 에러** — "등록 운용사 (공공데이터)" 탭에서 `DATA_GO_KR_API_KEY` 미설정으로 인한 502 반환
2. **AUM 숫자 잘림** — KOFIA 탭에서 `206,875,789,000,000` 같은 대금액이 카드 영역을 초과하여 잘림

## 수정 1: 502 에러 해결

### 근본 원인
- `kiis/app/services/public_data_service.py:67-71` — `DATA_GO_KR_API_KEY`가 빈 문자열(기본값)이면 `ExternalAPIError` 발생
- `kiis/app/core/exceptions.py:114-119` — `external_api_error_handler`가 HTTP 502 반환
- `docker-compose.yml` KIIS 서비스에 `DATA_GO_KR_API_KEY` 환경변수 누락

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `docker-compose.yml` (L113) | KIIS 서비스 environment에 `DATA_GO_KR_API_KEY: ${DATA_GO_KR_API_KEY:-}` 추가 |
| `kiis/app/services/public_data_service.py` (L142-144) | `search_gp_registry()` — API 키 없으면 빈 결과 반환 (graceful degradation) |
| `kiis/app/services/public_data_service.py` (L213-215) | `get_gp_by_name()` — API 키 없으면 None 반환 |

### 사용자 조치
- 루트 `.env` 파일에 `DATA_GO_KR_API_KEY=발급받은_키_값` 추가
- `docker compose up -d --build kiis-api` 재시작

## 수정 2: AUM 숫자 잘림 해결

### 근본 원인
- `format.ts:formatAmount()` — KRW일 때도 천 단위 콤마만 적용, 조/억 단위 축약 없음
- `formatCompact()` — 영문 B/M/K 단위만 지원
- `Card.tsx` — `overflow-hidden` 적용 → 긴 숫자 잘림
- 디자인 시스템 전체 수정 불필요, 포맷팅 함수 추가로 해결

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/lib/format.ts` | `formatAmountKRW()` 함수 추가 — 조/억/만 단위 자동 축약 |
| `amic-platform/src/modules/kiis/pages/GPListPage.tsx` (L17) | import에 `formatAmountKRW` 추가 |
| `amic-platform/src/modules/kiis/pages/GPListPage.tsx` (L117) | RegistryGPCard AUM: `formatAmount` → `formatAmountKRW` |
| `amic-platform/src/modules/kiis/pages/GPListPage.tsx` (L404) | KOFIA GP 카드 AUM: `formatAmount` → `formatAmountKRW` |

### `formatAmountKRW` 변환 규칙

| 범위 | 예시 입력 | 출력 |
|------|----------|------|
| ≥ 1조 | 206,875,789,000,000 | `206.9조` |
| ≥ 1억 | 1,234,567,890 | `12억` |
| ≥ 1만 | 50,000 | `5만` |
| < 1만 | 9,999 | `9,999` |

## 검증 방법

1. `.env`에 API 키 설정 후 `docker compose up -d --build kiis-api`
2. 브라우저 GP & Funds 페이지 → "등록 운용사" 탭: 502 에러 없이 로드 확인
3. KOFIA 탭: AUM이 `206.9조` 형태로 카드 내 정상 표시 확인
