# Phase 1: Critical Path — 종합 코드 리뷰 리포트

> **작성일**: 2026-02-13 14:55
> **리뷰 범위**: A1, A2, B2, B5, D1, E1, E2, E4, F1, F5 (10개 프롬프트)
> **방법론**: Verified Claim Protocol (VCP) — 파일:라인 기반 검증, 병렬 에이전트 실행
> **프롬프트 원본**: `docs/20260213_1344_Code_Review_Prompts_V3.md`

---

## Executive Summary

| 심각도 | 건수 | 비고 |
|---------|------|------|
| **CRITICAL / HIGH** | 9 | 즉시 수정 필요 |
| **MAJOR / MEDIUM** | ~30 | 스프린트 내 수정 권장 |
| **MODERATE / LOW** | ~30+ | 백로그 등록 |
| **이전 FP 확인** | 9 | 이전 리뷰 허위양성 검증 완료 |

**Top 5 위험 요소**:
1. JWT 해지/블랙리스트 부재 (E1-HIGH)
2. IM FactValidator가 검증 불가 claim을 `verified=True`로 처리 (E4-HIGH)
3. FDD NarrativeGenerator에서 guardrails 미호출 (E4-HIGH)
4. Celery chord/chain 에러 전파 미완 (F5-HIGH)
5. FX 환율 변환 미구현 (F1-HIGH)

---

## 1. A1 — API Client & 네트워크 레이어

**대상 파일**: `src/api/client.ts`, `AuthProvider.tsx`, `auth-events.ts`, `vite.config.ts`, `nginx/prod.conf`

### 발견 사항 (9건: 1 Major, 2 Moderate, 6 Minor)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **MAJOR** | `AuthProvider.tsx:28-35` | Force-logout 핸들러에서 `queryClient.clear()` 누락 — 로그아웃 후 캐시된 데이터 잔존 |
| 2 | MODERATE | `client.ts` (전체) | Refresh 실패 시 circuit breaker 없음 — 무한 refresh 루프 가능 |
| 3 | MODERATE | `auth-events.ts:1-8` | CustomEvent 방식은 단일 탭에서만 동작 — `BroadcastChannel`/`storage` event 미사용 |
| 4 | Minor | `client.ts` | `VITE_API_BASE_URL` 환경변수 미설정 시 fallback 없음 |
| 5 | Minor | `client.ts` | Request interceptor에서 `signal` 미전달 (AbortController 미지원) |
| 6 | Minor | `client.ts` | 403/500 전역 핸들링 없음 |
| 7 | Minor | `client.ts` | 일부 dead code (미사용 import) |
| 8 | Minor | 모듈별 | fddApi/kiisApi/imApi 인스턴스 중복 생성 패턴 |
| 9 | Minor | `vite.config.ts` | 프록시 매핑 정확 확인 (/api/fdd→:8000, /api/kiis→:8001, /api/im→:8002) ✅ |

**검증 완료**: 순환 의존 해결됨 (token-storage.ts 분리), nginx 포트 매핑 정확 ✅

### 권장 수정

```typescript
// AuthProvider.tsx — force-logout에 queryClient.clear() 추가
const handleForceLogout = useCallback(() => {
  tokenStorage.clear();
  queryClient.clear(); // ← 추가
  setUser(null);
}, [queryClient]);
```

---

## 2. A2 — 인증 플로우

**대상 파일**: `useAuth.ts`, `token-storage.ts`, `LoginPage.tsx`, `ProtectedRoute.tsx`, `auth.ts` (types)

### 발견 사항 (6건: 1 Major, 2 Moderate, 3 Minor)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **MAJOR** | `AuthProvider.tsx:28-35` | A1과 동일 — force-logout `queryClient.clear()` 누락 |
| 2 | MODERATE | `token-storage.ts:9-24` | localStorage 접근에 try-catch 없음 — Safari Private Browsing에서 크래시 |
| 3 | MODERATE | `LoginPage.tsx:22-26` | 렌더 타임에 `navigate()` 호출 — `<Navigate>` 컴포넌트로 교체 필요 |
| 4 | Minor | `auth.ts:69-74` | `expires_in` 필드 정의됨 but 클라이언트에서 미사용 |
| 5 | Minor | `auth.ts` | `is_active` 필드 응답에 포함되나 FE에서 미확인 |
| 6 | Minor | `token-storage.ts` | `removeItem` 미구현 (clear만 존재) |

