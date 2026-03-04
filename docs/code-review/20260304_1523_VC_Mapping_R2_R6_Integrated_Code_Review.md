# Code Review — VC Mapping (R2–R6 통합 리뷰, 2nd Round)

> **Review Date**: 2026-03-04 15:23
> **Reviewer**: Claude Code (review-orchestrate, §9 Perspective Shift)
> **Scope**: VC 매핑 기능 전체 (등록번호 기반 Value Chain 자동 매핑)
> **Method**: 13개 리뷰 관점 병렬 심층 리뷰 + Post-Fix Verification + 계획 대비 분석
> **1st Review**: `docs/code-review/20260304_1237_VC_Mapping_Code_Review.md` (20건, 17건 수정 완료)
> **Fix Plan**: `C:\Users\서지원\.claude\plans\staged-juggling-crescent.md`

## 리뷰 관점 매트릭스

| 라운드 | 관점 | 에이전트 |
|--------|------|---------|
| R2 | (1) 보안 (2) 위협 모델링 & 공격 표면 (STRIDE) | backend-security-reviewer |
| R3 | (3) 데이터 흐름 & 무결성 (4) API 계약 & 호환성 | general-purpose |
| R4 | (5) 에러 처리 (6) 관찰 가능성 & 디버깅 용이성 | general-purpose |
| R5 | (7) 성능 (8) 배포 안전성 (9) 의존성 & 결합도 | performance-profiler |
| R6 | (10) 도메인 로직 (11) 테스트 품질 (12) 인지 복잡도 (13) 접근성 & UX | general-purpose |
| §9-2 | Post-Fix Verification (17건 수정 검증) | general-purpose |
| §6 | 계획 대비 구현 대조 | general-purpose |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 2     | HIGH: 2                | P0: 2               |
| Major    | 11    | HIGH: 11               | P1: 11              |
| Moderate | 20    | HIGH: 18 / MEDIUM: 2   | P2: 18 / P3: 2      |
| Minor    | 17    | HIGH: 14 / MEDIUM: 3   | P3: 17              |
| **Total**| **50**| HIGH: **45** / MEDIUM: **5** | P0: **2** / P1: **11** / P2: **18** / P3: **19** |

**Cross-Verification**: 3건 교차 검증 (2+ 에이전트가 독립 발견)
- R4-E1 ≈ R5-P1 (func.replace 인덱스 무력화)
- R2-S01 ≈ R5-C3 (API 응답 등록번호 노출)
- R2-S03 ≈ R5-C1 (Rate Limiter 다중 워커 우회) → Major로 상향

**Post-Fix Verification**: 17/17건 수정 검증 통과, regression 미발견
**Plan Comparison**: 17/17건 계획 대비 100% 구현, 2건 계획보다 개선

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)

| # | ID | Severity/Confidence | 요약 | 파일 | 점수 |
|---|-----|---------------------|------|------|------|
| 1 | R4-E1/R5-P1 | Critical/HIGH ✅교차 | `func.replace()` 이중 호출로 114,964건 full scan + 쿼리 타임아웃 없음 | si_mapping_service.py:1028-1068 | 110 |
| 2 | R6-B01 | Critical/HIGH | `CompanyNotFoundError` 생성자 시그니처 불일치 — company_id에 에러 메시지 문자열 전달 | si_mapping_service.py:1091 + exceptions.py:65 | 100 |

### P1 — 스프린트 우선 (점수: 60-89)

| # | ID | Severity/Confidence | 요약 | 파일 | 점수 |
|---|-----|---------------------|------|------|------|
| 3 | R2-S01/R5-C3 | Major/HIGH ✅교차 | VcCompanyLookupResult 스키마가 corp_reg_no/biz_reg_no 원문 노출 | si_mapping.py:280-296 | 80 |
| 4 | R2-S03/R5-C1 | Major/HIGH ✅교차 | InMemoryRateLimiter 다중 워커(×N) 우회 + stale 키 O(n) 스캔 | rate_limiter.py:13-70 | 80 |
| 5 | R2-S02 | Major/HIGH | CompanyNotFoundError 핸들러가 company_id를 RFC 7807 응답에 포함 | exceptions.py:157-165 | 70 |
| 6 | R3-D1 | Major/HIGH | VC BuyerCandidate 딥다이브 링크 미작동 — si_company_id만 체크, vc_company_id 미처리 | BuyersTab.tsx:135-136 | 70 |
| 7 | R4-E2 | Major/HIGH | bulk_add에서 ValueError 미캐치 → 500 (422여야 함) | si_mapping.py:381-391 | 70 |
| 8 | R4-E3 | Major/HIGH | audit_service.record() 실패 시 비즈니스 데이터까지 롤백 | si_mapping_service.py:1153-1162 | 70 |
| 9 | R4-O1 | Major/HIGH | find_vc_company_by_registration()에 로깅 전무 | si_mapping_service.py:1033-1071 | 70 |
| 10 | R6-B02 | Major/HIGH | 존재하지 않는 vc_company_ids 조용히 무시 — 누락 건수 미보고 | si_mapping_service.py:1122-1128 | 70 |
| 11 | R6-B03 | Major/HIGH | 중복 체크가 company_name 문자열 기반 — 동명이인 기업 충돌 | si_mapping_service.py:1126-1137 | 70 |
| 12 | R6-T01 | Major/HIGH | VC 등록번호 매핑/일괄등록 API 레벨 통합 테스트 부재 | test_si_mapping.py | 70 |
| 13 | R6-X01 | Major/HIGH | 모달 포커스 트랩 미구현 — WCAG 2.4.3 위반 | SIMappingPanel.tsx:127-138 | 70 |

