# Code Review — FI 자동매핑 서비스 (deal-mgmt)

> **Review Date**: 2026-03-04 10:35 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: deal-mgmt FI 매핑 서비스 — fi_mapping_service.py, pef_registry.py (라우터/스키마), 관련 모델/유틸
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review (5 agents) + Cross-Verification + Auto-Verification
> **Quality Gates**: ruff(PASS) pytest-collect(PASS/1546 tests)
> **Review Gates**: Backend(deal-mgmt available) Agent-Filtering(5개 에이전트 호출, 0개 제외)

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical→Major | 1 | HIGH: 1 | P0: 1 |
| Warning | 7 | HIGH: 4 / MEDIUM: 2 / LOW: 1 | P2: 5 / P3: 2 |
| Moderate | 6 | HIGH: 2 / MEDIUM: 4 | P2: 2 / P3: 4 |
| Minor | 8 | HIGH: 3 / MEDIUM: 5 | P3: 8 |
| **Total** | **22** | HIGH: **10** / MEDIUM: **11** / LOW: **1** | P0: **1** / P2: **7** / P3: **14** |

**FP Prevention**: 가설 28건 검증, 6건 사전 거부 (거부율: 21%) | 교차 검증 6건 수행 (Critical/Major 3건 + Warning 3건)

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- Phase 2 교차 검증: Critical 2건 → Major 1건 + Warning 1건으로 하향, 1건 PARTIAL 판정
- Phase 2B 자동 검증: 16건 중 14건 verified, 2건 flagged (우선순위 1단계 하향)

---

## Priority Matrix

### P0 — 즉시 수정 (점수: 90+, 감사 추적성)

**1. [D1/S1/E2] 감사 로그 DB 미저장 — commit 누락 — [Major/HIGH] (점수: 95)**
- **파일**: `deal-mgmt/app/routers/pef_registry.py:244-255`
- **교차 검증**: 3개 에이전트(R2, R3, R4) 독립 발견 + review-verifier CONFIRMED
- **증거**:
  ```python
  # pef_registry.py:244-255 — audit 호출 후 commit 없음
  try:
      await audit_service.record(db, ...)  # db.add(log)만 수행
  except Exception:
      logger.exception("FI 추천 감사 로그 기록 실패")
  return results  # ← commit 없이 반환
  ```
  - `audit_service.record()` docstring(95행): "커밋은 호출 측에서"
  - `database.py` `get_db()`: auto-commit 아님, session.close()만 수행
  - 대조: `compliance.py:120-130`, `bids.py:104` 등 다른 라우터는 모두 `await db.commit()` 후 audit 또는 audit 후 commit
- **영향**: FI 추천 조회 감사 로그가 DB에 저장되지 않음. 기능 장애는 아니나 감사 추적성 완전 손실
- **수정 방향**: `audit_service.record()` 호출 후 `await db.commit()` 추가. 단, 읽기 전용 경로이므로 audit 전용 commit

⚠️ 원래 Critical로 보고되었으나, 교차 검증에서 "기능 장애 아닌 감사 추적 문제"로 Major/HIGH로 하향. 3개 에이전트 교차 검증(+10) + verifier 확인(+15)으로 P0 유지.

---

### P2 — 개선 권장 (점수: 30-59)

**2. [B4] 테스트 assertion 문자열 불일치 — CI 실패 가능 — [Warning/HIGH] (점수: 55)**
- **파일**: `deal-mgmt/tests/test_fi_mapping.py:390`
- **교차 검증**: review-verifier CONFIRMED
- **증거**:
  - 테스트 기대: `assert "최소 펀드 약정총액" in reason`
  - 현재 코드 출력: `f"최소 약정분담액 {_format_billions(min_size)}"`
  - GP count 보정 수정 시 match_reason 텍스트가 변경되었으나 테스트가 동기화되지 않음
- **수정 방향**: 테스트의 assert 문자열을 `"최소 약정분담액"`으로 업데이트

