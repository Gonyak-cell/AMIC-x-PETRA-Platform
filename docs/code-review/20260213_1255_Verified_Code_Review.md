# AMIC x PETRA Platform — 검증된 코드 리뷰

> **리뷰 일시**: 2026-02-13 12:53
> **리뷰어**: Claude Code (Opus 4.6)
> **범위**: FDD (FE+BE) + KIIS (FE+BE) + IM (FE+BE) + Platform 공통
> **방법론**: 3개 탐색 에이전트 병렬 분석 → 핵심 발견사항 소스코드 직접 교차 검증
> **이전 리뷰 정정**: 본 문서는 2026-02-13 이전 리뷰 문서들의 허위 발견사항을 정정합니다.

---

## 요약

| 모듈 | Critical | Major | Moderate | Minor | 합계 |
|------|----------|-------|----------|-------|------|
| **FDD** | 0 | 1 | 1 | 3 | 5 |
| **KIIS** | 1 | 2 | 0 | 9 | 12 |
| **IM + Platform** | 0 | 3 | 0 | 5 | 8 |
| **합계** | **1** | **6** | **1** | **17** | **25** |

> 전체 위험도: **낮음** — Critical 1건은 KIIS 백엔드 JWT 설정 (프론트엔드와 별개). 나머지는 성능·UX·타입안전성 개선 사항.

---

## 1. KIIS 모듈

### K1. JWT_SECRET / SECRET_KEY 빈 문자열 기본값 🔴 CRITICAL

- **파일**: `KIIS/app/core/config.py:10-11`
- **검증**: ✅ 직접 확인

```python
class Settings(BaseSettings):
    # ...
    SECRET_KEY: str = ""          # ← 빈 문자열 기본값
    JWT_SECRET: str = ""          # ← 빈 문자열 기본값
```

- **문제**: `.env` 파일 누락 시 빈 문자열로 JWT가 서명됨. 공격자가 유효한 토큰을 위조 가능.
- **FDD 백엔드와 비교**: FDD는 `config.py:40-48`에서 프로덕션 환경 시 `RuntimeError`를 발생시키는 시작 검증이 있음. KIIS에는 이러한 가드가 전혀 없음.
- **영향**: 인증 우회 가능 — 프로덕션 배포 전 반드시 수정
- **수정안**:
```python
# config.py 하단에 추가
settings = Settings()

_is_production = os.getenv("ENV", "").lower() in ("production", "prod")
if _is_production and not settings.JWT_SECRET and not settings.SECRET_KEY:
    raise RuntimeError("JWT_SECRET or SECRET_KEY must be set in production")
```

---

### K2. corpCode URL 경로 삽입 시 포맷 검증 없음 🟠 MAJOR

- **파일**: `amic-platform/src/modules/kiis/hooks/usePortfolio.ts:18`
- **검증**: ✅ 직접 확인

```typescript
export function usePortfolio(corpCode: string, params: PortfolioListParams = {}) {
  return useQuery<PortfolioListResponse>({
    queryFn: async () => {
      const { data } = await kiisApi.get<PortfolioListResponse>(
        `/portfolio/by-investor/${corpCode}`,  // ← corpCode가 URL 경로에 직접 삽입
        { params },
      );
      return data;
    },
    enabled: !!corpCode,  // ← 진위성만 체크, 포맷 미검증
  });
}
```

- **유사 패턴**: `useDisclosures.ts:16`, `useDisclosures.ts:35,54`, `PortfolioPage.tsx:54`, `CompanyDetailPage.tsx:152` 등 7곳
- **문제**: `corpCode`가 `^\d{8}$` 포맷인지 프론트엔드에서 검증하지 않음. 백엔드가 입력을 적절히 처리하면 실질적 위험은 낮으나, defense-in-depth 원칙 위반.
- **참고**: IM 모듈의 `CreateDocumentPage.tsx:131`은 `/^\d{8}$/.test()` 정규식으로 올바르게 검증하고 있음
- **수정안**: 호출하는 페이지 컴포넌트에서 corpCode 설정 시 포맷 검증 추가

---

### K3. 필수 설정(DART_API_KEY 등) 시작 검증 없음 🟠 MAJOR

- **파일**: `KIIS/app/core/config.py:41`
- **검증**: ✅ 직접 확인