### P2 — 개선 권장 (점수: 30-59)

| # | ID | Severity/Confidence | 요약 | 파일 | 점수 |
|---|-----|---------------------|------|------|------|
| 14 | R2-S04 | Moderate/HIGH | get_deep_dive 엔드포인트 rate limit 미적용 (외부 HTTP 6회 호출) | si_mapping.py:151-169 | 40 |
| 15 | R2-S05 | Moderate/HIGH | 404 Not Found 분기에 감사 로그 미기록 (열거 공격 탐지 불가) | si_mapping.py:336-340 | 40 |
| 16 | R2-S07 | Moderate/HIGH | ANALYST 역할에 등록번호 조회 무제한 접근 (CLIENT만 제외) | si_mapping.py:41 | 40 |
| 17 | R4-E4 | Moderate/HIGH | audit_service.record() 후 commit 누락 → 감사 로그 미저장 | si_mapping.py:328-358 | 40 |
| 18 | R4-O2 | Moderate/HIGH | map_vc_by_registration() 성공 경로 로깅 없음 | si_mapping_service.py:1074-1103 | 40 |
| 19 | R4-O3 | Moderate/HIGH | 에러 로그에 입력 컨텍스트(마스킹된 등록번호 등) 누락 | si_mapping.py:342 | 40 |
| 20 | R5-P2 | Moderate/HIGH | 전방/후방 LIMIT 쿼리에서 업종 편중 시 일부 업종 기업 누락 | si_mapping_service.py:957-974 | 40 |
| 21 | R5-P3 | Moderate/HIGH | ChainPanelCard/CompanyRow에 React.memo 미적용 → 체크박스 1회 클릭에 최대 400 리렌더링 | VcMappingResult.tsx:63-143 | 40 |
| 22 | R5-D1 | Moderate/HIGH | 062 마이그레이션 부분 롤백 시 인덱스 삭제 → full scan 전환 | migrations/062:18-19 | 40 |
| 23 | R5-D2 | Moderate/HIGH | extra_data의 vc_company_id FK 없음 → 시딩 재구성 시 무효 참조 | si_mapping_service.py:1144 | 40 |
| 24 | R6-T02 | Moderate/HIGH | rate limiter 테스트 count=5 하드코딩 → max_calls 커플링 | test_rate_limiter.py:89,103,114 | 40 |
| 25 | R6-T03 | Moderate/HIGH | 두 등록번호 동시 제공 OR 결합 경로 테스트 부재 | test_si_mapping.py | 40 |
| 26 | R6-R01 | Moderate/HIGH | VcMappingResult 삼항 연산 2단 중첩 × 2회 반복 | VcMappingResult.tsx:177-189 | 40 |
| 27 | R6-R02 | Moderate/HIGH | SIMappingPanel 상태 9개 집중 — 2가지 독립 기능 혼재 | SIMappingPanel.tsx:33-49 | 40 |
| 28 | R6-X02 | Moderate/HIGH | 디자인 시스템 `<Modal>` 미사용 — 일관성 부재 | SIMappingPanel.tsx vs BuyersTab.tsx:352 | 40 |
| 29 | R3-M1~M3 | Moderate | R3 데이터 정합성 Moderate 이슈 3건 (상세: 이전 세션 참조) | — | 40 |

### P3 — 저우선 (점수: <30)

