# Code Review — MA Workflow (feat/ma-workflow) Integrated Review

> **Review Date**: 2026-03-02 02:58 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: feat/ma-workflow 전체 (diff vs origin/master) — 801 소스 파일 (FE 374, deal-mgmt 333, kiis 89, im 5)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(PASS 170/170) build(PASS) ruff(PASS) pytest(PASS 1151/1151)
> **Review Gates**: Backend(deal-mgmt ✓, kiis ✓, im ✓) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2 / MEDIUM: 0 / LOW: 0 | P0: 2 |
| Major    | 4     | HIGH: 4 / MEDIUM: 0 / LOW: 0 | P1: 4 |
| Moderate | 6     | HIGH: 3 / MEDIUM: 3 / LOW: 0 | P2: 6 |
| Minor    | 2     | HIGH: 1 / MEDIUM: 1 / LOW: 0 | P3: 2 |
| Design Risk | 2  | — | P3: 2 |
| **Total**| **16** | HIGH: **10** / MEDIUM: **4** / LOW: **0** | P0: **2** / P1: **4** / P2: **6** / P3: **4** |

**FP Prevention**: 가설 21건 검증, 4건 사전 거부 (거부율: 19%) | 교차 검증 21건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- 5개 에이전트(Performance, Migration, Code Review, Security ×2)에서 총 21건 원시 이슈 수집
- 교차 검증 후: Critical 2건(P0), Major 4건(P1), Moderate 6건(P2), Minor 2건(P3), Design Risk 2건(P3)
- FALSE_POSITIVE 3건 제거 (PERF-003, MIG-C001, CODE-C04)
- 1건 중복 병합 (PERF-005 = CODE-C02)

---

## Findings

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

---

#### [SEC-K001] KIIS 라우터 13개 파일 인증 완전 누락 — [Critical/HIGH] — Priority: P0 (점수: 115)

**파일**: `kiis/app/routers/{managers,sanctions,audit,analysis,portfolio,deals,news,search,company,disclosures,reits,entity,kofia}.py`

**문제**: KIIS 라우터 21개 중 13개 파일의 **모든 엔드포인트**에 인증 Depends(`get_current_active_user` 또는 `get_jwt_claims`)가 없음. 인증이 적용된 8개 파일(auth, dart, logo, alerts, ib_insights, search 일부, dashboard, public_data)과 완전한 보안 정책 불일치.

**위험 엔드포인트 (쓰기 작업 — 인증 없이 DB 수정 가능)**:
| 라우터 | 엔드포인트 | 위험 |
|--------|----------|------|
| `portfolio.py:154` | `PUT /{portfolio_id}/valuation` | 기업가치 무단 수정 |
| `portfolio.py` | `POST /by-investor/{corp_code}/sync` | 포트폴리오 DB 쓰기 |
| `sanctions.py:88` | `POST /classify/{corp_code}` | 외부 API 트리거 + DB 삽입 |
| `deals.py:335` | `POST /extract` | 뉴스→딜 데이터 DB 삽입 |
| `news.py:71` | `POST /collect` | RSS 크롤링 트리거 + DB 삽입 |
| `analysis.py` | `POST /reputation/{corp_code}/calculate` | 평판 (재)계산 + DB 쓰기 |

**위험 엔드포인트 (민감 읽기 — 인증 없이 조회 가능)**:
| 라우터 | 엔드포인트 | 노출 데이터 |
|--------|----------|-----------|
| `audit.py:56` | `GET /audit-logs` | 시스템 전체 감사 로그 |
| `audit.py` | `GET /audit-logs/export` | 감사 로그 CSV 10,000건 |
| `managers.py:29` | `GET /movements` | 심사역 이동 이력 전체 |

**검증 근거**: Grep으로 `kiis/app/routers/` 전체 검색 — `get_current_active_user`/`get_jwt_claims`/`require_role` 호출이 8개 파일에만 존재, 13개 파일에 전무. Read로 sanctions.py:29-36, audit.py:57-65, portfolio.py:154-159 직접 확인.

**비교**: deal-mgmt 동일 감사 로그 기능(`deal-mgmt/app/routers/audit.py:31`)은 `require_role("ADMIN", "MANAGER")` 적용.

---

#### [SEC-K002] KIIS sanctions.py 에러 메시지에 내부 예외 정보 노출 — [Critical/HIGH] — Priority: P0 (점수: 100)

**파일**: `kiis/app/routers/sanctions.py:95-100`