```python
DART_API_KEY: str = ""     # ← 빈 문자열 기본값
SLACK_WEBHOOK_URL: str = ""
SMTP_HOST: str = ""
```

- **문제**: 애플리케이션이 정상 시작되지만 DART API 호출 시 401/403으로 실패. 배포 시점이 아닌 기능 사용 시점에 에러 발견됨.
- **수정안**: `app/main.py` startup 이벤트에서 필수 설정 검증

---

### K4. ReitDetailPage 안전하지 않은 non-null assertion 🟡 MINOR

- **파일**: `amic-platform/src/modules/kiis/pages/ReitDetailPage.tsx:37`
- **검증**: ✅ 직접 확인

```typescript
const { reitsCode } = useParams<{ reitsCode: string }>();
const { data, isLoading } = useReitDetail(reitsCode!);  // ← unsafe !
```

- **참고**: 같은 모듈 내 `CompanyDetailPage.tsx`는 `corpCode ?? ""`로 올바르게 처리
- **수정안**: `const code = reitsCode ?? "";` + 빈값 가드

---

### K5. ValuationUpdateResponse 타입 API 정합성 미검증 🟡 MINOR

- **파일**: `amic-platform/src/modules/kiis/types/portfolio.ts:62-69`
- **문제**: `target_company_name` 필드가 API 응답에 실제로 있는지 검증 없음. `PortfolioPage.tsx:105`에서 이 필드를 토스트 메시지에 사용하므로, 누락 시 "undefined" 표시.

---

### K6. DashboardPage 취약한 React key 생성 🟡 MINOR

- **파일**: `amic-platform/src/modules/kiis/pages/DashboardPage.tsx:139-141`
- **문제**: `_key: ${d.target_company}-${d.deal_date ?? "no-date"}-${d.sector ?? "no-sector"}` — 동일 회사/날짜/섹터 조합 시 key 충돌 가능
- **수정안**: DB ID가 있으면 해당 필드 사용

---

### K7. FundDetailPage index 기반 React key 🟡 MINOR

- **파일**: `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx:120-127`
- **문제**: `_id: ${m.manager_name}-${i}` — 배열 순서 변경 시 불필요한 리렌더
- **수정안**: 매니저 DB ID 사용

---

### K8. NewsListPage card button aria-label 과도 🟡 MINOR

- **파일**: `amic-platform/src/modules/kiis/pages/NewsListPage.tsx:107`
- **문제**: `aria-label={article.title}` — 100자 이상 가능한 제목이 그대로 label. 스크린 리더 UX 저하.

---

### K9. EntityResolutionPage 삭제 버튼 aria-label 없음 🟡 MINOR

- **파일**: `amic-platform/src/modules/kiis/pages/EntityResolutionPage.tsx:142-156`
- **문제**: 아이콘 전용 삭제 버튼에 aria-label 없음. WCAG 1.1.1 위반.
- **수정안**: `aria-label={`Delete alias: ${row.alias_name}`}`

---

### K10–K12. 에러 메시지 / 쿼리 무효화 🟡 MINOR

| # | 파일 | 문제 |
|---|------|------|
| K10 | `NewsListPage.tsx:36-41` | 뉴스 수집 성공/실패 메시지가 일반적 |
| K11 | `CompanyDetailPage.tsx:175-186` | 와치리스트 추가 실패 시 에러 상세 없음 |
| K12 | `useWatchlist.ts:40-46` | `invalidateQueries` 범위가 모든 alerts 쿼리에 매칭 |

---

## 2. FDD 모듈

### F1. Deal Summary 엔드포인트 3회 순차 쿼리 🟠 MAJOR

- **파일**: `Auto FDD/backend/app/api/deals.py:400-450`
- **검증**: ✅ 직접 확인

