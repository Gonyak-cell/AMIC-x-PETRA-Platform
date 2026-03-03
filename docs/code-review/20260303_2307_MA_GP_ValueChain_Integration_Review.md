# MA GP + ValueChain 데이터 SI/FI 자동매핑 통합 — 코드 리뷰

**리뷰 일시:** 2026-03-03 23:07 KST
**대상 브랜치:** feat/ma-workflow
**대상 모듈:** deal-mgmt
**리뷰 범위:** 모델 3, 마이그레이션 1, 서비스 2, 라우터 2, 스키마 2, 시딩 스크립트 4, 테스트 2 (총 16개 파일)

---

## 요약

| 심각도 | 건수 | 핵심 영역 |
|--------|------|-----------|
| **Critical** | 3 | 시크릿 노출, Decimal 정밀도 손실, LIKE escape 누락 |
| **High** | 9 | 무제한 메모리 로드, 인덱스 누락, IDOR, 접미사 순서 버그, 중간 commit 누락 |
| **Medium** | 11 | 캐싱 부재, N+1 UPDATE, dead code, Rate Limiting, 타입 힌트 누락 |
| **Low** | 7 | Literal 타입, 광범위 예외, 네이밍 일관성 |
| **합계** | **30** | |

---

## Critical (즉시 수정 필요)

### C1. `.env` 파일 실제 API 키 포함 — 커밋 히스토리 확인 필수

**파일:** `deal-mgmt/.env`
**유형:** 보안 — 시크릿 노출

`deal-mgmt/.env`에 ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, CLOVA 키가 평문으로 존재한다. `.gitignore`에 `.env`가 등록되어 있으나, 한 번이라도 커밋된 이력이 있으면 히스토리에 잔류한다.

**즉각 조치:**
1. `git log --all --full-history -- deal-mgmt/.env` 로 커밋 이력 확인
2. 커밋 이력 있으면 전 키 즉시 폐기 및 재발급
3. `.env.example`(더미 값)만 버전 관리에 포함

---

### C2. `enrich_vc_revenue.py:45-49` — float 변환으로 재무 데이터 정밀도 손실

**파일:** `deal-mgmt/scripts/enrich_vc_revenue.py:45`
**유형:** 데이터 무결성

```python
si_revenues: dict[str, float] = {}  # ← float 사용
...
si_revenues[name] = float(row[1])   # ← Decimal → float 변환
```

`VcCompany.revenue`는 `Numeric(20, 2)` 컬럼이다. `float` 변환 시 IEEE 754 부동소수점 오차가 발생하고 DB 저장 시 정밀도가 훼손된다.

**수정:** `dict[str, Decimal]`로 변경, `float()` 변환 제거.

---

### C3. `search_vc_industries` ILIKE에 `escape` 파라미터 누락

**파일:** `deal-mgmt/app/services/si_mapping_service.py:850`
**유형:** 보안 — LIKE 이스케이프 무력화

```python
# 현재 (문제)
.where(VcCompany.industry_name.ilike(pattern))  # escape="\\" 누락

# 동일 모듈 내 올바른 패턴 (search_ksic, 라인 120-124)
.where(SICompany.ksic_name.ilike(pattern, escape="\\"))
```

역슬래시로 `%`, `_` 를 이스케이프했지만 `escape` 인수 없으면 DB가 이스케이프 문자를 인식하지 못한다.

**수정:** `.ilike(pattern, escape="\\")` 추가.

---

## High (우선 수정)

### H1. `map_vc_candidates()` — 업종별 기업 조회 시 LIMIT 없는 전체 로드

**파일:** `deal-mgmt/app/services/si_mapping_service.py:931-943`
**유형:** 성능 — 메모리

```python
companies_q = (
    select(VcCompany)
    .where(VcCompany.industry_name.in_(related_industries))  # 최대 40개 업종
    .order_by(VcCompany.revenue.desc())
    # LIMIT 없음 → 수만 건 ORM 객체 메모리 적재
)
```

40개 업종의 전체 기업을 로드한 후 Python에서 `[:top_n]` 슬라이싱. 114,964개 기업 중 매출 조건 통과 기업이 수만 건이면 수 MB ORM 객체가 적재된다.

