# Code Review — FI 자동 매핑 시스템 (13개 관점)

> **Review Date**: 2026-03-02 00:44 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI 자동 매핑 시스템 신규 구현 (7개 파일)
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review (5 Agents, 13 Perspectives) + Cross-Verification
> **Quality Gates**: ruff(PASS) pytest(PASS, 11/11) tsc(PASS) ruff-format(PASS)
> **Review Gates**: Backend(available) Frontend(available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

## 리뷰 대상 파일

| # | 파일 | 유형 | 라인 |
|---|------|------|------|
| 1 | `deal-mgmt/app/routers/pef_registry.py` | BE 라우터 (핵심 알고리즘) | 197 |
| 2 | `deal-mgmt/app/schemas/pef_registry.py` | BE Pydantic 스키마 | 31 |
| 3 | `deal-mgmt/app/models/pef_fund_registry.py` | BE SQLAlchemy 모델 | 34 |
| 4 | `deal-mgmt/tests/test_fi_mapping.py` | 테스트 (신규) | 429 |
| 5 | `amic-platform/src/modules/ma/types/pef_registry.ts` | FE 타입 | 19 |
| 6 | `amic-platform/src/modules/ma/hooks/usePefRegistry.ts` | FE React Query 훅 | 71 |
| 7 | `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx` | FE 모달 UI | 197 |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 0     | — | — |
| Major    | 7     | HIGH: 7 / MEDIUM: 0 / LOW: 0 | P1: 7 |
| Moderate | 13    | HIGH: 9 / MEDIUM: 4 / LOW: 0 | P2: 9 / P3: 4 |
| Minor    | 21    | HIGH: 13 / MEDIUM: 8 / LOW: 0 | P3: 21 |
| **Total**| **41** (중복 제거 후 **29**) | HIGH: **29** / MEDIUM: **12** / LOW: **0** | P0: **0** / P1: **7** / P2: **9** / P3: **25** |

**Cross-Verification**: Major 7건 교차 검증 — 7건 CONFIRMED, 0건 FALSE_POSITIVE
**Deduplication**: 에이전트 간 중복 12건 병합 (41건 → 29건)

---

## Priority Matrix

### P1 — 스프린트 우선 (점수 60–89)

| # | ID | 심각도/신뢰도 | 점수 | 요약 | 위치 |
|---|-----|-------------|------|------|------|
| 1 | **SCHEMA-01** | Major/HIGH | 80 | **Decimal→string 직렬화 vs FE number 타입 불일치** — BE `Decimal` 필드 3개가 JSON에서 string(`"1500.00"`)으로 직렬화되나 FE는 `number` 선언. `formatBillion("1500.00")` → `"1500.00억"` (잘못된 포맷) | `pef_registry.py:26`, `pef_registry.ts:14` |
| 2 | **PERF-02** | Major/HIGH | 80 | **`registration_date` 인덱스 부재** — FI 추천 핵심 WHERE 조건에 인덱스 없음. 현재 1,137건에서는 허용 가능하나 데이터 증가 시 병목 | `pef_fund_registry.py:18-24` |
| 3 | **PERF-01** | Major/HIGH | 80 | **전체 테이블 메모리 로드 + String 날짜 비교** — 필터 후 전체 PEF를 Python 메모리에 올려 GP 그룹핑. `registration_date` String(10) 사전순 비교에 의존 | `pef_registry.py:137,146` |
| 4 | **TC-01** | Major/HIGH | 70 | **`estimated_deal_value` None/0/음수 분기 테스트 누락** — 3개 조기 반환 분기(line 119, 128) 미커버 | `test_fi_mapping.py` |
| 5 | **TC-02** | Major/HIGH | 70 | **`lower > upper` 422 에러 테스트 누락** — 배수 역전 검증(line 113-117) 미커버 | `test_fi_mapping.py` |
| 6 | **TC-04** | Major/HIGH | 70 | **`target_company_name` 기반 프로젝트 펀드 제외 테스트 누락** — line 144 필터 미커버 | `test_fi_mapping.py` |
| 7 | **TC-07** | Major/HIGH | 70 | **`list_pef_funds`/`pef_fund_count` 엔드포인트 완전 미커버** — CLIENT 403, search, 페이지네이션 | `test_fi_mapping.py` (범위 외 — 별도 테스트 파일 필요) |

### P2 — 개선 권장 (점수 30–59)

| # | ID | 심각도/신뢰도 | 점수 | 요약 | 위치 |
|---|-----|-------------|------|------|------|
| 8 | **AUTH-02** | Mod/HIGH | 50 | **txn_id Enumeration** — `get_transaction`(404)이 `check_client_deal_access`(403) 앞에 실행되어 거래 존재 여부 탐색 가능 | `pef_registry.py:110-111` |
| 9 | **SCHEMA-03** | Mod/HIGH | 50 | **FE 훅에 `limit` 파라미터 누락** — BE는 limit 1-200 지원하나 FE에서 전달 불가, 항상 기본 50건 | `usePefRegistry.ts:7-11` |
| 10 | **API-01** | Mod/HIGH | 40 | **`/pef-registry/count`에 search 필터 미반영** — 항상 전체 건수 반환, 페이지네이션 UI에 무의미 | `pef_registry.py:61-69` |
| 11 | **U-04** | Mod/HIGH | 40 | **모든 GP 추가 실패 시에도 모달 닫힘** — `added === 0`이어도 `onClose()` 호출 | `FIRecommendModal.tsx:77-80` |
| 12 | **U-02** | Mod/HIGH | 40 | **이미 추가된 GP `opacity-50`만으로 상태 구분 불명확** — badge도 함께 희미해짐 | `FIRecommendModal.tsx:133` |
| 13 | **TC-03** | Mod/HIGH | 40 | **Decimal 변환 실패 422 분기 미테스트** | `test_fi_mapping.py` |
| 14 | **TC-05** | Mod/HIGH | 40 | **gp2/gp3 전용 GP 경로 미테스트** — 모든 시드 데이터가 gp1만 설정 | `test_fi_mapping.py` |
| 15 | **TC-06** | Mod/HIGH | 40 | **`limit` 파라미터 동작 미테스트** | `test_fi_mapping.py` |
| 16 | **TQ-02** | Mod/MEDIUM ⚠️ | 24 | **DB 격리 취약** — `_seed_pefs`의 `commit()`이 세션 롤백 격리 깨뜨릴 수 있음 | `test_fi_mapping.py:54-55` |

### P3 — 저우선 (점수 <30)

| # | ID | 심각도/신뢰도 | 점수 | 요약 |
|---|-----|-------------|------|------|
| 17 | AUTH-03 | Mod/MEDIUM ⚠️ | 24 | CLIENT에게 FI 추천(GP 목록) 노출 — 의도 확인 필요 |
| 18 | A-03 | Mod/MEDIUM ⚠️ | 24 | disabled 체크박스 스크린리더 포커스 불가 |
| 19 | A-05 | Mod/MEDIUM ⚠️ | 24 | `opacity-50` WCAG AA 대비율 미충족 가능성 |
| 20 | TQ-01 | Mod/MEDIUM ⚠️ | 24 | `_create_txn` 고정 `target_company_name` 오염 위험 |
| 21 | LOG-001 | Minor/HIGH | 20 | `registration_date` String 사전순 비교 의존 |
| 22 | LOG-002 | Minor/HIGH | 20 | 입력값 검증이 DB 조회 이후 실행 |
| 23 | ERR-001 | Minor/HIGH | 20 | `deal_value=0` 빈 배열 반환 시 로그 없음 |
| 24 | DI-002 | Minor/HIGH | 20 | `unique_raw`/`unique_capitals` 집합 크기 불일치 가능성 |
| 25 | SEC-01 | Minor/HIGH | 20 | LIKE `escape="\\"` 절 누락 |
| 26 | AUTH-01 | Minor/HIGH | 20 | `pef_fund_count` CLIENT 접근 허용 비일관성 |
| 27 | VAL-01 | Minor/HIGH | 20 | `search` 파라미터 `max_length` 누락 |
| 28 | API-03 | Minor/HIGH | 20 | `matching_funds` nested 응답으로 불필요한 페이로드 |
| 29 | A-01 | Minor/HIGH | 20 | `<label>` 내 체크박스 `aria-label` 중복 |

*(Minor/MEDIUM 이하 8건 생략 — LOG-003, DI-003, SEC-02, AUTH-04, A-04, API-04, SCHEMA-02, PERF-04)*

---

## P1 이슈 상세

### [SCHEMA-01] Decimal→string 직렬화 vs FE number 타입 불일치 ★★★

**심각도**: Major | **신뢰도**: HIGH | **점수**: 80 (교차 검증 +10)
**검출 에이전트**: FE 타입 에이전트, API 스키마 에이전트 (2건 독립 검출)
**교차 검증**: CONFIRMED

**증거**:
- BE 스키마 `pef_registry.py:26`: `min_fund_size: Decimal`
- FE 타입 `pef_registry.ts:14`: `min_fund_size: number`
- 테스트에서 `float(a_cap["min_fund_size"])` 사용 → JSON 응답이 string임을 증명
- Pydantic v2 기본 직렬화: `Decimal` → `"1500.00"` (string)

**런타임 영향**:
```javascript
// FIRecommendModal.tsx:83-86
formatBillion("1500.00")       // v는 실제로 string
→ "1500.00" >= 10000           // JS: 1500 >= 10000 → false (우연히 정확)
→ "1500.00".toLocaleString()   // → "1500.00" (잘못됨, "1,500"이어야 함)
→ 출력: "1500.00억"            // 기대: "1,500억"
```

**영향 필드**: `min_fund_size`, `total_committed_sum`, `PefFundOut.total_committed_capital` (3개)

**수정 방향**:
- (A) BE: `FIRecommendation.model_config`에 `json_encoders={Decimal: float}` 추가
- (B) FE: 타입을 `string`으로 변경 + `formatBillion` 내부에서 `Number()` 변환

---

### [PERF-02] `registration_date` 인덱스 부재

**심각도**: Major | **신뢰도**: HIGH | **점수**: 80 (교차 검증 +10)
**검출 에이전트**: BE 로직 에이전트, API 성능 에이전트 (2건 독립 검출)
**교차 검증**: CONFIRMED — `pef_fund_registry.py:18-24` 인덱스 목록에 `registration_date` 없음

**현재 영향**: 1,137건 규모에서 무시 가능 (<1ms)
**미래 영향**: 데이터 증가 시 Full Table Scan 병목

---

### [PERF-01] 전체 테이블 메모리 로드 + String 날짜 비교

**심각도**: Major | **신뢰도**: HIGH | **점수**: 80 (교차 검증 +10)
**검출 에이전트**: BE 로직 에이전트, API 성능 에이전트 (2건 독립 검출)
**교차 검증**: CONFIRMED

**구조**:
1. `registration_date` = `String(10)` — ISO 8601 형식 전제 하에 사전순 비교가 우연히 정확
2. 필터 후 전체 PEF를 `list()`로 메모리 적재 → GP 그룹핑 → 범위 필터
3. gp1/gp2/gp3 멀티 컬럼 구조 때문에 SQL GROUP BY 직접 표현이 복잡하여 현 구조는 합리적 트레이드오프

---

### [TC-01] `estimated_deal_value` None/0/음수 분기 테스트 누락

**심각도**: Major | **신뢰도**: HIGH | **점수**: 70
**교차 검증**: CONFIRMED — `pef_registry.py:119,128` 분기에 대응 테스트 없음

**누락 시나리오**:
- `estimated_deal_value=None` → `[]` 반환
- `estimated_deal_value=0` → `[]` 반환
- `estimated_deal_value=-500` → `[]` 반환

---

### [TC-02] `lower_multiplier > upper_multiplier` 422 에러 테스트 누락

**심각도**: Major | **신뢰도**: HIGH | **점수**: 70
**교차 검증**: CONFIRMED — `pef_registry.py:113-117` 분기에 대응 테스트 없음

---

### [TC-04] `target_company_name` 기반 프로젝트 펀드 제외 테스트 누락

**심각도**: Major | **신뢰도**: HIGH | **점수**: 70
**교차 검증**: CONFIRMED — `pef_registry.py:144` 필터에 대응 테스트 없음

**누락 시나리오**:
- `pef_name`에 `target_company_name` 포함 → 자동 제외 확인
- `target_company_name` 1자 (길이 < 2) → 필터 스킵 확인

---

### [TC-07] `list_pef_funds`/`pef_fund_count` 엔드포인트 미커버

**심각도**: Major | **신뢰도**: HIGH | **점수**: 70
**교차 검증**: CONFIRMED — `test_fi_mapping.py`는 FI 매핑 전용. 별도 테스트 파일 필요.

---

## Methodology

- **Agents**: 5개 — BE 로직(4관점), 보안/인증(3관점), FE 타입/접근성/UX(3관점), 테스트(2관점), API/스키마/성능(3관점)
- **Perspectives**: 13개 (코드 정확성, 에러 처리, 데이터 무결성, 동시성, 보안, 인증/RBAC, 입력 검증, 타입 안전성, 접근성, UX 일관성, 테스트 커버리지, 테스트 품질, API 설계) + 2개 번외 (스키마 일관성, 성능)
- **Files scanned**: 7개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Major 7건 전량 검증
- **Backend availability**: deal-mgmt(available)

## 검증 투명성

### 검증 통계
- 에이전트 발견 총 이슈: 41건
- 중복 병합: 12건 (41 → 29건)
- 교차 검증 대상 (Major): 7건
  - CONFIRMED: 7건
  - FALSE_POSITIVE: 0건
- MEDIUM 신뢰도 하향: 8건 (점수 40% 감소)

### 중복 병합 내역

| 병합 ID | 원본 ID | 에이전트 |
|---------|--------|---------|
| SCHEMA-01 | T-01 + SCHEMA-01 | FE타입 + API스키마 |
| AUTH-02 | ERR-002 + AUTH-02 + API-02 | BE로직 + 보안 + API설계 |
| PERF-02 | DI-001 + PERF-02 | BE로직 + API성능 |
| PERF-01 | ASYNC-001 + PERF-01 | BE로직 + API성능 |
| SCHEMA-03 | T-03 + SCHEMA-03 | FE타입 + API스키마 |
