# Code Review — VC 매핑 (등록번호 기반 Value Chain 매핑)

> **Review Date**: 2026-03-04 12:37
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: VC 매핑 기능 — BE(si_mapping_service, si_mapping router/schema) + FE(SIMappingPanel, VcMappingResult, BuyersTab, useSIMapping, si_mapping types)
> **Method**: Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) pytest(PASS, 1532/15 skip)
> **Agents**: python-code-reviewer, performance-profiler, backend-security-reviewer(×2), frontend-code-reviewer

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 2     | HIGH: 2 | P1: 2 |
| Moderate | 8     | HIGH: 6 / MEDIUM: 2 | P2: 8 |
| Minor    | 10    | HIGH: 7 / MEDIUM: 3 | P3: 10 |
| **Total**| **20**| HIGH: **15** / MEDIUM: **5** | P0: **0** / P1: **2** / P2: **8** / P3: **10** |

**FP Prevention**: 가설 25건 검증, 5건 사전 거부 (거부율: 20%) | 교차 검증 5건 수행 (2건 CONFIRMED, 1건 DESIGN_RISK, 2건 FALSE_POSITIVE)

---

## Findings

### P1 — 스프린트 우선 (점수: 60-89)

#### [PERF-01] func.replace() 인덱스 무효화 + 공백 정규화 불일치 — [Major/HIGH] — Priority: P1 (점수: 80)

**교차 검증**: python-code-reviewer + performance-profiler (CONFIRMED)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:1040-1051`

**문제 1 — 인덱스 무효화**: `func.replace(VcCompany.corp_reg_no, "-", "") == normalized`는 SQL 함수를 컬럼에 적용하므로 B-Tree 인덱스(`ix_vc_companies_corp_reg_no`)를 무효화한다. 114,964건 테이블 풀 스캔 발생.

**문제 2 — 정규화 불일치**: Python `_normalize_reg_no()`는 `[\s\-]`(하이픈+공백)을 제거하지만, SQL `func.replace(..., "-", "")`는 하이픈만 제거. 공백이 포함된 등록번호(`110111 0000000`)는 Python과 SQL에서 다른 결과를 반환.

```python
# Python: 하이픈 + 공백 모두 제거
_REG_NO_STRIP_RE = re.compile(r"[\s\-]")  # "110111 0000000" → "1101110000000"

# SQL: 하이픈만 제거
func.replace(VcCompany.corp_reg_no, "-", "")  # "110111 0000000" → "110111 0000000" (공백 유지)
```

**수정 방안**:
1. Expression Index 생성 (migration 063): `CREATE INDEX ix_vc_corp_reg_normalized ON vc_companies (REPLACE(REPLACE(corp_reg_no, '-', ''), ' ', ''))`
2. SQL에도 공백 제거 추가: `func.replace(func.replace(VcCompany.corp_reg_no, "-", ""), " ", "")`
3. 또는 DB 데이터 자체를 정규화 (일회성 마이그레이션)

---

#### [DATA-01] extra_data vc_company_id int vs str 타입 불일치 — [Major/HIGH] — Priority: P1 (점수: 80)

**교차 검증**: python-code-reviewer + backend-security-reviewer + performance-profiler (CONFIRMED, 3개 에이전트)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:1126`

SI 매핑의 `bulk_add_to_buyers`는 `str(si.id)`로 명시적 변환하지만, VC 매핑은 `vc.id`(int)를 그대로 저장:

```python
# SI 버전 (line 284): str 변환
extra_data={"si_company_id": str(si.id)}

# VC 버전 (line 1126): int 그대로
extra_data={"vc_company_id": vc.id, "industry_name": vc.industry_name}
```

프론트엔드 BuyersTab(line 125-126)에서 `si_company_id`를 `string`으로 캐스팅하므로, 향후 `vc_company_id`를 같은 방식으로 읽으면 타입 불일치.

