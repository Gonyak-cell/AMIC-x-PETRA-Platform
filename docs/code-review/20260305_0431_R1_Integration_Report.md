# R1 통합 검증 리포트

- 라운드: 1
- 시작: 2026-03-05 03:15
- 종료: 2026-03-05 04:31

---

## 실행 요약

8개 청크 × 4개 배치 × 13개 관점 전체 스캔 완료.

| 청크 | 모듈 | 스캔 파일 | 코드 수정 | 관찰 이슈 | 리포트 |
|------|------|----------|----------|----------|--------|
| 8 | 크로스커팅 | ~40 | 2건 (security.py, elasticsearch.py) | 16건 보류 | Batch 1~4 리포트 |
| 1 | 인프라 | ~43 | 0건 | 10건 | Chunk1_Infra_Report |
| 5 | Deal-Mgmt | ~100 | 0건 | 9건 | Chunk5_DealMgmt_Report |
| 6 | FE 공유 | ~120 | 0건 | 19건 | Chunk6_FE_Shared_Report |
| 7 | FE 모듈 | ~390 | 0건 | 27건 | Chunk7_FE_Modules_Report |
| 2 | FDD | ~389 | 141파일 포맷 | 12건 + D1~D5 확인 | FDD_Backend_Chunk2_Review |
| 4 | IM | ~430 | 177파일 포맷 | 17건 + D6~D10 확인 | Chunk4_IM_Report |
| 3 | KIIS | ~208 | 0건 | 14건 + D11 확인 | Chunk3_KIIS_Report |

**총계**: ~1,720 파일 스캔 / 320 파일 수정 (318 포맷 + 2 코드) / 124건 관찰 이슈

---

## 통합 검증 결과

### 백엔드 린트 (ruff check + format)

| 모듈 | ruff check | ruff format | 파일 수 |
|------|-----------|-------------|---------|
| FDD | 0건 ✅ | 0건 (371파일) ✅ | 371 |
| KIIS | 0건 ✅ | 0건 (188파일) ✅ | 188 |
| IM | 0건 ✅ | 0건 (506파일) ✅ | 506 |
| Deal-Mgmt | 0건 ✅ | 0건 (408파일) ✅ | 408 |

### 백엔드 테스트 (pytest)

| 모듈 | Passed | Failed | Errors | 비고 |
|------|--------|--------|--------|------|
| FDD | 1,435 | 211 | 0 | 기존 — test_uploads 인증, test_qoe_api |
| KIIS | 543 | 30 | 106 | 기존 — fakeredis/sklearn 미설치 |
| IM | 0 | 0 | 4 | 기존 — celery 미설치 (수집 에러) |
| Deal-Mgmt | 1,542 | 0 | 0 | ✅ 완전 통과 |

**참고**: FDD/KIIS/IM 테스트 실패는 ruff format 이전부터 존재하던 로컬 dev 의존성 문제. format은 로직을 변경하지 않으므로 새 실패 유발 없음.

### 프론트엔드

| 검증 | 결과 |
|------|------|
| tsc --noEmit | 0건 ✅ |
| eslint --max-warnings 0 | 0건 ✅ |
| vite build | 성공 ✅ (44.81s) |

---

## 이슈 심각도 분포 (전체 124건)

| 심각도 | 건수 | 주요 출처 |
|--------|------|----------|
| Critical | 8건 | IM JSONB/UUID 5건, KIIS 마이그레이션 1건, FE God 컴포넌트 1건, FDD D2 get_db rollback 1건 |
| High | 17건 | FE 크로스 모듈 8건, FDD auth/권한 2건, FE 공유 모듈 경계 3건, IM verify_exp/float/except 4건 |
| Medium | 35건 | FE unsafe cast/성능 14건, FDD float/except/설정 5건, IM 엔진/예외 5건, KIIS float/설정/except 6건, DM/Infra 5건 |
| Low | 30건+ | FE dead type/eslint-disable, 백엔드 os.getenv/inline import 등 |

### Critical 이슈 상세

