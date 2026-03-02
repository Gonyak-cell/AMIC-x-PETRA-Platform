# Code Review — MA Full Integrated Review (Round 2)

> **Review Date**: 2026-03-02 01:31 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff origin/master...HEAD` — 2,761 files (커밋 푸시 제외 작업 내역)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(170 passed, PASS) build(PASS) ruff(PASS) pytest(1,146 passed, PASS)
> **Review Gates**: Backend(deal-mgmt:281, IM:204, KIIS:89) Agent-Filtering(5개 호출, 0개 제외)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 10    | HIGH: 7 / MEDIUM: 3 / LOW: 0 | P0: 4 / P1: 6 |
| Major    | 7     | HIGH: 5 / MEDIUM: 2 / LOW: 0 | P1: 5 / P2: 2 |
| Moderate | 4     | HIGH: 2 / MEDIUM: 2 / LOW: 0 | P2: 4 |
| Minor    | 2     | HIGH: 1 / MEDIUM: 1 / LOW: 0 | P3: 2 |
| **Total**| **23**| HIGH: **15** / MEDIUM: **8** / LOW: **0** | P0: **4** / P1: **11** / P2: **6** / P3: **2** |

**FP Prevention**: 가설 28건 검증, 5건 사전 거부 (거부율: 17.9%) | 교차 검증 17건 수행
- SEC-005: HIGH→MEDIUM 하향 (DESIGN_RISK — 전체 라우터 공통 패턴)
- M-C06: CRITICAL→DESIGN_RISK 하향 (PostgreSQL DROP COLUMN 자동 FK 삭제)
- C-03(perf): CRITICAL→MAJOR 하향 (db.add만 수행, 실제 N+1 아님)

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

---

#### [M-C01] 048 revision ID 중복 — Alembic 헤드 분기 — [Critical/HIGH] — P0 (점수: 115)

**파일**: `deal-mgmt/migrations/versions/048_contract_generation_indexes.py:11`, `048_pef_gp_indexes.py:13`
**교차 검증**: CONFIRMED + review-verifier 확인

두 파일이 동일한 `revision = "048"`, `down_revision = "047"`을 선언:
```python
# 048_contract_generation_indexes.py
revision = "048"
down_revision = "047"

# 048_pef_gp_indexes.py
revision = "048"
down_revision = "047"
```

`049_pef_name_index.py`가 `down_revision = "048"`을 참조하나 어느 048인지 비결정적. `alembic upgrade head` 시 한 마이그레이션이 스킵되어 인덱스 누락.

**수정**: `048_pef_gp_indexes.py`를 `052`로 리넘버링하고 `down_revision = "051"` 지정. 049/050도 체인 조정.

---

#### [M-C02] 045/051 enum ADD VALUE — autocommit_block 미사용 — [Critical/HIGH] — P0 (점수: 115)

**파일**: `deal-mgmt/migrations/versions/045_ma_directives_phase1.py:64-67`, `051_add_client_audit_actions.py:22-25`
**교차 검증**: CONFIRMED + review-verifier 확인

```python
# 045:64-67 — autocommit_block 없음
if bind.dialect.name == "postgresql":
    op.execute(sa.text("ALTER TYPE buyercandidatestatus ADD VALUE IF NOT EXISTS 'BID_SUBMITTED'"))

# 051:22-25 — 동일 패턴
if bind.dialect.name == "postgresql":
    op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_ASSIGNED'"))
```

PostgreSQL에서 `ALTER TYPE ADD VALUE`는 트랜잭션 내 실행 불가. 046에서는 `autocommit_block()`으로 올바르게 처리됨.

**수정**: 두 파일 모두 `with op.get_context().autocommit_block():` 래핑.

---

#### [C-03] BuyerCandidateOut — Decimal 금액 float 직렬화 — [Critical/HIGH] — P0 (점수: 115)

**파일**: `deal-mgmt/app/schemas/buyer.py:38-41`
**교차 검증**: CONFIRMED + 2개 에이전트 보고

```python
@field_serializer("ioi_value", "loi_value", "final_offer_value")
@classmethod
def _serialize_decimal(cls, v: Decimal | None) -> float | None:
    return float(v) if v is not None else None  # M&A 입찰금액 정밀도 손실