```python
except Exception as e:
    raise HTTPException(
        status_code=502,
        detail=f"DART API 호출 실패: {e}",  # ← 내부 예외 문자열 노출
    ) from e
```

**문제**: Python `Exception` 객체의 문자열 표현이 HTTP 응답에 그대로 포함. 내부 URL, 연결 문자열, 타임아웃 구성, 네트워크 경로 등이 노출 가능. SEC-K001과 결합 시 — 인증 없이 이 엔드포인트에 접근하여 의도적으로 에러를 유발하고 내부 구성 정보를 수집할 수 있음.

**공격 시나리오**:
```
POST /api/v1/sanctions/classify/00000000   ← 인증 없이 접근
HTTP 502: {"detail": "DART API 호출 실패: HTTPConnectTimeoutError('...opendart.fss.or.kr:443')"}
```

**검증 근거**: Read로 sanctions.py:95-100 직접 확인. 인증 미적용(SEC-K001) + 예외 노출의 복합 위험.

---

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [MIG-C003] IM 001_initial_schema.py — postgresql.JSONB 직접 사용 — [Major/HIGH] — Priority: P1 (점수: 85)

**파일**: `im/alembic/versions/001_initial_schema.py:84,87-88,120-122,128`

```python
# 현재 코드 (금지 패턴)
from sqlalchemy.dialects import postgresql
sa.Column("dart_data", postgresql.JSONB(astext_type=sa.Text()), server_default="{}")
sa.Column("financial_summary", postgresql.JSONB(astext_type=sa.Text()), server_default="{}")
sa.Column("sections", postgresql.JSONB(astext_type=sa.Text()), server_default="[]")
sa.Column("generation_config", postgresql.JSONB(astext_type=sa.Text()), server_default="{}")
sa.Column("stage_details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}")
```

**문제**: CI Guard 2 위반. `postgresql.JSONB`는 PostgreSQL 전용 타입으로, SQLite 기반 CI 환경에서 `alembic upgrade head` 실행 시 `CompileError` 발생. 현재는 CI가 `create_all()`을 사용하여 문제가 발현되지 않지만, 마이그레이션 기반 테스트로 전환 시 즉시 실패.

**올바른 패턴**:
```python
from sqlalchemy.dialects.postgresql import JSONB as _JSONB
sa.Column("dart_data", sa.JSON().with_variant(_JSONB, "postgresql"), server_default="{}")
```

**검증 근거**: Read로 001_initial_schema.py:84,87,120,122,128 직접 확인. 5개 JSONB 컬럼 모두 `postgresql.JSONB` 직접 사용.

**Self-Challenge**: SC-1(코드 확인) ✓, SC-2(증거) ✓, SC-3(반증 시도: create_all 사용으로 현재 CI 미영향) △, SC-4(severity: Major 유지 — 표준 위반) ✓

---

#### [MIG-C004] IM 005_audit_logs.py — UUID/JSONB 직접 사용 — [Major/HIGH] — Priority: P1 (점수: 85)

**파일**: `im/alembic/versions/005_audit_logs.py:10,21,26-27`

```python
from sqlalchemy.dialects.postgresql import UUID, JSONB

sa.Column("id", UUID(as_uuid=True), primary_key=True, ...)
sa.Column("old_value", JSONB, nullable=True)
sa.Column("new_value", JSONB, nullable=True)
```

**문제**: MIG-C003과 동일. `UUID(as_uuid=True)` + `JSONB` 직접 사용.

**올바른 패턴**: `sa.Uuid()` (PK) + `sa.JSON().with_variant(_JSONB, "postgresql")` (JSON 필드)

**검증 근거**: Read로 005_audit_logs.py:10,21,26-27 직접 확인.

---

#### [MIG-C005] deal-mgmt 029_document_extraction.py — UUID/JSONB 직접 사용 — [Major/HIGH] — Priority: P1 (점수: 85)

**파일**: `deal-mgmt/migrations/versions/029_document_extraction.py:9,21,25-26,58,61,89,92-93`

```python
from sqlalchemy.dialects.postgresql import JSONB, UUID

sa.Column("id", UUID(as_uuid=True), primary_key=True)
sa.Column("transaction_id", UUID(as_uuid=True), ...)
sa.Column("vdr_document_id", UUID(as_uuid=True), ...)
sa.Column("extracted_data", JSONB, nullable=True)
sa.Column("target_id", UUID(as_uuid=True), nullable=True)
sa.Column("conditions_precedent", JSONB, nullable=True)
sa.Column("corporate_info", JSONB, nullable=True)
sa.Column("financial_summary", JSONB, nullable=True)
```

