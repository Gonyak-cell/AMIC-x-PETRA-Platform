# Code Review (Post-Fix) — FI 자동매핑: 수정 후 13개 관점 통합 리뷰

> **Review Date**: 2026-03-04 12:16 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI 매핑 서비스 — 수정 후 전체 파일 (BE 6개 + FE 10개)
> **Method**: 3-Agent Parallel Review + Cross-Verification
> **Agents**: python-code-reviewer (§1~6,10), general-purpose/FE (§1,7,11~13), migration-validator (§8~9)
> **선행 리뷰**: `20260304_1035` (1차) + `20260304_1101` (보충) + 수정 적용 후

---

## Summary

| Severity | Count | Confidence | Priority |
|----------|-------|------------|----------|
| High | 0 | — | — |
| Moderate | 0 | — | — |
| Warning | 2 | HIGH: 2 | P2: 1 / P3: 1 |
| Low/Suggestion | 4 | HIGH: 3 / MEDIUM: 1 | P3: 4 |
| **Total (유효 신규)** | **6** | — | P2: **1** / P3: **5** |

**교차 검증**: 3개 에이전트 총 22건 보고 → 4건 FP 제거, 6건 기존 발견/범위 외, 6건 Info/PASS → **6건 유효 신규**
**블로커 이슈: 없음** — 배포 차단 사유 없음

---

## 교차 검증 결과

| ID | 에이전트 | 판정 | 사유 |
|----|---------|------|------|
| BE-H01/MIG-§9-1 | BE + Migration | 기존 보고 | 보충 리뷰 M-02/M-03과 동일 — 단일 워커에서 허용 |
| BE-W02 | BE | PASS | 404 응답 선언 확인 완료, 이슈 없음 |
| BE-W03 | BE | **FP-LOGIC** | Python 3.10+ asyncio.Lock은 생성 시 루프에 바인딩되지 않음 |
| BE-W04 | BE | Info | Co-GP total_committed_sum은 도메인 특성 — "총약정"으로 정확 |
| BE-S01 | BE | PASS | `_format_billions` 호출자가 이미 > 0 검증 |
| BE-S02 | BE | Info | downgrade() 주석 보강 제안 — 051과 동일 수준이면 충분 |
| MIG-§8-1~§8-5 | Migration | 전체 PASS | 061 마이그레이션 안전성 확인 완료 |
| MIG-§8-3 | Migration | 범위 외 | 005_phase5a는 기존 파일, 이번 수정 범위 아님 |
| MIG-§9-2~§9-3 | Migration | PASS | double-check locking 정상, 순환 의존 없음 |
| MIG-§9-4 | Migration | Info | deploy.yml이 마이그레이션을 코드 배포 전 실행 — 안전 |
| FE-S1-1~S1-3 | FE | PASS | DataTable header ReactNode, formatBillions import, BadgeVariant 모두 정상 |
| FE-S7-1~S7-2 | FE | PASS | BE↔FE 타입 계약 완전 일치 |
| FE-S12-2 | FE | Info | BuyersTab useState 9개 — 이미 하위 컴포넌트 분리됨 |
| FE-S13-4 | FE | PASS | FIRecommendModal a11y 양호 |

---

## 유효 신규 발견

### P2 — 개선 권장

#### [S11-1] MA 모듈 프론트엔드 테스트 전면 부재

- **관점**: §11 테스트 커버리지
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 40
- **범위**: `amic-platform/src/modules/ma/` (전체)

`modules/ma/` 하위에 `*.test.ts`, `*.test.tsx` 파일이 0개. 특히:
- `formatBillions` — 경계값(0, 9999, 10000, NaN, null) 동작 미검증
- `FIRecommendModal` — expanded state 토글, 기존 GP 필터링 로직 미검증

**권장**: 최소한 `format.test.ts`에 `formatBillions` 순수 함수 단위 테스트 작성.

---

### P3 — 저우선

#### [W-01] `normalized_name` 컬럼에 UNIQUE 제약 없음

- **관점**: §3 데이터 무결성
- **심각도/신뢰도**: Warning / HIGH
- **우선순위 점수**: 40 → P3 (운영 데이터 분석 선행 필요)
- **파일**: `deal-mgmt/app/models/gp_profile.py:30`

`raw_name`에는 `unique=True`이나 `normalized_name`에는 없음. `normalize_gp_name()`이 "(주)알파자산운용"과 "알파자산운용"을 동일하게 정규화하면 `_load_gp_profiles` 딕셔너리에서 하나가 덮어쓰여짐.

**권장**: 현재 GP 데이터에서 normalized_name 중복이 있는지 확인 후 판단.

#### [S13-1] ConsortiumPanel 삭제 — 확인 절차 부재 (A11Y-6 수정 트레이드오프)

- **관점**: §13 접근성 & UX
- **심각도/신뢰도**: Low / MEDIUM
- **우선순위 점수**: 12
- **파일**: `ConsortiumPanel.tsx:289`

A11Y-6 수정으로 `window.confirm` 제거 후 즉시 삭제 실행. `useDeleteConsortiumMapping` 훅 내 toast 피드백은 존재. 비가역적 삭제에 확인 절차 없음은 UX 리스크이나, `window.confirm`의 접근성 문제(스크린 리더 차단)와의 트레이드오프.

**향후 개선**: 커스텀 확인 Modal 또는 toast + undo 패턴 도입 고려.

#### [S13-2] ConsortiumPanel 삭제 버튼 `aria-label` 부재

- **관점**: §13 접근성
- **심각도/신뢰도**: Low / HIGH
- **우선순위 점수**: 20
- **파일**: `ConsortiumPanel.tsx:285-291`

