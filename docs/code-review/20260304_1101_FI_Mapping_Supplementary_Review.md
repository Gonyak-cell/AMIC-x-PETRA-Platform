# Code Review (Supplementary) — FI 자동매핑 서비스: 미수행 관점 보충 리뷰

> **Review Date**: 2026-03-04 11:01 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: FI 매핑 서비스 — 관점 8(배포안전성), 9(의존성&결합도), 12(인지복잡도&가독성), 13(접근성&UX)
> **Method**: 4-Agent Parallel Review + Cross-Verification
> **선행 리뷰**: `20260304_1035_FI_Mapping_Service_Code_Review.md` (관점 1~7, 10~11 커버)

---

## 보충 리뷰 배경

선행 13-관점 리뷰에서 아래 4개 관점이 미수행 또는 얕은 수준으로 확인되어 보충 리뷰를 수행하였다.

| 관점 | 선행 커버리지 | 보충 에이전트 |
|------|------------|-------------|
| §8 배포 안전성 | ⚠️ 얕음 | backend-security-reviewer |
| §9 의존성 & 결합도 | ❌ 미수행 | backend-security-reviewer |
| §12 인지 복잡도 & 가독성 | ⚠️ 얕음 | python-code-reviewer |
| §13 접근성 & UX 일관성 | ❌ 미수행 | general-purpose (FE 전문) |

추가로 수정 검증 에이전트(python-code-reviewer)가 선행 리뷰 수정 사항 7건의 정합성을 검증하였다.

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1 (FP) | — | — |
| High | 1 | HIGH: 1 | P0: 1 |
| Major | 1 | HIGH: 1 (mitigated) | P2: 1 |
| Moderate | 5 | HIGH: 5 | P2: 2 / P3: 3 |
| Minor/Suggestion | 15 | HIGH: 10 / MEDIUM: 5 | P3: 15 |
| **Total (유효)** | **22** | — | P0: **1** / P2: **3** / P3: **18** |

**교차 검증**: Critical 1건 FP 제거, High 3건 중 2건 FP 제거
**수정 검증**: 선행 리뷰 7/7건 수정 완료 확인, 회귀 1건 발견 및 수정

---

## 수정 검증 결과 (선행 리뷰 수정 사항)

| # | 이전 이슈 | 수정 상태 | 검증 근거 |
|---|---------|---------|---------|
| 1 | **D1/S1/E2** — audit commit 누락 (P0) | ✅ | `pef_registry.py:254` — `await db.commit()` 추가 확인 |
| 2 | **B4** — 테스트 match_reason 텍스트 불일치 | ✅ | `fi_mapping_service.py:238` — "최소 펀드 약정총액" 텍스트 복원 |
| 3 | **S6** — `_strip_paren` 인라인 정의 | ✅ | `fi_mapping_service.py:92` — 모듈 레벨로 이동 확인 |
| 4 | **S7** — per_gp 분담 로직 (사용자 지시 복원) | ✅ | `fi_mapping_service.py:198` — `total_committed_capital` 직접 사용 |
| 5 | **D3** — target_company_name strip 누락 | ✅ | `pef_registry.py:204-206` — `.strip()` 추가 확인 |
| 6 | **M1** — GP 프로필 0건 시 캐시 TTL | ✅ | `fi_mapping_service.py:117` — 60초 단축 TTL 적용 |
| 7 | Co-GP 테스트 추가 | ✅ | `test_fi_mapping.py:916-944` — Co-GP 시나리오 테스트 확인 |

### 회귀 발견 및 수정

**R-02**: Co-GP 테스트에서 `assert rec["min_fund_size"] == 1500` (int 비교)으로 작성했으나, `FIRecommendationV2` 스키마의 `@field_serializer`가 Decimal을 str로 직렬화함.
- **수정**: `assert float(rec["min_fund_size"]) == 1500.0`으로 변경 완료

---

## P0 — 즉시 수정 (배포 안전성)

### [H-01] AuditAction.READ — PostgreSQL enum 미등록 (프로덕션 크래시 위험)