**FP 확인**: `useAuth.ts:50-54`의 명시적 logout에서는 `queryClient.clear()` 정상 호출됨 ✅

### 권장 수정

```typescript
// token-storage.ts — try-catch 추가
export const tokenStorage = {
  get: (): string | null => {
    try {
      return localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  // ...
};
```

---

## 3. B2 — FDD 훅 (QoE/NWC/Debt) + FE-BE 스키마 교차검증

**대상 파일**: FDD types (`qoe.ts`, `nwc.ts`, `debt.ts`) vs BE schemas (`qoe.py`, `nwc.py`, `debt.py`)

### 발견 사항 (8건: 4 Moderate, 4 Minor)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | MODERATE | `qoe.ts` vs `qoe.py:87` | `category_breakdown` — FE: 구조화된 인터페이스, BE: `dict` (untyped) |
| 2 | MODERATE | `nwc.ts` vs `nwc.py:59` | `category_breakdown` — 동일 불일치 |
| 3 | MODERATE | `debt.ts` vs `debt.py:86` | `category_breakdown` — 동일 불일치 |
| 4 | MODERATE | `nwc.ts:58` vs `models/nwc.py:126-130` | `monthly_trend` 키 이름 불일치 가능 (`ca`/`cl` vs `current_assets`/`current_liabilities`) |
| 5 | MODERATE | 3개 모듈 전체 (10개 mutation) | 모든 mutation hook에 `onError` 콜백 누락 — 프로젝트 규칙 위반 |
| 6 | Minor | `nwc.ts` | `monthly_amounts` 타입 미정의 |
| 7 | Minor | `qoe.ts` | `source_entry_ids` 타입 미정의 |
| 8 | Minor | `debt.ts` | 인라인 타입 사용 (인터페이스 분리 권장) |

**검증 완료**: 쿼리키 (`["fdd","qoe"]` 등) 정확 ✅, `enabled` 가드 정확 ✅, Enum 매핑 정확 ✅

### 권장 수정

```python
# BE schemas — category_breakdown 타입 명시
class QoEBreakdownItem(BaseModel):
    category: str
    amount: Decimal
    percentage: Decimal

class QoEResult(BaseModel):
    category_breakdown: list[QoEBreakdownItem]  # dict → 구조화
```

---

## 4. B5 — FDD 계산 페이지 (QoE/NWC/Debt)

**대상 파일**: `QoEPage.tsx`, `NWCPage.tsx`, `NetDebtPage.tsx`

### 발견 사항 (8건: 2 Major, 3 Moderate, 3 Minor)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **MAJOR** | `QoEPage.tsx:335`, `NetDebtPage.tsx:340` | `approved_by: user?.email ?? "unknown"` — 하드코딩 fallback |
| 2 | **MAJOR** | `QoEPage.tsx:308`, `NWCPage.tsx:387`, `NetDebtPage.tsx:307` | `dealId!` non-null assertion + `latestX?.id ?? ""` 빈 문자열 전달 |
| 3 | MODERATE | `QoEPage.tsx:106` | `Number(qoe.balance_check_error) === 0` — 부동소수점 비교에 tolerance 없음 |
| 4 | MODERATE | `QoEPage.tsx:50-59` | D&A 값 부호 반전 없이 두 번 사용 |
| 5 | MODERATE | `NWCPage.tsx:301-306` | Custom value 입력에 숫자 유효성 검증 없음 |
| 6 | Minor | 3개 페이지 | 에러 핸들링 불일치 (일부 toast, 일부 silent) |
| 7 | Minor | `NWCPage.tsx` | `CLASS_ORDER` 타입 단언 미흡 |
| 8 | Minor | 3개 페이지 | 로딩 UX 불일치 (Skeleton vs Spinner) |

**Session 3 수정 확인**: NWC classOrder, approved_by 이전 수정 반영됨 ✅

### 권장 수정

```typescript
// approved_by — user 없으면 approve 버튼 비활성화
<Button
  disabled={!user?.email || isApproving}
  onClick={() => approveMutation.mutate({ approved_by: user!.email })}
>
```

---

## 5. D1 — IM 훅 & API

**대상 파일**: `useDocuments.ts`, `useCompanies.ts`, `document.ts`, `company.ts`, `useDocuments.test.tsx`

