# Deep Dive — 고위험 파일 심층 분석

> **Review Date**: 2026-03-01 00:52
> **Reviewer**: Claude Code (Strategy 3: Focused Deep Dive)
> **Scope**: R1~R6에서 반복 지적된 3개 파일 + 전수 접근 제어 감사
> **Method**: 호출 체인 추적 + 데이터 흐름 분석 + 실패 시나리오 + 크로스 파일 상호작용
> **Round**: R1→R3→R4→R5→R6→R2 이후 심층 분석

---

## 대상 파일 선정 (라운드별 이슈 누적 기준)

| 파일 | 누적 이슈 | 라운드 |
|------|----------|--------|
| `consortium.py` | 3건 (E-02, M-003, W-001) | R2, R3, R6 |
| `buyer_marketing.py` | 3건 (C-001, SEC-002, SEC-I02) | R2, R4, R6 |
| `security.py` | 3건 (SEC-E01, SEC-003, SEC-S01) | R2 |

---

## 1. consortium.py 심층 분석

### 1.1 호출 체인 (create_consortium_mapping)

```
FE: useCreateConsortiumMapping
  → POST /api/v1/transactions/{txn_id}/consortium/
    → Depends(get_db), Depends(require_write_access())  ← RBAC만, deal 접근 미검증
      → body 자기 참조 검증 (lead == co)
        → _validate_buyer_in_txn(lead)  → SELECT buyer_candidates
        → _validate_buyer_in_txn(co)    → SELECT buyer_candidates
          → SOLE_BUYER 가드 (deal_role 확인)
            → 중복 검증 SELECT consortium_mappings
              → ConsortiumMapping 생성 → db.flush()
                → try/except IntegrityError (UniqueConstraint 폴백)
                  → audit_service.record(mode="json") ← Decimal/UUID 안전
                    → db.commit() → db.refresh()
                      → _build_out(mapping, lead_name, co_name)
```

### 1.2 발견 사항

**[기존] E-02 재확인**: `check_client_deal_access` 누락. 동일 파일의 다른 4개 엔드포인트(list, update, delete, summary)는 모두 호출.

**[안전 확인] 동시성**: duplicate SELECT(step 5)와 flush(step 7) 사이 race condition → UniqueConstraint + IntegrityError catch로 정상 처리. 두 번째 요청은 409 반환.

**[안전 확인] SOLE_BUYER 가드 순서**: buyer 존재 확인 → deal_role 확인 순서 정확. `deal_role is None`일 때 `== DealRole.SOLE_BUYER` → False (정상).

**[안전 확인] state transition**: `_VALID_TRANSITIONS` dict로 명시적 FSM. DROPPED는 terminal (빈 set).

**[안전 확인] update PATCH**: `model_dump(exclude_unset=True)` + schema 필드 3개만 (status, equity_share_pct, notes) → Mass Assignment 안전.

### 1.3 트랜잭션 미검증 (Minor)

`create_consortium_mapping`은 `transaction_service.get_transaction(db, txn_id)`를 호출하지 않음. `_validate_buyer_in_txn`이 간접적으로 txn 존재를 검증하나, 에러 메시지가 "매수자를 찾을 수 없습니다"로 혼동 가능. 실질적 영향 없음.

---

## 2. buyer_marketing.py 심층 분석

### 2.1 호출 체인 (export_buyers_excel)

```
FE: export-excel 버튼
  → GET /api/v1/transactions/{txn_id}/buyers/export-excel
    → Depends(get_db), Depends(get_jwt_claims)  ← READ 레벨
      → check_client_deal_access(db, txn_id, claims)  ← CLIENT 딜 접근 검증
        → transaction_service.get_transaction(db, txn_id)  → txn 조회
          → SELECT buyer_candidates WHERE txn_id  → 전체 매수자 (필터 없음)
            → Marketing logs GROUP BY (buyer_id, stage)  → 최신 활동
              → Consortium mappings aliased join  → buyer별 관계
                → build_buyer_excel(buyers, marketing_latest, consortium_map)
                  → BytesIO → StreamingResponse
                    → Content-Disposition: filename="{txn.code_name}.xlsx"
```

### 2.2 발견 사항

**[기존] SEC-002 재확인**: `txn.code_name or txn.name` 미새니타이징. `txn.name`도 사용자 입력이므로 양쪽 모두 취약.

**[기존] SEC-I02 재확인**: READ 권한이면 CLIENT도 전체 Long-List Excel 다운로드 가능. `contact_email`, `contact_phone` 포함.

**[안전 확인] 마케팅 로그 CRUD**: 4개 엔드포인트 모두 `check_client_deal_access` + `require_write_access` 완비.

**[안전 확인] audit record**: `create_marketing_log`에서 `model_dump()` 사용. MarketingLogCreate 필드가 모두 str/StrEnum이므로 JSON 안전.

**[안전 확인] _get_buyer 헬퍼**: buyer_id + txn_id 복합 WHERE로 cross-txn 참조 방지.

### 2.3 DART 예외 처리 (Minor)