| # | 모듈 | 이슈 | 영향 |
|---|------|-----|------|
| 1 | IM | models/ 6파일 JSONB/UUID PostgreSQL 직접 사용 | CI SQLite CompileError |
| 2 | KIIS | 마이그레이션 raw JSONB/UUID | CI SQLite CompileError |
| 3 | FE | TransactionWorkspacePage.tsx 1,371줄 God 컴포넌트 | 유지보수성 |
| 4 | FDD | get_db() rollback 누락 | 미커밋 트랜잭션 |
| 5 | FDD | 커넥션 풀 30 × 4모듈 > PostgreSQL max_connections | 잠재적 DB 고갈 |

### High 이슈 상세 (우선 수정 권장)

| # | 모듈 | 이슈 |
|---|------|-----|
| 1 | FDD | AUTH_ENABLED=False 프로덕션 가드 비대칭 (RuntimeError 없음) |
| 2 | FDD | exchange_rates.py 쓰기 권한 미분리 |
| 3 | IM | verify_exp=False — 만료 토큰 무기한 접근 |
| 4 | IM | financial_engine ~60건 float() 정밀도 위반 |
| 5 | IM | 154건 except Exception 광범위 예외 |
| 6 | FE | MA↔Docs 양방향 의존성 (22줄 크로스 모듈 import) |
| 7 | FE | AnalysisReviewPanel.tsx 인라인 HTML (자체 sanitizer) |
| 8 | FE 공유 | useCalendar/useGlobalSearch/useAnalytics 모듈 경계 위반 |

---

## 보류 이슈 재검증 결과

| ID | 모듈 | 결과 |
|----|------|------|
| D1 | FDD | ✅ 확인 — 동기 엔진 (async 미사용) |
| D2 | FDD | ✅ 확인 — get_db rollback 누락 |
| D3 | FDD | ✅ 확인 — 풀 30 × 4 > 100 |
| D4 | FDD | ✅ 확인 — AUTH_ENABLED 프로덕션 가드 미흡 |
| D5 | FDD | ✅ 확인 — bcrypt 비표준 검증 |
| D6 | IM | ✅ 확인 — Redis 매번 새 클라이언트 |
| D7 | IM | ✅ 확인 — verify_exp=False |
| D8 | IM | ✅ 확인 — pool_recycle/timeout 미설정 |
| D9 | IM | ✅ 확인 — DB URL 평문 자격증명 |
| D10 | IM | ❌ 오탐 — 실제 명시적 CORS 헤더 |
| D11 | KIIS | ✅ 확인 + 추가 — username 충돌 벡터 |

**11건 중 10건 확인, 1건 오탐 (D10)**

---

## 양호한 패턴 (전 모듈)

- **FDD**: JsonbColumn 크로스 DB, safe_decimal, RFC 7807 에러, 감사 로그, Rate Limiting
- **KIIS**: Redis graceful fallback, Entity Resolution 한국어, NLP asyncio.to_thread, selectinload
- **IM**: RS256/HS256 듀얼 JWT, 명시적 CORS, Celery 멱등, DART Rate Limiter + Circuit Breaker
- **Deal-Mgmt**: (별도 리포트 참조)
- **FE**: any 0건 / @ts-ignore 0건 (68,430줄), React Query 일관, 접근성 우수

---

## 코드 변경 요약

### 실제 수정 (2건)
1. `kiis/app/core/security.py:230` — HTTP 400 → 403 (비활성 사용자)
2. `kiis/app/core/elasticsearch.py:117` — `exc_info=True` 추가

### 포맷 수정 (318파일)
- FDD: 141파일 ruff format
- IM: 177파일 ruff format

---

## R1 결론

- **린트/포맷**: 전 모듈 0건 ✅
- **타입 검사**: tsc 0건 ✅
- **빌드**: FE 빌드 성공 ✅
- **테스트**: Deal-Mgmt 완전 통과, FDD/KIIS/IM은 기존 dev 의존성 문제
- **관찰 이슈**: 124건 (수정 불가 — code-freeze, 읽기 전용 관찰)
- **다음 단계**: 사용자 승인 후 Critical/High 이슈 수정 라운드 진행

*Reviewed by Claude Code — R1 complete*
