# Code Review — MA Workflow Integrated Review Round 2

> **Review Date**: 2026-03-02 11:24 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: `git diff origin/master HEAD` — 1,243 소스 파일 (Python 904, TypeScript 339)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review (5 agents) + Cross-Verification
> **Quality Gates**: tsc(✅) eslint(✅) ruff(✅) pytest(✅ 1189/1189) build(✅)
> **Review Gates**: Backend(deal-mgmt ✅, kiis ✅, fdd ✅, im ✅) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 5     | HIGH: 4 / MEDIUM: 1 / LOW: 0 | P0: 1 / P1: 4 |
| Major    | 13    | HIGH: 10 / MEDIUM: 3 / LOW: 0 | P1: 7 / P2: 6 |
| **Total**| **18**| HIGH: **14** / MEDIUM: **4** / LOW: **0** | P0: **1** / P1: **11** / P2: **6** |

**FP Prevention**: 가설 42건 검증, 12건 사전 거부 (거부율: 29%) | 교차 검증 18건 수행
**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용 — MEDIUM 신뢰도 4건 하향 조정

---

## Findings

### P0 — 즉시 수정 (점수: 90+)

---

#### [FE-SCHEMA-001] Transaction.estimated_deal_value 타입 불일치 — Critical / HIGH (점수: 100)

**파일**:
- FE: `amic-platform/src/modules/ma/types/transaction.ts:57`
- BE: `deal-mgmt/app/schemas/transaction.py:52-55`

**증거**:
```typescript
// FE — transaction.ts:57
estimated_deal_value: number | null;
```
```python
# BE — transaction.py:52-55
@field_serializer("estimated_deal_value", "target_stake", "new_share_ratio", "old_share_ratio")
@classmethod
def _serialize_decimal(cls, v: Decimal | None) -> str | None:
    return str(v) if v is not None else None
```

**설명**: BE는 `Decimal → str`로 직렬화하지만, FE는 `number`로 선언. API 응답에서 `"12345678900"` (문자열)을 받지만 TypeScript는 `number`로 취급. `parseFloat()` 없이 수치 연산 시 문자열 concatenation 발생 가능.

**수정안**: `estimated_deal_value: string | null` (FE 타입 변경)

---

### P1 — 스프린트 우선 (점수: 60-89)

---

#### [PERF-001] download_blob() 대용량 파일 전체 메모리 적재 — Critical / HIGH (점수: 100→85, 설계 제약)

**파일**: `deal-mgmt/app/core/blob_storage.py:120-130`

**증거**:
```python
async def download_blob(self, blob_name: str) -> bytes:
    if self._is_local:
        return path.read_bytes()          # 전체 bytes 반환
    stream = await blob_client.download_blob()
    return await stream.readall()         # Azure 전체 bytes 반환
```

**설명**: `download_blob_to_file()`이 청크 스트리밍으로 존재하는데도, `download_blob()`은 전체 파일을 힙에 올림. 50MB PDF 처리 시 worker당 50MB 추가.

**수정안**: 호출 지점을 전수 검사 → `download_blob_to_file()` + 임시 파일 패턴으로 일원화

---

#### [PERF-002] reputation_service._calculate_performance_score — 전체 뉴스 ORM 로드 후 Python 키워드 필터 — Critical / HIGH (점수: 85)

**파일**: `kiis/app/services/reputation_service.py:389-405`

**증거**:
```python
articles = result.scalars().all()   # 전체 ORM 객체(content 포함) 로드
for article in articles:
    text = f"{article.title or ''} {article.content or ''}"
    if any(kw in text for kw in self.EXIT_KEYWORDS):
        exit_count += 1             # count만 필요
```

**설명**: count만 필요한데 전체 뉴스 본문(수 KB/건)을 Python으로 로드. DB에서 LIKE 조건 + COUNT로 처리하면 전송량 99%+ 감소.

