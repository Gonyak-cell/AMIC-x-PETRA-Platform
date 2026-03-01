# Code Review — MA 6대 핵심 지시사항 (R2~R6 통합 심층 리뷰)

> **Review Date**: 2026-03-01 23:15
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 6대 핵심 지시사항 구현 — R2~R6 13개 리뷰 관점 통합
> **Method**: 5-Cluster Multi-Agent Parallel Review + Cross-Verification
> **Prior Review**: R1 기본 체크리스트 (31건 발견, 24건 수정 완료)

## 클러스터 구성

| 클러스터 | 라운드 | 관점 | 에이전트 |
|---------|--------|------|---------|
| A | R2 | 보안 심층 + 위협 모델링 | backend-security-reviewer |
| B | R3 | 데이터 정합성 + API 계약 | python-code-reviewer |
| C | R3/R5 | 마이그레이션 + 배포 안전성 | migration-validator |
| D | R4/R5 | 에러 처리 + 성능 | performance-profiler |
| E | R6 | 도메인 로직 + 테스트 + 가독성 + 접근성 | Explore |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 3 (1 unique + 2 dup) | HIGH: 3 | P0: 1 (2건 기지/보류) |
| Major | 14 (13 unique + 1 dup) | HIGH: 13 / MEDIUM: 0 | P1: 13 |
| Moderate | 18 (17 unique + 1 dup) | HIGH: 11 / MEDIUM: 5 / LOW: 1 | P2: 11 / P3: 6 |
| Minor | 8 (7 unique + 1 dup) | HIGH: 4 / MEDIUM: 3 | P3: 7 |
| **Total** | **43 raw → 38 unique** | HIGH: **31** / MEDIUM: **8** / LOW: **1** | P0: **1** / P1: **13** / P2: **11** / P3: **13** |

**교차 검증**: 중복 5건 — UUID(as_uuid=True) ×3, estimated_deal_value float ×2, FI no ORDER BY ×2, audit no logger ×2

---

## Priority Matrix

### P0 — 즉시 수정 (점수 90+)

| # | ID | 심각도/신뢰도 | 이슈 | 파일 | 점수 | 비고 |
|---|-----|-------------|------|------|------|------|
| 1 | C-A1 | Critical/HIGH | `estimated_deal_value` float 타입 → Decimal 필요 | transaction.py | 100 | FI 추천 정밀도 손상 |
| — | C-A2 | Critical/HIGH | `UUID(as_uuid=True)` PostgreSQL 전용 | transaction.py:16 | 100 | **기지 이슈 — 30+ 파일 동일, 보류** |
| — | MV-1 | Critical/HIGH | 046 downgrade MOU_SIGNED/MAIN_DD 데이터 유실 | 046_transaction_phase.py | 100 | **기지 이슈 — R1에서 보류 결정** |

### P1 — 스프린트 우선 (점수 60-89)