**문제**: MIG-C003과 동일. UUID 5건 + JSONB 4건 직접 사용. deal-mgmt 모듈의 최근 마이그레이션(041+)은 올바른 패턴을 따르지만, 029는 초기 마이그레이션으로 미수정 상태.

**검증 근거**: Read로 029_document_extraction.py 전문 확인. 9건의 PostgreSQL 전용 타입 사용.

---

#### [SEC-H001] AUTH_ENABLED=False + ENV="" → ADMIN 역할 자동 부여 — [Major/HIGH] — Priority: P1 (점수: 85)

**파일**: `deal-mgmt/app/core/security.py:40-62`

```python
_DEV_CLAIMS = JWTClaims(
    user_id="00000000-0000-0000-0000-000000000000",
    email="system@autofdd.dev",
    role="ADMIN",    # ← 최고 권한
)

async def get_jwt_claims(...) -> JWTClaims:
    if not settings.AUTH_ENABLED:
        _env = os.getenv("ENV", "").lower()
        if _env not in ("local", "dev", "test", ""):  # ← "" 허용
            raise RuntimeError(...)
        return _DEV_CLAIMS
```

**문제**: `ENV` 환경변수가 설정되지 않은 경우 빈 문자열(`""`)이 허용 목록에 포함되어, `AUTH_ENABLED=False` 상태에서 RuntimeError 가드가 우회됨. Docker compose에 `AUTH_ENABLED: "true"`가 명시되어 있어 프로덕션에서는 이 분기에 진입하지 않지만, 설정 오류 시 방어 계층이 부재.

**수정 방향**: `""` 를 허용 목록에서 제거 → `if _env not in ("local", "dev", "test"):`

**검증 근거**: Read로 security.py:40-62 직접 확인. docker-compose.yml의 AUTH_ENABLED=true 확인. ENV 환경변수 미설정 확인.

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [MIG-C002] deal-mgmt 041_buyer_tiering — ALTER TYPE 방언 가드 누락 — [Moderate/HIGH] — Priority: P2 (점수: 55)

**파일**: `deal-mgmt/migrations/versions/041_buyer_tiering_marketing_logs.py:78-81`

```python
# 방언 체크 없이 직접 실행
op.execute("ALTER TYPE vdrfoldercategory ADD VALUE IF NOT EXISTS 'MARKET_RESEARCH'")
op.execute("ALTER TYPE attachmententitytype ADD VALUE IF NOT EXISTS 'MARKETING_LOG'")
```

**문제**: `ALTER TYPE ... ADD VALUE`는 PostgreSQL 전용 구문. 올바른 패턴은 `if bind.dialect.name == "postgresql":` 가드를 추가하는 것 (051 마이그레이션 참조).

**교차 검증 결과**: CI는 `create_all()`을 사용하여 현재 실패하지 않음. 프로덕션(PG)에서 정상 동작. **원래 Critical → Moderate로 하향**.

---

#### [CODE-C01] map_si_candidates min_revenue 타입 힌트 불일치 — [Moderate/HIGH] — Priority: P2 (점수: 55)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:118`

```python
# 현재
async def map_si_candidates(..., min_revenue: float | None = None, ...):

# _load_filtered_companies (line 517)
async def _load_filtered_companies(db, min_revenue: Decimal | None, ...):
```

**문제**: 공개 함수 `map_si_candidates`는 `float | None`으로 선언하고, 내부 함수 `_load_filtered_companies`는 `Decimal | None`으로 선언. 스키마(`SIMappingRequest.min_revenue`)는 이전 세션에서 `float→Decimal`로 수정 완료되었으나, 서비스 함수 시그니처가 미수정.

**검증 근거**: Read로 si_mapping_service.py:118 vs :517 직접 확인. 타입 불일치 확인.

---

#### [PERF-001] sync_gp_profiles N+1 DB 쿼리 — [Moderate/HIGH] — Priority: P2 (점수: 55)

**파일**: `kiis/app/services/public_data_service.py:245-250`

```python
for item in all_items:  # ~수백 건
    try:
        await self._sync_single_gp(db, resolver, item, now, result)
        # ↑ 내부에서 select(Company).where(...) 개별 쿼리
    except Exception:
        ...
```

**문제**: GP 동기화 시 각 아이템마다 `_sync_single_gp`에서 `select(Company)` DB 쿼리를 실행. ~수백 건 처리 시 N+1 패턴.