`dart_company_search` (line 291-296): `except Exception: return []` — 모든 예외를 삼키고 빈 배열 반환. 사용자는 검색 실패인지 결과 없음인지 구별 불가. `exc_info=True` 서버 로그는 남기지만 클라이언트 피드백 부재.

---

## 3. security.py 심층 분석

### 3.1 인가 아키텍처

```
                 ┌─────────────────────────────────┐
                 │ get_jwt_claims (Authentication)  │
                 │  JWT decode from header/cookie   │
                 │  → JWTClaims(user_id, email, role)│
                 └──────────────┬──────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
  require_write_access    get_jwt_claims          check_client_deal_access
  (Blocklist: CLIENT 차단) (인증만)              (CLIENT → DealClient 검증)
  (다른 역할 모두 통과)    (인가 없음)            (non-CLIENT → 즉시 통과)
        │                       │                       │
   WRITE endpoints         READ endpoints          딜 스코프 제한
```

### 3.2 발견 사항

**[NEW] DD-01: Blocklist 접근 제어 패턴**

`require_write_access()`는 CLIENT만 차단하고 다른 모든 역할을 통과시키는 blocklist 패턴.

```python
# security.py:106-112
async def checker(claims: JWTClaims = Depends(get_jwt_claims)) -> JWTClaims:
    if claims.role == _CLIENT_ROLE:
        raise HTTPException(...)
    return claims
```

- 현재 역할: ADMIN, MEMBER, CLIENT → ADMIN/MEMBER는 모든 쓰기 가능
- 리스크: 향후 VIEWER, ANALYST 등 읽기 전용 역할 추가 시 자동으로 쓰기 권한 획득
- 권장: allowlist 패턴 (`if claims.role not in ("ADMIN", "MEMBER"): raise`)

**[NEW] DD-02: check_client_deal_access의 비대칭 설계**

```python
# security.py:126-127
if claims.role != _CLIENT_ROLE:
    return  # non-CLIENT는 모든 딜에 접근 가능
```

- 의도: AMIC 내부 사용자(ADMIN/MEMBER)는 모든 딜에 접근
- 현실: Chinese Wall 없음 → 딜 팀이 아닌 내부 사용자도 민감 딜 접근 가능
- 성격: 설계 결정 (DESIGN_RISK). 현재 소규모 팀에서는 허용 가능

**[안전 확인] AUTH_ENABLED 프로덕션 가드**:

```python
# security.py:52-54
_env = os.getenv("ENV", "").lower()  # lowercase 변환 ✓
if _env in ("production", "prod", "staging", "stg"):
    raise RuntimeError("CRITICAL: AUTH_ENABLED=False is forbidden in production/staging")
```

정확한 가드. 대소문자 무관하게 프로덕션에서 인증 비활성화 차단.

**[안전 확인] JWT secret**: `config.py` startup validation에서 production/staging 시 JWT_SECRET 미설정 → RuntimeError. 빈 secret으로 서버 시작 불가.

---

## 4. 크로스 파일 상호작용 분석

### 4.1 [NEW] DD-03: CASCADE 삭제 감사 추적 누락 (Moderate/HIGH)

**데이터 흐름**:
```
buyers.py:remove_buyer()
  → audit_service.record(entity_type="BuyerCandidate", action=DELETE)
  → db.delete(buyer)
  → db.commit()
    → CASCADE: consortium_mappings (lead_buyer_id OR co_investor_buyer_id FK)
    → CASCADE: buyer_marketing_logs (buyer_id FK)
    → 감사 기록 없음 ✗
```

- **문제**: buyer 삭제 시 관련 ConsortiumMapping과 BuyerMarketingLog가 DB CASCADE로 삭제되지만, 개별 감사 기록이 남지 않음
- **영향**: 포렌식 감사에서 "buyer A가 삭제됨"은 확인 가능하나, "buyer A의 컨소시엄 관계 3건, 마케팅 로그 15건이 함께 삭제됨"은 추적 불가
- **수정 방향**: 삭제 전 관련 레코드를 조회하여 audit notes에 요약 기록

### 4.2 [NEW] DD-04: 시스템 전체 접근 제어 감사 결과 (Critical → 체계적 문제)

전수 조사(41개 라우터, 총 엔드포인트 ~200+) 결과:

| 카테고리 | 엔드포인트 수 | 위험도 |
|---------|-------------|--------|
| **NO_RBAC** (WRITE인데 require_write_access 없음) | **7개** | Critical |
| **MISSING** (READ에 deal_access 없음) | **18개** | High |
| **MISSING** (WRITE에 deal_access 없음, RBAC는 있음) | **83개** | Medium |
| **OK** (완전 보호) | 나머지 | — |

**Critical — 즉시 수정 필요 (7개)**:

| 파일 | 엔드포인트 | 문제 |
|------|----------|------|
| `financial_models.py` | POST, DELETE, PUT (6개) | require_write_access도 check_client_deal_access도 없음 |
| `template_visualization.py` | POST (1개) | require_write_access도 check_client_deal_access도 없음 |

