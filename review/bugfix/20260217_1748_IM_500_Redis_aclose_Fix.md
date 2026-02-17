# IM 백엔드 500 에러 — Redis `aclose()` 호환성 수정

> 작성일: 2026-02-17 17:48
> 카테고리: bugfix
> 심각도: Critical (서비스 전면 장애)
> 상태: ✅ 수정 완료

---

## 증상

- 홈페이지(DashboardPage)에서 `Request failed with status code 500` 에러 발생
- 브라우저 콘솔: `:3000/api/im/documents` → 500 (Internal Server Error) 2건
- IM 백엔드의 모든 인증이 필요한 엔드포인트에서 500 에러 반환
- Health 엔드포인트(`/health`)는 정상 (200 OK)

## 원인 분석

### 에러 위치
- **파일**: `im/src/api/security/blacklist.py` (라인 39, 56)
- **에러**: `AttributeError: 'Redis' object has no attribute 'aclose'`

### 에러 체인
```
GET /api/v1/documents
→ FastAPI 의존성 주입: get_current_user()
→ dependencies.py:60 — JWT 블랙리스트 체크
→ is_blacklisted(jti) 호출
→ blacklist.py:56 — await redis.aclose()
→ AttributeError: 'Redis' object has no attribute 'aclose'
→ 500 Internal Server Error
```

### 근본 원인
- Docker 컨테이너에 설치된 `redis-py` 버전: **5.0.0**
- `redis.asyncio.Redis.aclose()` 메서드는 **redis-py 5.0.1+**에서 추가됨
- 5.0.0에서는 `close()` 메서드만 존재 (async 호환)
- 인증이 필요한 모든 엔드포인트에서 JWT 블랙리스트 체크 시 `is_blacklisted()` 호출 → 전면 장애

### 영향 범위
- IM 백엔드의 **모든 인증 엔드포인트** (documents, companies, users, api_keys)
- Health 엔드포인트는 인증 불필요 → 정상
- 대시보드에서 IM 문서 목록 조회 실패 → KPI 카드 에러 표시

## 수정 내용

### 변경 파일
- `im/src/api/security/blacklist.py`

### 변경 사항
```python
# Before (라인 39, 56)
await redis.aclose()

# After
await redis.close()
```

- `blacklist_token()` 함수: 라인 39 — `aclose()` → `close()`
- `is_blacklisted()` 함수: 라인 56 — `aclose()` → `close()`

### 검증 결과
- 수정 후 Docker 컨테이너 자동 reload (WatchFiles)
- `GET /api/v1/documents` → **401 Unauthorized** (정상 — 인증 필요)
- `GET /health` → **200 OK** (정상)
- 500 에러 완전 해소

## 재발 방지

1. **redis-py 버전 핀닝**: `requirements.txt`에서 `redis>=5.0.1`로 최소 버전 지정 권장
2. **또는 호환 패턴 사용**: `close()`는 redis-py 4.x/5.x 모두 지원하므로 `close()` 사용이 안전