아이콘 전용 `<button>`에 `title="삭제"`만 있고 `aria-label` 없음. WCAG 2.1 AA "Name, Role, Value" (4.1.2) 위반 가능.

**권장**: `aria-label="컨소시엄 매핑 삭제"` 추가.

#### [H-02] 테스트 Decimal 비교에 `float()` 사용

- **관점**: §3 데이터 무결성 (테스트)
- **심각도/신뢰도**: Suggestion / HIGH
- **우선순위 점수**: 20
- **파일**: `test_fi_mapping.py:236, 360, 952`

`float(rec["min_fund_size"]) == 500.0` 패턴 사용. API가 Decimal→str 직렬화하므로 `float("500") == 500.0`은 통과하지만, 금융 값 비교는 `Decimal(str_val) == Decimal("500")`이 더 정확.

#### [S12-1] FIRecommendModal 카드 렌더링 컴포넌트 추출 권장

- **관점**: §12 인지 복잡도
- **심각도/신뢰도**: Low / HIGH
- **우선순위 점수**: 20
- **파일**: `FIRecommendModal.tsx:151-283`

`recommendations.map()` 내부 카드 렌더링이 130줄. `FIRecommendCard` 컴포넌트로 추출 시 가독성 개선.

#### [S13-3] MarketingStageTracker `role="img"` 시맨틱

- **관점**: §13 접근성
- **심각도/신뢰도**: Low / MEDIUM
- **우선순위 점수**: 12
- **파일**: `MarketingStageTracker.tsx:33`

compact 모드 dot에 `role="img"` 사용. 진행률 표현에는 `role="progressbar"` 또는 부모 그룹에 `role="img"`가 더 적절하나, 현재 구현도 스크린 리더에서 동작.

---

## 13개 관점 커버리지 현황

| # | 관점 | 결과 | 이슈 |
|---|------|------|------|
| §1 | 정합성 | ✅ PASS | 타입 힌트, import, ReactNode 변경 모두 호환 |
| §2 | 완전성 | ✅ PASS | 에지 케이스 처리 정상 |
| §3 | 데이터 무결성 | ⚠️ P3 | W-01(normalized_name), H-02(test Decimal) |
| §4 | 보안 | ✅ PASS | SQL injection 없음, 인증 RBAC 정상, 시크릿 미노출 |
| §5 | 에러 처리 | ✅ PASS | 예외 전파, HTTP 상태코드, 감사 로그 try/except 보호 |
| §6 | 성능 | ✅ PASS | N+1 없음, 단일 쿼리 + 인메모리 처리, 캐시 TTL |
| §7 | API 계약 | ✅ PASS | BE↔FE 타입 완전 일치 (8/8 필드) |
| §8 | 배포 안전성 | ✅ PASS | 061 마이그레이션 안전, 체인 정확, dialect 체크 |
| §9 | 의존성 & 결합도 | ✅ PASS | 단방향 의존, 순환 없음, double-check locking 정상 |
| §10 | 도메인 정합성 | ✅ PASS | 억원 단위, Tier 분류, GP 매칭 로직 정상 |
| §11 | 테스트 커버리지 | ⚠️ P2 | S11-1(MA 모듈 FE 테스트 부재) |
| §12 | 인지 복잡도 | ⚠️ P3 | S12-1(카드 추출 권장) |
| §13 | 접근성 & UX | ⚠️ P3 | S13-1~3(삭제 확인, aria-label, role 시맨틱) |

---

## 기존 보고 대비 변경 사항

### 수정 완료 확인 (이번 세션)

| 이슈 | 수정 상태 | 검증 |
|------|---------|------|
| H-01 AuditAction.READ | ✅ 061 마이그레이션 생성 | 체인/구문/dialect 모두 검증 통과 |
| SMELL-03 Feature Envy | ✅ 서비스 레이어 이동 | `parse_industry_keywords` 함수 추출 |
| SMELL-07 dict 타입 힌트 | ✅ `dict[str, object]` | replace_all 적용 |
| UX-1 Tier 2 뱃지 | ✅ Badge variant="info" | FIRecommendModal |
| A11Y-2 aria-disabled | ✅ 제거 | disabled 속성만 사용 |
| UX-7 opacity | ✅ bg-bg-muted | WCAG 대비 보장 |
| UX-2 gp_profile | ✅ 섹터 태그 UI | max 4 + overflow |
| UX-6 matching_funds | ✅ 펼치기/접기 | ChevronDown/Up |
| UX-4 formatBillions | ✅ format.ts 추가 | 억→조 자동 변환 |
| A11Y-3 DataTable 헤더 | ✅ sr-only "Short-List" | Column.header ReactNode |
| A11Y-5 StageTracker | ✅ role="img" + aria-label | compact 모드 dot |
| A11Y-6 window.confirm | ✅ 제거 | 직접 삭제 + hook toast |
| A11Y-4 Badge 통합 | ✅ BuyerTierBadge/DealRoleBadge | 공유 Badge 활용 |

### 린트/타입 검증

```
ruff check (BE): All checks passed!
tsc --noEmit (FE): 통과 (에러 0건)
```

---

## Methodology

- **에이전트**: python-code-reviewer, general-purpose (FE), migration-validator
- **파일 스캔**: BE 6개 + FE 10개 = 16개 파일
- **프로토콜**: Verified Claim Protocol v1.1
- **교차 검증**: 22건 보고 → 6건 유효 신규, 4건 FP, 6건 기존/범위 외, 6건 PASS/Info