CLIENT 역할이 아무 딜의 재무 모델을 생성/삭제/수정 가능.

**High — READ에서 CLIENT 딜 접근 미검증 (18개)**:

| 파일 | 주요 엔드포인트 |
|------|---------------|
| `financial_models.py` | GET /models, GET /models/{id}, GET /download, GET /checklist (4개) |
| `template_visualization.py` | GET /download (1개) |
| `dashboard.py` | GET /docs-stats (1개) |
| `meeting_logs.py` | GET /action-items (1개) |
| `ralph.py`, `integrations.py` | 수동 CLIENT 체크 사용 (deal-level 미적용, 7개) |
| `ldd_reports.py` | 전역 목록 (1개) |
| `audit.py` | 전역 감사 로그 (2개, deal 무관으로 의도적일 수 있음) |

**Medium — WRITE에서 deal_access 미검증 (83개)**:

`require_write_access()`가 CLIENT를 차단하므로 CLIENT는 도달 불가. non-CLIENT 간 딜 격리가 필요한 경우에만 이슈.

주요 라우터: transactions, bids, dd_checklists, earnout, engagements, ndas, pmi, workflow, approvals, notes, risks, meeting_logs, permits, closing, compliance, timeline, negotiation_issues, contracts, rfi, ralph, attachments

### 4.3 완전 보호된 라우터 (패턴 참조 기준)

| 파일 | 패턴 |
|------|------|
| `buyers.py` | WRITE + deal_access 모든 엔드포인트 ✓ |
| `buyer_marketing.py` | WRITE + deal_access 모든 엔드포인트 ✓ |
| `document_extraction.py` | WRITE + deal_access 모든 엔드포인트 ✓ |
| `vdr.py`, `legal_documents.py`, `marketing_materials.py` | `_get_and_authorize_txn()` 헬퍼 패턴 ✓ |

---

## 5. 신규 발견 사항 요약

| ID | 심각도 | 신뢰도 | 제목 | 파일 |
|----|--------|--------|------|------|
| DD-04 | **Critical** | HIGH | financial_models.py 7개 WRITE 엔드포인트 RBAC 없음 | financial_models.py |
| DD-03 | Moderate | HIGH | CASCADE 삭제 시 하위 레코드 감사 추적 누락 | buyers.py → consortium/marketing |
| DD-01 | Minor | HIGH | require_write_access blocklist 패턴 (확장 시 위험) | security.py |
| DD-02 | Minor | MEDIUM | DART search q 파라미터 max_length 없음 | buyer_marketing.py |

---

## 6. 기존 이슈 재확인

| ID | 상태 | 비고 |
|----|------|------|
| E-02 | ✓ 재확인 | consortium.py:104 — check_client_deal_access 누락 |
| SEC-002 | ✓ 재확인 | buyer_marketing.py:397 — txn.name도 동일 취약점 |
| SEC-E01 | ✓ 재확인 | security.py:126 — 비대칭 설계, 의도적 |
| SEC-003 | ✓ 재확인 | security.py:68 — python-jose 기본값 True로 안전 |

---

## 7. 안전 확인 (취약점 없음)

| 검사 항목 | 결과 | 근거 |
|----------|------|------|
| Race condition (consortium 생성) | ✓ 안전 | UniqueConstraint + IntegrityError catch |
| Mass Assignment (update PATCH) | ✓ 안전 | model_dump(exclude_unset=True) + 제한된 스키마 |
| Audit JSON serialization | ✓ 안전 | _sanitize_for_json: Decimal→float, UUID→str |
| AUTH_ENABLED 프로덕션 가드 | ✓ 안전 | lowercase 비교, prod/staging/stg 모두 차단 |
| JWT secret startup validation | ✓ 안전 | production에서 빈 secret → RuntimeError |
| Buyer cross-txn 참조 | ✓ 안전 | _get_buyer/_validate_buyer_in_txn에서 txn_id 복합 WHERE |
| SOLE_BUYER 가드 | ✓ 안전 | deal_role=None → False (정상 통과) |
| 상태 전이 | ✓ 안전 | 명시적 FSM, DROPPED terminal |

---

## 8. 수정 우선순위

### 즉시 (1~3줄 수정)
1. **DD-04/financial_models.py**: 6개 WRITE 엔드포인트에 `require_write_access()` 추가
2. **E-02/consortium.py**: POST에 `check_client_deal_access` 추가

### 단기
3. **SEC-002**: Content-Disposition filename 새니타이징
4. **DD-04/READ 18개**: `check_client_deal_access` 추가 (financial_models, dashboard, meeting_logs)
5. **DD-03**: buyer 삭제 전 CASCADE 대상 수 audit notes에 기록

### 중기 (설계 검토)
6. **DD-01**: blocklist → allowlist 전환 검토
7. **SEC-E01**: Chinese Wall / 딜 팀 기반 접근 제어 설계
8. **DD-04/WRITE 83개**: deal_access 일괄 적용 여부 결정