### 발견 사항 (5건: 2 Moderate, 3 Minor)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | MODERATE | `useDocuments.test.tsx:173` | `revokeObjectURL` 테스트 타이밍 — 200ms setTimeout, fake timer 미사용 |
| 2 | MODERATE | `document.ts:119` vs `documents.py:39-41` | BE `sections: list[str]` 유효성 검증 없음 — FE `SectionId[]`가 유일한 방어선 |
| 3 | Minor | `company.ts:7,16` | `DartIndustryString` branded type — mock에서 `as` 캐스팅 필요 |
| 4 | Minor | `useDocuments.test.tsx` | 에러 시나리오 테스트 미흡 |
| 5 | Minor | `useCompanies.ts` | `useFetchCompany`에 `onError` 없음 |

**FP 확인**: Blob URL revoke 정상 구현 (P2) ✅, DartIndustryString branded type 정확 (P3) ✅

---

## 6. E1 — FDD 백엔드 인증

**대상 파일**: `dependencies.py`, `token.py`, `auth_service.py`, `auth.py`, `config.py`, `main.py`

### 발견 사항 (7건: 1 High, 3 Medium, 3 Low)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **HIGH** | `token.py:36-45`, `auth_service.py:97-114` | JWT 해지/블랙리스트 메커니즘 부재 — logout 엔드포인트 없음, jti claim 없음 |
| 2 | MEDIUM | `auth.py:36-44` | 로그인 엔드포인트 전용 rate limit 없음 (전역 60/min만 적용) |
| 3 | MEDIUM | `main.py:116-134` | `/metrics`, `/metrics/json` 엔드포인트 인증 없음 |
| 4 | MEDIUM | `config.py:38` | `auth_enabled=False` 프로덕션 가드 없음 |
| 5 | Low | `dependencies.py:1-5` | Docstring "AUTH_ENABLED=False (기본값)" — 실제 기본값은 True (이전 FP 원인) |
| 6 | Low | `token.py` | HS256 사용 (RS256 권장) |
| 7 | Low | `auth_service.py` | 패스워드 복잡도 정책 없음 |

### 이전 FP 4건 모두 확인 ✅

| FP | 검증 결과 |
|----|-----------|
| "PBKDF2 사용" | `password.py` → **bcrypt** 사용 확인 ✅ |
| "auth_enabled 기본값 False" | `config.py:18` → 기본값 **True** 확인 ✅ |
| "CORS 와일드카드" | `main.py:71-78` → **명시적 origin 목록** 확인 ✅ |
| "setattr 취약" | `deals.py:105-120` → **_UPDATABLE_FIELDS 화이트리스트** 확인 ✅ |

### 권장 수정

```python
# JWT 블랙리스트 — Redis 기반 구현
class TokenBlacklist:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def revoke(self, jti: str, exp: int):
        ttl = exp - int(time.time())
        if ttl > 0:
            await self.redis.setex(f"bl:{jti}", ttl, "1")

    async def is_revoked(self, jti: str) -> bool:
        return await self.redis.exists(f"bl:{jti}") > 0
```

---

## 7. E2 — KIIS 백엔드 보안 설정

**대상 파일**: `config.py`, `security.py`, `rate_limit.py`, `auth_service.py`, `main.py`

### 발견 사항 (7건: 0 Critical, 4 Medium, 3 Low)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | — | `security.py:29-37`, `main.py:54-77` | **K1 CRITICAL → DEFENDED** (3중 방어: RuntimeError + lifespan guard + DEBUG warning) |
| 2 | MEDIUM | `rate_limit.py` | `/register` 엔드포인트 rate limit 미적용 |
| 3 | MEDIUM | `rate_limit.py` | Redis 에러 시 fail-open (요청 허용) |
| 4 | MEDIUM | `rate_limit.py` | IP 프록시 미고려 (`X-Forwarded-For` 미확인) |
| 5 | MEDIUM | `auth_service.py` | Refresh token rotation 없음 (만료까지 재사용 가능) |
| 6 | Low | `auth_service.py` | Email 유효성 검증 미흡 |
| 7 | Low | `auth_service.py:49-57` | 타이밍 공격 가능 (미존재 사용자에 bcrypt 미적용) |