```

`ioi_value`, `loi_value`, `final_offer_value`는 `Numeric(20,2)` DB 컬럼. 수백억~수조원 규모 금액에서 IEEE 754 부동소수점 오차 발생.

**수정**: `float(v)` → `str(v)`, 반환 타입 `float | None` → `str | None`.

---

#### [C-04] PefFundOut/FIRecommendation — Decimal 금액 float 직렬화 — [Critical/HIGH] — P0 (점수: 115)

**파일**: `deal-mgmt/app/schemas/pef_registry.py:23-26, 37-40`
**교차 검증**: CONFIRMED + 2개 에이전트 보고

```python
@field_serializer("total_committed_capital")
def _serialize_capital(cls, v: Decimal | None) -> float | None:
    return float(v) if v is not None else None

@field_serializer("min_fund_size", "total_committed_sum")
def _serialize_decimal(cls, v: Decimal) -> float:
    return float(v)
```

FI 추천 알고리즘의 약정액 비교에 float 오차가 누적.

**수정**: `float(v)` → `str(v)`, 반환 타입 `str | None` / `str`.

---

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [SEC-004] KIIS GP 조회 4개 엔드포인트 인증 누락 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `kiis/app/routers/public_data.py:42, 64, 129, 246`
**교차 검증**: CONFIRMED

4개 GET 엔드포인트에 `get_jwt_claims` Depends 없음. 동일 라우터의 POST 엔드포인트는 인증 적용. GP 운용사 AUM, 펀드 수, 연락처 등 기관전용 민감 정보 미인증 노출.

**수정**: `_claims: JWTClaims = Depends(get_jwt_claims)` 추가.

---

#### [SEC-006] attachments 상대경로 저장 + 경로 검증 불안정 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `deal-mgmt/app/routers/attachments.py:21, 170-176`
**교차 검증**: CONFIRMED

```python
UPLOAD_DIR = Path("uploads/attachments")  # CWD 기준 상대경로
```

Gunicorn이 다른 디렉토리에서 실행되면 파일 저장/검증 경로 불일치.

**수정**: `UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "attachments"`

---

#### [P-01] si_mapping _lookup_by_ksic O(N×M) 풀 스캔 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:584-592`
**교차 검증**: CONFIRMED

```python
for index_code, companies in ksic_index.items():  # M개 키 전부 순회
    if index_code.startswith(code) or code.startswith(index_code):
```

10,000건 × 수백 KSIC 코드 시 수백만 번 문자열 비교.

**수정**: 정렬된 키 + `bisect` 이진 탐색 또는 trie 구조 전환.

---

#### [P-02] si_mapping 10,000건 ORM 풀 로딩 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:514-527`
**교차 검증**: CONFIRMED

```python
return list(result.scalars().all())  # 10,000개 ORM 객체 인스턴스화
```

동시 요청 3건 = 30,000개 ORM 객체 RAM 상주. JSONB 컬럼 포함 시 메모리 폭증.

**수정**: 필요 컬럼만 `select(SICompany.id, .ksic_codes, .revenue, .company_name)` + `mappings()`.

---

#### [P-03] blob_storage Azure readall() 전체 메모리 로딩 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `deal-mgmt/app/core/blob_storage.py:139-141`
**교차 검증**: CONFIRMED

```python
data = await stream.readall()  # 50MB 파일 전체 메모리 적재
await asyncio.to_thread(dest.write_bytes, data)
```

docstring("청크 단위")과 실제 구현(`readall`)이 불일치. 동시 5건 × 50MB = 250MB+.

**수정**: `stream.chunks()` 또는 `readinto()` 청크 스트리밍.

---

#### [P-04] vdr_extraction N문서 직렬 HTTP 2회 호출 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `im/src/api/tasks/vdr_extraction.py:69-116`
**교차 검증**: CONFIRMED

N문서 × 직렬 HTTP 2회 × 500ms = 10건에 10초+. `content_resp.content` 전체 메모리 로딩.

**수정**: `httpx.AsyncClient` + `asyncio.gather()` 병렬화 또는 배치 API.

---

#### [P-05] KIIS public_data_service 500건 전량 페치 + 인메모리 필터 — [Critical/HIGH] — P1 (점수: 85)

**파일**: `kiis/app/services/public_data_service.py:139-205`
**교차 검증**: CONFIRMED

3개 외부 API × 500건 직렬 페치 → Python 인메모리 필터/정렬. 캐시 미스 시 9초+.

**수정**: API 요청에 `company_name` 파라미터 전달 + `asyncio.gather()` 병렬화.

---

#### [M-C03] 045 pef_fund_registry NUMERIC(20,2) 정밀도 — [Critical/HIGH] — P1 (점수: 70)

**파일**: `deal-mgmt/migrations/versions/045_ma_directives_phase1.py:33`
**교차 검증**: CONFIRMED

억원 단위 PEF 총약정액에 소수 2자리만 저장. 프로젝트 금액 표준 `NUMERIC(18,4)`와 불일치.