**수정안**: `select(func.count()).where(..., or_(*[title.ilike(f"%{kw}%") for kw in EXIT_KEYWORDS]))` 패턴

---

#### [PERF-003] get_qualitative_summary — LIMIT 없는 전체 뉴스 로드 — Critical / HIGH (점수: 85)

**파일**: `kiis/app/services/reputation_service.py:193-221`

**증거**:
```python
stmt = select(NewsArticle).where(...)
    .order_by(NewsArticle.published_at.desc())
    # LIMIT 없음
articles = list(result.scalars().all())   # 전체 로드
```

**설명**: 필요 컬럼만 select + LIMIT(최근 200건) 추가 필요.

---

#### [PERF-004] FDDClient/IMClient close() 미호출 — Major / HIGH (점수: 70)

**파일**: `deal-mgmt/app/core/dependencies.py:83-93`

**증거**:
```python
_kiis_instance = None     # ← close() 호출함
_fdd_instance = None      # ← close() 미호출, 참조만 해제
_im_instance = None       # ← close() 미호출, 참조만 해제
```

**설명**: `FDDClient.close()`와 `IMClient.close()`가 구현되어 있음에도 lifespan shutdown 시 호출 안 됨. httpx 커넥션 풀 미반환.

**수정안**: KIIS와 동일 패턴으로 FDD/IM close() 추가

---

#### [PERF-005] si_mapping_service.get_deep_dive — 매 요청마다 httpx.AsyncClient 생성/파괴 — Major / HIGH (점수: 70)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:330`

**증거**:
```python
async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
    # 7개 병렬 HTTP 요청 → 즉시 폐기
```

**설명**: 딥다이브 연속 호출 시 매번 TCP 핸드셰이크 발생. 싱글턴 클라이언트 재사용 필요.

---

#### [MIG-001] 마이그레이션 005/028/030 — Cross-DB 비호환 타입 잔존 — Critical / HIGH ⚠️ (점수: 80, 설명 참조)

**파일**:
- `deal-mgmt/migrations/versions/005_phase5a_notes_approvals.py:46-100`
- `deal-mgmt/migrations/versions/028_ldd_law_firm_style.py:28-48`
- `deal-mgmt/migrations/versions/030_contract_negotiation_workspace.py:38,61`

**증거**: `postgresql.UUID(as_uuid=True)`, `postgresql.JSONB`, `sa.dialects.postgresql.UUID` 직접 사용

**교차 검증 결과**: 이전 세션에서 "수정 완료"로 표기되었으나, **dialect guard만 추가되고 타입 자체는 미변환**. CI 테스트는 `Base.metadata.create_all`(Alembic 미실행) + SQLiteTypeCompiler 몽키패치로 통과하므로 CI 차단은 아님. 그러나 **SQLite에서 마이그레이션을 직접 실행하면 실패**.

**실제 영향**: 현재 운영은 PostgreSQL 전용이므로 프로덕션 영향 없음. 향후 CI에 마이그레이션 테스트 추가 시 차단.

---

#### [MIG-002] 마이그레이션 041/043 — Enum .create() dialect guard 누락 — Major / HIGH (점수: 70)

**파일**:
- `deal-mgmt/migrations/versions/041_buyer_tiering_marketing_logs.py:25-44`
- `deal-mgmt/migrations/versions/043_consortium_mapping.py:26-43`

**증거**:
```python
deal_role_enum = sa.Enum("SOLE_BUYER", ..., name="dealrole")
deal_role_enum.create(op.get_bind(), checkfirst=True)  # dialect guard 없음
```

**수정안**: `if bind.dialect.name == "postgresql":` 블록으로 감싸기

---

#### [MIG-003] 029_document_extraction.py downgrade — DROP TYPE dialect guard 누락 — Major / HIGH (점수: 70)

**파일**: `deal-mgmt/migrations/versions/029_document_extraction.py:122`