**3. [B2] multi-GP per_gp 분담액 계산 테스트 부재 — [Warning/HIGH] (점수: 55)**
- **파일**: `deal-mgmt/tests/test_fi_mapping.py`
- **교차 검증**: review-verifier CONFIRMED
- **증거**:
  - `fi_mapping_service.py:196-198`: `per_gp = f.total_committed_capital / max(gp_count, 1)` — 핵심 비즈니스 로직
  - 테스트에서 gp1+gp2 또는 gp1+gp2+gp3가 설정된 펀드의 per_gp 값을 검증하는 케이스 없음
  - `test_gp_only_in_gp2_or_gp3`(591행)는 gp_count=1 케이스만 테스트
- **수정 방향**: gp_count=2, gp_count=3 케이스의 min_fund_size, total_committed_sum 검증 테스트 추가

**4. [S3/P4] InMemory Rate Limiter 멀티 워커 bypass — [Moderate/HIGH] (점수: 50)**
- **파일**: `deal-mgmt/app/core/rate_limiter.py:69`
- **교차 검증**: 2개 에이전트(R2, R5) 독립 발견
- **증거**:
  - 클래스 docstring에 이미 경고 문서화: "다중 워커 환경에서는 ... max_calls × 워커 수"
  - 현재 프로덕션: `--workers 1` → 즉각 위험 없음
  - 스케일업 시 Redis 기반 분산 rate limiter 전환 필요
- **수정 방향**: 현재 상태 유지 (이미 문서화됨). 워커 증가 시 Redis 전환 계획

**5. [S4/D2/E3] GP 프로필 캐시 멀티 워커 불일치 — [Moderate/MEDIUM] (점수: 34)**
- **파일**: `deal-mgmt/app/services/fi_mapping_service.py:60-64`
- **교차 검증**: 3개 에이전트(R2, R3, R4) 독립 발견
- **증거**: 모듈 레벨 `_gp_cache`가 프로세스별 독립적. asyncio.Lock은 동일 프로세스 내 동기화만
- **수정 방향**: M2와 동일 — 현재 단일 워커에서는 문제 없음. 문서화로 충분

**6. [D3] Numeric 정밀도 불일치 (20,2 vs 20,4) — [Moderate/HIGH] (점수: 40)**
- **파일**: `deal-mgmt/app/models/transaction.py:36` vs `deal-mgmt/app/models/pef_fund_registry.py:35`
- **증거**: `estimated_deal_value: Numeric(20, 2)` vs `total_committed_capital: Numeric(20, 4)`. 비교는 Python Decimal에서 수행되므로 현재 기능 문제 없음
- **수정 방향**: 설계 일관성 관점. 실질 영향 없음

**7. [B1] total_committed_sum 필드 의미 변경 — [Warning/MEDIUM] (점수: 39)**
- **파일**: `deal-mgmt/app/services/fi_mapping_service.py:231`
- **교차 검증**: review-verifier DESIGN_RISK (Critical → Warning 하향)
- **증거**:
  - `total_sum = sum(unique_capitals)` — unique_capitals에는 per_gp 값이 들어감
  - FE `FIRecommendModal.tsx:196`: `총약정 {formatBillion(rec.total_committed_sum)}` 라벨 사용
  - GP 관점 분담액 합계는 설계 의도에 부합하나, "총약정"이라는 FE 라벨과 의미 차이 존재
- **수정 방향**: FE 라벨을 "GP 분담액 합계" 등으로 변경 검토. 코드 로직 자체는 정상

**8. [M8/E5] GP 프로필 0건 시 빈 캐시 1시간 지속 — [Moderate/MEDIUM] (점수: 24)**
- **파일**: `deal-mgmt/app/services/fi_mapping_service.py:109-118`
- **증거**: DB에서 0건 반환 시 `_gp_cache = {}` → `is not None` 통과 → TTL 동안 빈 캐시 유지
- **수정 방향**: 0건 시 shorter TTL 적용 또는 캐시 저장 건너뛰기

---

### P3 — 저우선 (점수: <30)