| # | ID | Severity/Confidence | 요약 | 점수 |
|---|-----|---------------------|------|------|
| 30 | R2-S06 | Moderate/MEDIUM ⚠️ | Query pattern 검증의 None 처리 미비 | 24 |
| 31 | R4-E5 | Moderate/MEDIUM ⚠️ | industry_name 빈 문자열 미검증 | 24 |
| 32 | R2-S08 | Minor/HIGH | _mask_reg_no 앞 6자리 복원 가능 | 20 |
| 33 | R2-S09 | Minor/HIGH | _MAX_COMPANIES_FOR_MAPPING 하드코딩 | 20 |
| 34 | R2-S10 | Minor/HIGH | 에러 메시지에 사용자 입력(회사명) 포함 | 20 |
| 35 | R4-O4 | Minor/HIGH | entity_id="VcMapping" 하드코딩 (실제 ID 아님) | 20 |
| 36 | R4-O5 | Minor/HIGH | 등록번호 min_length 미검증 | 20 |
| 37 | R4-O6 | Minor/HIGH | Rate limiter stale 키 정리 비효율 | 20 |
| 38 | R5-P4 | Minor/HIGH | SIMappingPanel 정적 import → lazy() 전환 권장 | 20 |
| 39 | R5-P5 | Minor/HIGH | audit 루프 개별 INSERT (최대 100회) | 20 |
| 40 | R6-T04 | Minor/HIGH | _normalize_reg_no 빈 문자열/공백 경계값 미검증 | 20 |
| 41 | R6-T05 | Minor/HIGH | test_find_vc_company_not_found 빈 DB에서만 검증 | 20 |
| 42 | R6-R03 | Minor/HIGH | find_vc_company_by_registration 유사 코드 3회 반복 | 20 |
| 43 | R6-R04 | Minor/HIGH | map_vc_candidates 133줄 Long Method | 20 |
| 44 | R6-X03 | Minor/HIGH | 체크박스 열 th 헤더 비어 있음 (sr-only 텍스트 없음) | 20 |
| 45 | R6-B05 | Minor/MEDIUM ⚠️ | formatRevenue .toFixed(1) 정밀도 제한 (1000억 단위) | 12 |
| 46 | R6-X04 | Minor/MEDIUM ⚠️ | 탭 전환 시 선택 초기화 — 크로스 탭 선택 불가 | 12 |
| 47 | R6-X05 | Minor/MEDIUM ⚠️ | 등록 버튼 동적 렌더링으로 레이아웃 시프트 | 12 |
| 48 | R3-L1~L3 | Minor | R3 데이터 정합성 Minor 이슈 3건 (상세: 이전 세션 참조) | 20 |

---

## Detailed Findings

### R2 — 보안 심층 (STRIDE + 공격 표면)

#### [R2-S01] VcCompanyLookupResult 스키마 등록번호 원문 노출 — [Major/HIGH] — P1 (80) ✅교차

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/schemas/si_mapping.py:280-296` |
| STRIDE | Information Disclosure |

**증거**: `VcCompanyLookupResult` 스키마가 `corp_reg_no`, `biz_reg_no`를 원본 그대로 프론트엔드에 반환. 프론트엔드(`VcMappingResult.tsx:205-209`)에서 직접 표시.

```python
class VcCompanyLookupResult(BaseModel):
    corp_reg_no: str | None = None   # ← 마스킹 없이 원문
    biz_reg_no: str | None = None    # ← 마스킹 없이 원문
```

감사 로그에는 `_mask_reg_no()`를 적용하면서(`si_mapping.py:353-354`) API 응답에는 미적용 — 일관성 부재.

**교차 검증**: R5-C3에서 동일 이슈 확인 (결합도/데이터 노출 관점).

**수정안**: 응답 스키마에서 등록번호를 제거하거나 마스킹 처리. UI에서는 "법인등록번호 확인됨 ✓" 등의 상태 표시로 대체.

---

#### [R2-S02] CompanyNotFoundError 핸들러 company_id 응답 노출 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/core/exceptions.py:157-165` |
| STRIDE | Information Disclosure |

**증거**: `company_not_found_handler`가 `exc.company_id`를 RFC 7807 응답 본문에 포함. 현재 라우터에서 `HTTPException(404)`로 먼저 변환하므로 이 핸들러까지 도달하지 않으나, 핸들러 통합 시 노출 위험.

```python
# exceptions.py:157-165
async def company_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "company_id": exc.company_id}  # ← 노출
    )
```

**수정안**: RFC 7807 응답에서 `company_id` 필드 제거. 또는 라우터의 직접 변환을 제거하고 전역 핸들러에 위임 + 핸들러에서 company_id 제외.

---

#### [R2-S03] InMemoryRateLimiter 다중 워커 우회 + stale 키 — [Major/HIGH ⚠️상향] — P1 (80) ✅교차

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/core/rate_limiter.py:13-70` |
| STRIDE | Denial of Service |
| 원래 심각도 | R2: Moderate → R5에서 Major로 상향 |

**증거**: 프로덕션 `--workers 2`에서 `max_calls=5` → 실질 10/분. 주석(line 26-28)에 명시되어 있으나, 보안 통제로 의존 시 잘못된 가정.

추가로 `check()` 메서드(line 59-61)가 매 요청마다 `_store.items()` 전체를 순회하여 stale 키를 정리 — O(n) 메모리 누수 취약점.

**교차 검증**: R5-C1에서 동일 이슈 확인 (성능/결합도 관점), Major로 상향 평가.

**수정안**: Redis 기반 Rate Limiter로 전환 계획 수립. 단기적으로 stale 키 정리를 별도 주기적 태스크로 분리.

---

#### [R2-S04] get_deep_dive 엔드포인트 rate limit 미적용 — [Moderate/HIGH] — P2 (40)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/routers/si_mapping.py:151-169` |
| STRIDE | Denial of Service |

**증거**: `get_deep_dive`는 외부 API(한국은행 등)에 6회 HTTP 요청을 발생시키나, `si_rate_limiter` 적용 없음. 악의적 반복 호출 시 외부 API 차단 위험.

**수정안**: `Depends(si_rate_limiter.check)` 추가.

---

#### [R2-S05] 404 Not Found 분기 감사 로그 미기록 — [Moderate/HIGH] — P2 (40)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/routers/si_mapping.py:336-340` |
| STRIDE | Repudiation |