**수정**: `extra_data={"vc_company_id": str(vc.id), ...}` 또는 타입 컨벤션 명문화

---

### P2 — 개선 권장 (점수: 30-59)

#### [A11Y-01] SIMappingPanel 모달 접근성 미구현 — [Moderate/HIGH] — Priority: P2 (점수: 50)

**교차 검증**: frontend-code-reviewer R01 + R09 병합

**파일**: `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx:111`

커스텀 모달에 `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, Escape 키 핸들링, 포커스 트랩이 모두 누락. 동일 모듈의 `FIRecommendModal`은 `<Modal>` 공통 컴포넌트를 사용하여 이 문제 없음.

**수정**: `<Modal>` 공통 컴포넌트로 교체하거나, 최소 `role="dialog"` + `aria-modal` + `onKeyDown(Escape)` 추가

---

#### [SEC-01] 등록번호 파라미터 형식 검증 없음 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**교차 검증**: backend-security-reviewer (2회 독립 확인)

**파일**: `deal-mgmt/app/routers/si_mapping.py:299-300`

`max_length=20`만 적용, 숫자/하이픈 외 문자 미검증. SQLAlchemy ORM 파라미터 바인딩으로 SQL 인젝션은 안전하나, 비표준 문자열로 불필요한 DB 탐색 가능.

```python
# 현재: max_length만
corp_reg_no: str | None = Query(None, max_length=20)

# 수정: pattern 추가
corp_reg_no: str | None = Query(None, max_length=14, pattern=r"^\d{6}-?\d{7}$|^\d{13}$")
biz_reg_no: str | None = Query(None, max_length=12, pattern=r"^\d{3}-?\d{2}-?\d{5}$|^\d{10}$")
```

---

#### [SEC-02] InMemoryRateLimiter 멀티 워커 환경 우회 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**교차 검증**: backend-security-reviewer (2회 독립 확인)

**파일**: `deal-mgmt/app/core/rate_limiter.py:69-70`

`si_rate_limiter = InMemoryRateLimiter(max_calls=10, window_seconds=60.0)` — 워커 N개 시 실질 `10×N`회/분. VC 매핑은 5,000건+ DB 로딩 수반.

**수정**: Redis 기반 Rate Limiter 교체 또는 Nginx `limit_req` 보완

---

#### [SEC-03] 감사 로그에 등록번호 평문 기록 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `deal-mgmt/app/routers/si_mapping.py:336-339`

```python
new_value={
    "action": "map_vc_by_registration",
    "corp_reg_no": corp_reg_no,   # 평문
    "biz_reg_no": biz_reg_no,      # 평문
}
```

**수정**: 마스킹 처리 (`*********1234` 형식)

---

#### [TEST-01] 등록번호 기반 VC 매핑 함수 테스트 없음 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `deal-mgmt/tests/`

`find_vc_company_by_registration()`, `map_vc_by_registration()`, `bulk_add_vc_to_buyers()` 3개 함수에 대한 유닛 테스트 없음. 정규화 로직, 등록번호 fallback, 중복 건너뜀 등의 엣지 케이스 미검증.

---

#### [TYPE-01] BuyersTab corporate_info 타입 단언 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx:61-62`

```tsx
const corporateInfo = txn?.corporate_info as CorporateDocsExtractedData | null;
```

`corporate_info`의 실제 타입은 `Record<string, unknown> | null`. 런타임 검증 없는 타입 단언은 타입 안전성 구멍.

**수정**: zod 스키마 파싱 또는 수동 타입 가드

---

#### [PERF-02] bulk_add_vc_to_buyers 순차 audit 기록 — [Moderate/HIGH] — Priority: P2 (점수: 40)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:1135-1143`

N건의 BuyerCandidate 생성 시 `audit_service.record()` N회 순차 호출. `max_length=100`이므로 최대 100회. 단일 트랜잭션 내 INSERT이므로 심각하진 않으나, bulk insert 패턴으로 개선 가능.