| # | ID | 심각도/신뢰도 | 이슈 | 파일 | 점수 |
|---|-----|-------------|------|------|------|
| 2 | M-B1 | Major/HIGH | Decimal → FE number 변환 시 정밀도 손실 (15자리 초과) | schemas/pef_registry.py | 70 |
| 3 | M-B2 | Major/HIGH | promote-short-list 후 contact 삭제 시 is_short_listed 유지 | buyers.py:158-220 | 70 |
| 4 | M-B3 | Major/HIGH | promote-short-list 감사+업데이트 원자성, race condition | buyers.py:158-220 | 70 |
| 5 | FI-ORD | Major/HIGH | FI 추천 결과 ORDER BY 없음 + 메모리 내 그룹핑 500건 | pef_registry.py | 80† |
| 6 | MV-2 | Major/HIGH | 046 `op.execute("COMMIT")` — Alembic 권장 패턴 위반 | 046_transaction_phase.py | 70 |
| 7 | MV-3 | Major/HIGH | 045/046 `op.execute()` raw string → `sa.text()` 미사용 | 045, 046 마이그레이션 | 70 |
| 8 | MV-4 | Major/HIGH | `Numeric(20,2)` — 프로젝트 표준 `NUMERIC(18,4)` 불일치 | pef_fund_registry.py | 70 |
| 9 | MV-5 | Major/HIGH | 045 downgrade: PostgreSQL enum 값 영구 잔존 | 045_ma_directives.py | 70 |
| 10 | PF-1 | Major/HIGH | 상태 전이 실패 시 로깅 없음 (디버깅 불가) | buyers.py:288 | 70 |
| 11 | PF-2 | Major/HIGH | DART 검색 — 과도 광범위 `except Exception` (실패 은폐) | buyer_marketing.py | 70 |
| 12 | PF-3 | Major/HIGH | `short_list_marketing_overview` 불필요 2단계 쿼리 | buyer_marketing.py | 70 |
| 13 | DL-1 | Major/HIGH | BuyerCandidateStatus 전이 규칙 — M&A 실무 유연성 부족 | buyers.py:37-55 | 70 |
| 14 | ICP-1 | Major/HIGH | `promote_short_list` 함수 CC=8~9 (권장 7 이하) | buyers.py:158-220 | 70 |

†교차 검증 보너스 +10 (Cluster B + D 동시 발견)

### P2 — 개선 권장 (점수 30-59)

| # | ID | 심각도/신뢰도 | 이슈 | 파일 | 점수 |
|---|-----|-------------|------|------|------|
| 15 | SEC-M1 | Moderate/HIGH | `buyer_marketing.py` 트랜잭션 존재 검증 누락 | buyer_marketing.py | 40 |
| 16 | SEC-M3 | Moderate/HIGH | PEF registry — CLIENT 역할 접근 제어 누락 | pef_registry.py | 40 |
| 17 | SEC-M4 | Moderate/HIGH | `AUTH_ENABLED=False` ENV 변수 보호 약함 | security.py | 40 |
| 18 | SEC-M5 | Moderate/HIGH | DART 검색 쿼리 `max_length` 없음 | buyer_marketing.py | 40 |
| 19 | m-C3 | Moderate/HIGH | `SHORT_LIST_STATUSES` — BID 3개 상태 누락 | constants/서비스 | 40 |
| 20 | MV-6 | Moderate/HIGH | 046 downgrade BIDDING_DD 복원 충돌 | 046_transaction_phase.py | 40 |
| 21 | MV-7 | Moderate/HIGH | 047 마이그레이션 PostgreSQL 전용 타입 | 047 마이그레이션 | 40 |
| 22 | PF-4 | Moderate/HIGH | Excel export 예외 처리 없음 | buyer_export_service.py | 40 |
| 23 | PF-5 | Moderate/HIGH | `audit_service.py` 로거 미정의 | audit_service.py | 40 |
| 24 | PF-6 | Moderate/HIGH | PEF 테이블 GP 검색 인덱스 없음 | pef_fund_registry.py | 40 |
| 25 | m-C1 | Moderate/HIGH | FI 추천 결과 비결정적 (ORDER BY 없음) | pef_registry.py | 40† |

†FI-ORD(P1)에 병합 가능

### P3 — 저우선 (점수 <30)