| # | ID | 심각도/신뢰도 | 설명 | 파일 | 점수 |
|---|-----|-------------|------|------|------|
| 9 | D4 | Warning/LOW | fund_count vs matching_funds 길이 불일치 가능 (현재 호출 경로에서는 SQL 필터로 방어됨) | fi_mapping_service.py:251 | 27 |
| 10 | M1/S2 | Moderate/MEDIUM | JSONB email partial matching (2차 Python 필터로 방어됨) | approvals.py:238 | 24 |
| 11 | M7/E4 | Moderate/MEDIUM | target_company_name 공백 미트림 | pef_registry.py:204 | 24 |
| 12 | M6/D5/B10 | Moderate/MEDIUM | normalized_name 충돌 가능 / gp_map raw vs normalized key | fi_mapping_service.py:116,176 | 24 |
| 13 | M4/S5 | Moderate/MEDIUM | target_keywords 개수 제한 없음 (max_length=500 물리적 상한 존재) | pef_registry.py:145 | 24 |
| 14 | m8/E1 | Minor/HIGH | model_validate ValidationError 미처리 (발생 확률 극히 낮음) | fi_mapping_service.py:241,249 | 20 |
| 15 | m5/P7 | Minor/HIGH | registration_date String 비교 (의도적 설계, YYYY-MM-DD 보장 시 정확) | pef_fund_registry.py:31 | 20 |
| 16 | m2/S8 | Minor/MEDIUM | Service token aud claim 미검증 | security.py:168,177 | 12 |
| 17 | m3/B5 | Minor/MEDIUM | _strip_paren 내부 함수 호출마다 재생성 (성능 영향 무시 가능) | fi_mapping_service.py:129 | 12 |
| 18 | m6/B6 | Minor/MEDIUM | _FI_DATE_CUTOFF 하드코딩 (네이밍된 상수로 이미 정의) | pef_registry.py:39 | 12 |
| 19 | m7/B8 | Minor/MEDIUM | _GP_CACHE_TTL 하드코딩 (네이밍된 상수로 이미 정의) | fi_mapping_service.py:63 | 12 |
| 20 | m1/S6 ⚠️ | Minor/HIGH | AUTH_ENABLED 오타 위험 — **자동 검증 flagged**: fail-secure 기본값으로 정상 동작 | security.py:58 | 10 |
| 21 | m4/D6 ⚠️ | Minor/HIGH | FE/BE 인터페이스명 불일치 — **자동 검증 flagged**: 필드 구조 완전 일치, 이름만 다름 | pef_registry.ts:23 | 10 |
| 22 | E1-partial | Warning/LOW | model_validate 예외 시 500 반환 (스키마-모델 완전 매칭 상태에서 발생 불가) | fi_mapping_service.py:241 | 12 |

---

## 계획 대비 구현 검증 (§6)

> 이전 세션 플랜(`humble-crafting-trinket.md`) 기반 검증

| # | 계획된 항목 | 구현 상태 | 검증 근거 |
|---|-----------|---------|---------|
| 1 | GP수 보정 (total_committed_capital / gp_count) | ✅ 구현 | fi_mapping_service.py:196-198 — `per_gp = f.total_committed_capital / max(gp_count, 1)` |
| 2 | 괄호 키워드 정규화 (_strip_paren) | ✅ 구현 | fi_mapping_service.py:129-134 — `re.sub(r"\s*\([^)]*\)\s*", "", s)` |
| 3 | match_reason 텍스트 변경 | ✅ 구현 | fi_mapping_service.py:234 — `"최소 약정분담액"` |
| 4 | 테스트 동기화 | ❌ 미완료 | test_fi_mapping.py:390 — "최소 펀드 약정총액" assert 미갱신 (B4) |
| 5 | multi-GP 테스트 추가 | ❌ 미완료 | gp_count=2,3 케이스 테스트 부재 (B2) |
| 6 | FE 변경 불필요 | ✅ 확인 | FE 타입 필드 구조 일치, 라벨만 검토 필요 |

---

## 품질 게이트 상태 (§7)

| 품질 게이트 | 상태 | 리뷰 영향 |
|------------|------|----------|
| ruff check | ✅ PASS | §1 정합성 자동 검증됨 |
| ruff format | ✅ PASS | §1 정합성 자동 검증됨 |
| pytest collect | ✅ 1546 tests | §2 완전성 수집 확인 (실행은 미실시) |

---

## Passed Checks (이상 없음 확인 항목)

