# MA GP + ValueChain 13개 관점 통합 리뷰 (수정 후)

> **리뷰 일시**: 2026-03-03 23:57 KST
> **리뷰 범위**: deal-mgmt 모듈 — MA GP + ValueChain SI/FI 자동매핑 통합 코드
> **리뷰 대상**: 16개 소스 파일 + 2개 테스트 파일 + 2개 마이그레이션
> **리뷰 방법**: 5개 병렬 에이전트 (Security, Performance, Python, Migration, Domain)
> **사전 수정**: 30건 이슈 중 29건 수정 완료 (6-Phase Plan), 1,459 테스트 통과

---

## 1. 종합 요약

| 항목 | 결과 |
|------|------|
| **Critical** | **3건** |
| **Major** | **14건** |
| **Moderate** | **22건** |
| **Minor** | **18건** |
| **합계** | **57건** (중복 제거 후) |
| **종합 판정** | ⚠️ Critical 3건 + Major 14건 우선 해결 후 프로덕션 투입 권장 |

> **참고**: 5개 에이전트 간 중복 발견(GP 캐시 경쟁 조건 등)은 한 번만 카운트.

---

## 2. Critical 이슈 (3건)

### CRIT-01: 하드코딩된 연도 — 2026년부터 최신 PEF 누락 [P0]

- **위치**: `si_mapping_service.py:401`
- **설명**: `range(2025, 2022, -1)` = [2025, 2024, 2023] 하드코딩. 2026년 현재 최신 연도(2025) 후 PEF가 누락됨
- **영향**: FI 매핑에서 2025~2026 설립 PEF가 결과에서 제외되어 부정확한 추천
- **신뢰도**: HIGH — 코드 직접 확인
- **수정**: `datetime.now(UTC).year` 기준 동적 계산 (1줄 변경)

### CRIT-02: 대용량 테이블 비-CONCURRENT 인덱스 생성 [P0]

- **위치**: `059_composite_indexes_and_vc_timestamps.py:34-60`
- **설명**: 114,964건 `vc_companies`에 인덱스 3개 + 수십만 건 `vc_industry_coefficients`에 인덱스 2개를 `CREATE INDEX`(비-CONCURRENT)로 생성
- **영향**: 배포 중 테이블 전체 잠금(ShareLock) → 수 분 간 SI/VC 매핑 요청 타임아웃
- **신뢰도**: HIGH — PostgreSQL DDL 동작 확인
- **수정**: `postgresql_concurrently=True` 옵션 + `transaction_per_migration=False` 설정

### CRIT-03: `normalize_gp_name` — 문자열 전체 위치 치환 버그 [P0]

- **위치**: `fi_mapping_service.py:57-63`
- **설명**: `str.replace()`가 접미사를 **문자열 중간 위치에서도** 제거. 예: `"캐피탈라인자산운용"` → `"라인"` (중간 "캐피탈" + 끝 "자산운용" 모두 제거)
- **영향**: GP명에 접미사 문자열이 중간에 포함된 경우 비직관적 정규화 → 매칭 실패/오매칭
- **신뢰도**: HIGH — 코드 + 테스트로 확인
- **수정**: `endswith()` + 슬라이싱 기반으로 변경 (5줄)

---

## 3. Major 이슈 (14건)