| # | ID | 심각도/신뢰도 | 이슈 | 파일 | 점수 |
|---|-----|-------------|------|------|------|
| 26 | m-C2 | Moderate/MEDIUM | audit `old_value` getattr 기본값 누락 | audit_service.py | 24 |
| 27 | PF-7 | Moderate/MEDIUM | WorkflowError vs DB 예외 미분리 | workflow_engine.py | 24 |
| 28 | PF-8 | Moderate/MEDIUM | `list_buyers` SELECT * 전 컬럼 로드 | buyers.py | 24 |
| 29 | SEC-M2 | Moderate/MEDIUM | Content-Disposition 파일명 RFC 5987 미준수 | buyer_marketing.py | 24 |
| 30 | DL-2 | Moderate/MEDIUM | Short-List 연락처 3개 필드 모두 필수 (email만으로 충분?) | buyers.py:186-194 | 24 |
| 31 | T-1 | Moderate/MEDIUM | 경계값 테스트 부재 (빈 리스트, 중복 승격, 부분 실패) | test_short_list_promotion.py | 24 |
| 32 | ICP-3 | Moderate/MEDIUM | `update_buyer` is_short_listed 검증 중첩 과도 | buyers.py:301-316 | 24 |
| 33 | SEC-L1 | Minor/HIGH | 에러 메시지에 내부 enum 값 노출 | buyers.py | 20 |
| 34 | SEC-L3 | Minor/HIGH | 빈 role 문자열 → `require_write_access` 우회 | security.py | 20 |
| 35 | SEC-L4 | Minor/HIGH | 전역 Rate Limiting 없음 | 전체 | 20 |
| 36 | L-D1 | Minor/MEDIUM | `ioi_date`/`loi_date` 형식 검증 없음 | schemas/buyer.py | 12 |
| 37 | SEC-L2 | Minor/MEDIUM | 에러 메시지에 Python 예외 텍스트 노출 | pef_registry.py | 12 |
| 38 | ICP-2 | Minor/MEDIUM | SI 매핑 파라미터 기본값 출처 불명확 | si_mapping_service.py | 12 |

---

## Findings (상세)

### P0: estimated_deal_value float → Decimal [C-A1]

**위치**: `deal-mgmt/app/models/transaction.py`
**클러스터**: B (데이터 정합성) + C (마이그레이션) — 교차 검증됨
**신뢰도**: HIGH

**문제**: `estimated_deal_value`가 Python `float` 타입 힌트를 사용. DB 컬럼은 `Numeric`이지만 Python 레이어에서 float 변환 시 부동소수점 정밀도 손실 발생.

**영향**: FI 추천 로직에서 `deal_value < capital < deal_value*5` 비교 시 잘못된 결과 가능. 100억 단위 거래에서 1원 미만 오차 누적.

**수정 방향**: `Mapped[Decimal | None]` + Pydantic 스키마에서 `Decimal` 타입 사용.

---

### P1 상세 (13건)

#### FI 추천 비결정적 + 메모리 과사용 [FI-ORD] (교차 검증)

**위치**: `deal-mgmt/app/routers/pef_registry.py`
**클러스터**: B + D — 동일 이슈 독립 발견
**신뢰도**: HIGH

**문제**: (1) ORDER BY 없이 쿼리 실행 → 동일 입력에 다른 결과 반환 가능, (2) 최대 500건 PEF를 메모리에 로드하여 GP별 그룹핑 → 대용량 시 성능 저하.

**수정 방향**: `.order_by(PefFundRegistry.total_committed_capital.desc())` 추가 + DB 레벨 GROUP BY.

#### 상태 전이 실패 시 로깅 없음 [PF-1]

**위치**: `deal-mgmt/app/routers/buyers.py:288`
**클러스터**: D (에러 처리)
**신뢰도**: HIGH

**문제**: 422 반환만 하고 `logger.warning()` 없음 → 실패 패턴 분석 불가, 악의적 상태 조작 시도 추적 불가.

#### BuyerCandidateStatus 전이 규칙 M&A 실무 유연성 [DL-1]

**위치**: `deal-mgmt/app/routers/buyers.py:37-55`
**클러스터**: E (도메인 로직)
**신뢰도**: HIGH

**문제**:
1. NDA_SIGNED → CIM_SENT 강제 (동시 발송 불가)
2. INTEREST_CONFIRMED 필수 (전략적 매수자 IOI 직접 제출 불가)
3. DD_GRANTED → DD_IN_PROGRESS 강제 (즉시 진행 불가)
4. BID_DROPPED — IOI_ACCEPTED에서만 진입 가능 (더 이른 단계 포기 불가)

**수정 방향**: 도메인 전문가 논의 후 선택적 단계 허용 또는 병렬 경로 추가.