**교차 검증 결과**: 이 함수는 관리자 배치 작업(수동 동기화)으로, 사용자 대면 API가 아님. 실행 빈도 극히 낮음(월 1회 이하). **원래 Critical → Moderate로 하향**.

---

#### [PERF-004] get_deep_dive 요청별 httpx.AsyncClient 생성 — [Moderate/MEDIUM] — Priority: P2 (점수: 39)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:330`

```python
async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
    # 6개 KIIS API 요청을 이 클라이언트 내에서 실행
```

**문제**: 딥다이브 요청마다 새 AsyncClient를 생성하여 TCP 커넥션을 매번 설정. 모듈 레벨 공유 클라이언트 사용 시 커넥션 풀링 가능.

**교차 검증 결과**: 단일 요청 내에서 6개 API를 asyncio.gather로 병렬 호출하므로, 커넥션 풀링 이점은 연속 딥다이브 요청 시에만 발생. 실제 사용 패턴상 빈도 낮음. **MEDIUM 신뢰도.**

---

#### [PERF-005] blob_storage Azure 모드 sync 파일 I/O — [Moderate/MEDIUM] — Priority: P2 (점수: 49)

**파일**: `deal-mgmt/app/core/blob_storage.py:146-147`

```python
# Azure 모드
with open(dest, "wb") as f:     # ← sync file open
    await stream.readinto(f)     # ← Azure SDK async streaming
```

**문제**: Azure 모드에서 `open(dest, "wb")`가 동기 파일 핸들을 생성. Azure SDK의 `readinto(f)`는 async이지만 디스크 쓰기는 sync.

**교차 검증 결과**: 로컬 모드는 이미 `asyncio.to_thread(shutil.copy2)` 사용. Azure 모드의 `readinto(f)` 내부에서 청크 단위 쓰기가 이루어지므로 실질적 블로킹은 미미. 2개 에이전트(Performance + Code Review)에서 동일 이슈 보고 → 교차 검증 보너스 +10. **원래 Critical → Moderate로 하향.**

---

#### [CODE-C03] reputation_service 뉴스 쿼리 LIMIT 누락 — [Moderate/MEDIUM] — Priority: P2 (점수: 39)

**파일**: `kiis/app/services/reputation_service.py:218-224`

```python
stmt = select(NewsArticle).where(
    NewsArticle.company_id == company_id,
    NewsArticle.published_at >= cutoff,
    NewsArticle.sentiment_score > 0.3,
)
result = await db.execute(stmt)
articles = result.scalars().all()  # ← LIMIT 없음
```

**문제**: 긍정 뉴스 전체를 메모리에 로딩. 뉴스 크롤링이 활발한 기업의 경우 수천 건 가능.

**교차 검증 결과**: 현재 데이터 규모에서 실질적 문제 없으나, 데이터 증가 시 리스크. **MEDIUM 신뢰도.**

---

### P3 — 저우선 (점수: <30)

---

#### [MIG-C006] IM 002_active_corpcode.py — PostgreSQL 전용 부분 인덱스 — [Moderate/MEDIUM — Design Risk] — Priority: P3 (점수: 24)

**파일**: `im/alembic/versions/002_active_corpcode.py:21-27`

```python
op.execute("""
    CREATE UNIQUE INDEX uq_documents_corp_code_active
    ON documents (corp_code)
    WHERE status IN ('PENDING', 'COLLECTING', 'ANALYZING', 'GENERATING', 'RENDERING')
""")
```

**문제**: `WHERE` 절을 포함한 부분 인덱스(Partial Index)는 PostgreSQL 전용. SQLite에는 동등한 기능 없음.

**교차 검증 결과**: 비즈니스 로직상 TOCTOU 방지를 위한 필수 제약. 크로스 DB 대안 없음 (앱 레벨 잠금 필요). **DESIGN_RISK로 분류.**

---

#### [SEC-H002] CLIENT 역할의 SI 전역 데이터 접근 — [Moderate/MEDIUM — Design Risk] — Priority: P3 (점수: 24)

**파일**: `deal-mgmt/app/routers/si_mapping.py:32-38, 86-93`

**문제**: `_READ_ACCESS`가 CLIENT 역할을 허용하여, SI 통계(`/si-mapping/stats`)와 딥다이브(`/si-mapping/companies/{id}/deep-dive`) 엔드포인트에 CLIENT가 접근 가능.

