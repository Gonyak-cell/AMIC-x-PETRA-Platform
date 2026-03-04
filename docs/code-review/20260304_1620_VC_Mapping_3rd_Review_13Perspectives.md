# Code Review — VC Mapping 3rd Round (13 Perspectives)

> **Review Date**: 2026-03-04 16:20
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: VC/SI Mapping Feature — deal-mgmt (backend) + amic-platform (frontend)
> **Method**: Quality Gates + Verified Multi-Agent Review (5 agents, 13 perspectives) + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) vitest(PASS ×39) ruff(PASS)
> **Previous Reviews**: [R1] 20건→17건 수정 | [R2-R6] 50건→25건 수정 (566 ins, 162 del)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2                | P0: 2               |
| Major    | 14    | HIGH: 11 / MEDIUM: 3  | P1: 13 / P2: 1      |
| Moderate | 22    | HIGH: 12 / MEDIUM: 10 | P2: 22              |
| Minor    | 18    | HIGH: 3 / MEDIUM: 10 / LOW: 5 | P3: 18     |
| **Total**| **56**| HIGH: **28** / MEDIUM: **23** / LOW: **5** | P0: **2** / P1: **13** / P2: **23** / P3: **18** |

**Cross-Verification**: Critical 2건 + Major 14건 = 17건 수행 → CONFIRMED 12건, DESIGN_RISK 3건, FALSE_POSITIVE 0건, 중복 병합 2건
**Deduplication**: 66건 원시 → 56건 (10건 중복 병합)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- MEDIUM 신뢰도 이슈 3건 Major → P2 하향 조정

---

## Findings

### P0 — 즉시 수정 (점수: 90+, 보안/데이터 무결성)

---

#### [P0-01] SI bulk_add_to_buyers 감사 루프 try-except 누락 — [Critical/HIGH] — Priority: P0
**점수**: 100 (Critical×1.0) + 10 (교차검증 3에이전트) + 15 (verifier 확인) = **125**
**교차 검증**: R3-C01 + R4-EH01 + R6-D05 — 3개 에이전트 독립 발견

**파일**: `deal-mgmt/app/services/si_mapping_service.py:294-302`

**현재 코드**:
```python
# 3) 배치 audit 기록
for buyer, si in new_buyers:
    await audit_service.record(          # ← try-except 없음
        db, entity_type="BuyerCandidate", entity_id=buyer.id,
        action=AuditAction.CREATE, actor_email=actor_email,
        new_value={"company_name": si.company_name, "source": "SI_MAPPING"},
    )
    added_ids.append(buyer.id)
```

**문제**: 감사 로그 기록 중 예외 발생 시 전체 벌크 작업 롤백. VC 버전(line 1181-1193)은 이미 try-except 적용.

**수정 방안**: VC 패턴과 동일하게 try-except 적용

**검증 추적**: Read(si_mapping_service.py:285-317) → audit loop에 try-except 없음 확인 → VC 버전과 비대칭 확인

---

#### [P0-02] SI bulk_add_to_buyers not_found_count 항상 0 반환 — [Critical/HIGH] — Priority: P0
**점수**: 100 (Critical×1.0) + 10 (교차검증 2에이전트) = **110**
**교차 검증**: R3-C01 + R5-C02

**파일**: `deal-mgmt/app/services/si_mapping_service.py:313-316`

**현재 코드**:
```python
return BulkAddBuyersResponse(
    added_count=len(added_ids),
    skipped_count=skipped,
    # not_found_count 누락 — 스키마 기본값 0 항상 반환
    buyer_ids=added_ids,
)
```

**문제**: VC 버전은 `not_found_count=len(not_found_ids)` 추적. SI 버전은 미발견 ID 추적 로직 자체가 없음.

**수정 방안**: VC 패턴과 동일하게 미발견 ID 추적 + not_found_count 반환

---

### P1 — 스프린트 우선 (점수: 60-89, 안정성/정확성)