**수정**: 마이그레이션으로 `ALTER COLUMN ... TYPE NUMERIC(20,4)` 적용.

---

#### [P-06] fss_pef_service PEF 건당 N+1 DB 쿼리 — [Critical/MEDIUM] — P1 (점수: 60)

**파일**: `kiis/app/services/fss_pef_service.py:149-179`
**교차 검증**: CONFIRMED

⚠️ MEDIUM 신뢰도 — 캐시(`gp_cache`)가 동일 GP 중복을 방지하므로 실제 쿼리 수는 고유 GP 수에 비례.

PEF 1건 × GP 최대 3개 × 2~3회 쿼리. 1,000건 PEF = 수천 회 DB 왕복.

**수정**: 전체 GP 이름 수집 → IN 배치 쿼리 1회 → 미매칭분 bulk_insert.

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [SEC-007] contract_generation 인메모리 레이트 리미터 멀티 워커 무효 — [Moderate/HIGH] — P2 (점수: 55)

**파일**: `deal-mgmt/app/routers/contract_generation.py:40-61`
**교차 검증**: CONFIRMED + 2개 에이전트 보고

프로세스 로컬 dict → 2-worker 환경에서 분당 10회까지 우회 가능.

---

#### [W-01] contract_generation Jinja2 필터 float 변환 — [Moderate/HIGH] — P2 (점수: 40)

**파일**: `deal-mgmt/app/services/contract_generation_service.py:44, 55`
**교차 검증**: CONFIRMED

계약서 금액 포맷팅에 `float()` 사용. 표시 전용이나 법적 문서에 잘못된 금액 표시 위험.

---

#### [W-02] si_mapping DART 재무 금액 float 반환 — [Moderate/HIGH] — P2 (점수: 40)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:459-469`
**교차 검증**: CONFIRMED

`_extract_amount()` → `float(raw)`. 수백억~수조원 재무 데이터 정밀도 손실.

---

#### [SEC-008] KVIC CSV 업로드 MIME 검증 누락 — [Moderate/MEDIUM] — P2 (점수: 36)

**파일**: `kiis/app/routers/public_data.py:419-421`
**교차 검증**: CONFIRMED

CSV 확장자 파일은 매직 바이트 검증 없이 파싱. 다른 엔드포인트와 일관성 부재.

---

#### [P-07] list_extractions 미페이지네이션 전량 반환 — [Moderate/MEDIUM] — P2 (점수: 36)

**파일**: `deal-mgmt/app/services/document_extraction_service.py:129-139`
**교차 검증**: CONFIRMED

VDR 문서 수백 건 업로드 시 전량 반환 + JSONB 직렬화. 폴링 엔드포인트에서 반복 실행.

---

#### [SEC-005] pef_registry fi-recommendations 비CLIENT 딜 소유 검증 누락 — [Moderate/MEDIUM] — P2 (점수: 36)

**파일**: `deal-mgmt/app/routers/pef_registry.py:126`
**교차 검증**: DESIGN_RISK (대부분의 deal-mgmt 라우터 공통 패턴)

⚠️ HIGH→MEDIUM 하향 — `check_client_deal_access`는 CLIENT 역할만 검증하며, 비-CLIENT의 딜 소유 검증은 설계 리스크.

---

### P3 — 저우선 (점수: <30)

---

#### [SEC-009] blob_storage 로컬 모드 경로 탐색 미검증 — [Minor/HIGH] — P3 (점수: 20)

**파일**: `deal-mgmt/app/core/blob_storage.py:103, 121`

`blob_name`이 `../../` 포함 가능하나, 현재 사용자 입력이 직접 전달되지 않아 실현 가능성 낮음.

---

#### [W-03] permit_knowledge_base threshold float 타입 — [Minor/MEDIUM] — P3 (점수: 12)

**파일**: `deal-mgmt/app/services/permit_knowledge_base.py:28`

`Decimal < float` 비교에서 의도치 않은 결과 가능. KB 데이터 고정값이므로 영향 제한적.

---

## Priority Matrix

### P0 — 즉시 수정 (4건)
1. **[M-C01]** [Critical/HIGH]: 048 revision ID 중복 → Alembic 헤드 분기 (점수: 115)
2. **[M-C02]** [Critical/HIGH]: 045/051 autocommit_block 미사용 → PostgreSQL 배포 실패 (점수: 115)
3. **[C-03]** [Critical/HIGH]: BuyerCandidateOut Decimal→float 직렬화 → 금액 정밀도 손실 (점수: 115)
4. **[C-04]** [Critical/HIGH]: PefFundOut Decimal→float 직렬화 → 펀드 약정액 정밀도 손실 (점수: 115)