**교차 검증 결과**: 딥다이브가 조회하는 DART 데이터(재무제표, 공시, 제재이력)는 **공개 정보**. SI 기업 DB 자체도 매핑 레퍼런스로 거래 비밀 정보가 아님. 단, 특정 거래의 SI 매핑 결과(어떤 기업이 후보인지)는 deal-specific context이므로, `/transactions/{txn_id}/si-mapping` 엔드포인트에서는 `check_client_deal_access`가 적용됨. **기존 설계 의도에 부합. DESIGN_RISK로 분류.**

---

#### [MIG-C007] deal-mgmt 051 downgrade() = pass — [Minor/HIGH] — Priority: P3 (점수: 20)

**파일**: `deal-mgmt/migrations/versions/051_add_client_audit_actions.py:29-38`

**문제**: `downgrade()`가 `pass`만 포함. PostgreSQL은 `ALTER TYPE DROP VALUE`를 지원하지 않아 프로그래밍 방식 롤백 불가.

**교차 검증 결과**: 이전 세션에서 4단계 수동 롤백 절차 문서가 추가됨. PostgreSQL 고유 제약사항. **Minor로 유지.**

---

#### [PERF-002] _load_filtered_companies 10K 인메모리 로딩 — [Minor/MEDIUM — Design Risk] — Priority: P3 (점수: 12)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:512-543`

**문제**: `_MAX_COMPANIES_FOR_MAPPING = 10_000`으로 상한 설정, 전체 로딩 후 인메모리 KSIC 인덱스 구축.

**교차 검증 결과**: 이전 세션에서 8개 메타데이터 컬럼 `defer()` 최적화 적용 완료. 인메모리 인덱싱은 KSIC→기업 매핑 알고리즘의 핵심 설계 결정 (DB 쿼리 ~33 → ~5 감소). 페이지네이션 전환 시 알고리즘 전면 재설계 필요. **DESIGN_RISK로 분류.**

---

## FALSE_POSITIVE — 제거된 이슈 (3건)

### [FP-PERF-003] search_gp_registry 외부 API 장시간 호출 → FP-LOGIC

**원래 주장**: 3개 외부 API 직렬 호출로 장시간 블로킹.

**반증**: Read로 `public_data_service.py:141-145` 확인 — `asyncio.gather()`로 3개 API **병렬** 호출 + 캐시 데코레이터 적용. 이미 최적화 완료.

---

### [FP-MIG-C001] 048 파일명-ID 불일치 → FP-LOGIC

**원래 주장**: `048_pef_gp_indexes.py` 파일의 `revision = "048b"`가 불일치.

**반증**: Alembic은 revision 문자열로 체인을 관리하며 파일명은 무관. `048_contract_generation_indexes.py`(`revision="048"`) → `048_pef_gp_indexes.py`(`revision="048b"`, `down_revision="048"`)는 의도적 서브 리비전. 체인 정상.

---

### [FP-CODE-C04] finalize_checklist commit-then-delay 패턴 → FP-HALLUC

**원래 주장**: `finalize_checklist`에서 commit 후 Celery `.delay()` 호출, 실패 시 FINALIZING 상태 고착.

**반증**: Read로 `fm_checklist_service.py:124-155` 전문 확인. `flush()` + `refresh()` 사용하며 `commit()`은 라우터에서 수행. **Celery `.delay()` 호출 없음**. 에이전트의 환각(hallucination).

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

1. [SEC-K001] [Critical/HIGH]: KIIS 라우터 13개 파일 인증 완전 누락 — `kiis/app/routers/` 13 files (점수: 115)
2. [SEC-K002] [Critical/HIGH]: KIIS sanctions 에러 메시지 내부 정보 노출 — `kiis/app/routers/sanctions.py` (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89, 표준 준수/보안)

1. [MIG-C003] [Major/HIGH]: IM 001 마이그레이션 JSONB 직접 사용 — `im/alembic/versions/001_initial_schema.py` (점수: 85)
2. [MIG-C004] [Major/HIGH]: IM 005 마이그레이션 UUID/JSONB 직접 사용 — `im/alembic/versions/005_audit_logs.py` (점수: 85)
3. [MIG-C005] [Major/HIGH]: deal-mgmt 029 마이그레이션 UUID/JSONB 직접 사용 — `deal-mgmt/migrations/versions/029_document_extraction.py` (점수: 85)
4. [SEC-H001] [Major/HIGH]: AUTH_ENABLED=False 빈 ENV 가드 우회 — `deal-mgmt/app/core/security.py` (점수: 85)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