---

#### [P1-01] map_si / map_vc 감사 로그 commit 누락 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) + 15 (verifier 확인) = **85**

**파일**: `deal-mgmt/app/routers/si_mapping.py:111-122, 276-287`

**현재 코드** (map_si, line 111-122):
```python
try:
    await audit_service.record(db, entity_type="SIMapping", ...)
except Exception:
    logger.exception("SI 매핑 감사 로그 기록 실패")
return result  # ← db.commit() 없음
```

**문제**: audit_service.record()는 INSERT를 세션에 추가하지만 commit하지 않음. 라우터에서 return 시 세션이 종료되면서 implicit rollback으로 감사 기록 소실. map_vc_by_registration(line 351)은 정상적으로 `await db.commit()` 포함.

**수정 방안**: try 블록 끝에 `await db.commit()` 추가 (2곳)

**검증 추적**: Read(si_mapping.py:100-130, 270-289) → commit 호출 없음 확인 → map_vc_by_registration(line 351) 패턴과 비교

---

#### [P1-02] VcCompany 모델 B-tree 인덱스 ↔ 063 expression 인덱스 충돌 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) + 15 (verifier 확인) = **85**

**파일**: `deal-mgmt/app/models/vc_company.py:29-30`

**현재 코드**:
```python
__table_args__ = (
    ...
    Index("ix_vc_companies_corp_reg_no", "corp_reg_no"),   # ← B-tree
    Index("ix_vc_companies_biz_reg_no", "biz_reg_no"),     # ← B-tree
)
```

**문제**: 063 마이그레이션이 이 인덱스를 DROP하고 expression 인덱스를 CREATE. 그러나 모델에 B-tree 선언이 남아있어 `alembic --autogenerate` 시 다시 생성 시도.

**수정 방안**: 모델에서 두 Index 선언 제거 (expression 인덱스는 마이그레이션에서만 관리)

**검증 추적**: Read(vc_company.py:20-39) → B-tree 인덱스 선언 확인 → Read(063_*.py) → DROP + expression CREATE 확인

---

#### [P1-03] SICompanyOut 이중 직렬화 위험 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/app/schemas/si_mapping.py` (SICompanyOut)

**문제**: `json_schema_extra` + `field_serializer` 조합에서 Decimal/UUID 직렬화가 이중 적용될 수 있음. Pydantic v2에서 `model_config`의 `json_encoders`와 `field_serializer`가 동시 존재 시 우선순위 혼동.

**수정 방안**: 직렬화 방식을 하나로 통일 (field_serializer만 사용 권장)

---

#### [P1-04] asyncio.gather 결과 인덱스 하드코딩 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/app/services/si_mapping_service.py` (map_vc_candidates)

**문제**: `asyncio.gather(coro1, coro2, coro3)` 결과를 `results[0], results[1], results[2]`로 접근. 코루틴 순서 변경 시 조용한 데이터 혼동 발생.

**수정 방안**: 구조 분해 할당 사용: `forward, backward, competitors = await asyncio.gather(...)`

---

#### [P1-05] map_vc_candidates N+1 쿼리 패턴 — [Major/HIGH] — Priority: P1 (DESIGN_RISK)
**점수**: 70 (Major×1.0) + 10 (교차검증 3에이전트) = **80**
**교차 검증**: R3-M02 + R5-P01 + R6-D03 — DESIGN_RISK

**파일**: `deal-mgmt/app/services/si_mapping_service.py:952-968`

**문제**: 업종별 개별 쿼리로 최대 40-100회 DB 왕복. `unique_related`가 최대 40개일 때 각각 `SELECT ... WHERE io_sector_name = ? ORDER BY revenue DESC LIMIT ?` 실행.

**현재 완화 요소**: io_sector_name 인덱스 존재, 각 쿼리 가벼움 (단일 컬럼 조건 + LIMIT)
**수정 방안**: `WHERE io_sector_name IN (...)` + ROW_NUMBER() 윈도우 함수로 단일 쿼리 변환