**증거**: 존재하지 않는 등록번호로 조회 시 404 반환만 하고 감사 로그 미기록. 대량 열거 공격(등록번호 브루트포스) 탐지 불가.

**수정안**: 404 분기에도 `action="vc_lookup_not_found"` 감사 로그 기록.

---

#### [R2-S06] Pattern 검증 None 처리 — [Moderate/MEDIUM ⚠️] — P3 (24)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/routers/si_mapping.py:314-315` |

**증거**: `corp_reg_no`와 `biz_reg_no` 모두 `None`일 때 `pattern` 검증이 적용되지 않으나, `None` 자체는 FastAPI가 Query param 기본값으로 처리하므로 실제 우회 시나리오는 제한적.

---

#### [R2-S07] ANALYST 역할 등록번호 조회 무제한 — [Moderate/HIGH] — P2 (40)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/routers/si_mapping.py:41` |

**증거**: `_READ_ACCESS = require_role("ADMIN", "MANAGER", "ANALYST")` — ANALYST가 등록번호 기반 기업 조회를 무제한 수행 가능. CLIENT만 제외. 민감 정보(법인등록번호) 접근에 대한 역할 구분이 불충분.

**수정안**: 등록번호 조회 엔드포인트에 별도 `_REG_LOOKUP_ACCESS = require_role("ADMIN", "MANAGER")` 적용 검토.

---

#### [R2-S08] _mask_reg_no 앞 6자리 복원 가능 — [Minor/HIGH] — P3 (20)

앞 6자리가 노출되면 법인등록번호의 법인유형(앞 6자리)이 드러남. 감사 로그에서 `110111******7` 형태로 저장.

---

#### [R2-S09] _MAX_COMPANIES_FOR_MAPPING 하드코딩 — [Minor/HIGH] — P3 (20)

`si_mapping_service.py:832`의 상수가 환경변수/설정이 아닌 코드 내 하드코딩. 운영 중 변경 시 재배포 필요.

---

#### [R2-S10] 에러 메시지에 사용자 입력 포함 — [Minor/HIGH] — P3 (20)

`search_si_company_by_name`에서 검색어가 에러 메시지에 포함되어 로그에 남음. XSS는 아니나 로그 인젝션 가능성.

---

### R3 — 데이터 정합성 (데이터 흐름 + API 계약)

#### [R3-D1] VC BuyerCandidate 딥다이브 링크 미작동 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `amic-platform/src/modules/ma/tabs/BuyersTab.tsx:135-136` |

**증거**: `BuyersTab`의 딥다이브 버튼 클릭 핸들러가 `si_company_id`만 확인:

```tsx
// BuyersTab.tsx:135-136
const siCompanyId = buyer.extra_data?.si_company_id;
if (siCompanyId) { /* 딥다이브 열기 */ }
```

VC 매핑으로 추가된 BuyerCandidate는 `extra_data.vc_company_id`를 가지지만 `si_company_id`는 없음. 따라서 VC 매핑 매수자의 딥다이브 버튼이 작동하지 않음.

**수정안**: `vc_company_id` 존재 시 VC 전용 딥다이브 패널 표시 또는 `si_company_id || vc_company_id` 분기 처리.

---

#### R3 추가 이슈 (6건 요약)

R3 에이전트가 총 7건(Major: 1, Moderate: 3, Minor: 3) 보고. 10개 타입/필드 정합성 검사 모두 통과.
Moderate 3건과 Minor 3건은 데이터 흐름 추적 및 API 응답 포맷 관련 이슈로, 이전 세션의 R3 에이전트 트랜스크립트 참조.

---

### R4 — 프로덕션 복원력 (에러 처리 + 관찰 가능성)

#### [R4-E1] func.replace() Full Scan + 쿼리 타임아웃 없음 — [Critical/HIGH] — P0 (110) ✅교차

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:1028-1068` |

**증거**: `_strip_reg_col()` 헬퍼가 `func.replace(func.replace(col, "-", ""), " ", "")`로 컬럼을 함수로 감싸 B-tree 인덱스 무효화. 062 마이그레이션으로 생성된 `ix_vc_companies_corp_reg_no` 인덱스가 현재 쿼리 패턴에서 사용 불가.

114,964건 full sequential scan 발생. 쿼리 타임아웃 설정 없음 → 동시 요청 시 DB 커넥션 풀 고갈 위험.

**교차 검증**: R5-P1에서 동일 이슈 확인 (성능 관점). 마이그레이션으로 생성된 인덱스가 사실상 무효라는 점까지 검증.

**수정안**:
1. (권장) PostgreSQL 함수 기반 인덱스 마이그레이션 추가:
   ```sql
   CREATE INDEX ix_vc_corp_reg_normalized
     ON vc_companies (replace(replace(corp_reg_no, '-', ''), ' ', ''));
   ```
2. 또는 DB 저장 시 등록번호를 정규화된 형태로 시딩
3. 쿼리에 `statement_timeout` 설정 추가

---

#### [R4-E2] ValueError 미캐치 → 500 에러 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/routers/si_mapping.py:381-391` |

