# Code Review — MA Full Integrated Review (feat/ma-workflow)

> **Review Date**: 2026-03-02 00:59 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `feat/ma-workflow` vs `origin/master` — 전체 MA 워크플로우 브랜치 (2,644 파일)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) pytest(PASS — 1,120/1,120) build(PASS)
> **Review Gates**: Backend(deal-mgmt available, FDD available, KIIS available) Agent-Filtering(5개 에이전트 호출, 0개 제외)
> **Severity Filter**: `--severity critical` (Critical 이슈만 보고)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 17    | HIGH: 8 / MEDIUM: 5 / LOW: 4 | P0: 4 / P1: 5 / P2: 4 / P3: 4 |
| **Total**| **17** | HIGH: **8** / MEDIUM: **5** / LOW: **4** | P0: **4** / P1: **5** / P2: **4** / P3: **4** |

**FP Prevention**: 가설 42건 검증, 25건 사전 거부 (거부율: 60%) | 교차 검증 17건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 5건 하향 조정
- LOW 신뢰도 이슈 4건 하향 조정 (기존 마이그레이션에 대한 이슈 — 프로덕션 이미 적용)

---

## Findings

### [SEC-001] INTERNAL_SERVICE_KEY 빈 문자열 허용 — VDR 기밀문서 무인증 접근 — [Critical/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/routers/vdr_internal.py:35,54`

**증거**:
```python
# vdr_internal.py:35
_INTERNAL_SERVICE_KEY = os.getenv("INTERNAL_SERVICE_KEY", "")

# vdr_internal.py:54
if x_internal_key != _INTERNAL_SERVICE_KEY:
    raise HTTPException(status_code=403, detail="Invalid internal service key")
```

**위험**: `INTERNAL_SERVICE_KEY` 미설정 시 기본값 `""`. 공격자가 `X-Internal-Key:` 헤더에 빈 문자열 전송 → `"" == ""` 통과 → `/internal/vdr/` 하위 전체 VDR 문서 무인증 접근. M&A 기밀 실사 문서 전량 노출.

**교차 검증**: CONFIRMED — Read로 코드 직접 확인. `_verify_internal_key`가 유일한 인증 수단이며, 빈 키 허용 로직 확인.

**수정안**:
```python
async def _verify_internal_key(
    x_internal_key: str | None = Header(None, alias="X-Internal-Key"),
) -> None:
    if not _INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=503, detail="Internal service not configured")
    if not x_internal_key or x_internal_key != _INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Invalid internal service key")
```

**점수**: 100 (Critical × HIGH)

---

### [SEC-002] Ralph API source_dir Path Traversal — 서버 파일 LLM 유출 — [Critical/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/routers/ralph.py:140-141`

**증거**:
```python
# ralph.py:123
def _build_pipeline(doc_type, llm_call, source_dir=None, learned_patterns=None):
    ...
    # ralph.py:140-141
    if source_dir:
        for file_info in scan_directory(source_dir):  # 경로 검증 없음
            parsed = parse_and_classify(file_info["path"])
```

**위험**: 인증된 사용자(ANALYST 이상)가 `POST /ralph/transactions/{txn_id}/sessions`에서 `source_dir: "/etc"` 또는 `source_dir: "/"` 지정 → 서버 임의 경로 재귀 스캔 → 파일 내용이 LLM API로 전달되어 서버 기밀 유출. 비교: `ldd_report_service.py:66-72`에 `_validate_source_dir()`이 이미 존재하나 Ralph에는 미적용.

**교차 검증**: CONFIRMED — `ralph.py:71`에서 `body.source_dir`가 직접 `_build_pipeline`에 전달됨. 경로 검증 함수 호출 없음.

**수정안**: `_build_pipeline()` 진입 시 `ldd_report_service._validate_source_dir()` 적용.

**점수**: 100 (Critical × HIGH)

---

### [C-01] Bid.amount에 float 저장 — Decimal 컬럼 정밀도 훼손 — [Critical/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/services/document_extraction_service.py:900-902`

**증거**:
```python
# document_extraction_service.py:900-902
elif attr in _NUMERIC_FIELDS and isinstance(val, str):
    try:
        val = float(val)   # ← Decimal이어야 함
```

**위험**: `Bid.amount`는 `Numeric(20, 2)` / `Decimal` 타입. LLM이 `"10000000000.55"` 반환 시 `float` 변환으로 부동소수점 오차 발생 → M&A 입찰 금액(수백억~수조 원) 정밀도 훼손. DB에 잘못된 값이 영구 저장.