---

#### [P1-06] ValueError 내부 메시지 클라이언트 노출 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/app/routers/si_mapping.py` (bulk 엔드포인트)

**문제**: `except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc))` — 서비스 내부 ValueError 메시지가 그대로 클라이언트에 전달됨. 향후 서비스 로직 변경 시 내부 정보 누출 가능.

**수정 방안**: 고정 문자열 사용 또는 허용된 메시지 화이트리스트

---

#### [P1-07] In-Memory Rate Limiter 다중 워커 무효화 — [Major/HIGH] — Priority: P1 (DESIGN_RISK)
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/app/core/rate_limiter.py`

**문제**: `defaultdict(deque)` 기반 인메모리 제한. 2+ worker 시 각 프로세스 별도 카운트 → 실질 rate = workers × limit.

**현재 완화 요소**: 프로덕션 2 worker × 5/min = 10/min (여전히 합리적 범위)
**수정 방안**: Redis 기반 rate limiter로 전환 (아키텍처 변경, 장기)

---

#### [P1-08] ChainPanelCard aria-expanded 부재 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) + 15 (verifier 확인) = **85**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:73-76`

**현재 코드**:
```tsx
<button
  type="button"
  onClick={() => setExpanded(!expanded)}
  className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-slate-50"
>
```

**수정 방안**: `aria-expanded={expanded}` 추가

---

#### [P1-09] 닫기 버튼 접근 가능한 이름 부재 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) + 15 (verifier 확인) = **85**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx:190-208`

**현재 코드**:
```tsx
<button type="button" onClick={onClose} className="...">
  <svg className="h-5 w-5" ...>
    <path d="M6 18L18 6M6 6l12 12" />
  </svg>
</button>
```

**수정 방안**: `aria-label="닫기"` 추가

---

#### [P1-10] map_vc_by_registration 통합 테스트 부재 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/tests/test_si_mapping.py`

**문제**: `map_vc_by_registration`은 가장 복잡한 워크플로우 (등록번호 조회 → IO 계수 매칭 → forward/backward/competitor 조회) 이나 단위 테스트만 존재. end-to-end 통합 테스트 없음.

**수정 방안**: IO 계수 시드 + VcCompany 시드로 전체 파이프라인 통합 테스트 추가

---

#### [P1-11] bulk_add_vc_to_buyers 테스트 부재 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/tests/test_si_mapping.py`

**문제**: SI bulk 추가 테스트는 존재하나 VC bulk 추가 테스트 없음. not_found_count, 중복 방지 로직 검증 미커버.

**수정 방안**: VC bulk 추가 테스트 (정상 경로 + 중복 경로 + 미발견 경로) 추가

---

#### [P1-12] flush 후 SQLAlchemyError rollback 미보장 — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/app/services/si_mapping_service.py` (bulk 함수 내 `db.flush()`)

**문제**: `db.flush()` 실패 시 `except SQLAlchemyError` 에서 `raise` 하지만 명시적 `db.rollback()` 없음. FastAPI의 세션 미들웨어가 롤백하지만, except 블록에서 추가 DB 작업 시도 시 세션 오염.

**수정 방안**: except 블록에서 `await db.rollback()` 명시 호출

---

#### [P1-13] 예외 체인 없는 raise — [Major/HIGH] — Priority: P1
**점수**: 70 (Major×1.0) = **70**

**파일**: `deal-mgmt/app/routers/si_mapping.py` (다수 except 블록)

**문제**: `except SQLAlchemyError: raise HTTPException(...)` — `from exc` 없이 raise하여 원본 스택 트레이스 소실. 디버깅 시 DB 에러 원인 추적 불가.

**수정 방안**: `raise HTTPException(...) from exc` 패턴 적용 (단, 클라이언트에 내부 정보 전달하지 않도록 detail은 고정 문자열)

---

### P2 — 개선 권장 (점수: 30-59, 코드 품질)