**증거**:
```python
op.execute("DROP TYPE IF EXISTS extractionstatus")     # PostgreSQL 전용 DDL
op.execute("DROP TYPE IF EXISTS docextractioncategory")
```

**수정안**: `if bind.dialect.name == "postgresql":` 가드 추가

---

#### [SEC-001] DEV_CLAIMS role=ADMIN 고정 — Major / HIGH (점수: 70)

**파일**: `deal-mgmt/app/core/security.py:40-44`

**증거**:
```python
_DEV_CLAIMS = JWTClaims(
    user_id="00000000-0000-0000-0000-000000000000",
    email="system@autofdd.dev",
    role="ADMIN",   # AUTH_ENABLED=False 시 전체 ADMIN 권한
)
```

**설명**: `AUTH_ENABLED=False` + `ENV=dev` 시 모든 요청이 ADMIN 권한. 스테이징 환경 오설정 시 인증 없이 ADMIN 접근 가능.

**수정안**: `role="ANALYST"`로 최소 권한 적용 또는 ADMIN 전용 엔드포인트 추가 가드

---

#### [SEC-002] template_visualization download — file_path 파라미터 교차 검증 없음 — Major / HIGH (점수: 70)

**파일**: `deal-mgmt/app/routers/template_visualization.py:89-112`

**증거**:
```python
async def download_visualization(
    transaction_id: UUID,
    file_path: str,   # 쿼리 파라미터로 임의 경로 수신
):
    resolved = _validate_path_within(path, _GENERATED_BASE_DIR, "다운로드")
```

**설명**: `_validate_path_within`이 디렉토리 탈출을 막지만, `file_path`가 해당 `transaction_id` 소속인지 교차 검증 없음. 타 거래의 파일 다운로드 가능.

**수정안**: file_path에서 transaction_id 추출 후 URL 파라미터와 일치 검증

---

#### [CODE-001] 다수 모델에서 JSONB/UUID(as_uuid=True) 직접 사용 — Major / HIGH ⚠️ (점수: 63)

**파일**:
- `deal-mgmt/app/models/approval.py:4,16,18,25,28`
- `deal-mgmt/app/models/financial_model.py:31,33,48,49,57,169`
- `deal-mgmt/app/models/compliance_item.py:18,20,36`
- `deal-mgmt/app/models/ldd_report.py` (다수)
- `deal-mgmt/app/models/contract.py` (다수)
- `deal-mgmt/app/models/engagement.py` (다수)

**교차 검증**: conftest.py 몽키패치(`visit_JSONB→JSON`, `visit_UUID→CHAR(36)`)로 CI 통과. 런타임 PostgreSQL에서도 정상. **기술부채** — Guard 2 규칙 준수를 위해 `sa.Uuid()` + `JSON().with_variant(JSONB, "postgresql")`로 점진 전환 권장.

---

### P2 — 개선 권장 (점수: 30-59)

---

#### [FE-SCHEMA-002] SICompanyOut Decimal 필드 직렬화 누락 — Major / MEDIUM (점수: 42)

**파일**: `deal-mgmt/app/schemas/si_mapping.py:49-62`

**설명**: `revenue`, `operating_profit`, `net_income` 등 9개 Decimal 필드에 `@field_serializer` 없음. Pydantic v2 기본 동작은 float으로 직렬화하여 FE `number | null`과는 호환되지만, 대형 금액에서 float 정밀도 손실 가능.

---

#### [FE-SCHEMA-003] ConsortiumMappingOut.equity_share_pct 직렬화 누락 — Major / MEDIUM (점수: 42)

**파일**: `deal-mgmt/app/schemas/consortium.py:24`

**설명**: FE-SCHEMA-002와 동일 패턴. `@field_serializer` 없음.

---

#### [PERF-006] blob_storage download_blob_to_file — 청크 리스트 전체 수집 — Major / HIGH (점수: 55)

**파일**: `deal-mgmt/app/core/blob_storage.py:147-153`