**수정 방향:** PostgreSQL 윈도우 함수 `ROW_NUMBER() OVER (PARTITION BY industry_name ORDER BY revenue DESC)` 서브쿼리로 DB 레벨에서 업종별 Top N 처리. 또는 `LIMIT top_n * len(related_industries)` 상한 추가.

---

### H2. `vc_industry_coefficients` — 복합 인덱스 누락 (쿼리 최적화 불가)

**파일:** `deal-mgmt/app/models/vc_industry_coefficient.py:27-29`
**유형:** 성능 — DB 인덱스

전방 쿼리 `WHERE source_industry = ? ORDER BY coefficient DESC LIMIT 20`에 단일 인덱스(`source_industry`)만 존재. 정렬을 위해 추가 filesort 발생.

**수정:** 마이그레이션 059에 복합 인덱스 추가:
- `(source_industry, coefficient DESC)` — 전방 쿼리용
- `(target_industry, coefficient DESC)` — 후방 쿼리용

---

### H3. `vc_companies` — 복합 인덱스 + `io_sector_name` 인덱스 누락

**파일:** `deal-mgmt/app/models/vc_company.py:21-26`
**유형:** 성능 — DB 인덱스

경쟁사 쿼리 `WHERE industry_name = ? AND revenue >= ? ORDER BY revenue DESC LIMIT 20`에 복합 인덱스 없음. `io_sector_name` 컬럼은 인덱스 자체가 없음.

**수정:**
- `(industry_name, revenue DESC)` 복합 인덱스
- `(io_sector_name, revenue DESC)` 복합 인덱스

---

### H4. ORM `index=True` vs 마이그레이션 인덱스 이름 불일치

**파일:** `deal-mgmt/app/models/vc_industry_coefficient.py:27-29`, `058_gp_profile_vc_tables.py:58-66`
**유형:** 모델 — 인덱스 일관성

모델의 `index=True`는 `ix_vc_industry_coefficients_source_industry` 이름을 생성하고, 마이그레이션은 `ix_vc_coeff_source`를 생성. `alembic check` 또는 `create_all()` 실행 시 중복 인덱스가 생성될 수 있다.

**수정:** 모델에서 `index=True` 제거하고 마이그레이션에서만 인덱스 관리, 또는 이름 통일.

---

### H5. `pef_registry.py` FI 추천 — IDOR 취약점

**파일:** `deal-mgmt/app/routers/pef_registry.py:125-158`
**유형:** 보안 — A01 Broken Access Control

`/transactions/{txn_id}/fi-recommendations`에서 `check_client_deal_access` 검증 없이 CLIENT가 아닌 역할이면 **모든 거래 ID의 FI 추천 결과를 조회** 가능.

```python
# check_client_deal_access 호출 없음 — txn_id IDOR 가능
async def fi_recommendations(txn_id: uuid.UUID, ...):
    if not claims.role or claims.role == "CLIENT":
        raise HTTPException(status_code=403, ...)
    txn = await transaction_service.get_transaction(db, txn_id)
    # claims.user_id와 txn 소유자 비교 없음
```

**수정:** `check_client_deal_access(db, txn_id, claims)` 추가, 또는 ANALYST/MANAGER/ADMIN이 모든 거래에 접근 가능한 것이 의도적 설계라면 명시적 문서화.

---

### H6. 역할 검증 패턴 불일치 — 블랙리스트 vs 화이트리스트

**파일:** `deal-mgmt/app/routers/pef_registry.py:68-72`
**유형:** 보안 — 확장성 위험

`si_mapping.py`는 화이트리스트 `require_role("ADMIN", "MANAGER", "ANALYST")` 사용. `pef_registry.py`는 블랙리스트 `if role == "CLIENT": raise 403`. 새 역할(GUEST, VIEWER) 추가 시 pef_registry는 자동 허용된다.

**수정:** `require_role()` 화이트리스트 패턴으로 통일.

---

### H7. `normalize_gp_name` — 접미사 제거 순서 의존성 버그

**파일:** `deal-mgmt/app/services/fi_mapping_service.py:37-38`
**유형:** 비즈니스 로직

`_STRIP_SUFFIXES` 리스트에서 `"어드바이저"`(인덱스 4)가 `"어드바이저스"`(인덱스 5)보다 앞에 있다.

```
"XYZ어드바이저스" → replace("어드바이저", "") → "XYZ스" (불완전 제거)
```