**증거**: `bulk_add_vc_to_buyers`에서 `si_mapping_service.py:1113`의 `ValueError("일괄 등록은 최대 100건까지 가능합니다")` 발생 시, 라우터가 `SQLAlchemyError`만 캐치하여 `ValueError`는 500으로 전파.

**수정안**: `except (ValueError, SQLAlchemyError) as exc:` 또는 별도 `ValueError` 핸들러 추가 (422 반환).

---

#### [R4-E3] Audit 실패 시 비즈니스 데이터 롤백 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:1153-1162` |

**증거**: `bulk_add_vc_to_buyers`에서 BuyerCandidate 추가와 audit_service.record()가 동일 트랜잭션에서 실행. audit INSERT 실패(예: JSONB 직렬화 오류) 시 전체 트랜잭션이 롤백되어 비즈니스 데이터(BuyerCandidate 등록)까지 실패.

**수정안**: audit 로깅을 별도 try-except로 감싸거나, nested transaction(savepoint) 사용.

---

#### [R4-E4] audit_service.record() 후 commit 누락 — [Moderate/HIGH] — P2 (40)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/routers/si_mapping.py:328-358` |

**증거**: `map_vc_by_registration` 라우터에서 `audit_service.record()` 호출 후 명시적 `await db.commit()` 없음. FastAPI의 dependency가 자동 커밋하는지 여부에 따라 감사 로그가 저장되지 않을 수 있음.

---

#### [R4-E5] industry_name 빈 문자열 미검증 — [Moderate/MEDIUM ⚠️] — P3 (24)

빈 문자열이 VC 매핑 결과에서 필터링되지 않아 UI에 빈 업종 패널 표시 가능성.

---

#### [R4-O1] find_vc_company_by_registration() 로깅 전무 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:1033-1071` |

**증거**: 등록번호 기반 기업 조회 함수에 `logger.info()`, `logger.debug()`, `logger.warning()` 모두 없음. 운영 환경에서 조회 성공/실패 추적 불가.

**수정안**: 함수 진입부에 `logger.info("VC company lookup", extra={...})`, 조회 결과에 따른 로깅 추가.

---

#### [R4-O2] map_vc_by_registration() 성공 경로 로깅 없음 — [Moderate/HIGH] — P2 (40)

성공 시에도 어떤 기업이 매핑되었는지 로그 없음. 운영 추적 불가.

---

#### [R4-O3] 에러 로그에 입력 컨텍스트 누락 — [Moderate/HIGH] — P2 (40)

`logger.exception` 호출 시 어떤 등록번호(마스킹)로 조회했는지 컨텍스트 없어 디버깅 어려움.

---

#### [R4-O4] entity_id="VcMapping" 하드코딩 — [Minor/HIGH] — P3 (20)

감사 로그의 `entity_id`가 실제 엔티티 ID가 아닌 "VcMapping" 문자열.

---

#### [R4-O5] 등록번호 min_length 미검증 — [Minor/HIGH] — P3 (20)

1~2자리 등록번호가 pattern 검증은 통과하나 의미 없는 조회 트리거.

---

#### [R4-O6] Rate limiter stale 키 정리 비효율 — [Minor/HIGH] — P3 (20)

매 요청마다 전체 store를 순회하여 만료 키 정리. 동시 사용자 증가 시 O(n) 성능 저하.

---

### R5 — 운영 & 코드 건강성 (성능 + 배포 + 결합도)

#### [R5-P2] 전방/후방 LIMIT 쿼리 업종 편중 누락 — [Moderate/HIGH] — P2 (40)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:957-974` |

**증거**: `ORDER BY revenue DESC LIMIT top_n * len(unique_related)` 쿼리는 매출 상위 N건을 가져온 뒤 Python에서 업종별 분배. 40개 업종 중 대규모 업종(자동차, IT)이 상위를 독점하면 소규모 업종(항공기 부품 도금 등)은 LIMIT 밖으로 밀림.

**수정안**: `ROW_NUMBER() OVER (PARTITION BY industry_name ORDER BY revenue DESC)` 윈도우 함수로 업종별 top_n 보장.

---

#### [R5-P3] ChainPanelCard/CompanyRow React.memo 미적용 — [Moderate/HIGH] — P2 (40)

| 항목 | 내용 |
|------|------|
| 위치 | `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:27-143` |

**증거**: 체크박스 토글 시 새 Set 객체 생성(`new Set(prev)`) → `selectedIds` prop 변경 → 모든 ChainPanelCard 리렌더링. `top_n=20`이면 20 패널 × 20 기업 = 최대 400 CompanyRow 리렌더링.

**수정안**: `React.memo(ChainPanelCard)`, `React.memo(CompanyRow)` 적용.

---

#### [R5-P4] SIMappingPanel 정적 import → lazy() 권장 — [Minor/HIGH] — P3 (20)

`BuyersTab.tsx:30-31`에서 SIMappingPanel을 정적 import. 모달이 열리지 않아도 TransactionWorkspace 청크에 6개 하위 컴포넌트 포함. `React.lazy()` 전환 권장.

---