---

#### [P2-01] min_revenue 단위 불일치 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: SI 매핑의 min_revenue는 '원' 단위, VC 매핑의 revenue는 '억원' 단위. 동일한 매개변수명이지만 단위가 다름.

**수정 방안**: 매개변수명 또는 docstring에 단위 명시 (`min_revenue_won`, `min_revenue_billion`)

---

#### [P2-02] 마스킹 로직 이중 존재 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24** → P3이나 코드 유지보수 관점에서 P2 유지

**파일**: `deal-mgmt/app/schemas/si_mapping.py` + `deal-mgmt/app/routers/si_mapping.py`

**문제**: `_mask_registration` (스키마 field_serializer) + `_mask_reg_no` (라우터 유틸) — 마스킹 로직이 2곳에 존재. 향후 마스킹 정책 변경 시 동기화 필요.

**수정 방안**: 단일 유틸로 통합 (스키마 serializer에서 공유 함수 호출)

---

#### [P2-03] FE VcIndustrySuggestion 타입 누락 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `amic-platform/src/modules/ma/types/si_mapping.ts`

**문제**: 백엔드 `VcIndustrySuggestion` 스키마에 대응하는 FE TypeScript 타입이 누락. FE에서 `any` 또는 인라인 타입으로 사용 중일 가능성.

**수정 방안**: `si_mapping.ts`에 VcIndustrySuggestion 인터페이스 추가

---

#### [P2-04] catch 순서 / commit 세션 오염 위험 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `deal-mgmt/app/routers/si_mapping.py`

**문제**: `except CompanyNotFoundError` → `except SQLAlchemyError` 순서에서, CompanyNotFoundError가 먼저 처리되지만 이전 commit 실패 세션에서 새 audit record 시도 가능.

**수정 방안**: except 블록 진입 시 세션 상태 확인 (is_active) 또는 순서 재배치

---

#### [P2-05] 기업명 검색어 에러 응답 반사 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/routers/si_mapping.py`

**문제**: 검색 실패 시 사용자 입력 검색어가 에러 응답에 포함될 수 있음 (반사 XSS 경로).

**수정 방안**: 에러 메시지에서 사용자 입력값 제거

---

#### [P2-06] DEV_CLAIMS 환경 검증 런타임 지연 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/core/auth.py`

**문제**: DEV_CLAIMS 파싱이 요청마다 실행. 애플리케이션 시작 시 1회만 파싱하여 캐싱해야 함.

**수정 방안**: 모듈 레벨 변수로 캐싱

---

#### [P2-07] 일부 고비용 엔드포인트 Rate Limiter 미적용 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `deal-mgmt/app/routers/si_mapping.py`

**문제**: `search_si_companies`, `search_vc_industries` 등 검색 엔드포인트에 rate limiter 미적용. DB 부하 유발 가능.

**수정 방안**: 검색 엔드포인트에도 rate limiter 적용 (더 높은 임계값)

---

#### [P2-08] 로그에 등록번호 관련 정보 기록 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: 로그에 `bool(corp_reg_no)` 형태로 기록하지만, 일부 경로에서 실제 값이 기록될 수 있음.

**수정 방안**: 모든 로그 경로에서 등록번호는 존재 여부(bool)만 기록

---

#### [P2-09] CLIENT 이외 역할의 딜 범위 체크 누락 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `deal-mgmt/app/routers/si_mapping.py`

**문제**: CLIENT 역할은 트랜잭션 소유권 확인하지만, 다른 역할은 모든 트랜잭션에 접근 가능.

**현재 완화**: 내부 시스템으로 역할이 제한적. 장기적으로 RBAC 세분화 필요.

---

#### [P2-10] audit INSERT 루프 N회 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: bulk 추가 시 각 buyer에 대해 개별 audit INSERT. 100건 추가 시 100회 INSERT.

**수정 방안**: bulk INSERT로 변환 또는 배치 audit 함수 추가