**수정:** 긴 접미사 우선 정렬 (`sorted(suffixes, key=len, reverse=True)`), 또는 정규식 기반 전환.

---

### H8. `normalize_gp_name` — "캐피털" 이형태 누락

**파일:** `deal-mgmt/app/services/fi_mapping_service.py:38`
**유형:** 비즈니스 로직

`_STRIP_SUFFIXES`에 `"캐피탈"`만 있고 `"캐피털"` 누락. 금감원 PEF 데이터에서 두 표기가 공존.

**수정:** `"캐피털"`, `"파트너스"` 등 누락된 접미사 추가. 실제 PEF 레지스트리 데이터에서 매칭 실패 패턴 분석 후 보완.

---

### H9. 시딩 스크립트 — 청크별 중간 commit 누락 (OOM + 전체 롤백 위험)

**파일:** `deal-mgmt/scripts/seed_vc_companies.py:115-127`, `seed_vc_coefficients.py:126-130`
**유형:** 안정성 — 메모리/트랜잭션

5,000건 청크마다 `insert` 실행하지만 commit은 전체 루프 완료 후 한 번만. 114,964건 또는 750K 계수가 세션 버퍼에 누적.

**수정:** 청크 삽입 후 `await session.commit()` 추가.

---

## Medium (개선 권장)

### M1. `_load_gp_profiles` — 매 요청마다 전체 테이블 로드 (캐싱 없음)

**파일:** `fi_mapping_service.py:61-65`
**유형:** 성능

GP 프로필 358건은 정적 참조 데이터. 모듈 레벨 TTL 캐시(1시간) 적용 권장.

### M2. `search_vc_industries` — 114K행 대상 ILIKE 순차 스캔

**파일:** `si_mapping_service.py:845-854`
**유형:** 성능

`%키워드%` ILIKE는 B-Tree 인덱스 미사용. 고유 업종명 1,574개만 있으므로 별도 `vc_industry_names` 조회 테이블 분리 권장.

### M3. `get_vc_data_stats()` — 두 번의 COUNT 쿼리 (별도 DB 왕복)

**파일:** `si_mapping_service.py:813-828`
**유형:** 성능

단일 SQL 서브쿼리로 병합 가능. Redis TTL 캐싱(1시간) 적용 권장.

### M4. `enrich_vc_revenue.py:75-80` — 개별 UPDATE N+1 쿼리

**파일:** `enrich_vc_revenue.py:75-80`
**유형:** 성능

1,000건 배치라고 되어 있지만 실제로는 건별 UPDATE 루프. `UPDATE ... WHERE id = ANY(...)` bulk 패턴 사용 권장.

### M5. `FIRecommendation` v1 클래스 — 미사용 dead code

**파일:** `pef_registry.py:33-44`
**유형:** 코드 정리

v1 `FIRecommendation`은 라우터/서비스 어디에서도 참조되지 않음. 제거 권장.

### M6. `si_mapping.py` — 5개 엔드포인트 반환 타입 힌트 누락

**파일:** `si_mapping.py:37, 47, 59, 91, 106`
**유형:** CI 강행 규정 3 위반

`get_stats`, `search_ksic`, `map_si`, `get_deep_dive`, `bulk_add_buyers`에 반환 타입 힌트 없음.

### M7. 검색/매핑 엔드포인트 전체 Rate Limiting 미적용

**파일:** `si_mapping.py`, `pef_registry.py`
**유형:** 보안 — A04 Insecure Design

`contract_generation.py`에는 Rate Limiter 적용되어 있으나 신규 엔드포인트에는 전무. 특히 `POST /si-mapping/map`은 호출당 10K 기업 로드.

### M8. FI 추천 조회 감사 추적 없음

**파일:** `pef_registry.py:125`
**유형:** 보안 — 감사

`bulk_add_buyers`는 `audit_service.record()` 사용. `fi_recommendations`는 GP 프로필/펀드 약정 등 민감 데이터 반환하면서 감사 기록 없음.

### M9. `text("total_value DESC")` — raw SQL 사용

**파일:** `si_mapping_service.py:691, 704`
**유형:** 코드 품질

SQLAlchemy label 직접 참조 방식으로 전환 권장: `total_value_col.desc()`.