- **관점**: §8 배포 안전성
- **심각도/신뢰도**: High / HIGH
- **우선순위 점수**: 100 (Severity 100 × Confidence 1.0)
- **파일**:
  - `deal-mgmt/app/models/enums.py:463` — `READ = "READ"` 정의
  - `deal-mgmt/app/routers/pef_registry.py:250` — `AuditAction.READ` 사용
  - `deal-mgmt/app/routers/si_mapping.py:112,276` — `AuditAction.READ` 사용
  - `deal-mgmt/migrations/versions/001_initial_schema.py:167-170` — `READ` 누락

**현상**:
```python
# enums.py:463
READ = "READ"  # Python enum에는 존재

# 001_initial_schema.py:168 — PostgreSQL enum 정의
sa.Enum(
    "CREATE", "UPDATE", "DELETE", "PHASE_TRANSITION", "STATUS_CHANGE",
    "MEMBER_ADDED", "MEMBER_REMOVED", "SERVICE_LINKED",
    name="auditaction",
)
# ← "READ" 없음
```

**검증 근거**:
1. `Grep "ADD VALUE.*READ" migrations/` → 0건 (어떤 마이그레이션에서도 READ 미추가)
2. 005, 051 마이그레이션에서 APPROVAL_REQUESTED, CLIENT_ASSIGNED 등은 추가했으나 READ는 누락
3. SQLite CI는 enum을 VARCHAR로 처리하므로 테스트 통과 → **프로덕션에서만 발생**
4. `pef_registry.py:254`에서 `await db.commit()` 추가 후, READ INSERT 시 PostgreSQL이 `invalid input value for enum auditaction: "READ"` 에러 발생
5. `si_mapping.py:112,276`에서도 동일 AuditAction.READ 사용 → 해당 엔드포인트도 영향

**영향**: FI 추천 + SI 매핑 엔드포인트에서 audit 로그 커밋 시 500 에러. 결과 자체는 try/except로 보호되어 반환되지만 감사 로그 저장 실패.

**수정 방향**: 새 Alembic 마이그레이션 생성
```python
def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        with op.get_context().autocommit_block():
            op.execute(sa.text("ALTER TYPE auditaction ADD VALUE IF NOT EXISTS 'READ'"))
```

---

## P2 — 개선 권장

### [A11Y-1] Modal 포커스 트래핑 — `<dialog>` 네이티브 동작에 의존

- **관점**: §13 접근성
- **심각도/신뢰도**: Major / HIGH → **Mitigated**
- **우선순위 점수**: 42 (Severity 70 × Confidence 1.0 × mitigated 0.6)
- **파일**: `amic-platform/src/components/ui/Modal.tsx`

**현상**: `FOCUSABLE_SELECTOR` 상수를 정의하고 첫 요소 포커스 이동은 구현했으나, Tab 키 트래핑 로직은 없음. 단, `<dialog>.showModal()`의 네이티브 포커스 트래핑이 최신 브라우저(Chrome/Firefox/Safari)에서 동작하므로 실질 영향은 제한적.

**권장**: 브라우저 테스트로 Tab 이탈 없음을 확인. `FOCUSABLE_SELECTOR`가 미사용이면 정리 고려.

### [UX-1] FIRecommendModal — Tier 2 시각적 구분 부재

