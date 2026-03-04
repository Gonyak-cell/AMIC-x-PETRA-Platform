# 코드 리뷰 리포트: KIIS 백엔드 — Chunk 3

- 라운드: 1
- 모듈: Chunk 3 KIIS 백엔드
- 배치: 1~4 통합
- 시작: 2026-03-05 04:01
- 종료: 2026-03-05 04:20

## 배치 1: 린트/포맷

- ruff check: 0건
- ruff format: 0건 (188개 파일 이미 포맷됨)
- 코드 수정: 0건 (배치 1)

## 배치 2~4: 통합 리뷰 (읽기 전용)

25개 파일 상세 읽기 + 208개 파일 패턴 스캔.

### Chunk 8 보류 이슈 재검증

| ID | 파일 | 라인 | 원래 이슈 | 결과 |
|----|-----|------|----------|------|
| D11 | core/security.py | 202-212 | FDD 토큰 → KIIS 사용자 자동 생성 시 동시 IntegrityError | **확인 + 에스컬레이션** — upsert 미사용, username 충돌 벡터 추가 발견 (email.split("@")[0] 동일 이름 다른 도메인) |

### 신규 이슈

| # | 심각도 | 관점 | 파일 | 라인 | 이슈 |
|---|--------|------|-----|------|-----|
| N1 | Critical | CI Guard 2 | migrations/c1a2b3d4e5f6_audit_logs.py | 10,21,26-27 | 마이그레이션에서 raw JSONB + UUID 직접 사용 — CI SQLite CompileError |
| N2 | Medium | 데이터 무결성 | services/deal_service.py | 207,219 | float(amount) Decimal 정밀도 손실 |
| N3 | Medium | 설정 | core/security.py | 59 | os.getenv("ENV") — Settings 우회 |
| N4 | Medium | 설정 | routers/auth.py | 12 | os.getenv("ENV") — 쿠키 Secure 플래그 제어에 영향 |
| N6 | Medium | 예외처리 | 82건 (ib_crawl_service 7건 최다) | 다수 | except Exception 광범위 — ~15건 조용히 삼킴 |
| N9 | Medium | 보안/무결성 | core/security.py | 202-212 | username=email.split("@")[0] 충돌 — john@a.com, john@b.com 동일 username |
| N10 | Medium | 아키텍처 | 23개+ 서비스 파일 | 다수 | 서비스 레이어에서 db.commit() 직접 호출 — 트랜잭션 경계 제어 불가 |
| N5 | Low | 데이터 무결성 | services/alert_service.py | 53,62 | json.dumps를 Text 컬럼에 저장 — JSON 타입 미사용 |
| N7 | Low | 데이터 무결성 | models/news.py | sentiment_score | Float 타입 — Numeric/Decimal 미사용 |
| N8 | Low | 보안 | routers/auth.py | 쿠키 설정 | 세션 쿠키 max_age 없음 + CSRF 미보호 |
| N11 | Low | 성능 | services/deal_service.py | 207-210 | 단계 추정 선형 탐색 |
| N12 | Low | 데이터 무결성 | services/dashboard_service.py | 104 | float(score.total_score) JSON 직렬화 |
| N13 | Low | 동시성 | services/news_service.py | 157-168 | 뉴스 배치 삽입 TOCTOU 윈도우 |
| N14 | Low | 아키텍처 | routers/portfolio.py | 126-127 | 라우트 핸들러 내 지연 import |

### 양호한 패턴

- JSONB 크로스 DB 호환 (models/audit.py, company.py) — `JSON().with_variant(JSONB, "postgresql")`
- expire_on_commit=False 올바른 설정
- TimestampMixin 19개 모델 일관 적용
- Redis 캐시 graceful fallback (@cached 데코레이터)
- URL SHA256 해시 중복 방지 (news_service.py)
- DART Rate Limiter 안전 마진 (900/1000분)
- get_jwt_claims 경량 DB-free 인증
- APScheduler 11개 비동기 작업 + 타임존 인식
- Entity Resolution 한국어 기업명 별칭 처리
- Reputation upsert 패턴 (security.py D11과 대비)
- NLP asyncio.to_thread() 블로킹 방지
- selectinload N+1 방지
- bare except 0건
- 전 라우터 JWT 인증 일관 적용

## 검증 결과

- ruff check: 0건
- ruff format: 0건

## 에러 카운트

| 심각도 | 건수 |
|--------|------|
| Critical | 1건 (마이그레이션 JSONB/UUID) |
| Medium | 6건 (float, os.getenv, except Exception, username 충돌, 서비스 commit) |
| Low | 7건 |
| 합계 | 14건 + 보류 D11 확인 (코드 수정 0건) |

## 충족 관점 체크리스트

- [x] 9. 린트/포맷 (0건)
- [x] 6. 타입 안전성 (관찰)
- [x] 7. 데이터 무결성 (마이그레이션 JSONB, float 관찰)
- [x] 8. 환경변수/설정 (os.getenv 2건 관찰)
- [x] 1. 보안 (D11 재확인, 쿠키 관찰)
- [x] 2. 성능 (관찰)
- [x] 4. 예외처리 (except Exception 82건 관찰)
- [x] 5. 동시성 (TOCTOU, 서비스 commit 관찰)
- [x] 3. 아키텍처 (서비스 commit 패턴 관찰)
- [x] 11. 테스트 (관찰)