**교차 검증**: CONFIRMED — `_NUMERIC_FIELDS = frozenset({"amount"})`, `Bid.amount: Mapped[Decimal | None]` 확인.

**수정안**: `float(val)` → `Decimal(val)`, except에 `InvalidOperation` 추가.

**점수**: 100 (Critical × HIGH)

---

### [M-C01] AuditAction enum 스키마 드리프트 — PostgreSQL 런타임 크래시 — [Critical/HIGH] — Priority: P0

**파일**: `deal-mgmt/app/models/enums.py:462-463` vs 전체 마이그레이션

**증거**:
```python
# enums.py:462-463
CLIENT_ASSIGNED = "CLIENT_ASSIGNED"   # 마이그레이션 없음
CLIENT_REMOVED = "CLIENT_REMOVED"     # 마이그레이션 없음
```

```python
# deal_clients.py:76,111
action=AuditAction.CLIENT_ASSIGNED,
action=AuditAction.CLIENT_REMOVED,
```

`grep -r "CLIENT_ASSIGNED\|CLIENT_REMOVED" deal-mgmt/migrations/` → **0건**. 어떤 마이그레이션에도 `ALTER TYPE auditaction ADD VALUE` 없음.

**위험**: PostgreSQL에서 `audit_logs` INSERT 시 `invalid input value for enum auditaction: "CLIENT_ASSIGNED"` → 500 에러. CI(SQLite)에서는 VARCHAR이므로 통과하지만 프로덕션 런타임 크래시 확정.

**교차 검증**: CONFIRMED — Grep으로 전체 마이그레이션 디렉토리 검색, 0건.

**수정안**: 마이그레이션 051 생성:
```python
op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_ASSIGNED'"))
op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'CLIENT_REMOVED'"))
```

**점수**: 100 (Critical × HIGH)

---

### [SEC-003] AUTH_ENABLED=False + ENV 오설정 시 전체 API ADMIN 우회 — [Critical/MEDIUM] — Priority: P1

**파일**: `deal-mgmt/app/core/security.py:51-55`

**증거**:
```python
if not settings.AUTH_ENABLED:
    _env = os.getenv("ENV", "").lower()
    if _env in ("production", "prod", "staging", "stg"):
        raise RuntimeError("CRITICAL: AUTH_ENABLED=False is forbidden in production/staging")
    return _DEV_CLAIMS   # role="ADMIN"
```

**위험**: `AUTH_ENABLED=False` + `ENV=development`(프로덕션에서 오설정) → 모든 요청이 ADMIN 권한 획득. 단, 1차 방어선(`AUTH_ENABLED=True`)이 프로덕션 기본값이므로 실현 가능성은 중간.

**교차 검증**: DESIGN_RISK — ENV 오설정이라는 전제 조건이 필요. 블랙리스트(금지 목록) 대신 화이트리스트(허용 목록) 방식으로 전환하면 강화 가능.

**수정안**: 블랙리스트 → 화이트리스트: `if _env not in ("local", "dev", ""):` + `_DEV_CLAIMS.role`을 `ANALYST`로 하향.

**점수**: 60 (Critical × MEDIUM)

---

### [C-02] BlobStorageClient.download_blob_to_file — async 컨텍스트 동기 블로킹 — [Critical/MEDIUM] — Priority: P1

**파일**: `deal-mgmt/app/core/blob_storage.py:132-141`

**증거**:
```python
async def download_blob_to_file(self, blob_name: str, dest: Path) -> None:
    if self._is_local:
        shutil.copy2(src, dest)   # 동기 블로킹
        return
    ...
    with dest.open("wb") as f:    # 동기 open
        async for chunk in stream.chunks():
            f.write(chunk)        # 동기 write
```

**위험**: Azure 모드에서 대용량 VDR 파일(50MB+) 다운로드 시 이벤트 루프 블로킹. 다만 주요 호출 경로가 Celery 백그라운드 태스크이므로 직접적 API 응답 지연 가능성은 중간.

**교차 검증**: PARTIAL — 주 호출자가 백그라운드 태스크인 점을 고려하여 MEDIUM으로 하향.

**수정안**: `aiofiles` 사용 또는 `asyncio.to_thread` 래핑.

**점수**: 60 (Critical × MEDIUM)

---

### [P1] RFI 동기화 이중 N+1 쿼리 — [Critical/HIGH] — Priority: P1

**파일**: `deal-mgmt/app/services/rfi_sync_service.py:38-52`