| ID | 관점 | 위치 | 설명 |
|----|------|------|------|
| MAJ-01 | R2-1 보안 | `si_mapping_service.py:292-316` | JWT 서비스 토큰이 모듈 레벨 전역 변수에 평문 캐시. KIIS에서 `scope: internal` 검증 여부 불확인 |
| MAJ-02 | R2-1 보안 | `si_mapping_service.py:57` | httpx.AsyncClient에 connect/read/write 타임아웃 미분리. Slow Loris 유사 공격 취약 |
| MAJ-03 | R3-2 API | `si_mapping.py:209` | `GET /vc-map`이 4회 DB 쿼리의 무거운 연산인데 GET 메서드 사용. POST와 설계 비일관 |
| MAJ-04 | R4-1 에러 | `si_mapping_service.py:437` | httpx 예외 중 `RemoteProtocolError`, `InvalidURL` 등이 미포착 → 500 전파 |
| MAJ-05 | R4-1 에러 | `si_mapping_service.py:295-316` | `_make_service_token()` lock 없음 → 동시 JWT 중복 발급 + `get_jwt_secret()` 실패 무처리 |
| MAJ-06 | R4-2 관찰 | `fi_mapping_service.py` 전체 | `recommend_fi()` 서비스에 완료 로그 없음. 추천 GP 수, Tier 1/2 분포, 소요 시간 미기록 |
| MAJ-07 | R5-1 성능 | `si_mapping_service.py:552-583` | 10,000건 SICompany ORM 객체 전체 메모리 로딩 (50-100MB/요청). Rate Limit 우회와 결합 시 DoS |
| MAJ-08 | R5-1 성능 | `fi_mapping_service.py:52-86` | GP 캐시 asyncio 비안전 (TOCTOU 경쟁) + 멀티워커 간 불일치 (최대 1시간) |
| MAJ-09 | R5-3 결합 | `si_mapping_service.py:44` | 서비스 레이어에서 `jose.jwt` 직접 import → JWT 생성 로직이 `core/security.py`에서 분산 |
| MAJ-10 | R5-3 결합 | `si_mapping_service.py:14-15` | 서비스에서 `fastapi.HTTPException` 직접 사용 → 웹 프레임워크 종속. 도메인 예외로 분리 필요 |
| MAJ-11 | R6-1 도메인 | `fi_mapping_service.py:52-86` | GP 캐시 멀티워커 불일치 → 동일 요청이 워커 A=Tier 1, 워커 B=Tier 2로 반환 가능 |
| MAJ-12 | R6-2 테스트 | `test_fi_mapping_v2.py` | FI 라우터 에러 경로 5종 (429, 422, 503, 404) 테스트 전무 |
| MAJ-13 | R6-2 테스트 | `test_vc_mapping.py` | VC/SI rate limit(429) + 인증/인가(403) 테스트 전무. conftest ADMIN 고정 |
| MAJ-14 | R6-3 복잡도 | `si_mapping_service.py:320-439` | `get_deep_dive` 120줄, 7단계 책임 혼재 → 분리 필요 |

---

## 4. 13개 관점별 분석 결과

### R2-1: 보안 (Security) — 12건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| S-01 | Major | HIGH | `si_mapping_service.py:292-316` | JWT 서비스 토큰 전역 평문 캐시 |
| S-02 | Major | HIGH | `si_mapping_service.py:57` | httpx 타임아웃 미분리 (connect/read/write) |
| S-03 | Moderate | HIGH | `pef_registry.py:48-67` / `si_mapping.py:36-57` | 인메모리 Rate Limiter — 다중 워커/재시작 시 완전 우회 |
| S-04 | Moderate | HIGH | `pef_registry.py:181` / `si_mapping.py:105` | Rate Limit 키 `"anonymous"` fallback → 서비스 방해 가능 |
| S-05 | Moderate | HIGH | `si_mapping_service.py:552` | `_MAX_COMPANIES = 10,000` 메모리 기반 DoS 가능 |
| S-06 | Moderate | HIGH | `si_mapping.py:218-231` | `map_vc` 엔드포인트 Rate Limit 미적용 |
| S-07 | Moderate | HIGH | `gp_profile.py:9` | `JSONB` 직접 import — Guard 2 일관성 파손 |
| S-08 | Moderate | MEDIUM | `pef_registry.py:223-226` | `target_company_name` ILIKE 최대 길이 미제한 |
| S-09 | Minor | HIGH | `fi_mapping_service.py:52-86` | GP 캐시 asyncio 비안전 — 동시 DB 중복 쿼리 |
| S-10 | Minor | MEDIUM | `seed_gp_profiles.py:125` 외 | openpyxl `keep_links=False` 미설정 |
| S-11 | Minor | MEDIUM | `si_mapping.py:163` | `bulk_add_buyers` dead code (CLIENT 도달 불가) |
| S-12 | Minor | HIGH | `pef_registry.py:105` | 에러 로그 사용자 입력값 직접 노출 (CRLF 인젝션 가능) |

**양호 사항**: SQL Injection 0건 (전수 확인), IDOR 위험 0건, Mass Assignment 0건, 하드코딩 시크릿 0건

### R2-2: 위협 모델링 (Threat Modeling)

| 엔드포인트 | 인증 | 역할 | Rate Limit | 위험 |
|-----------|------|------|-----------|------|
| `GET /pef-registry` | JWT | READ | 없음 | 낮음 |
| `GET /fi-recommendations` | JWT | READ | 10/분 ✅ | 낮음 |
| `POST /si-mapping/map` | JWT | READ | 10/분 ✅ | 낮음 |
| `GET /si-mapping/vc-map` | JWT | READ | **없음 ❌** | S-06 |
| `POST /add-buyers` | JWT | WRITE | 없음 | S-11 |
| 나머지 6개 | JWT | READ | 없음 | 낮음 |