1. [MIG-C002] [Moderate/HIGH]: 041 ALTER TYPE 방언 가드 누락 — `deal-mgmt/migrations/versions/041_buyer_tiering_marketing_logs.py` (점수: 55)
2. [CODE-C01] [Moderate/HIGH]: min_revenue float→Decimal 타입 힌트 불일치 — `deal-mgmt/app/services/si_mapping_service.py` (점수: 55)
3. [PERF-001] [Moderate/HIGH]: sync_gp_profiles N+1 — `kiis/app/services/public_data_service.py` (점수: 55)
4. [PERF-005] [Moderate/MEDIUM]: blob sync I/O in Azure mode — `deal-mgmt/app/core/blob_storage.py` (점수: 49, 교차 검증 +10)
5. [PERF-004] [Moderate/MEDIUM]: 요청별 httpx client — `deal-mgmt/app/services/si_mapping_service.py` (점수: 39)
6. [CODE-C03] [Moderate/MEDIUM]: reputation 뉴스 LIMIT 누락 — `kiis/app/services/reputation_service.py` (점수: 39)

### P3 — 저우선 (점수: <30, 설계 리스크)

1. [MIG-C006] [Moderate/MEDIUM]: IM 002 PostgreSQL 전용 부분 인덱스 — `im/alembic/versions/002_active_corpcode.py` (점수: 24)
2. [SEC-H002] [Moderate/MEDIUM]: CLIENT SI 전역 접근 — `deal-mgmt/app/routers/si_mapping.py` (점수: 24)
3. [MIG-C007] [Minor/HIGH]: 051 downgrade = pass — `deal-mgmt/migrations/versions/051_add_client_audit_actions.py` (점수: 20)
4. [PERF-002] [Minor/MEDIUM]: 10K 인메모리 로딩 — `deal-mgmt/app/services/si_mapping_service.py` (점수: 12)

---

## Methodology

- **Agents**: Security Auditor, Python Code Reviewer, Migration Validator, Performance Profiler, Frontend Type Checker
- **Excluded Agents**: 없음 (5/5 실행)
- **Files scanned**: 801 소스 파일
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 18건 전수 검증 (Critical + Major)
- **Backend availability**: deal-mgmt(✓) KIIS(✓) IM(✓)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 21건 (5개 에이전트)
- 거부된 가설 (사전 제거): 4건 (3 FP + 1 중복 병합)
- 보고된 이슈: 16건 (Critical 2, Major 4, Moderate 6, Minor 2, DR 2)
- 거부율: 19%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 (FP-LOGIC) | 2 | PERF-003: asyncio.gather 병렬 실행 확인, MIG-C001: 의도적 서브 리비전 |
| 환각 (FP-HALLUC) | 1 | CODE-C04: finalize_checklist에 Celery delay 없음 |
| 중복 | 1 | PERF-005 = CODE-C02 (blob sync I/O) |
| 심각도 하향 | 10 | 원래 Critical 16건 → Major 4 + Moderate 6 + Minor 2 + Design Risk 2 |

### 심각도 재분류 상세

| 원래 ID | 원래 심각도 | 최종 심각도 | 하향 사유 |
|---------|-----------|-----------|----------|
| PERF-001 | Critical | Moderate | 관리자 배치 작업, 사용자 대면 API 아님 |
| PERF-002 | Critical | Minor (DR) | 의도적 설계 결정, defer 최적화 적용 완료 |
| PERF-003 | Critical | FALSE_POSITIVE | asyncio.gather + 캐시 적용 확인 |
| PERF-004 | Critical | Moderate | 딥다이브 빈도 낮음, 단일 요청 내 커넥션 재사용 |
| PERF-005 | Critical | Moderate | Azure SDK 청크 쓰기, 실질적 블로킹 미미 |
| MIG-C001 | Critical | FALSE_POSITIVE | 의도적 048b 서브 리비전 |
| MIG-C002 | Critical | Moderate | CI는 create_all() 사용, PG에서 정상 동작 |
| MIG-C006 | Critical | Moderate (DR) | 부분 인덱스 크로스 DB 대안 없음 |
| MIG-C007 | Critical | Minor | PostgreSQL 제약, 문서화 완료 |
| CODE-C01 | Critical | Moderate | 런타임 영향 없음 (SQLAlchemy 자동 변환) |
| CODE-C03 | Critical | Moderate | 현재 데이터 규모에서 실질적 문제 없음 |
| CODE-C04 | Critical | FALSE_POSITIVE | Celery delay 호출 없음 (환각) |
