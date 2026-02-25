# Testing Standards

> 출처: software-dev-ai-claude-toolkit (Ashfaqbs) + obra/superpowers TDD 참조

## 커버리지 목표
- 비즈니스 로직: 최소 80% 코드 커버리지.
- 크리티컬 경로 (인증, 데이터 변경): 100% 커버리지.

## 테스트 유형
- **단위 테스트**: 격리, 빠름, 외부 의존성 모킹. 모든 서비스 메서드에 단위 테스트.
- **통합 테스트**: 실제 DB 상호작용, API 엔드포인트 테스트.
- **E2E 테스트**: 크리티컬 사용자 플로우만. 과투자 금지 (느리고 깨지기 쉬움).

## TDD 워크플로우
1. **RED** — 실패하는 테스트 작성 (원하는 동작 정의).
2. **GREEN** — 테스트를 통과하는 최소 코드 작성.
3. **IMPROVE** — 테스트 그린 유지하며 리팩터링.

## Python/FastAPI 테스트 도구
- `pytest` + `pytest-asyncio` (비동기 테스트).
- `httpx.AsyncClient` 또는 `TestClient` (API 테스트).
- `unittest.mock` 또는 `pytest-mock` (모킹).
- 픽스처: `conftest.py`에 공통 픽스처 정의.

## React/TypeScript 테스트 도구
- Vitest + React Testing Library (단위/컴포넌트 테스트).
- Playwright (E2E 테스트).
- 동작 테스트, 구현 세부사항 테스트 금지. 내부 상태 테스트 금지.

## 테스트 네이밍
- Python: `test_returns_user_when_id_exists()`, `test_raises_when_email_invalid()`
- JS/TS: `it('returns user when id exists')`, `it('throws when email is invalid')`

## 규칙
- 테스트 간 독립성 보장. 공유 뮤터블 상태 금지.
- 테스트에서 `time.sleep()` 금지. 폴링 또는 async assertion 사용.
- Flaky 테스트 즉시 수정. Flaky 테스트는 없는 것보다 나쁨.
- 프레임워크 코드 테스트 금지. 자체 로직만 테스트.
- 외부 서비스 (HTTP 호출, 서드파티 API) 모킹 필수.