**공격 표면 총평**: 인증 필수(JWT), 역할 체크(require_role) 일관 적용. Rate Limit은 FI/SI 매핑에만 적용, VC 매핑 누락(S-06).

---

### R3-1: 데이터 흐름 & 무결성 (Data Flow) — 4건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| DF-01 | **Critical** | HIGH | `fi_mapping_service.py:57-63` | `normalize_gp_name` replace() 전역 치환 버그 (= CRIT-03) |
| DF-02 | Moderate | HIGH | `fi_mapping_service.py:52-86` | 캐시 TOCTOU 경쟁 → 동시 DB 중복 쿼리 |
| DF-03 | Minor | HIGH | `seed_gp_profiles.py:131,136` | row 길이 검증 없이 인덱스 접근 → IndexError 가능 |
| DF-04 | Moderate | MEDIUM | `seed_gp_profiles.py:125` | Excel 시트명 KeyError 미처리 |

**양호 사항**: Decimal 타입 전 구간 일관 (Model→Service→Schema), SQL Injection 없음, ILIKE escape 올바름

### R3-2: API 계약 & 호환성 (API Contract) — 4건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| AC-01 | **Critical** | HIGH | `si_mapping_service.py:401` | 하드코딩 연도 `range(2025, 2022, -1)` (= CRIT-01) |
| AC-02 | Major | HIGH | `si_mapping.py:209` | VC 매핑 무거운 연산이 GET 메서드 |
| AC-03 | Minor | HIGH | `si_mapping.py:41-57` / `pef_registry.py:53-67` | Rate limit 함수 완전 중복 (DRY 위반) |
| AC-04 | Minor | HIGH | `pef_registry.py:60` / `si_mapping.py:48` | 429 응답에 Retry-After 헤더 없음 |

**양호 사항**: Pydantic v2 ConfigDict 일관 적용, Literal 타입 적용, 페이지네이션 구현

---

### R4-1: 에러 처리 (Error Handling) — 4건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| EH-01 | Major | HIGH | `si_mapping_service.py:437` | httpx 예외 `RemoteProtocolError` 등 미포착 → 500 |
| EH-02 | Major | HIGH | `si_mapping_service.py:295-316` | `_make_service_token` 예외 무처리 + lock 없음 |
| EH-03 | Moderate | HIGH | `si_mapping.py:163` | `bulk_add_buyers` DB 에러 try/except 없음 |
| EH-04 | Moderate | HIGH | `si_mapping_service.py:282` | audit 실패 시 commit 정책 불명확 |

**양호 사항**: `asyncio.gather(return_exceptions=True)` 적용, Pydantic 자동 검증

### R4-2: 관찰 가능성 (Observability) — 3건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| OB-01 | Major | HIGH | `fi_mapping_service.py` 전체 | `recommend_fi()` 완료 로그 없음 |
| OB-02 | Moderate | HIGH | `si_mapping.py` 전체 | SI 라우터 Audit 기록 없음 (FI만 기록) |
| OB-03 | Moderate | MEDIUM | `pef_registry.py:53-67` | Rate limit 발동 로그 없음 → 남용 탐지 불가 |

---

### R5-1: 성능 (Performance) — 7건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| PF-01 | Major | HIGH | `si_mapping_service.py:552-583` | 10,000건 ORM 전체 로딩 (50-100MB/요청) |
| PF-02 | Major | HIGH | `fi_mapping_service.py:52-86` | GP 캐시 멀티프로세스 불일치 + thundering herd |
| PF-03 | Moderate | HIGH | `si_mapping_service.py:612-665` | `sorted_keys` 매 호출 O(K log K) 반복 (최대 10회/요청) |
| PF-04 | Moderate | HIGH | `si_mapping_service.py:862-991` | VC 매핑 3개 독립 쿼리 순차 실행 → `asyncio.gather()` 가능 |
| PF-05 | Moderate | HIGH | `si_mapping_service.py:834-859` | `ILIKE '%검색어%'` B-Tree 인덱스 미활용 (114K건 풀스캔) |
| PF-06 | Moderate | HIGH | `pef_registry.py:65-67` | Rate limiter stale key 자기자신 미정리 패턴 |
| PF-07 | Minor | HIGH | `si_mapping_service.py:941-954` | LIMIT이 업종 편중 시 타 업종 기업 잘림 |