**K1 방어 구조 확인**:
- Layer 1: `_get_jwt_secret()` → 빈 문자열이면 `RuntimeError` 즉시 raise
- Layer 2: `lifespan()` → 프로덕션 환경에서 빈 SECRET이면 서버 시작 차단
- Layer 3: DEBUG 모드에서 경고 로그 출력

---

## 8. E4 — LLM 프롬프트 인젝션 & 가드레일

**대상 파일**: FDD(`qoe_analyzer.py`, `narrative_generator.py`, `guardrails.py`), IM(`base.py`, `validator.py`, `model_router.py`)

### 발견 사항 (13건: 2 High, 1 Medium-High, 3 Medium, 3 Low-Medium, 2 Low, 2 Info)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **HIGH** | IM `validator.py:147-152` | 검증 불가 claim → `verified=True` 기본 처리, `pass_rate=1.0` |
| 2 | **HIGH** | FDD `narrative_generator.py:81-88` | `validate_narrative_claims()` 구현 완료되었으나 **NarrativeGenerator에서 호출하지 않음** |
| 3 | MEDIUM-HIGH | IM `base.py:92-116` | RAG 컨텍스트 sanitization 없이 프롬프트 삽입 (간접 인젝션) |
| 4 | MEDIUM | FDD `qoe_analyzer.py:58-73` | `deal_name`, `ebitda_definition` → `str.format()`으로 프롬프트 삽입 |
| 5 | MEDIUM | FDD `narrative_generator.py:68-88` | `deal_name`/`industry_name` → f-string으로 삽입 (system/user 분리는 정상) |
| 6 | MEDIUM | FDD `guardrails.py:215-275` | 숫자 <100 검증 스킵 — 퍼센티지 할루시네이션 미탐지 |
| 7-13 | Low~Info | 다수 | max_tokens 설정 정상, system/user 분리 정상, 프로바이더별 구현 정확 |

### 권장 수정 (최우선)

```python
# validator.py — 검증 불가 claim 처리 개선
def validate_claim(self, claim: str) -> ClaimResult:
    if not self._is_verifiable(claim):
        return ClaimResult(
            verified=False,        # True → False로 변경
            confidence=0.0,        # 1.0 → 0.0
            reason="unverifiable",
            needs_human_review=True  # 사람 검토 플래그 추가
        )
```

```python
# narrative_generator.py — guardrails 호출 추가
class NarrativeGenerator:
    async def generate(self, deal_data: DealData) -> Narrative:
        narrative = await self._generate_raw(deal_data)
        # ↓ 이 줄 추가
        validation = validate_narrative_claims(narrative, deal_data)
        if not validation.is_valid:
            raise GuardrailViolation(validation.violations)
        return narrative
```

---

## 9. F1 — FDD 계산 엔진

**대상 파일**: `qoe_engine.py`, `nwc_engine.py`, `debt_engine.py`, `anomaly_engine.py`, `qoe_service.py`, `fx_service.py`

### 발견 사항 (14건: 1 High, 5 Medium, 8 Low)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **HIGH** | `qoe_service.py:55-73` | `fx_service.py` 존재하지만 QoE/NWC/Debt 서비스에서 **FX 변환 미호출** — 다중 통화 미지원 |
| 2 | MEDIUM | `anomaly_engine.py:244` | `math.sqrt(float(variance))` — Z-score에서 float 누수 (Decimal 정밀도 손실) |
| 3 | MEDIUM | `nwc_service.py:103`, `debt_service.py:67` | `_get_line_items_map()` 전체 항목 로드 (필터링 없음) |
| 4 | MEDIUM | `nwc_service.py:124-125` | 동일 TB 데이터 중복 쿼리 |
| 5 | MEDIUM | `debt_engine.py:417-447` | Rule 4/5 상호 배타 미보장 — 이중 계산 가능 |
| 6 | MEDIUM | `qoe_engine.py` + `anomaly_engine.py` | 키워드 목록 중복 정의 |
| 7-14 | Low | 다수 | 컨벤션/일관성 이슈, Decimal 생성자 올바름 ✅, Division-by-zero 가드 정상 ✅ |

**검증 완료**: 모든 엔진 Decimal + `ROUND_HALF_UP` 정상 ✅, `_q()` quantize 헬퍼 정상 ✅

### 권장 수정 (최우선)