```python
# Line 400-408: QoE 조회
qoe = (
    db.query(QoECalculation)
    .filter(QoECalculation.deal_id == deal_id, QoECalculation.status == QoEStatus.COMPLETED)
    .order_by(QoECalculation.created_at.desc())
    .first()
)

# Line 417-425: NWC 조회 (동일 패턴)
nwc = (
    db.query(NWCCalculation)
    .filter(NWCCalculation.deal_id == deal_id, NWCCalculation.status == NWCStatus.COMPLETED)
    .order_by(NWCCalculation.created_at.desc())
    .first()
)

# Line 434-442: Debt 조회 (동일 패턴)
debt = (
    db.query(NetDebtCalculation)
    .filter(NetDebtCalculation.deal_id == deal_id, NetDebtCalculation.status == DebtStatus.COMPLETED)
    .order_by(NetDebtCalculation.created_at.desc())
    .first()
)
```

- **문제**: 한 번의 API 호출에 3회 DB 쿼리. 단일 딜 조회 시에는 무방하나, IM 모듈에서 크로스모듈 참조 시 병목 가능.
- **수정안**: UNION ALL 또는 서브쿼리로 1회 조회, 또는 서비스 레이어 캐싱

---

### F2. QoEPage mutation hook에 빈 문자열 ID 전달 🟡 MODERATE

- **파일**: `amic-platform/src/modules/fdd/pages/QoEPage.tsx:313-314`
- **검증**: ✅ 직접 확인

```typescript
const latestQoE = qoeList.length > 0 ? qoeList[0] : null;

const approveMutation = useApproveAdjustment(dealId!, latestQoE?.id ?? "");
const recalcMutation = useRecalculateBridge(dealId!, latestQoE?.id ?? "");
```

- **문제**: QoE 계산이 없을 때 `""` (빈 문자열)이 mutation hook의 qoeId로 전달됨. 사용자가 실수로 버튼을 클릭하면 빈 ID로 API 요청 발생 가능.
- **수정안**: mutation 호출 시점에 `latestQoE?.id` 가드 추가 (이미 `handleApprove`에는 가드 있으나, hook 자체가 빈 ID로 초기화되는 점이 문제)

---

### F3. category_breakdown 느슨한 타입 🟡 MINOR

- **파일**: `fdd/types/qoe.ts`, `nwc.ts`, `debt.ts`
- **문제**: `Record<string, unknown>` — 백엔드 응답의 구체적 필드에 대한 컴파일 타임 검증 불가
- **수정안**: 각 계산 유형별 구체적 인터페이스 정의

---

### F4. GET /deals 읽기 엔드포인트 권한 체크 누락 🟡 MINOR

- **파일**: `Auto FDD/backend/app/api/deals.py:65-91`
- **검증**: ✅ 직접 확인

```python
@router.get("/deals", response_model=list[DealRead])
def list_deals(
    current_user: CurrentUser = Depends(get_current_user),  # ← 인증만, 권한 미체크
    db: Session = Depends(get_db),
):
```

- **참고**: `POST /deals` (line 39-62)는 `require_permission(Permission.DEAL_CREATE)` 사용
- **문제**: 인증된 모든 사용자가 전체 딜 목록 조회 가능. 폐쇄형 시스템에서는 낮은 위험.
- **수정안**: `require_permission(Permission.DEAL_READ)` 추가 + 팀/조직 필터링 검토

---

### F5. QoEPage 에러 메시지 일반적 🟡 MINOR

- **파일**: `amic-platform/src/modules/fdd/pages/QoEPage.tsx:318-348`
- **검증**: ✅ 직접 확인
- **문제**: `handleRun`, `handleApprove`, `handleRecalculate` 모두 `catch { toast.error("Failed to ...") }` — 400/500/네트워크 오류 구분 불가
- **수정안**: `err?.response?.data?.detail` 추출하여 표시

---

## 3. IM + Platform 공통

### P1. CreateDocumentPage useEffect cleanup 없음 🟠 MAJOR

- **파일**: `amic-platform/src/modules/im/pages/CreateDocumentPage.tsx:110-124`
- **검증**: ✅ 직접 확인

```typescript
const fetchCompanyMutate = fetchCompany.mutateAsync;
useEffect(() => {
  if (!urlCorpCode || !/^\d{8}$/.test(urlCorpCode)) return;
  if (urlCorpCode === lastFetchedCorpCode.current) return;
  lastFetchedCorpCode.current = urlCorpCode;
  fetchCompanyMutate(urlCorpCode)
    .then(() => {
      setFormData((prev) => ({ ...prev, corp_code: urlCorpCode, industry: "general" }));
      toast.success("Company data fetch initiated");
    })
    .catch(() => {
      toast.error("Failed to fetch company data");
    });
}, [urlCorpCode, fetchCompanyMutate]);
// ← cleanup 함수 없음: unmount 시 .then()의 setFormData가 실행되면 React 경고
```