**증거**:
```python
for item in accepted_items:                       # 루프 1
    mapping_q = select(RFIChecklistMapping).where(
        RFIChecklistMapping.rfi_item_id == item.id,  # N회 DB 왕복
    )
    mappings = list((await db.execute(mapping_q)).scalars().all())
    for mapping in mappings:                      # 루프 2
        dd_q = select(DDChecklist).where(DDChecklist.id == mapping.target_item_id)  # M회 DB 왕복
```

**위험**: ACCEPTED 아이템 N개, 매핑 M개 시 총 1 + N + N*M번 DB 쿼리. 20건, 매핑 3개씩이면 단일 API에 쿼리 61회.

**교차 검증**: CONFIRMED — Read로 N+1 패턴 직접 확인.

**수정안**: IN 쿼리 2회로 일괄 조회 후 인메모리 매핑.

**점수**: 100 (Critical × HIGH) — 단, 성능 이슈이므로 P1

---

### [P3] SI 매핑 전체 테이블 풀 스캔 (limit 없음) — [Critical/MEDIUM] — Priority: P1

**파일**: `deal-mgmt/app/services/si_mapping_service.py:498-510`

**증거**:
```python
async def _load_filtered_companies(db, min_revenue, require_investment_history):
    q = select(SICompany)
    ...
    result = await db.execute(q)
    return list(result.scalars().all())   # limit 없음 — 수만 건 전체 로딩
```

**위험**: SI 기업 수만 건(상장 2,500 + 비상장 수천 건) 전체를 ORM 객체로 메모리 로딩. revenue/has_investment_history에 인덱스 없음.

**교차 검증**: CONFIRMED — 코드에 limit 없음 + 인덱스 부재 확인.

**수정안**: limit 상한 추가 + revenue 컬럼 인덱스 추가.

**점수**: 60 (Critical × MEDIUM)

---

### [P5] list_buyers — limit 없는 SELECT ALL — [Critical/MEDIUM] — Priority: P1

**파일**: `deal-mgmt/app/routers/buyers.py:76-99`

**증거**:
```python
@router.get("", response_model=list[BuyerCandidateOut])
async def list_buyers(...):
    q = q.order_by(BuyerCandidate.created_at.desc())
    result = await db.execute(q)
    return [BuyerCandidateOut.model_validate(b) for b in result.scalars().all()]
    # ↑ limit 없음 — 거래당 매수자 전원 로딩
```

**위험**: 대형 M&A 거래에서 매수자 100-500건 이상 가능. SI 매핑 `bulk_add_to_buyers` 기능으로 대량 등록이 쉬움.

**교차 검증**: CONFIRMED — `transaction_id` 스코핑은 있으나 pagination 파라미터 없음.

**수정안**: `limit: int = Query(50, ge=1, le=200)`, `offset: int = Query(0, ge=0)` 추가.

**점수**: 60 (Critical × MEDIUM)

---

### [P2] batch_extract 루프 내 직렬 DB 쿼리 — [Critical/MEDIUM] — Priority: P2

**파일**: `deal-mgmt/app/routers/document_extraction.py:123-129`

**증거**: 최대 10건 `vdr_document_ids`에 대해 `has_active_extraction`(SELECT) + `create_extraction`(INSERT+flush) 직렬 실행. 10건 배치 시 최대 20회 DB 왕복.

**교차 검증**: CONFIRMED — 단, 최대 10건으로 제한됨. 실질적 영향은 ~100ms 추가 지연 수준.

**수정안**: IN 쿼리 1회로 중복 체크, flush 1회로 통합.

**점수**: 40 (Critical × MEDIUM, bounded scope)

---

### [P4] get_data_stats — 6회 직렬 COUNT 쿼리 — [Critical/MEDIUM] — Priority: P2

**파일**: `deal-mgmt/app/services/si_mapping_service.py:44-64`

**증거**: 6개 독립 COUNT 쿼리가 직렬 실행. SICompany 관련 4개를 단일 집계 쿼리로 병합 가능.

**교차 검증**: CONFIRMED — AsyncSession은 단일 커넥션이라 `asyncio.gather` 무효. 단, SICompany 관련 4개를 1개로 병합하여 4→1로 줄일 수 있음.

**수정안**: `select(func.count(), func.count(SICompany.revenue), ...)` 단일 집계 쿼리.

**점수**: 40 (Critical × MEDIUM, bounded scope)

---

### [M-C04] 046번 upgrade() 명시적 COMMIT — 트랜잭션 무결성 — [Critical/MEDIUM] — Priority: P2