```python
# qoe_service.py — FX 변환 통합
from app.services.fx_service import FXService

class QoEService:
    def __init__(self, db: Session, fx_service: FXService):
        self.fx_service = fx_service

    async def calculate(self, deal_id: int) -> QoEResult:
        deal = self._get_deal(deal_id)
        line_items = self._get_line_items(deal_id)
        # FX 변환 적용
        if deal.currency != "KRW":
            line_items = self.fx_service.convert_all(
                line_items, deal.currency, "KRW", deal.base_date
            )
        return self.engine.calculate(line_items)
```

---

## 10. F5 — IM 문서 생성 파이프라인

**대상 파일**: `generate_im.py`, `document_service.py`, `progress.py`, `model_router.py`, `session.py`

### 발견 사항 (18건: 3 High, 7 Medium, 8 Low)

| # | 심각도 | 파일:라인 | 내용 |
|---|--------|-----------|------|
| 1 | **HIGH** | `generate_im.py:92-107` | Celery chord\|chain `link_error`가 chain subtask 실패까지 전파 안됨 |
| 2 | **HIGH** | `document_service.py:47-65` | `corp_code` 중복 체크 TOCTOU race condition (DB-level lock 없음) |
| 3 | **HIGH** | `progress.py:81-86` | 상태 업데이트 예외 무시 — COMPLETED/FAILED 전환 silent fail |
| 4 | MEDIUM | `progress.py:56-86` | 매 progress 호출마다 새 sync engine 생성+폐기 |
| 5 | MEDIUM | `generate_im.py:271-277` | `industry` 파라미터 NarrativeOrchestrator에 미전달 |
| 6 | MEDIUM | `model_router.py:154-191` | Primary provider 실패 시 fallback retry 없음 |
| 7 | MEDIUM | `document_service.py` | 상태 전이 유효성 검증 없음 (DRAFT→COMPLETED 직접 가능) |
| 8 | MEDIUM | 파이프라인 전체 | LLM 비용 제어 메커니즘 부재 (budget/quota) |
| 9 | MEDIUM | `generate_im.py` | async/sync 혼용 불일치 |
| 10 | Low | `session.py:64-82` | Double-commit 위험 (session generator + service 양쪽 commit) |
| 11-18 | Low | 다수 | 유지보수/성능 이슈 |

**검증 완료**: Celery chord/chain 아키텍처 정확 ✅, DataPriority 전략 양호 ✅, 토큰 버짓 관리 정상 ✅

### 권장 수정 (최우선)

```python
# progress.py — 예외 처리 개선
def update_progress(self, doc_id: int, status: str, progress: float):
    try:
        with self._get_session() as session:
            doc = session.get(Document, doc_id)
            if doc:
                doc.status = status
                doc.progress = progress
                session.commit()
    except Exception as e:
        logger.error(f"Progress update failed: {doc_id=}, {status=}, {e}")
        raise  # ← silent fail 제거, 예외 재발생
```

```python
# document_service.py — DB-level uniqueness
# models.py에 unique constraint 추가
class Document(Base):
    corp_code = Column(String, unique=True, index=True)  # ← unique 추가
```

---

## Cross-Cutting Themes (교차 분석)

### Theme 1: 에러 핸들링 불일치
- **FE**: mutation hook `onError` 누락 (B2), toast/silent 혼용 (B5)
- **BE**: progress 예외 무시 (F5), fail-open rate limit (E2)
- **권장**: 프로젝트 전반 에러 핸들링 가이드라인 수립

### Theme 2: FE-BE 스키마 동기화
- `category_breakdown` 3중 불일치 (B2)
- `sections` 유효성 검증 BE 부재 (D1)
- `monthly_trend` 키 이름 불일치 가능 (B2)
- **권장**: OpenAPI 스키마 자동 생성 또는 공유 타입 계약(contract) 도입