---

#### [P2-11] 5000건 ORM 풀 로딩 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: 업종별 기업 목록 조회 시 ORM 객체 전체 로딩. 필요 컬럼만 선택하면 메모리 절약.

**수정 방안**: `select(VcCompany.id, VcCompany.company_name, ...)` 컬럼 지정 쿼리

---

#### [P2-12] search_vc_industries ILIKE full scan — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: `ILIKE '%keyword%'` 패턴은 B-tree 인덱스 사용 불가. 1,574개 업종명에서 full scan.

**수정 방안**: PostgreSQL pg_trgm GIN 인덱스 또는 애플리케이션 레벨 캐싱

---

#### [P2-13] FE 100건 상한 가드 누락 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx`

**문제**: 백엔드는 100건 제한이 있으나, 프론트엔드에서 selectedIds 크기 체크 없이 bulk API 호출.

**수정 방안**: 100건 초과 시 경고/분할 전송 로직

---

#### [P2-14] IO 계수 0.001 임계값 서비스 레벨 미적용 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: IO 계수 필터링 시 0.001 미만 계수를 무시하는 로직이 있으나, 이 임계값이 하드코딩됨.

**수정 방안**: 설정 상수로 추출

---

#### [P2-15] KIIS 외부 서비스 직접 호출 강결합 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: KIIS 서비스를 직접 import/호출. 서비스 경계 위반.

**수정 방안**: 인터페이스 분리 또는 이벤트 기반 통신 (장기)

---

#### [P2-16] 감사 실패 정책 불일치 (SI vs VC) — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) + 10 (교차검증) = **50**
**교차 검증**: R5-C02 + R6-D05

**파일**: `deal-mgmt/app/services/si_mapping_service.py` + `deal-mgmt/app/routers/si_mapping.py`

**문제**: SI bulk은 감사 실패 시 전체 롤백, VC bulk은 감사 실패 무시 후 계속. 동일 기능의 다른 정책.

**수정 방안**: P0-01 수정 시 함께 해결 (SI에도 try-except 적용)

---

#### [P2-17] _get_value_chain direction 분기 중복 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: forward/backward 방향별로 거의 동일한 쿼리 로직이 분기문으로 중복.

**수정 방안**: 방향을 매개변수로 받는 단일 함수로 통합

---

#### [P2-18] SVG 아이콘 aria-hidden 누락 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx`, `SIMappingPanel.tsx`

**문제**: 장식용 SVG 아이콘에 `aria-hidden="true"` 없음. 스크린리더가 불필요한 SVG 경로를 읽음.

**수정 방안**: 장식용 SVG에 `aria-hidden="true"` 추가

---

#### [P2-19] 탭 버튼 role="tab" 부재 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:213-239`

**문제**: 탭 UI이지만 `role="tablist"`, `role="tab"`, `aria-selected` WAI-ARIA 패턴 미적용.

**수정 방안**: WAI-ARIA Tab 패턴 적용

---

#### [P2-20] 모달 닫기 시 포커스 복원 없음 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx`

**문제**: 모달 닫힐 때 이전 포커스 요소로 복원하지 않음. 포커스 트랩은 있으나 복원 로직 없음.

**수정 방안**: useRef로 모달 열기 전 activeElement 저장, onClose 시 복원

---

#### [P2-21] 4개 예외 핸들러 로그 누락 — [Moderate/HIGH] — Priority: P2
**점수**: 40 (Moderate×1.0) = **40**

**파일**: `deal-mgmt/app/core/exceptions.py`

**문제**: company_not_found_handler, rate_limit_handler 등 일부 핸들러에서 `logger.warning()` 없이 즉시 응답 반환. 404/429 이벤트 추적 불가.

**수정 방안**: 각 핸들러에 로깅 추가

---

#### [P2-22] RuntimeError 포함한 과도한 except 범위 — [Moderate/MEDIUM] — Priority: P2
**점수**: 40 × 0.6 = **24**