- **관점**: §13 UX 일관성
- **심각도/신뢰도**: Moderate / HIGH
- **우선순위 점수**: 40 (Severity 40 × Confidence 1.0)
- **파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx:169-177`

**현상**: Tier 1만 `<Badge variant="success">` + Star 아이콘으로 표시. Tier 2는 아무 표시 없음. 반면 BuyersTab의 BuyerTierBadge에서는 Tier 2를 파란색 뱃지로 구분.

**권장**: `{rec.tier === 2 && <Badge variant="info">Tier 2</Badge>}` 추가.

### [UX-2] FIRecommendModal — gp_profile 데이터 UI 미노출

- **관점**: §13 UX 일관성
- **심각도/신뢰도**: Moderate / HIGH
- **우선순위 점수**: 40 (Severity 40 × Confidence 1.0)
- **파일**: `amic-platform/src/modules/ma/components/buyers/FIRecommendModal.tsx`

**현상**: API 응답에 `gp_profile` (portfolio_sectors, portfolio_companies, recent_pef_count 등)이 포함되지만 UI에서 미사용. GP 선택 시 핵심 의사결정 정보 누락.

**권장**: 각 GP 카드에 확장 가능한 상세 영역 추가.

---

## P3 — 저우선

### 관점 8: 배포 안전성 (추가 발견)

| ID | 이슈 | 심각도 | 판정 |
|----|------|--------|------|
| H-02 | 모듈 레벨 `asyncio.Lock` 이벤트 루프 의존 | High | **FP** — Python 3.10+에서 Lock은 현재 루프에 자동 바인딩, running loop 외에서 생성해도 안전 |
| H-03 | `target_company_name` ilike 패턴 검증 | High | **FP** — SQLAlchemy 파라미터 바인딩 + escape 처리 완비 |
| M-02 | 모듈 레벨 캐시 수동 무효화 불가 (1시간 TTL) | Moderate | 유효 — 관리 엔드포인트 또는 TTL 단축 고려 |
| M-03 | Rate Limiter 다중 워커 비공유 | Moderate | 유효 — 현재 단일 워커로 허용 가능. Redis 전환 시 해결 |

### 관점 9: 의존성 & 결합도

| ID | 이슈 | 심각도 | 판정 |
|----|------|--------|------|
| M-01 | `gp_profile.py`에서 JSONB 직접 import | Moderate | **FP** — `JSON().with_variant(JSONB, "postgresql")` 패턴으로 올바르게 사용 |
| C-01 | .env 파일에 API 키 평문 저장 | Critical | **FP (코드 리뷰 범위 외)** — .gitignore 보호됨, 운영 보안 영역 |

### 관점 12: 인지 복잡도 & 가독성

| ID | 이슈 | 심각도 | 설명 |
|----|------|--------|------|
| SMELL-01 | `recommend_fi()` Long Method (129줄, C등급) | Warning | 5단계 논리를 단일 함수에 포함. 단계별 주석(# 1.~# 4.)으로 구분됨. 헬퍼 추출 권장 |
| SMELL-02 | `fi_recommendations()` Long Method (137줄, C등급) | Warning | Rate Limiting~감사 로그까지 8개 관심사 혼재. 키워드 파싱/PEF 쿼리 추출 권장 |
| SMELL-03 | Feature Envy — 키워드 파싱 로직이 라우터에 존재 | Suggestion | `txn.industry` 파싱을 서비스 레이어로 이동 권장 |
| SMELL-04 | 중첩 루프 + 임시 상태 변수 누적 (최대 4단계) | Warning | `_deduplicate_funds()`, `_determine_tier()` 추출 권장 |
| SMELL-05 | 변수 초기화 후 조건부 재할당 패턴 | Suggestion | `tier=2 → if profile → tier=1` 패턴. SMELL-04 해결 시 자연 해소 |
| SMELL-06 | Magic String — 기본 배수값 분산 | Suggestion | FastAPI Query default로 중앙 관리되어 있어 오탐 가능성 |
| SMELL-07 | 테스트 `dict` 타입 힌트 미완성 | Warning | `payload: dict` → `dict[str, object]` 권장 |
| SMELL-08 | 모듈 레벨 가변 글로벌 상태 (캐시) | Warning | 단일 워커에서 허용 가능. double-check locking 정상 |

**네이밍 개선 제안** (Suggestion):
- `_t0` → `_start_time` (타이밍 의도 명확화)
- `keywords_list` → `keywords` (Python 관례상 `_list` 접미사 불필요)
- `threshold_pass` → `is_threshold_met` (불리언 접두사 규칙)

**양호한 사례**: `normalize_gp_name`, `_check_keyword_match`, `_load_gp_profiles` 등 동사+목적어 패턴 준수. 모듈 docstring과 단계별 주석이 129줄 함수의 가독성을 보완.

### 관점 13: 접근성 & UX 일관성

| ID | 이슈 | 심각도 | 설명 |
|----|------|--------|------|
| A11Y-2 | FIRecommendModal 체크박스 `aria-disabled` 중복 | Moderate | `disabled` 속성과 `aria-disabled` 동시 사용 — 하나만 사용 권장 |
| A11Y-3 | BuyersTab DataTable 체크박스 열 빈 헤더 | Moderate | `header: ""` → `<span className="sr-only">Short-List</span>` 권장 |
| A11Y-4 | BuyerTierBadge/DealRoleBadge 공용 Badge 미사용 | Minor | 디자인 시스템 일관성 저하. 커스텀 색상 → Badge variant 통합 권장 |
| A11Y-5 | MarketingStageTracker compact 모드 `title`만 사용 | Moderate | `title`은 스크린 리더 미보장 → `aria-label` 추가 권장 |
| A11Y-6 | ConsortiumPanel `window.confirm` 사용 | Minor | toast 패턴과 혼재. 삭제 확인 UX 통일 권장 |
| UX-3 | FIRecommendModal 정렬/필터 기능 없음 | Minor | 서버측 정렬(Tier ASC, min_fund_size DESC)에 의존. 클라이언트 필터 추가 고려 |
| UX-4 | `formatBillion` vs `formatKRW` 단위 체계 불일치 | Minor | 억 단위 vs 원 단위 — 혼동 방지를 위해 통합 또는 JSDoc 명시 |
| UX-5 | 삭제 확인 패턴 불일치 (toast vs window.confirm) | Minor | = A11Y-6과 동일 이슈 |
| UX-6 | `matching_funds` 배열 UI 미노출 | Minor | fund_count만 표시. 개별 펀드 목록 expandable 영역 추가 고려 |
| UX-7 | "추가됨" 항목 `opacity-70` 대비 비율 저하 가능 | Minor | `opacity-70` 대신 배경색 변경으로 WCAG 4.5:1 보장 |

**양호한 사례 (Well-Done)**:
- `<dialog>` 네이티브 요소 + `aria-labelledby` + `useId()` 적용
- ESC 핸들링, 포커스 이동/복원 완비
- `aria-live="polite"` + `aria-atomic="true"` 로딩/선택 상태 알림
- 장식용 아이콘 `aria-hidden="true"` 일관 적용
- GSAP 설정에서 `prefers-reduced-motion` 대응 (`gsap.ts`)

---

## 허위 양성 분석

| ID | 보고 심각도 | 판정 | FP 사유 |
|----|-----------|------|---------|
| C-01 | Critical | FP-CTX | .env 파일은 .gitignore 보호. 코드 리뷰가 아닌 운영 보안 영역 |
| H-02 | High | FP-LOGIC | Python 3.10+에서 asyncio.Lock은 이벤트 루프에 자동 바인딩되어 안전 |
| H-03 | High | FP-IMPL | SQLAlchemy 파라미터 바인딩 + escape 처리 완비 |
| M-01 | Moderate | FP-IMPL | `JSONB`를 `with_variant` 인자로만 사용 — CI Guard 2 허용 패턴 |

**교차 검증 통계**:
- 검증한 가설: 26건
- 거부된 가설 (FP): 4건
- 유효 이슈: 22건
- 거부율: 15%

---

## Methodology

- **에이전트**: python-code-reviewer (2), backend-security-reviewer (1), general-purpose (1)
- **파일 스캔**: BE 6개 + FE 16개 = 22개 파일
- **프로토콜**: Verified Claim Protocol v1.1
- **교차 검증**: High 이상 4건 → 1건 유효, 3건 FP
- **수정 검증**: 선행 리뷰 7/7건 수정 확인, 회귀 1건 수정

---

## 조치 권장 우선순위

1. **H-01 (P0)**: AuditAction.READ 마이그레이션 생성 — **즉시** (프로덕션 audit 커밋 실패)
2. **UX-1 (P2)**: Tier 2 뱃지 추가 — 소규모 변경, UX 개선 효과 높음
3. **UX-2 (P2)**: gp_profile 데이터 UI 노출 — 의사결정 지원 강화
4. **SMELL-01/02 (P3)**: 장기적 리팩토링 — 129줄/137줄 함수 분할
5. **A11Y-3/5 (P3)**: 스크린 리더 접근성 — aria-label 추가