**양호 사항**: 시딩 스크립트 배치 처리(CHUNK_SIZE), `defer()` 컬럼 지연 로딩 적용

### R5-2: 배포 안전성 (Deployment Safety) — 4건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| DS-01 | **Critical** | HIGH | `059_migration.py:34-60` | 비-CONCURRENT 인덱스 생성 → 테이블 잠금 (= CRIT-02) |
| DS-02 | Moderate | HIGH | `gp_profile.py:9` | `JSONB` 직접 import (Guard 2) |
| DS-03 | Moderate | HIGH | `seed_*.py` `--force` | 프로덕션 실수 삭제 위험 (확인 절차 없음) |
| DS-04 | Minor | HIGH | `058_migration.py:25` | `gp_profiles.id` UUID `server_default` 누락 |

### R5-3: 의존성 & 결합도 (Dependencies) — 4건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| DC-01 | Major | HIGH | `si_mapping_service.py:44` | 서비스에서 `jose.jwt` 직접 사용 (보안 로직 분산) |
| DC-02 | Major | HIGH | `si_mapping_service.py:14-15` | 서비스에서 `HTTPException` 직접 사용 (계층 위반) |
| DC-03 | Moderate | HIGH | `si_mapping_service.py` 함수 내 | VC 모델 반복 지연 import (정적 분석 불가) |
| DC-04 | Moderate | HIGH | `seed_gp_profiles.py:22` | `normalize_gp_name`이 서비스 파일에 위치 (유틸로 분리 필요) |

**양호 사항**: fi_mapping ↔ si_mapping 간 의존 0건, 순환 참조 0건, openpyxl 등록 확인

---

### R6-1: 도메인 로직 (Domain Logic) — 5건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| DL-01 | **Critical** | HIGH | `fi_mapping_service.py:57-63` | replace() 전역 치환 버그 (= CRIT-03) |
| DL-02 | Moderate | HIGH | `fi_mapping_service.py:33-49` | 접미사 목록에 "투자", "증권" 누락 → 매칭 실패 가능 |
| DL-03 | Moderate | HIGH | `si_mapping_service.py:612-665` | KSIC 역접두사 2자리 매칭 → 과도하게 넓은 대분류 포함 |
| DL-04 | Minor | MEDIUM | `si_mapping_service.py:865` | VC `min_revenue` 기본값 100억 → 니치 업종 빈 결과 |
| DL-05 | Minor | MEDIUM | `si_mapping_service.py:940-946` | 업종 편중 LIMIT → 일부 업종 기업 0건 가능 |

**양호 사항**: Tier 분류 로직 비즈니스 적합, 전후방 관계 IO 계수표 기반 도출 정확

### R6-2: 테스트 품질 (Test Quality) — 6건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| TQ-01 | Major | HIGH | `test_fi_mapping_v2.py` | 에러 경로 5종 (429, 422×2, 503, 404) 테스트 전무 |
| TQ-02 | Major | HIGH | `test_vc_mapping.py` | 인증/인가 (403) + Rate Limit (429) 테스트 전무 |
| TQ-03 | Major | HIGH | `scripts/` 전체 | 시딩 유틸 함수 (`parse_portfolio` 등) 단위 테스트 전무 |
| TQ-04 | Moderate | HIGH | `test_fi_mapping_v2.py` | 경계값 테스트 부족 (target_amount=0, limit=1, 중복 GP 등) |
| TQ-05 | Moderate | HIGH | `tests/` 전체 | SI 매핑(KSIC) 통합 테스트 없음 (VC만 테스트) |
| TQ-06 | Minor | HIGH | `conftest.py:103-107` | JWT mock ADMIN 고정 → 역할 분기 테스트 불가 |

**양호 사항**: 47건 테스트 통과, GP 캐시/Rate Limit 리셋 격리 확보, 타임스탬프 테스트 포함

### R6-3: 인지 복잡도 (Cognitive Complexity) — 4건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| CX-01 | Major | HIGH | `si_mapping_service.py:320-439` | `get_deep_dive` 120줄, 7단계 책임 혼재 |
| CX-02 | Moderate | HIGH | `si_mapping_service.py:862-991` | `map_vc_candidates` 130줄, 쿼리+그룹핑+패널 조립 인라인 |
| CX-03 | Moderate | HIGH | `si_mapping_service.py:612-665` | `_lookup_by_ksic` 4단 중첩, 3전략 혼합 |
| CX-04 | Minor | HIGH | `pef_registry.py:149-266` | `fi_recommendations` 118줄, PEF 쿼리 구성 서비스 위임 필요 |