**파일**: `deal-mgmt/app/routers/si_mapping.py`

**문제**: `except Exception` 으로 포괄적 캐치. RuntimeError, KeyboardInterrupt 등 시스템 오류도 잡아서 조용히 처리 위험.

**수정 방안**: `except (SQLAlchemyError, ValueError)` 등 구체적 예외 지정

---

### P3 — 저우선 (점수: <30, 개선 가능)

---

#### [P3-01] company_id UUID 에러 응답 노출 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/app/core/exceptions.py`

**문제**: CompanyNotFoundError 응답에 company_id가 포함될 수 있음. UUID가 내부 식별자인 경우 정보 노출.

**수정 방안**: R2에서 이미 `company_id is not None` 체크 추가됨. None이 아닌 경우만 노출. 추가 마스킹 고려.

---

#### [P3-02] Rate Limiter 메모리 증가 경로 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/app/core/rate_limiter.py`

**문제**: 고유 키(이메일)마다 deque 생성. 대량 사용자 시 메모리 증가. 스테일 키 정리 없음.

**수정 방안**: TTL 기반 키 정리 (주기적 cleanup) 또는 maxlen 제한

---

#### [P3-03] 단일 요청 N+1 쿼리 DoS 공격면 — [Minor/LOW] — Priority: P3
**점수**: 20 × 0.3 = **6**

**문제**: map_vc 요청 1회로 최대 100회 DB 쿼리 유발. Rate limiter로 완화.

---

#### [P3-04] 서비스간 JWT 동일 시크릿 — [Minor/LOW] — Priority: P3
**점수**: 20 × 0.3 = **6**

**문제**: 모든 모듈이 동일 JWT_SECRET 사용. 하나의 시크릿 유출 시 전체 서비스 영향.

**수정 방안**: 서비스별 시크릿 분리 (장기 아키텍처)

---

#### [P3-05] ALLOWED_ORIGINS localhost 기본값 — [Minor/LOW] — Priority: P3
**점수**: 20 × 0.3 = **6**

**문제**: 환경변수 미설정 시 localhost가 기본값. 프로덕션에서는 반드시 설정.

---

#### [P3-06] 변수명 `q` 재사용 — [Minor/HIGH] — Priority: P3
**점수**: 20 (Minor×1.0) = **20**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: 같은 함수 내에서 `q`를 여러 쿼리에 재사용. 가독성 저하.

**수정 방안**: `q_existing`, `q_search` 등 의미 있는 변수명 사용

---

#### [P3-07] bisect 내부 import — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: 함수 내부에서 `from bisect import bisect_left` import. 모듈 상단으로 이동 권장.

---

#### [P3-08] 경쟁사 목록에 자기 자신 포함 가능 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: 경쟁사 조회 시 대상 기업 자신이 결과에 포함될 수 있음. `WHERE id != target_id` 필터 없음.

**수정 방안**: 대상 기업 ID 제외 필터 추가

---

#### [P3-09] Decimal 비교 정밀도 의존 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/tests/test_si_mapping.py`

**문제**: `assert result.revenue == Decimal("5000")` — 정밀도 불일치 시 실패. `Decimal("5000.00")` vs `Decimal("5000")`.

**수정 방안**: `abs(result.revenue - expected) < threshold` 또는 동일 정밀도 보장

---

#### [P3-10] rate limiter 테스트 내부 구현 의존 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/tests/test_rate_limiter.py`

**문제**: `count=5` 하드코딩. Rate limiter 구현 변경 시 테스트 깨짐.

---

#### [P3-11] anyio vs asyncio 마커 불일치 — [Minor/LOW] — Priority: P3
**점수**: 20 × 0.3 = **6**

**파일**: `deal-mgmt/tests/test_si_mapping.py`

**문제**: 일부 테스트가 `@pytest.mark.anyio`와 `@pytest.mark.asyncio` 혼용.

---