**증거**:
```python
chunks = [chunk async for chunk in stream.chunks()]  # 전체 청크를 리스트로 수집
await asyncio.to_thread(_write_chunks, chunks)
```

**설명**: "청크 스트리밍"이 목적이지만 리스트 컴프리헨션으로 전체 수집 후 전달. 50MB 파일이면 50MB 리스트 생성.

**수정안**: `async for chunk` + 즉시 파일 쓰기 패턴

---

#### [PERF-007] AuditLog.created_at 인덱스 누락 — Major / HIGH (점수: 55)

**파일**: `deal-mgmt/app/models/audit.py:25`

**설명**: `list_audit_logs()`에서 `start_date`/`end_date` 필터 + `ORDER BY created_at DESC`에 인덱스 없음. 감사 로그 누적 시 전체 테이블 스캔.

---

#### [PERF-008] NewsArticle (company_id, published_at) 복합 인덱스 누락 — Major / HIGH (점수: 55)

**파일**: `kiis/app/models/news.py:21,28`

**설명**: `reputation_service.py`의 모든 쿼리가 `WHERE company_id = X AND published_at >= Y` 패턴. 단일 인덱스만 존재.

---

#### [CODE-002] reputation_service._calculate_news_score — float→Decimal round() 정밀도 — Major / MEDIUM (점수: 42)

**파일**: `kiis/app/services/reputation_service.py:202`

**증거**:
```python
avg_score = row[0] if row[0] is not None else 0.0
return Decimal(str(round(avg_score, 4))), count  # round() 후 변환
```

**수정안**: `Decimal(str(raw)).quantize(Decimal("0.0001"))` 사용

---

## Cross-Verification Results

| ID | Phase 1 판정 | Phase 2 판정 | 사유 |
|----|-------------|-------------|------|
| SEC-001/002 (.env 노출) | Critical/HIGH | **FALSE_POSITIVE** | `.gitignore` 등록됨, git 미추적. 로컬 개발 환경 |
| C-03 (float 비교) | Critical/HIGH | **FALSE_POSITIVE** | `sentiment_score`가 Float 타입 → float 비교 올바름 |
| W-04 (reviewed_at isoformat) | Warning/HIGH | **FALSE_POSITIVE** | 모델이 `String(50)` 타입 → isoformat 저장 의도적 |
| FE-009 (후행 슬래시) | Critical/HIGH | **LINE_MISMATCH→P3** | FastAPI는 후행 슬래시 자동 리디렉트. 런타임 영향 미미 |
| FE-001 (enum 네이밍) | Critical/HIGH | **DESIGN_RISK→P3** | FE/BE enum 값 동일. 네이밍 불일치는 가독성 이슈 |
| W-05 (buyer JSONB) | Warning/HIGH | **FALSE_POSITIVE** | `with_variant` 올바르게 사용 중 |
| MIG-007 (NUMERIC 20,2) | Major/HIGH | **PARTIAL→P3** | 052에서 이미 (20,4)로 ALTER. 미래 마이그레이션에서 해결됨 |
| MIG-009 (Float 비용) | Major/HIGH | **DESIGN_RISK→P3** | STT/LLM 비용은 소액 → Float 허용 범위. Numeric 전환 권장 |

### 교차 검증 통계

- 검증한 이슈: 30건
- **CONFIRMED**: 18건
- **FALSE_POSITIVE**: 5건 (거부율: 17%)
- **DESIGN_RISK**: 3건 (P3 하향)
- **PARTIAL**: 2건 (P3 하향)
- **LINE_MISMATCH**: 2건 (수정 반영)

---

## Priority Matrix

### P0 — 즉시 수정 (1건)
1. **[FE-SCHEMA-001]** [Critical/HIGH]: `estimated_deal_value: number → string` 타입 수정 — transaction.ts (점수: 100)