### Theme 3: LLM 안전성 갭
- Guardrails 구현 완료되었으나 호출 미연결 (E4-#2)
- FactValidator 기본 pass 정책 (E4-#1)
- RAG 간접 인젝션 (E4-#3)
- **권장**: LLM 파이프라인 end-to-end 안전성 감사, guardrails 연결 확인

### Theme 4: 인증/세션 관리 미완
- JWT 블랙리스트 없음 (E1), refresh token rotation 없음 (E2)
- force-logout `queryClient.clear()` 누락 (A1/A2)
- cross-tab 로그아웃 미지원 (A1)
- **권장**: 인증 레이어 통합 리팩토링 스프린트

### Theme 5: 데이터 정합성 위험
- FX 변환 미구현 (F1), 이중 계산 가능 (F1)
- TOCTOU race condition (F5), 중복 TB 쿼리 (F1)
- **권장**: 금융 계산 정합성 전용 테스트 스위트 구축

---

## 우선순위별 수정 로드맵

### 🔴 P0 — 즉시 (이번 주)
1. **E4-#2**: NarrativeGenerator에서 `validate_narrative_claims()` 호출 연결
2. **E4-#1**: FactValidator `verified=True` → `False` + `needs_human_review` 추가
3. **F5-#3**: progress.py 예외 무시 제거 (`raise` 추가)
4. **A1/A2-#1**: force-logout에 `queryClient.clear()` 추가

### 🟠 P1 — 1주 내
5. **E1-#1**: JWT 블랙리스트 + logout 엔드포인트 구현
6. **F5-#1**: Celery chord/chain 에러 전파 수정
7. **F5-#2**: corp_code DB-level unique constraint 추가
8. **F1-#1**: FX 서비스 통합 (다중 통화 지원)
9. **E4-#3**: RAG 컨텍스트 sanitization 추가

### 🟡 P2 — 스프린트 내
10. **B2-#1~3**: BE category_breakdown 스키마 타입 명시
11. **B2-#5**: 10개 mutation hook `onError` 추가
12. **B5-#1**: approved_by fallback 제거 + UI 비활성화
13. **B5-#2**: dealId non-null assertion 제거 + 가드 추가
14. **E2-#2~4**: Rate limit 강화 (register, fail-close, proxy IP)
15. **F1-#5**: Debt engine Rule 4/5 상호 배타 보장

### 🟢 P3 — 백로그
16. A1-#2: Refresh circuit breaker
17. A1-#3: Cross-tab 로그아웃 (BroadcastChannel)
18. A2-#2: token-storage.ts try-catch
19. E2-#5: Refresh token rotation
20. F1-#2: Z-score Decimal 정밀도 수정
21. F5-#4: progress.py session 재사용

---

## 이전 리뷰 FP (False Positive) 검증 결과

| 이전 주장 | 검증 결과 | 비고 |
|-----------|-----------|------|
| FDD: PBKDF2 사용 | ❌ FP — bcrypt 사용 | `password.py` 확인 |
| FDD: auth_enabled 기본 False | ❌ FP — 기본 True | `config.py:18` 확인 |
| FDD: CORS 와일드카드 | ❌ FP — 명시적 origin | `main.py:71-78` 확인 |
| FDD: setattr 취약 | ❌ FP — 화이트리스트 | `deals.py:105-120` 확인 |
| IM: Blob URL 미해제 | ❌ FP — 정상 해제 | `useDocuments.ts` P2 확인 |
| IM: branded type 오류 | ❌ FP — 정상 작동 | `company.ts` P3 확인 |
| KIIS: K1 빈 SECRET_KEY | ✅ **방어됨** — 3중 방어 | 실질적 위험 아님 |
| IM: 순환 의존 | ❌ FP — 해결됨 | `token-storage.ts` 분리 |
| FDD: non-null assertion | ⚠️ **유효** — 실제 위험 | 수정 필요 (B5-#2) |

---

## 통계 요약

| 리뷰 ID | 대상 | 발견 건수 | High/Major | Medium | Low+ |
|----------|------|-----------|------------|--------|------|
| A1 | API Client | 9 | 1 | 2 | 6 |
| A2 | Auth Flow | 6 | 1 | 2 | 3 |
| B2 | FDD Hooks | 8 | 0 | 4 | 4 |
| B5 | FDD Pages | 8 | 2 | 3 | 3 |
| D1 | IM Hooks | 5 | 0 | 2 | 3 |
| E1 | FDD BE Auth | 7 | 1 | 3 | 3 |
| E2 | KIIS BE Security | 7 | 0 | 4 | 3 |
| E4 | LLM Guardrails | 13 | 2 | 4 | 7 |
| F1 | FDD Engines | 14 | 1 | 5 | 8 |
| F5 | IM Pipeline | 18 | 3 | 7 | 8 |
| **합계** | | **95** | **11** | **36** | **48** |

---

*Generated by Claude Code — Phase 1 Critical Path Review*
*Methodology: Verified Claim Protocol (VCP) with parallel agent execution*
