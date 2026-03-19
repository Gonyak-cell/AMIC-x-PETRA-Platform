# Code Review — Short-List Tier 동기화 (R2~R6 통합 리뷰)

> **Review Date**: 2026-03-09 13:54
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 커밋 `6ccfeed` + `1540ab8` — deal-mgmt BE + amic-platform FE
> **Method**: R1 기본 리뷰 완료 후, 미수행 5개 라운드(R2~R6) 통합 심층 리뷰
> **Quality Gates**: ruff(PASS) pytest(13/13 PASS) tsc(PASS)

## 리뷰 라운드 커버리지

| 라운드 | 그룹명 | 수행 세션 |
|--------|-------|----------|
| R1 | 전체 체크리스트 (§0~§8) | 1차 리뷰 (`20260309_1339`) |
| R2 | 보안 심층 (위협 모델링, 공격 표면) | **이번 리뷰** |
| R3 | 데이터 정합성 (데이터 흐름, API 계약) | **이번 리뷰** |
| R4 | 프로덕션 복원력 (에러 처리, 관찰 가능성) | **이번 리뷰** |
| R5 | 운영 & 코드 건강성 (성능, 배포, 의존성) | **이번 리뷰** |
| R6 | 비즈니스 & UX (도메인 로직, 테스트, 접근성) | **이번 리뷰** |

---

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| Critical | 0 | — | — |
| Major | 1 | HIGH: 1 | P1: 1 |
| Moderate | 1 | HIGH: 1 | P2: 1 |
| Minor | 6 | HIGH: 5 / MEDIUM: 1 | P3: 4 / P4: 2 |
| Info | 2 | HIGH: 2 | P5: 2 |
| **Total** | **10** | HIGH: **9** / MEDIUM: **1** | P1: **1** / P2: **1** / P3: **4** / P4: **2** / P5: **2** |

---

## Findings

### P1 — 스프린트 우선

#### [R3-01] bulk_add 경로에서 Tier→is_short_listed 동기화 누락 (잠재) — [Major/HIGH]

- **위치**: `deal-mgmt/app/services/si_mapping_service.py:305-312` (SI bulk), `:1180-1187` (VC bulk)
- **카테고리**: 데이터 정합성 (§4)
- **설명**: `bulk_add_to_buyers()`와 `bulk_add_vc_to_buyers()`에서 `BuyerCandidate` 직접 생성 시, Tier 필드를 설정하지 않으므로 **현재는** 정합성 문제 없음 (tier=None → is_short_listed=False 정확). 그러나 향후 bulk_add에 tier 파라미터가 추가되면 `buyers.py:148-154`의 add_buyer 패턴과 달리 동기화가 빠질 수 있다.
- **현재 영향**: 없음. 잠재적 리스크.
- **권장**: Tier 동기화 로직을 헬퍼 함수로 추출하여 add_buyer, update_buyer, bulk_add 모두에서 호출하도록 통일.

### P2 — 개선 권장

#### [R6-A11Y-05] 에러 배너가 버튼 영역 내부에 잘못 중첩됨 — [Moderate/HIGH]

