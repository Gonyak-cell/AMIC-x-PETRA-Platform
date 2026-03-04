# 코드 리뷰 리포트: Cross-cutting — 배치 2

- 라운드: 1
- 모듈: Chunk 8 크로스커팅
- 배치: 2 (데이터 무결성, 환경변수/설정, API 계약)
- 시작: 2026-03-05 03:02
- 종료: 2026-03-05 03:08

## 발견된 이슈

| # | 관점 | 파일 | 라인 | 이슈 | 심각도 | 수정 내용 |
|---|------|-----|------|-----|--------|----------|
| 1 | 환경변수/설정 | im/src/api/config.py | 61 | `jwt_secret_key` 기본값 `"change-me-in-production"` — 프로덕션 startup validation 누락. FDD/DealMgmt는 프로덕션 환경에서 RuntimeError로 차단하지만 IM에는 없음 | Medium | DealMgmt 패턴에 맞춘 startup validation 추가 |
| 2 | 환경변수/설정 | im/src/api/config.py | 122 | `secret_key` 기본값 동일 이슈 | Minor | jwt_secret_key 검증에 포함됨 |

## 이슈 없음 (Read로 검증)

### 데이터 무결성 (관점 7)
- fdd/backend/app/core/ (10 files): Decimal/UUID/Enum → JSON 직렬화 안전 (`json.dumps(..., default=str)`, `str()` 변환)
- kiis/app/core/ (11 files): 동일 — 이슈 없음
- deal-mgmt/app/core/ (12 files): 동일 — 이슈 없음
- im/src/api/security/ (5 files): 동일 — 이슈 없음
- amic-platform/src/api/ (2 files): Axios 자동 JSON 파싱 — 이슈 없음

### 환경변수/설정 (관점 8)
- CORS 형식: FDD=`str`, KIIS/DM/IM=`list[str]` — 각 모듈 자기 패턴 유지 ✅
- JWT 변수명: FDD=`jwt_secret`, KIIS/DM=`JWT_SECRET`, IM=`jwt_secret_key(alias=JWT_SECRET)` ✅
- 기본값 보안: FDD=RuntimeError, DM=RuntimeError, KIIS=빈 문자열, IM=**수정 완료** ✅

### API 계약 (관점 12)
- client.ts: 401 자동 갱신, 중복 방지, 경로 제외 로직 일관적 ✅
- errors.ts: RFC 7807 + Pydantic validation 두 형태 모두 처리 ✅

## 검증 결과

- IM ruff check: ✅ 0건
- IM ruff format: ✅ 0건

## 에러 카운트

| 관점 | 수정 전 | 수정 후 |
|------|--------|--------|
| 데이터 무결성 | 0건 | 0 |
| 환경변수/설정 | 2건 | 0 |
| API 계약 | 0건 | 0 |
| 합계 | 2건 | 0 |

## 충족 관점 체크리스트

- [x] 7. 데이터 무결성
- [x] 8. 환경변수/설정
- [x] 12. API 계약