**양호 사항**: 네이밍 명확, 상수 명명 일관적, 주석 블록으로 단계 구분

### R6-4: 접근성 & UX — 3건

| ID | 심각도 | 신뢰도 | 위치 | 설명 |
|----|--------|--------|------|------|
| UX-01 | Moderate | HIGH | Rate Limit 429 응답 | `Retry-After` 헤더 없음 → FE 자동 재시도 불가 |
| UX-02 | Moderate | HIGH | `si_mapping.py:117-131` | 기업 미발견 시 200+null 반환 (REST 관례 404 위반) |
| UX-03 | Minor | MEDIUM | `si_mapping_service.py:333-334` | 404 메시지에 요청 company_id 미포함 |

---

## 5. 마이그레이션 검증 결과

| 항목 | 상태 | 설명 |
|------|------|------|
| Revision 체인 | ✅ PASS | 057 → 058 → 059, head 1개 |
| downgrade() 역연산 | ✅ PASS | 059: 인덱스→컬럼 역순 올바름 |
| models/__init__.py 등록 | ✅ PASS | 3개 모델 모두 등록 + `__all__` 포함 |
| 모델-마이그레이션 일치 | ⚠️ DRIFT | `vc_industry_coefficient` 복합 인덱스가 모델=058, 마이그레이션=059 분리 |
| `revenue` 정밀도 | ⚠️ WARNING | `Numeric(20,2)` — 규칙 기준 `Numeric(18,4)` 대비 scale 부족 |
| UUID server_default | ⚠️ WARNING | `gp_profiles.id` Python-side only (DB 직접 INSERT 시 실패) |
| CONCURRENT 인덱스 | ❌ CRITICAL | 114K건 테이블에 비-CONCURRENT 생성 (= CRIT-02) |

---

## 6. 관점 × 심각도 매트릭스

| 관점 | Critical | Major | Moderate | Minor | 합계 |
|------|----------|-------|----------|-------|------|
| R2-1 보안 | 0 | 2 | 5 | 4 | **11** |
| R2-2 위협 모델링 | 0 | 0 | 1 | 0 | **1** |
| R3-1 데이터 흐름 | 1 | 0 | 2 | 1 | **4** |
| R3-2 API 계약 | 1 | 1 | 0 | 2 | **4** |
| R4-1 에러 처리 | 0 | 2 | 2 | 0 | **4** |
| R4-2 관찰 가능성 | 0 | 1 | 2 | 0 | **3** |
| R5-1 성능 | 0 | 2 | 4 | 1 | **7** |
| R5-2 배포 안전성 | 1 | 0 | 2 | 1 | **4** |
| R5-3 의존성 | 0 | 2 | 2 | 0 | **4** |
| R6-1 도메인 로직 | 1 | 0 | 2 | 2 | **5** |
| R6-2 테스트 품질 | 0 | 3 | 2 | 1 | **6** |
| R6-3 인지 복잡도 | 0 | 1 | 2 | 1 | **4** |
| R6-4 접근성 | 0 | 0 | 2 | 1 | **3** |
| **합계** | **3** | **14** | **22** | **18** | **57** |

> 일부 이슈는 복수 관점에서 발견되었으나 가장 적합한 관점에 1회만 카운트

---

## 7. 우선순위별 권장 조치

### P0 — 즉시 (Critical 3건)

| # | ID | 수정 난이도 | 설명 |
|---|-----|-----------|------|
| 1 | CRIT-01 | 낮음 (1줄) | 하드코딩 연도 → `datetime.now(UTC).year` 동적 계산 |
| 2 | CRIT-03 | 낮음 (5줄) | `normalize_gp_name` replace() → endswith() + 슬라이싱 |
| 3 | CRIT-02 | 중간 | 059 마이그레이션 `postgresql_concurrently=True` 적용 |

### P1 — 단기 (Major 14건 중 상위 7건)