**파일**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:36`

**증거**:
```python
op.execute(sa.text("COMMIT"))
```

**위험**: Alembic 트랜잭션 격리 깨짐. 단, PostgreSQL `ALTER TYPE ADD VALUE`는 트랜잭션 내에서 새 값 즉시 사용 불가 — 이것은 PostgreSQL의 알려진 제한. 코드에 상세 주석으로 복구 절차 문서화됨.

**교차 검증**: CONFIRMED — PostgreSQL 제한으로 인한 필수 패턴이나, `autocommit_block()` 사용이 더 안전.

**수정안**: `op.get_context().autocommit_block()` 사용.

**점수**: 40 (Critical × MEDIUM, documented workaround)

---

### [M-C05] 046번 downgrade() — MOU_SIGNED/MAIN_DUE_DILIGENCE 데이터 손실 — [Critical/MEDIUM] — Priority: P2

**파일**: `deal-mgmt/migrations/versions/046_transaction_phase_restructure.py:45-61`

**증거**: downgrade 시 `MOU_SIGNED`/`MAIN_DUE_DILIGENCE` → `NEGOTIATION` 강제 변환. 원래 단계 정보 영구 소실.

**교차 검증**: CONFIRMED — 단, 코드에 ⚠️ 데이터 유실 경고 주석이 상세히 문서화됨. 프로덕션 롤백 전 영향 건수 확인 쿼리도 제공.

**수정안**: downgrade에 `count > 0` 가드 추가하여 데이터 존재 시 롤백 차단.

**점수**: 40 (Critical × MEDIUM, documented risk)

---

### [M-C02] 27개 마이그레이션 — PostgreSQL 전용 타입 직접 사용 — [Critical/LOW] — Priority: P3

**파일**: 001~030 범위 27개 마이그레이션 파일

**증거**: `postgresql.UUID(as_uuid=True)`, `postgresql.JSONB()` 직접 사용. 047번부터 올바른 크로스 DB 패턴 적용.

**교차 검증**: DESIGN_RISK — 기존 마이그레이션이며 프로덕션에 이미 적용 완료. CI는 마이그레이션을 직접 실행하지 않고 모델 기반 테이블 생성 사용. 향후 CI 마이그레이션 테스트 추가 시에만 문제.

**점수**: 30 (Critical × LOW, already applied)

---

### [M-C03] 037번 downgrade() 빈 함수 — [Critical/LOW] — Priority: P3

**파일**: `deal-mgmt/migrations/versions/037_retry_seed_si_reference_data.py:35-37`

**증거**: `downgrade() -> pass`. 036의 재실행 마이그레이션이므로 036의 downgrade에 위임.

**교차 검증**: PARTIAL — 설계 의도에 따른 위임 패턴. 실제 데이터 손실 위험은 036 downgrade 범위 내.

**점수**: 30 (Critical × LOW, documented delegation)

---

### [M-C06] 007/010/014 — PostgreSQL 전용 트리거/함수 — [Critical/LOW] — Priority: P3

**파일**: 007, 010, 014 마이그레이션 파일

**증거**: `CREATE OR REPLACE FUNCTION ... LANGUAGE plpgsql` — SQLite 비호환.

**교차 검증**: DESIGN_RISK — 기존 마이그레이션이며 프로덕션 적용 완료. M-C02와 동일한 맥락.

**점수**: 30 (Critical × LOW, already applied)

---

### [M-C07] 035번 — 비가역적 데이터 삭제 — [Critical/LOW] — Priority: P3

**파일**: `deal-mgmt/migrations/versions/035_si_schema_improvements.py:29-43`

**증거**: 중복 데이터 삭제 후 UNIQUE 제약 추가. 코드 주석에 비가역성 명시.

**교차 검증**: PARTIAL — 이미 적용된 마이그레이션이며, 주석에 위험 문서화됨.

**점수**: 30 (Critical × LOW, already applied and documented)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

1. **[SEC-001]** [Critical/HIGH]: VDR 내부 API 빈 키 인증 우회 — `vdr_internal.py` (점수: 100)
2. **[SEC-002]** [Critical/HIGH]: Ralph source_dir Path Traversal — `ralph.py` (점수: 100)
3. **[C-01]** [Critical/HIGH]: Bid.amount float→Decimal 정밀도 훼손 — `document_extraction_service.py` (점수: 100)
4. **[M-C01]** [Critical/HIGH]: AuditAction enum 스키마 드리프트 — `enums.py` vs migrations (점수: 100)

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)

1. **[SEC-003]** [Critical/MEDIUM ⚠️]: AUTH_ENABLED=False ENV 가드 화이트리스트 전환 — `security.py` (점수: 60, 신뢰도 하향)
2. **[C-02]** [Critical/MEDIUM ⚠️]: Blob download 동기 블로킹 I/O — `blob_storage.py` (점수: 60, 신뢰도 하향)
3. **[P1]** [Critical/HIGH]: RFI 동기화 이중 N+1 쿼리 — `rfi_sync_service.py` (점수: 100, 성능)
4. **[P3]** [Critical/MEDIUM]: SI 매핑 전체 테이블 풀 스캔 — `si_mapping_service.py` (점수: 60)
5. **[P5]** [Critical/MEDIUM]: list_buyers 페이지네이션 누락 — `buyers.py` (점수: 60)

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

1. **[P2]** [Critical/MEDIUM]: batch_extract 직렬 DB 왕복 — `document_extraction.py` (점수: 40)
2. **[P4]** [Critical/MEDIUM]: get_data_stats 직렬 6회 COUNT — `si_mapping_service.py` (점수: 40)
3. **[M-C04]** [Critical/MEDIUM]: 046 명시적 COMMIT — `046_*.py` (점수: 40)
4. **[M-C05]** [Critical/MEDIUM]: 046 downgrade 데이터 손실 — `046_*.py` (점수: 40)

### P3 — 저우선 (점수: <30, 기존 마이그레이션)

1. **[M-C02]** [Critical/LOW ⚠️]: 27개 마이그레이션 PostgreSQL 전용 타입 — 기존 적용 (점수: 30)
2. **[M-C03]** [Critical/LOW ⚠️]: 037 downgrade pass — 설계 의도 (점수: 30)
3. **[M-C06]** [Critical/LOW ⚠️]: plpgsql 트리거 — 기존 적용 (점수: 30)
4. **[M-C07]** [Critical/LOW ⚠️]: 035 비가역적 삭제 — 기존 적용 (점수: 30)

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, performance-profiler, migration-validator, general-purpose (frontend)
- **Excluded Agents**: 없음 (5개 전원 호출)
- **Files scanned**: 2,644 (backend: 276 Python app, frontend: 370 TS/TSX, tests: 50+, migrations: 50)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 17건 전수 검증
- **Backend availability**: deal-mgmt(available) FDD(available) KIIS(available)

## 검증 투명성

### 검증 통계
- 검증한 가설: 42건 (5개 에이전트 합산)
- 거부된 가설 (사전 제거): 25건
- 보고된 이슈: 17건 (Critical만)
- 거부율: 60%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 8 | "SQL 인젝션" → Grep으로 전부 SQLAlchemy ORM 파라미터 바인딩 확인 |
| 범위 외 | 3 | Minor/Moderate 이슈 (--severity critical 필터) |
| 이미 수정됨 | 4 | Round 2 리뷰에서 이미 수정된 항목 |
| 오판 | 5 | "N+1 쿼리" → Read로 확인 시 제한된 건수 (Major 미만) |
| 신뢰도 불충분 | 5 | 증거 약함 — 기존 적용 마이그레이션에 대한 추측성 이슈 |

### 에이전트별 결과 상세

| 에이전트 | 보고 | 확인됨 | 허위 양성 | 하향 |
|---------|------|--------|---------|------|
| backend-security-reviewer | 3 | 3 | 0 | SEC-003: HIGH→MEDIUM |
| python-code-reviewer | 2+2W | 2 | 0 | C-02: HIGH→MEDIUM |
| performance-profiler | 5 | 5 | 0 | P2,P4: bounded scope |
| migration-validator | 7 | 4 | 0 | M-C02,C03,C06,C07: LOW |
| frontend-security | 0 | N/A | N/A | N/A |

### 긍정 평가 (보안 강점)

- **SQL 인젝션 방어**: 전체 코드베이스 SQLAlchemy ORM 파라미터 바인딩 사용. f-string SQL 0건.
- **JWT 검증**: `verify_exp=True`, HS256 알고리즘 고정, 빈 시크릿 시 RuntimeError
- **파일 업로드 보안**: 확장자 + MIME + 교차검증 + 100MB 제한 (VDR)
- **IDOR 방어**: 모든 리소스 `transaction_id` 교차 검증 + `check_client_deal_access()`
- **프론트엔드 보안**: httpOnly 쿠키, `dangerouslySetInnerHTML` 0건, `as any` 0건, 자동 refresh
- **감사 추적**: `audit_service.record()` 모든 쓰기 작업에 적용
- **Path Traversal 방어**: `financial_models.py`, `template_visualization.py`에 경로 검증 구현 (Ralph만 누락)