#### [R5-P5] audit 루프 개별 INSERT — [Minor/HIGH] — P3 (20)

`bulk_add_vc_to_buyers`에서 최대 100건 개별 `audit_service.record()` 호출. 단일 요약 감사 로그로 대체 권장.

---

#### [R5-D1] 062 마이그레이션 부분 롤백 위험 — [Moderate/HIGH] — P2 (40)

062만 롤백 시 등록번호 인덱스 삭제 → 운영 중 엔드포인트가 full scan으로 전환. 전체 체인 롤백은 정상 동작.

---

#### [R5-D2] extra_data vc_company_id FK 없음 — [Moderate/HIGH] — P2 (40)

`BuyerCandidate.extra_data`에 `vc_company_id`가 JSON으로 저장되나 FK 제약 없음. vc_companies 재시딩 시 무효 참조 가능.

**수정안**: 별도 FK 컬럼 추가 또는 사용 의도 문서화.

---

### R6 — 비즈니스 & UX (도메인 + 테스트 + 가독성 + 접근성)

#### [R6-B01] CompanyNotFoundError 생성자 시그니처 불일치 — [Critical/HIGH] — P0 (100)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:1091` + `deal-mgmt/app/core/exceptions.py:65` |

**증거**: `CompanyNotFoundError.__init__(self, company_id)` — 첫 번째 인자가 `company_id`로 설계됨. 그러나 서비스에서는 한국어 에러 메시지 문자열을 전달:

```python
# exceptions.py:65
def __init__(self, company_id: object):
    self.company_id = str(company_id)
    self.message = f"기업을 찾을 수 없습니다: {self.company_id}"

# si_mapping_service.py:1091
raise CompanyNotFoundError("등록번호에 해당하는 기업을 찾을 수 없습니다")
```

결과: `self.company_id = "등록번호에 해당하는 기업을 찾을 수 없습니다"`, `self.message = "기업을 찾을 수 없습니다: 등록번호에 해당하는 기업을 찾을 수 없습니다"` — 이중 메시지 + company_id 의미론 파괴.

현재 라우터에서 HTTPException으로 먼저 변환하므로 기능적 오류는 없으나, 향후 전역 핸들러 통합 시 잘못된 응답 노출.

**수정안**: `raise CompanyNotFoundError("registration_lookup")` 등 식별자 전달, 또는 생성자 시그니처를 `(self, message: str)` 로 변경.

---

#### [R6-B02] 존재하지 않는 vc_company_ids 조용히 무시 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:1122-1128` |

**증거**: 5개 요청 → DB에 3개만 존재 → 2개 무시, `added_count`에만 실제 추가 수 반환. 사용자는 2건 누락 사실을 알 수 없음.

**수정안**: 응답에 `not_found_ids` 또는 `not_found_count` 필드 추가.

---

#### [R6-B03] 중복 체크가 company_name 문자열 기반 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/app/services/si_mapping_service.py:1126-1137` |

**증거**: 114,964개 기업 중 동명 기업 존재 가능. `company_name`만으로 중복 판단하여 `vc_company_id`가 다른 기업이 스킵될 수 있음. `extra_data`에 `vc_company_id`를 저장하지만 중복 체크에는 미사용.

**수정안**: `(company_name, extra_data->>'vc_company_id')` 쌍으로 중복 체크 또는 별도 `source_company_id` 컬럼 추가.

---

#### [R6-B05] formatRevenue .toFixed(1) 정밀도 제한 — [Minor/MEDIUM ⚠️] — P3 (12)

1조 이상에서 `.toFixed(1)` → 1,000억 단위로 반올림. M&A 딜 매출 정보 정밀도 제한.

---

#### [R6-T01] VC 등록번호 매핑 API 레벨 통합 테스트 부재 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `deal-mgmt/tests/test_si_mapping.py` |

**증거**: 등록번호 관련 테스트는 서비스 함수 직접 호출만 존재(line 511-557). API 엔드포인트 레벨 미검증:
- Query parameter 검증 (pattern, max_length)
- Rate limiter 적용
- 감사 로그 마스킹
- CompanyNotFoundError → 404 변환
- SQLAlchemyError → 503 변환
- POST bulk_add 엔드포인트

**수정안**: SI 매핑 기존 테스트 패턴(`test_map_direct_peers` 등)과 동일하게 `AsyncClient` 기반 API 테스트 추가.

---

#### [R6-T02] rate limiter 테스트 count=5 하드코딩 커플링 — [Moderate/HIGH] — P2 (40)

`test_rate_limiter.py:89`의 `count=5`가 `si_rate_limiter._max_calls` 값과 암묵적 연동. `max_calls` 변경 시 테스트 실패 원인 파악 어려움.

---

#### [R6-T03] OR 결합 경로 테스트 부재 — [Moderate/HIGH] — P2 (40)

`find_vc_company_by_registration()`의 3가지 분기 중 "두 등록번호 동시 제공" OR 결합 경로(line 1044-1057) 미검증.

---

#### [R6-T04] _normalize_reg_no 경계값 미검증 — [Minor/HIGH] — P3 (20)