- [x] SQL Injection 없음 — SQLAlchemy 파라미터 바인딩, LIKE escape 처리
- [x] 하드코딩된 시크릿 없음 — JWT, DB URL 모두 환경변수
- [x] Decimal 사용 올바름 — `Decimal(str(...))` 패턴, `field_serializer`로 직렬화
- [x] N+1 쿼리 없음 — GP 프로필 1회 전체 로드 후 딕셔너리 처리
- [x] TTL 캐시 + 이중 확인 락 — 올바른 double-check locking 패턴
- [x] RBAC 적용 — `require_role("ADMIN", "MANAGER", "ANALYST")`, CLIENT 제외
- [x] 감사 로그 실패 격리 — `except Exception` + 로그 후 정상 반환
- [x] 구조화된 로깅 — txn_id, target_amount, elapsed 등 컨텍스트 포함
- [x] Pydantic v2 패턴 — `ConfigDict(from_attributes=True)`, `model_validate`
- [x] 페이지네이션 적용 — skip/limit 구현
- [x] Async/await 일관성 — 모든 DB 접근 await 사용
- [x] snake_case/PascalCase 준수

---

## Methodology

- **Agents**: R2(보안+위협모델링), R3(데이터정합성+API계약), R4(프로덕션복원력), R5(성능+배포+의존성), R6(도메인로직+테스트+가독성)
- **Excluded Agents**: 없음 (deal-mgmt 백엔드 available)
- **Files scanned**: fi_mapping_service.py, pef_registry.py(라우터), pef_registry.py(스키마), pef_fund_registry.py(모델), gp_profile.py, transaction.py, audit_service.py, rate_limiter.py, security.py, database.py, config.py, approvals.py, compliance.py, bids.py, test_fi_mapping.py, pef_registry.ts
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: Critical 3건 + Warning 3건 = 6건 교차 검증 수행
- **Auto-verification**: Moderate 8건 + Minor 8건 = 16건 자동 검증 (14건 verified, 2건 flagged)

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 28건
- 거부된 가설 (사전 제거): 6건
- 보고된 이슈: 22건
- 거부율: 21%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| 반증됨 | 2 | "ANALYST 접근 불가" → RBAC 확인 시 ANALYST 포함, "UUID 노출 보안 위험" → UUID 자체는 비밀 아님 |
| 이미 수정됨 | 1 | 이전 세션에서 GP count 보정 이미 구현 |
| 오판 | 1 | "fi_recommendations 404 미반환" → transaction_service가 HTTPException(404) 발생, SQLAlchemyError catch에 걸리지 않음 |
| 신뢰도 불충분 | 2 | 증거 약함 — 추측성 주장 |

### Phase 2 교차 검증 결과

| Issue | 원본 심각도 | 판정 | 조정 심각도 | 핵심 이유 |
|-------|-----------|------|-----------|----------|
| D1/S1/E2 | Critical/HIGH | CONFIRMED | Major/HIGH | 3개 에이전트 교차 확인. 기능 장애 아닌 감사 추적 문제로 하향 |
| B1 | Critical/HIGH | DESIGN_RISK | Warning/MEDIUM | GP 분담액 합계는 의도된 설계. FE 라벨 차이만 존재 |
| E1 | Critical/HIGH | PARTIAL | Warning/LOW | 스키마-모델 완전 매칭으로 발생 확률 극히 낮음 |
| D4 | Warning/HIGH | CONFIRMED | Warning/LOW | 현재 호출 경로에서 SQL 사전 필터로 방어됨 |
| B4 | Warning/HIGH | CONFIRMED | Warning/HIGH | 테스트 문자열 불일치 확정 |
| B2 | Warning/HIGH | CONFIRMED | Warning/HIGH | 핵심 비즈니스 로직 테스트 부재 확정 |

### Phase 2B 자동 검증 결과

| 판정 | 건수 | 비율 |
|------|------|------|
| verified | 14건 | 87.5% |
| flagged | 2건 | 12.5% |

Flagged 이슈:
- m1 (AUTH_ENABLED 오타): fail-secure 기본값으로 정상 동작 — 취약점 아님 (60/100)
- m4 (FE/BE 인터페이스명): 필드 구조 완전 일치, 이름만 다름 — 기능 이슈 아님 (65/100)