| # | ID | 수정 난이도 | 설명 |
|---|-----|-----------|------|
| 4 | S-06 | 낮음 (1줄) | `map_vc` Rate Limit 추가 |
| 5 | S-04 | 낮음 (2줄) | Rate Limit 키 `claims.user_id` fallback |
| 6 | EH-01 | 낮음 (1줄) | httpx 예외 `httpx.HTTPError`로 범위 확장 |
| 7 | OB-01 | 낮음 | `recommend_fi()` 완료 INFO 로그 추가 |
| 8 | TQ-01/02 | 중간 | FI/VC 에러 경로 + 인증 테스트 추가 |
| 9 | PF-04 | 낮음 (5줄) | VC 쿼리 3회 → `asyncio.gather()` 병렬화 |
| 10 | DC-02 | 중간 | `HTTPException` → 도메인 예외 분리 |

### P2 — 중기 (Moderate 22건)

| 카테고리 | 핵심 조치 |
|----------|----------|
| 보안 | Rate Limiter Redis 기반 교체, JSONB import 제거 |
| 성능 | GP 캐시 `asyncio.Lock()`, ILIKE `pg_trgm` 인덱스, ORM 로딩 경량화 |
| 관찰 | SI 라우터 Audit 추가, Rate Limit 발동 로깅 |
| 테스트 | 경계값 테스트, SI 매핑 통합 테스트, 시딩 유틸 단위 테스트 |
| 도메인 | 접미사 목록 확장 ("투자", "증권"), KSIC 역접두사 최소 길이 조정 |
| 복잡도 | `get_deep_dive`, `map_vc_candidates` 함수 분리 |

### P3 — 개선 (Minor 18건)

- Retry-After 헤더 추가, Rate Limit 함수 DRY 통합
- JWT 생성 `core/security.py`로 이전
- 시딩 스크립트 `--force` 확인 프롬프트 추가
- conftest 역할별 JWT fixture 추가
- 에러 메시지에 company_id 포함
- `normalize_gp_name`을 `app/utils/` 유틸로 이동

---

## 8. 이전 리뷰 대비 개선 현황

| 항목 | 이전 (30건 리뷰) | 현재 (수정 후) |
|------|-----------------|---------------|
| SQL Injection | C3 (escape 미적용) | ✅ 해결 — 전수 확인 |
| LIMIT 미적용 | H1 | ✅ 해결 — `top_n * len(related_industries)` |
| float 정밀도 | C2, M10 | ✅ 해결 — Decimal 전면 적용 |
| 인덱스 최적화 | H2, H3, H4 | ✅ 해결 — 복합 인덱스 + 마이그레이션 |
| 역할 체크 | H5, H6 | ✅ 해결 — `require_role()` 적용 |
| Rate Limiting | M7 | ✅ 해결 — 인메모리 구현 (분산 한계 잔존) |
| Audit | M8 | ⚠️ 부분 — FI만 적용, SI 누락 |
| 캐시 | M1 | ✅ 해결 — TTL 캐시 (경쟁 조건 잔존) |
| 접미사 정렬 | H7, H8 | ⚠️ 부분 — 정렬 해결, replace() 버그 신규 발견 |

---

## 9. Cross-cutting 품질 지표

| 지표 | 결과 | 판정 |
|------|------|------|
| 순환 참조 | 0건 | ✅ |
| SQL Injection | 0건 (전수 확인) | ✅ |
| IDOR | 0건 | ✅ |
| Mass Assignment | 0건 | ✅ |
| 하드코딩 시크릿 | 0건 | ✅ |
| Decimal 일관성 | 전 구간 적용 | ✅ |
| Ruff lint | 0건 | ✅ |
| 테스트 통과 | 1,459 passed, 0 failed | ✅ |
| 타입 힌트 | 100% (모든 함수/메서드) | ✅ |
| Pydantic v2 | ConfigDict 일관 적용 | ✅ |

---

## 10. 결론

6-Phase 수정으로 기존 30건 중 29건이 해결되었으나, 13개 관점 심층 리뷰에서 **신규 57건** (Critical 3, Major 14, Moderate 22, Minor 18)이 발견되었습니다.

**강점**:
- SQL Injection, IDOR, Mass Assignment 등 OWASP Top 10 핵심 취약점 0건
- Decimal 타입 전 구간 일관 적용으로 금융 데이터 정밀도 확보
- 순환 참조 0건, 타입 힌트 100%, 1,459 테스트 전체 통과
- require_role() RBAC + JWT 인증 일관 적용

**즉시 조치 필요**:
- CRIT-01 (하드코딩 연도) — 현재 2026년, 이미 영향 발생 중
- CRIT-03 (replace 버그) — GP명 정규화 정확도 직접 영향
- CRIT-02 (인덱스 잠금) — 059 마이그레이션 프로덕션 적용 전 수정 필수