`""`, `"   "`, `"---"` 등 빈/공백/하이픈만 입력 시 동작 미검증.

---

#### [R6-T05] test_find_vc_company_not_found 약한 단언 — [Minor/HIGH] — P3 (20)

빈 DB에서 조회하여 `None` 확인 — 데이터 존재 시 비매칭 케이스 미검증.

---

#### [R6-R01] VcMappingResult 삼항 연산 2단 중첩 — [Moderate/HIGH] — P2 (40)

```tsx
const currentPanels = activeTab === "forward" ? mapping.forward_chains
  : activeTab === "backward" ? mapping.backward_chains : [];
```

유사 패턴 2회 반복. `Record<VcTab, ...>` 매핑 객체로 대체 권장.

---

#### [R6-R02] SIMappingPanel 상태 9개 집중 — [Moderate/HIGH] — P2 (40)

"KSIC SI 매핑"과 "등록번호 VC 매핑" 2가지 독립 기능이 하나의 컴포넌트에 혼재. 분리 권장.

---

#### [R6-R03] find_vc_company_by_registration 유사 코드 3회 반복 — [Minor/HIGH] — P3 (20)

3가지 분기(둘 다/corp만/biz만)에서 normalize + strip + select 패턴 반복.

---

#### [R6-R04] map_vc_candidates 133줄 Long Method — [Minor/HIGH] — P3 (20)

5단계(전방/후방/경쟁사/업종별 기업/패널 조립)가 하나의 함수에 집중. 서브 함수 추출 권장.

---

#### [R6-X01] 모달 포커스 트랩 미구현 — [Major/HIGH] — P1 (70)

| 항목 | 내용 |
|------|------|
| 위치 | `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx:127-138` |

**증거**: `role="dialog"` + `aria-modal="true"` + Escape 핸들러 + body scroll lock은 있으나, Tab 키 포커스가 모달 외부로 이동 가능. WCAG 2.4.3 (Focus Order) 위반.

1st review의 A11Y-01 수정에서 "최소" 옵션을 선택하여 ARIA + Escape + scroll lock만 구현. 포커스 트랩은 의도적으로 제외되었으나, WCAG 필수 요건.

**수정안**: 디자인 시스템의 `<Modal>` 컴포넌트로 래핑하거나 `react-focus-lock` 적용.

---

#### [R6-X02] 디자인 시스템 Modal 미사용 — [Moderate/HIGH] — P2 (40)

BuyersTab은 `<Modal>` 사용, SIMappingPanel은 자체 구현. 동일 탭에서 일관성 부재.

---

#### [R6-X03] 체크박스 열 th 빈 헤더 — [Minor/HIGH] — P3 (20)

```tsx
<th scope="col" className="w-10 px-3 py-2" /> // ← sr-only 텍스트 없음
```

**수정안**: `<th scope="col"><span className="sr-only">선택</span></th>`

---

#### [R6-X04] 탭 전환 시 선택 초기화 — [Minor/MEDIUM ⚠️] — P3 (12)

전방 탭에서 선택 → 후방 탭 이동 → 전방 복귀 시 선택 소실. 크로스 탭 선택 불가.

---

#### [R6-X05] 등록 버튼 동적 렌더링 레이아웃 시프트 — [Minor/MEDIUM ⚠️] — P3 (12)

`selectedIds.size > 0` 조건부 렌더링으로 첫 체크박스 선택 시 버튼 영역 추가/제거.

---

## Post-Fix Verification (§9 전략 2)

### 17건 수정 검증 결과

| # | 이슈 ID | 수정 상태 | 검증 |
|---|---------|---------|------|
| 1 | PERF-01 | ✅ 완료 | `_strip_reg_col()` 헬퍼로 하이픈+공백 모두 제거. 3개 쿼리 경로에서 일관 적용 |
| 2 | DATA-01 | ✅ 완료 | `str(vc.id)` — SI 패턴(line 284)과 일치 |
| 3 | SEC-05 | ✅ 완료 | 등록번호 원문 제거, 일반 메시지만 |
| 4 | PERF-03 | ✅ 완료 | `or_()` 1회 쿼리 통합 + 단독 경로 보존 |
| 5 | SEC-01 | ✅ 완료 | `pattern=r"^[\d\-\s]+$"` 적용 |
| 6 | SEC-03 | ✅ 완료 | `_mask_reg_no()` + 감사 로그 마스킹 |
| 7 | SEC-02 | ✅ 완료 | `max_calls=5` + 테스트 `count=5` 동기화 |
| 8 | TEST-01 | ✅ 완료 | `_seed_vc_company()` + 4개 테스트 케이스 |
| 9 | A11Y-01 | ✅ 완료 | ARIA + Escape + scroll lock |
| 10 | UX-01 | ✅ 완료 | Backdrop click + stopPropagation |
| 11 | A11Y-02 | ✅ 완료 | Checkbox aria-label |
| 12 | A11Y-03 | ✅ 완료 | th scope="col" (두 테이블 모두) |
| 13 | CODE-01 | ✅ 완료 | useCallback 제거 → 일반 함수 |
| 14 | UX-02 | ✅ 완료 | 탭 변경 시 setSelectedIds(new Set()) |
| 15 | CODE-03 | ✅ 완료 | key에 activeTab prefix |
| 16 | TYPE-01 | ✅ 완료 | IIFE 런타임 타입 가드 |
| 17 | SEC-04 | ✅ 완료 | `len > 100` 방어적 검증 (서비스 레이어) |