### M10. `seed_vc_coefficients.py:42` — float `min_coeff` 타입 불일치

**파일:** `seed_vc_coefficients.py:39-42`
**유형:** 타입 안전성

`DEFAULT_MIN_COEFF = 0.001` (float 리터럴). `Decimal("0.001")`로 변경 권장.

### M11. `VcCompany` 모델 — `TimestampMixin` 미상속

**파일:** `vc_company.py:13`
**유형:** 운영

DART enrichment 최종 시점을 추적할 `updated_at` 컬럼 없음. `GpProfile`은 정상 적용.

---

## Low (참고)

### L1. `Mapped[list | None]` → `Mapped[list[str] | None]` 타입 구체화

**파일:** `gp_profile.py:59, 64`

### L2. `SICandidateOut.relation` — `Literal["DIRECT", "BACKWARD", "FORWARD"]` 타입 적용

**파일:** `si_mapping.py:95`

### L3. `FIRecommendationV2.tier` — `Literal[1, 2]` 또는 `Field(ge=1, le=2)` 제약

**파일:** `pef_registry.py:70`

### L4. `_extract_amount` — `except Exception` → `except (InvalidOperation, ValueError)` 범위 축소

**파일:** `si_mapping_service.py:509`

### L5. `_safe_decimal` — 0→None 변환 비즈니스 로직 은닉

**파일:** `seed_gp_profiles.py:61`

### L6. `VcChainCompany` 스키마에 `id` 필드 없음 — FE 식별 불가

**파일:** `si_mapping.py:214-229`

### L7. `si_mapping.py` — `responses` OpenAPI 딕셔너리 미선언

**파일:** `si_mapping.py:36-165`

---

## 통과 항목 (Passed Checks)

- [x] SQL Injection 없음 — 모든 쿼리 SQLAlchemy ORM 파라미터 바인딩
- [x] Cross-DB 타입 호환 — `Uuid` + `JSON().with_variant(JSONB, "postgresql")` 정상
- [x] Decimal 일관 사용 — `float` 미사용 (enrich 스크립트 제외)
- [x] `Decimal("...")` 문자열 리터럴 사용 — `Decimal(float)` 금지 준수
- [x] async/await 일관 — 동기 I/O 블로킹 없음
- [x] N+1 쿼리 방지 — batch IN 쿼리 + 인메모리 그룹핑 패턴
- [x] self-loop 제외 로직 — DB 레벨 WHERE 조건 적용
- [x] Tier 분류 비즈니스 로직 정확 — Tier 1/2 조건과 테스트 일치
- [x] ValueChain 방향성 정확 — forward=고객, backward=공급 산업연관표 기준 일치
- [x] Pydantic v2 ConfigDict 패턴 적용
- [x] `X | None` 패턴 — `Optional` 미사용
- [x] pathlib 경로 처리 — 하드코딩 절대 경로 없음
- [x] `openpyxl read_only=True` — 대용량 Excel 스트리밍
- [x] `from __future__ import annotations` 일관 사용
- [x] `--force` 플래그로 시딩 멱등성 지원
- [x] 마이그레이션 `downgrade()` 정상 구현
- [x] 43/43 테스트 통과, ruff 0건

---

## 수정 우선순위 로드맵

### 즉시 (P0)
1. **C1** — `.env` 커밋 히스토리 확인 + 키 재발급
2. **C2** — `enrich_vc_revenue.py` float → Decimal
3. **C3** — `search_vc_industries` ilike에 `escape="\\"` 추가

### 단기 (P1 — 다음 PR)
4. **H1** — `map_vc_candidates()` 윈도우 함수 또는 LIMIT 상한
5. **H2+H3** — 마이그레이션 059: 복합 인덱스 5개 추가
6. **H4** — ORM vs 마이그레이션 인덱스 이름 통일
7. **H5+H6** — `pef_registry.py` IDOR 수정 + 역할 검증 패턴 통일
8. **H7+H8** — `normalize_gp_name` 접미사 순서 + 이형태 보완
9. **H9** — 시딩 스크립트 중간 commit 추가

### 중기 (P2)
10. M1~M4 — 캐싱, 인덱스 최적화, bulk UPDATE
11. M5~M8 — dead code 정리, 타입 힌트, Rate Limiting, 감사 추적
12. M9~M11 — 코드 품질 개선