---

#### [SEC-04] bulk_add_vc_to_buyers 서비스 레이어 개수 미검증 — [Moderate/MEDIUM] — Priority: P2 (점수: 24)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:1091-1096`

Pydantic `max_length=100`은 HTTP 계층에서만 적용. 서비스 함수를 직접 호출하는 내부 코드/테스트에서 무제한 리스트 전달 가능.

---

### P3 — 저우선 (점수: <30)

#### [A11Y-02] VcMappingResult 체크박스 aria-label 누락 — [Minor/HIGH] — P3 (20)

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:39-44`

#### [A11Y-03] 테이블 th scope="col" 누락 — [Minor/HIGH] — P3 (20)

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:112-118, 242-249`

ConsortiumPanel은 올바르게 `scope="col"` 사용 — 패턴 불일치.

#### [UX-01] SIMappingPanel 백드롭 클릭 시 onClose 미호출 — [Minor/HIGH] — P3 (20)

**파일**: `amic-platform/src/modules/ma/components/si-mapping/SIMappingPanel.tsx:111`

#### [CODE-01] useCallback 의존성에 mutation 객체 포함 (메모이제이션 무효화) — [Minor/HIGH] — P3 (20)

**파일**: `VcMappingResult.tsx:160-166`, `SIMappingPanel.tsx:55-60, 66-80, 102-108`

`useMutation` 반환 객체는 매 렌더 새 참조 → `useCallback` 실효 없음.

#### [CODE-02] DealRoleBadge variant 미사용 — [Minor/HIGH] — P3 (20)

**파일**: `amic-platform/src/modules/ma/components/buyers/DealRoleBadge.tsx:22`

Badge의 유효 variant에 purple/indigo/cyan이 없어 의도적 사용이나, 디자인 시스템 확장이 바람직.

#### [PERF-03] 등록번호 2개 제공 시 순차 DB 쿼리 — [Minor/HIGH] — P3 (20)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:1038-1054`

corp_reg_no 실패 → biz_reg_no 재시도. OR 조건으로 단일 쿼리 가능.

#### [SEC-05] CompanyNotFoundError 예외에 입력값 포함 (잠재 위험) — [Minor/MEDIUM] — P3 (12)

**파일**: `deal-mgmt/app/services/si_mapping_service.py:1074-1076`

현재 라우터가 잡아서 일반 메시지 반환하므로 즉각 위험 없음. 다른 호출 경로에서 전역 핸들러 도달 시 노출 가능.