### P1 — 스프린트 우선 (7건)
1. **[SEC-004]** [Critical/HIGH]: KIIS GP 조회 4개 인증 누락 (점수: 85)
2. **[SEC-006]** [Critical/HIGH]: attachments 상대경로 (점수: 85)
3. **[P-01]** [Critical/HIGH]: si_mapping O(N×M) 풀 스캔 (점수: 85)
4. **[P-02]** [Critical/HIGH]: si_mapping 10K ORM 로딩 (점수: 85)
5. **[P-03]** [Critical/HIGH]: blob_storage readall 메모리 (점수: 85)
6. **[P-04]** [Critical/HIGH]: vdr_extraction 직렬 HTTP (점수: 85)
7. **[P-05]** [Critical/HIGH]: KIIS 500건 전량 페치 (점수: 85)
8. **[M-C03]** [Critical/HIGH]: NUMERIC(20,2) 정밀도 (점수: 70)
9. **[P-06]** [Critical/MEDIUM ⚠️]: fss_pef N+1 (점수: 60)

### P2 — 개선 권장 (6건)
1. **[SEC-007]** [Moderate/HIGH]: 레이트 리미터 멀티 워커 (점수: 55)
2. **[W-01]** [Moderate/HIGH]: Jinja2 float 포맷 (점수: 40)
3. **[W-02]** [Moderate/HIGH]: DART 재무 float (점수: 40)
4. **[SEC-008]** [Moderate/MEDIUM ⚠️]: CSV MIME 검증 (점수: 36)
5. **[P-07]** [Moderate/MEDIUM ⚠️]: 추출 미페이지네이션 (점수: 36)
6. **[SEC-005]** [Moderate/MEDIUM ⚠️]: 비CLIENT 딜 소유 검증 (점수: 36)

### P3 — 저우선 (2건)
1. **[SEC-009]** [Minor/HIGH]: blob 로컬 경로 탐색 (점수: 20)
2. **[W-03]** [Minor/MEDIUM ⚠️]: permit threshold float (점수: 12)

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | Long-List 3컬럼 제거 | ✅ | TransactionWorkspacePage.tsx |
| 2 | PEF 레지스트리 + FI 추천 | ✅ | pef_fund_registry.py + pef_registry.py router + FIRecommendModal.tsx |
| 3 | Short-List 연락처 필수화 | ✅ | buyers.py promote-short-list 엔드포인트 |
| 4 | Short-List↔마케팅 로그 통합 | ✅ | ShortListOverview.tsx + is_short_listed 플래그 |
| 5 | 입찰 결과 추적 | ✅ | BID_SUBMITTED/NOT_SUBMITTED/DROPPED enums |
| 6 | 파이프라인 9단계 | ✅ | TransactionPhase 9값 + 046 마이그레이션 |
| 7 | 계약서 생성 모듈 | ✅ | contract_template/clause/variable 모델 + 서비스 + 라우터 |

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| tsc --noEmit | ✅ PASS | §1 타입 정합성 자동 검증됨 |
| eslint | ✅ PASS | §1 코드 스타일 자동 검증됨 |
| vitest (170 passed) | ✅ PASS | §2 프론트 테스트 자동 검증됨 |
| vite build | ✅ PASS | §1 빌드 정합성 자동 검증됨 |
| ruff check + format | ✅ PASS | §1 Python 린트/포맷 자동 검증됨 |
| pytest (1,146 passed) | ✅ PASS | §2 백엔드 테스트 자동 검증됨 |

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, performance-profiler, migration-validator, general-purpose (frontend)
- **Excluded Agents**: 없음 (5/5 호출)
- **Files scanned**: 2,761 (diff vs origin/master)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 17건 수행
- **Backend availability**: deal-mgmt(available, 281) IM(available, 204) KIIS(available, 89)

## 검증 투명성

### 검증 통계
- 검증한 가설: 28건
- 거부된 가설 (사전 제거): 5건
- 보고된 이슈: 23건
- 거부율: 17.9%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 심각도 하향 | 2 | SEC-005(HIGH→MEDIUM, 공통 패턴), C-03perf(Critical→Major, db.add만) |
| 분류 변경 | 1 | M-C06(Critical→DESIGN_RISK, PG 자동 FK 삭제) |
| 중복 | 1 | W-04(SEC-007과 동일 이슈 — 레이트 리미터) |
| 반증됨 | 1 | SEC-010(Jinja2 SandboxedEnvironment + AST 화이트리스트로 실제 공격 불가) |