- **문제**: 컴포넌트 언마운트 후 `.then()` 콜백에서 `setFormData()` 호출 → React state update warning
- **수정안**: `let isMounted = true` + cleanup에서 `isMounted = false` 설정, 또는 `fetchCompanyMutate`를 deps에서 제거하고 ref로 안정화

---

### P2. useDownloadDocument blob URL 즉시 revoke 🟠 MAJOR

- **파일**: `amic-platform/src/modules/im/hooks/useDocuments.ts:108-113`
- **검증**: ✅ 직접 확인

```typescript
link.click();
} finally {
  if (document.body.contains(link)) {
    document.body.removeChild(link);
  }
  window.URL.revokeObjectURL(url);  // ← link.click() 직후 즉시 revoke
}
```

- **문제**: `link.click()` 후 브라우저가 다운로드를 시작하기 전에 blob URL이 해제될 수 있음. 대부분의 브라우저에서 실질적 문제는 드물지만, 느린 시스템이나 대용량 파일에서 다운로드 실패 가능성 존재.
- **수정안**: `setTimeout(() => URL.revokeObjectURL(url), 100)` 으로 약간의 딜레이 추가

---

### P3. Company.industry 타입이 string | null (IndustryId 아님) 🟠 MAJOR

- **파일**: `amic-platform/src/modules/im/types/company.ts:10`
- **검증**: ✅ 직접 확인

```typescript
export interface Company {
  // ...
  /** Raw DART industry string (e.g. "소프트웨어"). Mapped to IndustryId in CreateDocumentPage. */
  industry: string | null;  // ← IndustryId가 아닌 plain string
}
```

- **문제**: `Company.industry`가 DART에서 가져온 raw 문자열("소프트웨어", "금융업" 등)인데, `IndustryId`로 오인하여 직접 사용할 위험. `CreateDocumentPage.tsx:184-200`에서 매핑 로직을 별도로 구현해둔 이유가 이것.
- **수정안**: JSDoc 코멘트는 있으나, branded type(`DartIndustryString`)이나 명시적 변환 함수로 타입 수준 안전성 강화 권장

---

### P4. ProgressTracker getFailedStageIndex 입력 검증 없음 🟡 MINOR

- **파일**: `amic-platform/src/modules/im/components/ProgressTracker.tsx:32-37`
- **검증**: ✅ 직접 확인
- **문제**: NaN이나 음수 `progressPct` 입력 시 `0`을 반환하지만 경고 없음
- **수정안**: `isFinite()` 체크 추가

---

### P5. DocumentDetailPage handleDownload unmount guard 없음 🟡 MINOR

- **파일**: `amic-platform/src/modules/im/pages/DocumentDetailPage.tsx:63-73`
- **문제**: P1과 동일 패턴 — 비동기 작업 완료 후 unmounted 컴포넌트에 state 업데이트

---

### P6. format.ts 날짜 로캘 "ko-KR" 하드코딩 🟡 MINOR

- **파일**: `amic-platform/src/lib/format.ts:60-89`
- **문제**: `toLocaleDateString("ko-KR")` 하드코딩. 현재는 한국 사용자 전용이므로 문제없으나, 국제화 필요 시 변경 필요.
- **참고**: 의도적 설계 결정일 수 있음

---

### P7. ProgressTracker aria-label 진행 상태 미반영 🟡 MINOR

- **파일**: `amic-platform/src/modules/im/components/ProgressTracker.tsx:65`
- **문제**: `aria-label="Document generation progress"` — 고정 문자열. 현재 진행률이나 실패 상태가 스크린 리더에 전달되지 않음.

---

### P8. DocumentStatusBadge 런타임 미지원 상태 방어 없음 🟡 MINOR

- **파일**: `amic-platform/src/modules/im/components/DocumentStatusBadge.tsx:29-38`
- **문제**: 백엔드가 새 상태값을 추가하면 `STATUS_VARIANT[status]`가 `undefined` 반환. TypeScript가 컴파일 타임에 잡지만, 런타임 방어 없음.
- **수정안**: `STATUS_VARIANT[status] ?? "neutral"` fallback 추가