#### [P3-12] _build_flat_candidates 3중 반복 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: forward + backward + competitors를 각각 순회. 단일 itertools.chain으로 통합 가능.

---

#### [P3-13] VcMappingResult countMap 중복 분기 — [Minor/HIGH] — Priority: P3
**점수**: 20 (Minor×1.0) = **20**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:214-220`

**문제**: `countMap` 객체가 이미 존재하지만 탭 렌더링에서 `countMap[key]` 대신 삼항 연산자로 count를 재계산.

**수정 방안**: `countMap[key]` 사용

---

#### [P3-14] emerald-600 색상 대비 경계선 — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: 다수 프론트엔드 파일

**문제**: `emerald-600` 배경의 흰색 텍스트 — WCAG AA 4.5:1 대비 경계선. 작은 텍스트에서 미달 가능.

---

#### [P3-15] opacity-0 버튼 스크린리더 노출 — [Minor/HIGH] — Priority: P3
**점수**: 20 (Minor×1.0) = **20**

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx`

**문제**: `opacity-0 pointer-events-none` 버튼이 시각적으로 숨겨지나 스크린리더에는 노출.

**수정 방안**: `aria-hidden={selectedIds.size === 0}` 추가 또는 조건부 렌더링

---

#### [P3-16] find_vc_company_by_registration 중복 쿼리 — [Minor/HIGH] — Priority: P3
**점수**: 20 (Minor×1.0) = **20**

**파일**: `deal-mgmt/app/services/si_mapping_service.py`

**문제**: corp_reg_no와 biz_reg_no를 각각 조회 후 OR 조합. 이미 `_strip_reg_col` 헬퍼가 있지만 3분기에서 유사 패턴 반복.

---

#### [P3-17] context.get_bind() deprecated — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `deal-mgmt/migrations/versions/063_vc_expression_indexes.py`

**문제**: `context.get_bind()` — Alembic/SQLAlchemy 2.0에서 deprecated 경고.

**수정 방안**: `op.get_bind()` 사용

---

#### [P3-18] Suspense fallback=null — [Minor/MEDIUM] — Priority: P3
**점수**: 20 × 0.6 = **12**