- **위치**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx:293-308`
- **카테고리**: 접근성 & UX (§4)
- **설명**: 에러 배너(`isBuyersError || isOverviewError` 조건부)가 `<div className="flex items-center gap-2">` 내부(우측 버튼 영역)에 위치. ShortListViewToggle과 Excel 다운로드 버튼과 같은 flex row에 렌더링되어 레이아웃이 깨질 수 있음.
- **권장**: 에러 배너를 탭/버튼 영역 바깥(부모 div)으로 이동하여 전체 너비에서 표시.

### P3 — 저우선

#### [R3-02] tier + is_short_listed 동시 PATCH 시 tier가 우선 — [Minor/HIGH]

- **위치**: `deal-mgmt/app/routers/buyers.py:257-263`
- **카테고리**: 데이터 정합성 (§4)
- **설명**: `{"tier": "NOT_TARGET", "is_short_listed": true}` 전송 시 tier 동기화 로직이 `is_short_listed=False`로 덮어씀. FE에서 이런 불일치 payload를 보내는 코드는 없으나, API 계약 문서화 필요.

#### [R5-PERF-01] GridView/TimelineView sorted 배열 useMemo 미적용 — [Minor/HIGH]

- **위치**: `MarketingGridView.tsx:37-43`, `MarketingTimelineView.tsx:48-56`
- **카테고리**: 성능 (§3)
- **설명**: `[...buyers].sort(...)` 가 매 렌더링마다 실행. buyers 수가 수십~수백이라 실질 영향은 미미하나 패턴 일관성 개선 여지.

#### [R6-TEST-05] Tier/is_short_listed 불일치 시나리오 테스트 부재 — [Minor/HIGH]

- **위치**: `deal-mgmt/tests/test_short_list_promotion.py`
- **카테고리**: 테스트 완전성 (§2)
- **설명**: Tier=TIER_1인 상태에서 `is_short_listed=False`로 직접 PATCH하는 불일치 시나리오 테스트 없음. 의도적 허용이라면 해당 테스트 추가로 문서화 효과.

#### [R4-RES-02] Tier 동기화 시 명시적 로깅 부재 — [Minor/MEDIUM]

- **위치**: `deal-mgmt/app/routers/buyers.py:257-263`
- **카테고리**: 관찰 가능성 (§4)
- **설명**: Tier 변경 시 is_short_listed 자동 동기화에 대한 `logger.info/debug` 없음. 감사 로그에는 기록되나 애플리케이션 로그에서 즉시 확인 어려움.

### P4 — 참고

#### [R4-RES-03] FE 에러 배너 위치 문제 — [Minor/HIGH]

- R6-A11Y-05와 동일 이슈. 중복 제거, R6-A11Y-05로 통합.

#### [R5-PERF-02] FunnelKPIBar buyers 5회 순회 — [Minor/HIGH]

- **위치**: `FunnelKPIBar.tsx:43-64`
- 5개 step마다 `buyers.filter()` 호출. 단일 루프로 최적화 가능하나 buyers 수 기준 실질 영향 없음.

#### [R5-STRUCT-01] BuyersTab.tsx 510줄 — [Minor/MEDIUM]

- 상태 변수 10개 이상, Long List/Short List 두 서브탭 관리. lazy import와 Suspense 적절 사용. 추후 기능 추가 시 분할 고려 필요.

### P5 — 정보

#### [R2-SEC-01] Rate Limiting 미적용 — [Info/HIGH]

- buyers 라우터에 rate limiting 없음. 인증 필수 + deal access 제한으로 실질 위험 낮음. 프로덕션 규모 확대 시 검토.

#### [R6-BIZ-04] is_short_listed 직접 PATCH로 Tier 불일치 허용 — [Info/HIGH]

- 의도적 설계 (주석 + 테스트 존재). 비즈니스 관점에서 "Tier 없는 Short-List"가 유효한지 도메인 판단 필요.

---

## R2 보안 심층 — 검증 통과 항목

| 항목 | 결과 | 검증 근거 |
|------|------|----------|
| 인증/인가 전수 검사 (7 엔드포인트) | ✅ PASS | 읽기: `get_jwt_claims`, 쓰기: `require_write_access()` |
| Spoofing (인증 우회) | ✅ PASS | JWT verify_exp, 401 응답, AUTH_ENABLED 환경 제한 |
| Tampering (Tier 값 조작) | ✅ PASS | `BuyerTier(StrEnum)` + Pydantic 422 자동 거부 |
| Repudiation (감사 로그) | ✅ PASS | add/update/remove 모두 audit_service.record 호출 |
| Information Disclosure | ✅ PASS | 에러 응답에 내부 정보 미노출 |
| SQL 인젝션 | ✅ PASS | raw SQL 없음, ORM 사용 |
| 시크릿 노출 | ✅ PASS | 하드코딩 토큰/키 없음 |
| Elevation of Privilege | ✅ PASS | `check_client_deal_access`로 거래 범위 제한 |

## R3 데이터 정합성 — 검증 결과

| 항목 | 결과 |
|------|------|
| promote 잔존 참조 | ✅ 완전 제거 (Grep 0건) |
| BE↔FE Enum 동기화 (BuyerTier/Status/Type/DealRole) | ✅ 완전 일치 |
| BE Pydantic ↔ FE TypeScript 필드 (5 스키마) | ✅ 완전 일치 |
| Tier→is_short_listed 동기화 (단건 add/update) | ✅ 정상 |
| Tier→is_short_listed 동기화 (bulk) | ⚠️ 현재 문제 없으나 잠재 리스크 |
| 상태 전이 매트릭스 | ✅ 종단 상태 전이 차단 |
| Race Condition | ℹ️ last-write-wins (M&A 특성상 낮은 위험) |

## R4 프로덕션 복원력 — 검증 결과

| 항목 | 결과 |
|------|------|
| 트랜잭션 안전성 (flush→audit→commit) | ✅ PASS |
| 감사 로그 직렬화 (_sanitize_for_json) | ✅ PASS |
| FE 에러 핸들링 UI | ✅ PASS (위치 문제 별도 이슈) |
| Lazy Loading + Suspense | ✅ PASS |
| division by zero 방지 (FunnelKPIBar) | ✅ PASS |

## R5 운영 & 코드 건강성 — 검증 결과

| 항목 | 결과 |
|------|------|
| BE N+1 쿼리 | ✅ 없음 |
| FE buildStageMap useMemo | ✅ 적절히 캐시됨 |
| 마이그레이션 필요 여부 | ✅ 불필요 확인 |
| 환경변수 변경 | ✅ 변경 없음 |
| 무중단 배포 가능 | ✅ breaking change 없음 |
| 순환 의존성 | ✅ 없음 |

## R6 비즈니스 & UX — 검증 결과

| 항목 | 결과 |
|------|------|
| "Tier 1/2/3 = Short List" 규칙 | ✅ 정확히 구현 |
| NOT_TARGET → Short List 해제 | ✅ 정상 동작 |
| null Tier → Short List 해제 | ✅ 정상 동작 |
| 13개 테스트 — 행동 기반 검증 | ✅ 구현 세부 미검사 |
| 경계값/실패 경로 테스트 | ✅ 충분 |
| Mock 과용 | ✅ 없음 (실제 DB 사용) |
| aria-label 접근성 | ✅ FunnelKPIBar, StageTracker, 3개 뷰 |
| 로딩/빈 상태 처리 | ✅ EmptyState 일관 사용 |
| 에러 표시 (색상+텍스트) | ✅ 이중 표시 |

---

## 잘 된 점

1. **보안 견고**: 7개 엔드포인트 모두 인증/인가 + deal access 제한 완비
2. **STRIDE 전 항목 통과**: Spoofing, Tampering, Repudiation, InfoDisclosure, EoP 모두 적절히 대응
3. **트랜잭션 원자성**: flush→audit→commit 패턴으로 부분 커밋 방지
4. **BE↔FE 타입 완전 동기화**: 5개 스키마, 4개 Enum 모두 일치
5. **테스트 품질**: 행동 기반 통합 테스트, Mock 미사용, 경계값 커버
6. **접근성 양호**: aria-label, role, 색상+텍스트 이중 표시
7. **무중단 배포 가능**: 모델/마이그레이션/환경변수 변경 없음

---

## Methodology

- Agents: 3개 병렬 (R2+R4, R3, R5+R6)
- Files scanned: BE 8파일, FE 12파일 = 20파일
- Protocol: Verified Claim Protocol v1.1
- Quality Gates: ruff(PASS) pytest(13/13 PASS) tsc(PASS)