#### promote_short_list 인지 복잡도 [ICP-1]

**위치**: `deal-mgmt/app/routers/buyers.py:158-220`
**클러스터**: E (가독성)
**신뢰도**: HIGH

**문제**: CC=8~9. 연락처 검증 로직 + 업데이트 로직 + 감사 기록이 단일 함수에 혼합. 50줄 초과.

**수정 방향**: `_validate_short_list_contacts()`, `_update_buyers_short_listed()` 서브 함수 추출.

#### DART 검색 silent failure [PF-2]

**위치**: `deal-mgmt/app/routers/buyer_marketing.py`
**클러스터**: D (에러 처리)
**신뢰도**: HIGH

**문제**: KIIS 외부 API 호출 실패 시 `except Exception: pass` 패턴으로 오류 은폐. 사용자에게 빈 결과만 반환되어 장애 인지 불가.

#### 마이그레이션 패턴 이슈 4건 [MV-2~5]

**클러스터**: C (마이그레이션)
**신뢰도**: HIGH

| ID | 이슈 | 위치 |
|----|------|------|
| MV-2 | `op.execute("COMMIT")` — Alembic `connection.execute(sa.text("COMMIT"))` 권장 | 046 |
| MV-3 | raw string → `sa.text()` 미사용 (SQLAlchemy 2.0 경고) | 045, 046 |
| MV-4 | `Numeric(20,2)` — 프로젝트 표준 `NUMERIC(18,4)` 불일치 | pef_fund_registry.py |
| MV-5 | PostgreSQL enum ADD VALUE 후 downgrade 불가 (문서화만 필요) | 045 |

---

## 검증된 안전 항목 (Verified OK)

5개 클러스터에서 **문제 없음 확인**된 항목:

| 카테고리 | 검증 항목 |
|---------|---------|
| **SQL Injection** | 모든 쿼리 파라미터화됨, raw string 결합 없음 |
| **IDOR** | `txn_id` + `buyer_id` 조합 검증, 크로스 트랜잭션 접근 차단 |
| **Mass Assignment** | Pydantic `exclude_unset=True`로 필드 선택적 업데이트 |
| **JWT** | `get_current_user` 주입 일관적 |
| **CORS** | 프로덕션 도메인만 허용 |
| **CLIENT RBAC** | 읽기 전용 접근 제한 |
| **감사 로깅** | `audit_service.record()` 일관적 호출 |
| **Hardcoded Secrets** | 발견 없음 |
| **Enum BE↔FE 동기화** | BuyerCandidateStatus 17개, TransactionPhase 9개 일치 |
| **STATUS_LABELS** | 17개 상태 전체 한글 레이블 정의 |
| **Transition Map** | 17개 상태 전체 커버 |

---

## Methodology

- **Agents**: backend-security-reviewer, python-code-reviewer, migration-validator, performance-profiler, Explore(R6)
- **Files scanned**: ~35개 (백엔드 20+, 프론트엔드 5+, 테스트 5+, 마이그레이션 3)
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 5건 중복 발견 → 교차 검증됨
- **Deduplication**: 43건 raw → 38건 unique

## 검증 투명성

### 검증 통계
- 에이전트별 보고 이슈: A=9, B=9, C=10, D=11, E=7 = **46건**
- 중복 제거: **5건** (UUID ×3, float ×2, ORDER BY ×2, logger ×2)
- 최종 unique 이슈: **38건**
- 기지 이슈 (이전 R1에서 보류): **2건** (UUID, 046 downgrade)

### 클러스터별 교차 검증

| 이슈 | 발견 클러스터 | 교차 검증 |
|------|------------|---------|
| `UUID(as_uuid=True)` | B, C, (R1) | ✓ 3회 독립 발견 |
| `estimated_deal_value` float | B, C | ✓ 2회 독립 발견 |
| FI 추천 ORDER BY | B, D | ✓ 2회 독립 발견 |
| `audit_service` 로거 | D (2곳) | 내부 중복 |