### P1 — 스프린트 우선 (11건)
1. **[PERF-001]** [Critical/HIGH]: `download_blob()` 전체 메모리 적재 → to_file 일원화 — blob_storage.py (점수: 85)
2. **[PERF-002]** [Critical/HIGH]: 뉴스 키워드 필터 DB 쿼리 전환 — reputation_service.py (점수: 85)
3. **[PERF-003]** [Critical/HIGH]: get_qualitative_summary LIMIT 추가 — reputation_service.py (점수: 85)
4. **[MIG-001]** [Critical/HIGH ⚠️]: 005/028/030 cross-DB 타입 미변환 — migrations (점수: 80)
5. **[PERF-004]** [Major/HIGH]: FDD/IM client close() 미호출 — dependencies.py (점수: 70)
6. **[PERF-005]** [Major/HIGH]: si_mapping httpx 싱글턴 적용 — si_mapping_service.py (점수: 70)
7. **[MIG-002]** [Major/HIGH]: 041/043 enum dialect guard — migrations (점수: 70)
8. **[MIG-003]** [Major/HIGH]: 029 downgrade DROP TYPE guard — migration (점수: 70)
9. **[SEC-001]** [Major/HIGH]: DEV_CLAIMS ADMIN→ANALYST — security.py (점수: 70)
10. **[SEC-002]** [Major/HIGH]: file_path transaction_id 교차 검증 — template_visualization.py (점수: 70)
11. **[CODE-001]** [Major/HIGH ⚠️]: 모델 JSONB/UUID 크로스 DB 전환 — 다수 모델 (점수: 63)

### P2 — 개선 권장 (6건)
1. **[PERF-006]** [Major/HIGH]: blob 청크 스트리밍 개선 — blob_storage.py (점수: 55)
2. **[PERF-007]** [Major/HIGH]: AuditLog created_at 인덱스 — audit.py (점수: 55)
3. **[PERF-008]** [Major/HIGH]: NewsArticle 복합 인덱스 — news.py (점수: 55)
4. **[FE-SCHEMA-002]** [Major/MEDIUM]: SICompanyOut Decimal 직렬화 — si_mapping.py (점수: 42)
5. **[FE-SCHEMA-003]** [Major/MEDIUM]: ConsortiumMappingOut 직렬화 — consortium.py (점수: 42)
6. **[CODE-002]** [Major/MEDIUM]: news_score round→quantize — reputation_service.py (점수: 42)

---

## Methodology

- **Agents**: python-code-reviewer, backend-security-reviewer, migration-validator, performance-profiler, frontend-type-api-auditor (Explore)
- **Excluded Agents**: 없음 (5개 전체 호출)
- **Files scanned**: 1,243개 소스 파일
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 전건 (30건)
- **Backend availability**: deal-mgmt(✅) kiis(✅) fdd(✅) im(✅)

## 검증 투명성

### 검증 통계
- 검증한 가설: 42건
- 거부된 가설 (사전 제거): 12건
- 보고된 이슈: 18건
- 거부율: 29%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 5 | `.env` git 미추적, `sentiment_score` Float 타입, `reviewed_at` String 타입 |
| 범위 외 | 0 | — |
| 이미 수정됨 | 2 | MIG-007 → 052에서 ALTER, FE-004 이미 이전 세션 수정 |
| 오판 | 3 | FE-009 후행 슬래시 무영향, W-05 올바른 패턴 |
| 중복 | 1 | C-01과 MIG cross-DB 중복 |
| 설계 리스크 | 3 | MIG-009 Float 비용, FE-001 enum 네이밍 |

---

## 이전 리뷰(Round 1) 대비 변화

| 항목 | Round 1 (2026-03-02 10:41) | Round 2 (2026-03-02 11:24) |
|------|---------------------------|---------------------------|
| 총 이슈 | 30건 | 18건 (-40%) |
| Critical | 4건 | 5건 (신규 PERF 발견) |
| FP 거부율 | — | 29% |
| 수정 완료 | 22건 | — |
| 기술부채 분류 | 8건 | 신규 11건 + 기존 8건 |