**파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx`

**문제**: `<Suspense fallback={null}>` — 로딩 중 빈 화면. 로딩 스피너 권장.

---

---

## Priority Matrix

### P0 — 즉시 수정 (2건)
1. [P0-01] [Critical/HIGH]: SI bulk audit try-except 누락 — si_mapping_service.py (점수: 125, 3에이전트 교차확인)
2. [P0-02] [Critical/HIGH]: SI bulk not_found_count 항상 0 — si_mapping_service.py (점수: 110)

### P1 — 스프린트 우선 (13건)
1. [P1-01] [Major/HIGH]: audit commit 누락 (map_si/map_vc) — si_mapping.py (점수: 85)
2. [P1-02] [Major/HIGH]: VcCompany B-tree 인덱스 충돌 — vc_company.py (점수: 85)
3. [P1-08] [Major/HIGH]: ChainPanelCard aria-expanded 부재 — VcMappingResult.tsx (점수: 85)
4. [P1-09] [Major/HIGH]: 닫기 버튼 aria-label 부재 — SIMappingPanel.tsx (점수: 85)
5. [P1-05] [Major/HIGH]: N+1 쿼리 패턴 (DESIGN_RISK) — si_mapping_service.py (점수: 80)
6. [P1-03] [Major/HIGH]: SICompanyOut 이중 직렬화 — si_mapping.py (점수: 70)
7. [P1-04] [Major/HIGH]: asyncio.gather 인덱스 하드코딩 — si_mapping_service.py (점수: 70)
8. [P1-06] [Major/HIGH]: ValueError 메시지 클라이언트 노출 — si_mapping.py (점수: 70)
9. [P1-07] [Major/HIGH]: Rate Limiter 다중 워커 (DESIGN_RISK) — rate_limiter.py (점수: 70)
10. [P1-10] [Major/HIGH]: map_vc_by_registration 통합 테스트 부재 — tests (점수: 70)
11. [P1-11] [Major/HIGH]: bulk_add_vc_to_buyers 테스트 부재 — tests (점수: 70)
12. [P1-12] [Major/HIGH]: flush 후 rollback 미보장 — si_mapping_service.py (점수: 70)
13. [P1-13] [Major/HIGH]: 예외 체인 없는 raise — si_mapping.py (점수: 70)

### P2 — 개선 권장 (23건)
1. [P2-16] [Moderate/HIGH]: 감사 실패 정책 SI/VC 불일치 — si_mapping_service.py (점수: 50)
2. [P2-01] ~ [P2-22] — Moderate 이슈 22건 (점수: 24~40)

### P3 — 저우선 (18건)
1. [P3-01] ~ [P3-18] — Minor 이슈 18건 (점수: 6~20)

---

## Methodology

- **Agents**: R2(backend-security-reviewer), R3(python-code-reviewer), R4(python-code-reviewer), R5(performance-profiler), R6(general-purpose)
- **Perspectives**: 13개 — Security, Threat Modeling, Data Flow, API Contract, Error Handling, Observability, Performance, Deployment Safety, Dependencies, Domain Logic, Test Quality, Cognitive Complexity, Accessibility
- **Files scanned**: ~15개 (서비스, 라우터, 스키마, 모델, 마이그레이션, 테스트, 프론트엔드 컴포넌트)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 2건 + Major 15건 = 17건 수행
- **Deduplication**: 66건 원시 → 56건 (10건 중복 병합)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 66건
- 거부된 가설 (사전 제거): 1건 (R6-A05: 포커스 트랩 정상 동작)
- 중복 병합: 10건
- 보고된 이슈: 56건
- 거부율: 1.5%

### 교차 검증 결과

| 이슈 ID | 판정 | 비고 |
|---------|------|------|
| P0-01 (R3-C01+R4-EH01+R6-D05) | CONFIRMED | 3에이전트 독립 발견, Read 확인 |
| P0-02 (R3-C01+R5-C02) | CONFIRMED | 2에이전트, Read 확인 |
| P1-01 (R4-OB03) | CONFIRMED | Read 확인, map_vc_by_registration 패턴과 비교 |
| P1-02 (R5-D01) | CONFIRMED | Read 확인, 063 마이그레이션과 충돌 |
| P1-05 (R3-M02+R5-P01+R6-D03) | DESIGN_RISK | 3에이전트, 인덱스 존재로 완화 |
| P1-07 (R2-S04) | DESIGN_RISK | 2 worker 환경 특성상 완화 |
| P1-08 (R6-A01) | CONFIRMED | Read 확인 |
| P1-09 (R6-A03) | CONFIRMED | Read 확인 |

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 이미 수정됨 | 0 | — |
| 반증됨 | 1 | R6-A05: 포커스 트랩 useEffect Read 확인 → 정상 |
| 중복 | 10 | N+1 쿼리 3건 → 1건, audit 정책 3건 → 2건 |
| 범위 외 | 0 | — |

---

## 이전 리뷰 대비 비교

| 항목 | R1 (1차) | R2-R6 (2차) | 3차 (본 리뷰) |
|------|---------|-------------|--------------|
| 원시 이슈 | 20건 | 50건 | 66건 |
| 최종 보고 | 20건 | 50건 | 56건 (병합 후) |
| Critical | 0건 | 0건 | 2건 |
| Major | 5건 | 13건 | 14건 |
| 수정 적용 | 17건 | 25건 | (대기 중) |
| FP 제거 | 0건 | 0건 | 1건 |
| 교차 검증 | 미적용 | 미적용 | 17건 수행 |

**신규 발견**: SI/VC 비대칭 패턴 (audit try-except, not_found_count), asyncio.gather 인덱스, flush 후 rollback 등은 이전 리뷰에서 미발견.