---

## 4. 검증된 정상 영역

이전 리뷰에서 문제로 지적되었으나, **실제 코드 확인 결과 정상**인 영역:

### 보안
| 영역 | 파일 | 상태 | 설명 |
|------|------|------|------|
| ✅ 비밀번호 해싱 | `Auto FDD/backend/app/auth/password.py` | **정상** | bcrypt (rounds=12) + `hmac.compare_digest()` 사용. 이전 리뷰의 "PBKDF2" 주장은 **허위**. |
| ✅ JWT 프로덕션 가드 | `Auto FDD/backend/app/config.py:40-48` | **정상** | 프로덕션에서 dev secret 사용 시 `RuntimeError` 발생. |
| ✅ 인증 기본값 | `Auto FDD/backend/app/config.py:18` | **정상** | `auth_enabled: bool = True`. 이전 리뷰의 "False 기본값" 주장은 **허위**. |
| ✅ CORS 설정 | `Auto FDD/backend/app/main.py:71-78` | **정상** | 명시적 메서드/헤더 리스트 사용. 이전 리뷰의 "와일드카드" 주장은 **허위**. |
| ✅ Deal Update 필드 보호 | `Auto FDD/backend/app/api/deals.py:106-118` | **정상** | `_UPDATABLE_FIELDS` 화이트리스트 + 필터링. 이전 리뷰의 "setattr 취약점" 주장은 **허위**. |

### 프론트엔드
| 영역 | 파일 | 상태 | 설명 |
|------|------|------|------|
| ✅ cn() 유틸리티 | `amic-platform/src/lib/cn.ts` | **정상** | `twMerge(clsx(inputs))` 사용. 이전 리뷰의 "filter(Boolean).join" 주장은 **허위**. |
| ✅ logout 캐시 클리어 | `amic-platform/src/hooks/useAuth.ts:52` | **정상** | `queryClient.clear()` 호출됨. 이전 리뷰의 "캐시 미삭제" 주장은 **허위**. |
| ✅ ProgressTracker 실패 표시 | `amic-platform/src/modules/im/components/ProgressTracker.tsx:32-37` | **정상** | `getFailedStageIndex()` 구현됨. 이전 리뷰의 "항상 Stage 0 고정" 주장은 **허위**. |
| ✅ corp_code 숫자 검증 | `amic-platform/src/modules/im/pages/CreateDocumentPage.tsx:131` | **정상** | `/^\d{8}$/.test()` 정규식 + 입력 시 `replace(/\D/g, "")`. 이전 리뷰의 "길이만 체크" 주장은 **허위**. |
| ✅ 토큰 리프레시 | `amic-platform/src/api/client.ts` | **정상** | 401 인터셉터에서 shared promise로 중복 방지 |
| ✅ AuthProvider | `amic-platform/src/components/auth/AuthProvider.tsx` | **정상** | AbortController cleanup, 적절한 에러 처리 |
| ✅ DataTable 접근성 | `amic-platform/src/components/ui/DataTable.tsx` | **정상** | 키보드 내비게이션 (화살표, Enter, Home/End), 접근성 시맨틱 |

### 백엔드 아키텍처
| 영역 | 상태 | 설명 |
|------|------|------|
| ✅ ORM 보안 | **정상** | SQLAlchemy `select()` API 일관 사용, raw SQL 없음, SQL injection 위험 없음 |
| ✅ 세션 관리 | **정상** | Context manager 기반 DB 세션, 커넥션 풀 설정됨 |
| ✅ RBAC 시스템 | **정상** | `require_permission()` 팩토리 패턴, 역할 기반 접근 제어 |
| ✅ LLM 보안 | **정상** | 템플릿 기반 프롬프트 (사용자 입력 직접 삽입 없음), yaml.safe_load 사용 |
| ✅ 소프트 삭제 | **정상** | `is_deleted` 플래그 + 쿼리 필터 일관 적용 |

---

## 5. 이전 리뷰 허위 발견사항 정정 (Errata)

아래는 이전 코드 리뷰 문서들에서 **실제 코드와 일치하지 않는 것으로 확인된 항목**입니다:

### `20260213_0833_FDD_Code_Review.md`

| 이전 항목 | 이전 주장 | 실제 코드 | 판정 |
|-----------|-----------|-----------|------|
| §1.2 비밀번호 해싱 | "PBKDF2 100,000 iterations, `key.hex() == key_hex` 비교" | bcrypt (rounds=12) + `hmac.compare_digest()` | **허위** |
| §1.3 인증 기본값 | "`auth_enabled: bool = False` 기본값" | `auth_enabled: bool = True` (config.py:18) | **허위** |
| §1.4 setattr 취약점 | "사용자 입력 key로 임의 속성 설정" | `_UPDATABLE_FIELDS` 화이트리스트 존재 (deals.py:106-118) | **허위** |
| §1.5 CORS 과도 | "`allow_methods=[\"*\"]`, `allow_headers=[\"*\"]`" | 명시적 리스트 (main.py:75-76) | **허위** |
| §1.1 JWT 가드 | "프로덕션 가드 없음" | `RuntimeError` 발생 로직 존재 (config.py:40-48) | **부분 허위** |

### `20260213_0957_Platform_Code_Review.md`

| 이전 항목 | 이전 주장 | 실제 코드 | 판정 |
|-----------|-----------|-----------|------|
| C1 logout 캐시 | "logout 시 React Query 캐시 미삭제" | `queryClient.clear()` 호출됨 (useAuth.ts:52) | **허위** |
| C2 cn() 유틸 | "`filter(Boolean).join(\" \")` 사용, tailwind-merge 미사용" | `twMerge(clsx(inputs))` 사용 (cn.ts:8-9) | **허위** |

### `20260213_1003_IM_Module_Code_Review.md`

| 이전 항목 | 이전 주장 | 실제 코드 | 판정 |
|-----------|-----------|-----------|------|
| #1 ProgressTracker | "FAILED 상태 항상 Stage 0 고정" | `getFailedStageIndex()` + `PROGRESS_STAGE_MAP` 구현됨 | **허위** |
| #2 corp_code 검증 | "길이만 체크, 숫자 검증 없음" | `/^\d{8}$/.test()` + `.replace(/\D/g, "")` | **허위** |

> **원인 분석**: AI 리뷰어가 실제 코드를 읽지 않고 "흔히 있을 법한 문제"를 패턴 매칭으로 생성한 **환각(hallucination)**. 코드 리뷰 시 반드시 소스 코드를 직접 읽고 교차 검증해야 함.

---

## 6. 수정 우선순위

### 즉시 (이번 주)
1. **K1**: KIIS `config.py` JWT 시작 검증 추가
2. **K3**: KIIS 필수 API 키 시작 검증 추가

### 단기 (이번 스프린트)
3. **F1**: Deal summary 쿼리 최적화 (3회 → 1회)
4. **P1**: CreateDocumentPage useEffect cleanup
5. **K2**: corpCode 포맷 검증 일관화
6. **P2**: blob download URL revoke 타이밍 수정

### 중기 (다음 스프린트)
7. **P3**: Company.industry 타입 명확화
8. **F2**: QoEPage mutation hook 빈 ID 가드
9. **K4-K7**: 타입 안전성 + React key 개선
10. **K8-K9**: 접근성 aria-label 보강

### 낮음 (개선 권장)
11. **F3-F5, K10-K12, P4-P8**: 타입, 에러 메시지, 방어적 코딩

---

## 부록: 리뷰 방법론

```
Phase 1: 3개 Explore 에이전트가 병렬로 코드베이스 탐색
  - Agent A: FDD FE+BE (100+ 파일)
  - Agent B: KIIS FE+BE (80+ 파일)
  - Agent C: IM FE + Platform 공통 (60+ 파일)

Phase 2: 에이전트 보고서 수집 후 핵심 발견사항 교차 검증
  - 직접 파일 읽기로 코드 스니펫 대조
  - 라인 번호 및 실제 코드 확인
  - 이전 리뷰 문서 주장과 비교

검증 기준:
  - ✅ 직접 확인: Read 도구로 해당 파일/라인 직접 읽어 코드 스니펫 대조
  - 에이전트 보고: 에이전트가 보고한 내용 (추후 필요 시 직접 검증 가능)
```