#### [UX-02] VcMappingResult 탭 전환 시 selectedIds 미초기화 — [Minor/MEDIUM] — P3 (12)

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:147-148, 222`

의도적일 수 있으나, "N개" 표시와 현재 탭 선택이 불일치할 수 있음.

#### [CODE-03] ChainPanelCard key에 industry_name 사용 (충돌 가능) — [Minor/MEDIUM] — P3 (12)

**파일**: `amic-platform/src/modules/ma/components/si-mapping/VcMappingResult.tsx:272`

#### [PERF-04] ILIKE wildcard prefix 인덱스 미활용 — [Minor/MEDIUM] — P3 (12)

**파일**: `deal-mgmt/app/services/si_mapping_service.py` (기존 코드, 현재 변경과 직접 관련 없음)

---

## Out-of-Scope Findings (참고)

### [OOS-01] .env 파일에 실제 API 키 존재 — [Critical/HIGH]

**파일**: `deal-mgmt/.env`

보안 리뷰어가 `.env` 파일에 Anthropic, OpenAI, Google, Clova API 키가 평문으로 존재함을 발견. `.gitignore`에 등록되어 추적되지 않으나, 키 유출 시 즉시 revoke 필요. **VC 매핑 기능과 무관한 기존 이슈**.

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+)
없음

### P1 — 스프린트 우선 (점수: 60-89)
1. [PERF-01] func.replace() 인덱스 무효화 + 공백 정규화 불일치 — si_mapping_service.py (점수: 80, 교차검증)
2. [DATA-01] extra_data vc_company_id int vs str 불일치 — si_mapping_service.py (점수: 80, 교차검증 3건)

### P2 — 개선 권장 (점수: 30-59)
1. [A11Y-01] SIMappingPanel 모달 접근성 — SIMappingPanel.tsx (점수: 50, R01+R09 병합)
2. [SEC-01] 등록번호 형식 검증 없음 — si_mapping.py (점수: 40)
3. [SEC-02] InMemoryRateLimiter 멀티 워커 우회 — rate_limiter.py (점수: 40)
4. [SEC-03] 감사 로그 등록번호 평문 — si_mapping.py (점수: 40)
5. [TEST-01] VC 매핑 테스트 없음 (점수: 40)
6. [TYPE-01] corporate_info 타입 단언 — BuyersTab.tsx (점수: 40)
7. [PERF-02] 순차 audit 기록 — si_mapping_service.py (점수: 40)
8. [SEC-04] 서비스 레이어 개수 미검증 — si_mapping_service.py (점수: 24)

### P3 — 저우선 (점수: <30)
1. [A11Y-02] 체크박스 aria-label 누락 (20) 2. [A11Y-03] th scope 누락 (20) 3. [UX-01] 백드롭 클릭 미동작 (20) 4. [CODE-01] useCallback 무효화 (20) 5. [CODE-02] DealRoleBadge variant (20) 6. [PERF-03] 순차 DB 쿼리 (20) 7. [SEC-05] 예외 입력값 포함 (12) 8. [UX-02] 탭 전환 선택 유지 (12) 9. [CODE-03] key 충돌 가능 (12) 10. [PERF-04] ILIKE prefix (12)

---

## Methodology

- **Agents**: python-code-reviewer, performance-profiler, backend-security-reviewer(×2), frontend-code-reviewer
- **Files scanned**: 15+
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical + Major 5건 수행 (2 CONFIRMED, 1 DESIGN_RISK, 2 FALSE_POSITIVE)

## 검증 투명성

### 검증 통계
- 검증한 가설: 25건
- 거부된 가설 (사전 제거): 5건
- 보고된 이슈: 20건
- 거부율: 20%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 (FP-CTX) | 2 | SEC-002: 라우터가 CompanyNotFoundError 잡아 일반 404 반환, I-04: 세션 의존성 자동 커밋 |
| 설계 의도 (DESIGN_RISK) | 1 | SEC-003: 레퍼런스 데이터 API로 딜 접근 제어 불필요 (RBAC+rate limit+audit 적용) |
| 범위 외 | 1 | SEC-001: .env 파일 API 키 (기존 이슈, VC 매핑 무관) |
| 중복 | 1 | SEC-006 SSRF: 사용자 입력 아닌 설정값, DB 값 사용 (간접 경로도 실질 위험 낮음) |

### 긍정 평가 항목 (잘 된 부분)
1. **SQLAlchemy ORM 일관 사용**: SQL Injection 안전 (파라미터 바인딩)
2. **RBAC 일관 적용**: 모든 엔드포인트에 `require_role` Depends 주입
3. **딜 접근 제어**: 쓰기 엔드포인트 모두 `check_client_deal_access()` 호출
4. **감사 추적**: 매핑 실행·일괄 등록 모두 `audit_service.record()` 기록
5. **LIKE Escape 처리**: `%`, `_`, `\` 이스케이프 일관 적용
6. **FE-BE 타입 동기화**: `si_mapping.ts` ↔ `si_mapping.py` 스키마 필드 완전 일치
7. **에러 핸들링**: 라우터에서 예외를 잡아 일반 메시지 반환 (정보 노출 방지)
8. **React Query 패턴**: 캐시 무효화·토스트 피드백 올바르게 적용
