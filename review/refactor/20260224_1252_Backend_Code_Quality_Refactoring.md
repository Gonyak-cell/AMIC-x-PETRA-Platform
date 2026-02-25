# 백엔드 코드 품질 리팩토링

> 작성: 2026-02-24 12:52:00
> 근거 문서: `docs/code-review/20260224_1119_Backend_Codebase_Review.md`

## 요약

백엔드 코드베이스 종합 평가(검증 점수 8.3/10)에서 도출된 P1/P2 개선사항 5건을 수정 완료.

## 수정 내역

### P1-1: deal-mgmt JWT 기본 시크릿 프로덕션 가드 강화

**문제**: deal-mgmt의 JWT_SECRET 기본값(`dev-secret-change-in-production-!!`)이 빈 문자열이 아니라 프로덕션 가드를 통과할 수 있었음.

**수정**:
- `deal-mgmt/app/core/config.py`: FDD 패턴 적용 — `_DEV_SECRET` 상수 추출 + `os.getenv("ENV")` 기반 프로덕션 감지
- `deal-mgmt/app/main.py`: lifespan 내 중복 JWT 검증 로직 제거 (config.py import 시 자동 검증)

**파일**: `deal-mgmt/app/core/config.py`, `deal-mgmt/app/main.py`

---

### P1-2: 에러 응답 RFC 7807 통일

**문제**: FDD만 RFC 7807 `application/problem+json` 사용, 나머지 3개 모듈은 각기 다른 에러 포맷.

**수정**:
- `deal-mgmt/app/core/exceptions.py`: `_problem_response()` 헬퍼 추가, 5개 예외 핸들러 RFC 7807 변환 (`urn:deal-mgmt:error:{type}`)
- `kiis/app/core/exceptions.py`: 동일 패턴 적용 (`urn:kiis:error:{type}`)
- `im/src/api/__init__.py`: `_ERROR_TYPE_MAP` 딕셔너리 기반 RFC 7807 변환 (`urn:im:error:{type}`)

**파일**: `deal-mgmt/app/core/exceptions.py`, `kiis/app/core/exceptions.py`, `im/src/api/__init__.py`

---

### P1-3: KIIS N+1 쿼리 최적화

**문제**: KIIS에서 N+1 쿼리 패턴 발견 (High 2건, Medium 3건).

**수정**:
- `kiis/app/services/dashboard_service.py`: `_get_risk_companies()` 10+1 쿼리 → JOIN 1 쿼리
- `kiis/app/services/manager_service.py`: `get_manager_profile()` Fund 중복 조회 제거 (2번 → 1번)
- `kiis/app/services/reputation_service.py`: `get_reputation()`, `get_reputation_history()` company_id 키워드 인자 추가
- `kiis/app/routers/analysis.py`: 서비스 호출 시 이미 조회한 `company.id` 전달

**파일**: `kiis/app/services/dashboard_service.py`, `kiis/app/services/manager_service.py`, `kiis/app/services/reputation_service.py`, `kiis/app/routers/analysis.py`

---

### P2-1: CORS 메서드/헤더 명시 (FDD 수준)

**문제**: deal-mgmt, KIIS, IM이 `allow_methods=["*"]`, `allow_headers=["*"]` 사용. FDD만 6개 메서드 + 3개 헤더 명시.

**수정**: 3개 모듈 모두 FDD 수준으로 통일:
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
allow_headers=["Content-Type", "Authorization", "X-Request-ID"]
max_age=3600
```

**파일**: `deal-mgmt/app/main.py`, `kiis/app/main.py`, `im/src/api/middleware/cors.py`

---

### P2-2: 페이지네이션 공통 헬퍼 추출

**문제**: KIIS 8개 라우터, deal-mgmt 16개 라우터에서 동일한 count + offset + limit 패턴 반복.

**수정**:
- `kiis/app/core/pagination.py` (신규): `PaginationParams` 클래스 + `paginate()` 함수
- `deal-mgmt/app/core/pagination.py` (신규): 동일 패턴 (offset/limit 스타일)
- `kiis/app/routers/company.py`: 헬퍼 적용 예시
- `kiis/app/routers/analysis.py`: 헬퍼 적용 예시 (list_reputations)

**파일**: `kiis/app/core/pagination.py`, `deal-mgmt/app/core/pagination.py`, `kiis/app/routers/company.py`, `kiis/app/routers/analysis.py`

---

## 수정 통계

| 우선순위 | 건수 | 수정 파일 수 |
|---------|------|------------|
| P1 | 3건 | 10파일 |
| P2 | 2건 | 7파일 |
| **합계** | **5건** | **17파일** |

## 미수정 항목 (P3, 외부 의존)

| 항목 | 사유 |
|------|------|
| FDD 동기→비동기 전환 | 대규모 리팩토링 (P3) |
| CPU 작업 asyncio.to_thread() 래핑 | 프로파일링 후 결정 (P3) |
| 테스트 커버리지 CI 통합 | CI 인프라 필요 (P2, 외부 의존) |