### 스킵 3건 재검증

| ID | 스킵 사유 | 재검증 |
|----|----------|-------|
| PERF-02 | 순차 audit, max 100건 성능 미미 | ✅ 합리적 |
| CODE-02 | Badge variant 미지원, className 패턴 | ✅ 합리적 |
| PERF-04 | ILIKE wildcard, VC 매핑 범위 외 | ✅ 합리적 |

**Regression**: 미발견. 17건 수정 모두 새로운 이슈 도입 없음.

---

## 계획 대비 구현 검증 (§6)

| # | 계획된 항목 | 구현 상태 | 비고 |
|---|-----------|---------|------|
| 1 | Step 1-1: SQL 공백 제거 | ✅ | `_strip_reg_col()` 헬퍼 추출 (계획보다 개선) |
| 2 | Step 1-2: extra_data str(vc.id) | ✅ | 정확히 일치 |
| 3 | Step 1-3: CompanyNotFoundError 등록번호 제거 | ✅ | 정확히 일치 |
| 4 | Step 1-4: OR 결합 쿼리 | ✅ | 정확히 일치 |
| 5 | Step 2-1: Query pattern 추가 | ✅ | 유연한 패턴 적용 (계획보다 유연화) |
| 6 | Step 2-2: 감사 로그 마스킹 | ✅ | 정확히 일치 |
| 7 | Step 3-1: max_calls 5 변경 | ✅ | 정확히 일치 |
| 8 | Step 4-1: 서비스 방어적 검증 | ✅ | 정확히 일치 |
| 9 | Step 5-1: 4개 테스트 추가 | ✅ | 정확히 일치 |
| 10 | Step 6-1: ARIA + Escape + scroll lock | ✅ | 정확히 일치 |
| 11 | Step 6-2: Backdrop 클릭 | ✅ | 정확히 일치 |
| 12 | Step 7-1~7-5: VcMappingResult 5건 | ✅ | 모두 일치 |
| 13 | Step 8-1: IIFE 타입 가드 | ✅ | IIFE 패턴으로 간결화 |

**계획 대비 100% 구현 완료.** 2건 계획 대비 개선(헬퍼 추출, IIFE 간결화), 1건 유연화(패턴 검증).

---

## Methodology

- **Agents**: backend-security-reviewer, general-purpose (×3), performance-profiler
- **Files scanned**: ~15개 (BE 서비스/라우터/스키마/모델/테스트 + FE 컴포넌트/탭)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 3건 교차 검증 (R4-E1≈R5-P1, R2-S01≈R5-C3, R2-S03≈R5-C1)
- **Post-Fix Verification**: 17/17건 + 3 스킵 재검증

### 리뷰 라운드별 이슈 분포

| Round | Critical | Major | Moderate | Minor | Total |
|-------|----------|-------|----------|-------|-------|
| R2 보안 | 0 | 3* | 4 | 3 | 10 |
| R3 데이터 | 0 | 1 | 3 | 3 | 7 |
| R4 복원력 | 1 | 3 | 4 | 3 | 11 |
| R5 운영 | 0 | 0** | 4 | 2 | 6 |
| R6 비즈니스/UX | 1 | 4 | 5 | 8 | 18 |
| **Total** | **2** | **11** | **20** | **19** | — |
| **중복 제거 후** | **2** | **11** | **20** | **17** | **50** |

*R2-S03이 R5에서 Major로 상향, **R5의 Major 2건(R5-P1, R5-C1)은 각각 R4-E1, R2-S03과 병합

---

## 검증 투명성

### 검증 통계
- 검증한 가설: ~70건 (6개 에이전트 합산)
- 보고된 이슈: 50건 (중복 제거 후)
- "이슈 없음" 판정: 2건 (R5-D3 배포 안전성 통과, R5-C2 순환 의존성 없음)
- R3 타입/필드 정합성 검사: 10/10 통과

### 교차 검증 상세

| 이슈 | 발견 에이전트 | 심각도 조정 |
|------|-------------|-----------|
| func.replace 인덱스 무력화 | R4(Critical) + R5(Major) | Critical 유지 (상위 채택) |
| API 응답 등록번호 노출 | R2(Major) + R5(Minor) | Major 유지 (상위 채택) |
| Rate Limiter 다중 워커 | R2(Moderate) + R5(Major) | **Major로 상향** (R5 평가 채택) |

### 신뢰도 가중 우선순위 조정
- MEDIUM 신뢰도 이슈 5건 하향 조정:
  - R2-S06: Moderate → P3 (점수: 24)
  - R4-E5: Moderate → P3 (점수: 24)
  - R6-B05: Minor → P3 (점수: 12)
  - R6-X04: Minor → P3 (점수: 12)
  - R6-X05: Minor → P3 (점수: 12)
