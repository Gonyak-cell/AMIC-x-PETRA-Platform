# FDD 모듈 전체 코드 리뷰 프롬프트

## Context

FDD(Financial Due Diligence) 모듈 전체에 대한 세부적이고 꼼꼼한 코드 리뷰를 수행하기 위한 프롬프트.
FDD는 4개 FastAPI 백엔드 + 1개 React 프론트엔드 모노레포 내에서 가장 복잡한 도메인 모듈로,
30개 API 라우터, 28개 ORM 모델, 30+ 서비스, 3개 LLM 에이전트, 12개 프론트엔드 훅을 포함.

---

## 프롬프트 (바로 사용 가능)

````
FDD 모듈 전체에 대해 실제 코드베이스를 기준으로 세부항목별 코드 리뷰를 수행해줘.
백엔드(`fdd/backend/`)와 프론트엔드(`amic-platform/src/modules/fdd/`) 모두 대상.

리뷰 시 반드시 실제 파일을 `Read`로 읽고, 주장에 대해 `Grep`으로 검증한 후 이슈를 보고할 것.
추측이나 기억에 의존한 이슈 보고를 절대 금지.

---

## 0단계: 리뷰 범위 및 사전 파악

아래 파일을 순서대로 `Read`로 읽어 전체 구조를 파악:

**백엔드 진입점 및 설정:**
- `fdd/backend/app/main.py` — 라우터 등록, 미들웨어, lifespan 이벤트
- `fdd/backend/app/config.py` — 환경 설정 (JWT, DB, CORS 등)
- `fdd/backend/app/core/exceptions.py` — 에러 계층 구조
- `fdd/backend/app/core/errors.py` — 에러 코드 체계 (1000~9019)

**인증/인가:**
- `fdd/backend/app/auth/rbac.py` — 역할-권한 매트릭스 (ADMIN/MANAGER/ANALYST/VIEWER/CLIENT)
- `fdd/backend/app/auth/dependencies.py` — `get_current_user`, `require_permission`
- `fdd/backend/app/api/auth.py` — 로그인/로그아웃/리프레시 엔드포인트
- `fdd/backend/app/services/auth_service.py` — 인증 비즈니스 로직

**프론트엔드 진입점:**
- `amic-platform/src/modules/fdd/FddRoutes.tsx` — 라우팅 구조
- `amic-platform/src/api/client.ts` — axios 인스턴스 설정

---

## 1단계: 백엔드 아키텍처 및 정합성 (Backend Architecture & Consistency)

### 1-1. 라우터-서비스-모델 계층 분리

아래 30개 라우터 파일을 **모두** 읽고 검증:
```
fdd/backend/app/api/
  auth.py, deals.py, uploads.py, mapping.py, qoe.py, nwc.py, debt.py,
  evidence.py, charts.py, issues.py, reports.py, templates.py, audit.py,
  jobs.py, retention.py, vdr.py, workflow.py, entities.py, exchange_rates.py,
  consolidation.py, industries.py, analysis.py, checklist.py, ralph.py,
  notifications.py, exports.py, webhooks.py, settings.py
```

각 라우터에 대해:
- [ ] 비즈니스 로직이 라우터에 직접 작성되어 있지 않은지 (서비스 계층으로 분리되었는지)
- [ ] `Depends(get_current_user)` 또는 `require_permission(Permission.XXX)` 로 보호되는지
- [ ] Pydantic 스키마로 요청/응답이 타입화되어 있는지 (raw dict 반환 금지)
- [ ] HTTP 상태 코드가 적절한지 (201 Created, 404 Not Found, 422 Validation Error 등)
- [ ] 에러 처리가 `FDDError` 계층 또는 `NotFoundError`/`ValidationError` 사용하는지

### 1-2. 데이터 모델 무결성

아래 28개 모델 파일을 **모두** 읽고 검증:
```
fdd/backend/app/models/
  deal.py, qoe.py, nwc.py, debt.py, issue.py, evidence.py, user.py,
  upload.py, template.py, tie_out.py, entity.py, vdr.py, exchange_rate.py,
  journal_entry.py, account_mapping.py, standard_line_item.py, job.py,
  export_record.py, notification.py, webhook.py, email_preference.py,
  token_blacklist.py, audit_log.py, report_version.py,
  fdd_checklist.py, analysis_run.py, ralph_session.py, __init__.py
```

각 모델에 대해:
- [ ] **금액 필드가 `NUMERIC(18,4)` (Decimal)인지** — `Float` 사용 시 Critical 이슈 (`NUMERIC`/`Decimal`은 FDD의 핵심 설계 원칙)
- [ ] 타임스탬프가 `DateTime(timezone=True)` 인지 (TIMESTAMPTZ, 절대 TIMESTAMP 금지)
- [ ] FK에 적절한 인덱스가 있는지 (`ix_{table}_{column}` 패턴)
- [ ] `__tablename__`이 snake_case 복수형인지
- [ ] soft delete 모델(`is_deleted`, `deleted_at`)이 일관되게 적용되는지
- [ ] cascade 삭제 설정이 적절한지 (고아 레코드 방지)
- [ ] JSONB 컬럼 사용 시 기본값과 nullable 설정이 적절한지

### 1-3. Pydantic 스키마 일관성

모든 스키마 파일을 읽고:
- [ ] `model_config = ConfigDict(from_attributes=True)` 사용 여부 (ORM→스키마 변환)
- [ ] `Create`/`Update`/`Read`(Response) 패턴 분리 여부
- [ ] 금액 필드가 `Decimal` 타입인지 (`float` 사용 금지)
- [ ] nullable 필드에 `None` 기본값이 명시되어 있는지
- [ ] `Field(...)` 제약 조건이 적절한지 (min_length, max_length, ge, le 등)

### 1-4. 서비스 계층 품질

핵심 서비스 모듈을 읽고:
```
fdd/backend/app/services/
  auth_service.py, ingestion/parser.py, ingestion/validator.py,
  qoe/engine.py, nwc/engine.py, debt/engine.py, mapping/engine.py,
  report/report_service.py, evidence/index.py,
  llm/client.py, llm/routing.py,
  analysis/orchestrator.py, checklist_service.py, ralph_service.py
```

- [ ] **엔진 순수 함수 패턴**: QoE/NWC/Debt 엔진이 `(입력) → (결과, 증거링크)` 순수 함수인지 (DB 사이드 이펙트 없어야 함)
- [ ] **LLM 클라이언트**: 타임아웃 설정, 에러 핸들링, 재시도 로직 존재 여부
- [ ] **데이터 파싱**: Excel 파싱 시 셀 타입 검증, 빈 행/열 처리, 인코딩 처리
- [ ] **N+1 쿼리 방지**: `joinedload()` / `selectinload()` 적절 사용
- [ ] **트랜잭션 경계**: 여러 DB 작업을 하나의 트랜잭션으로 묶고 있는지, 실패 시 롤백 보장

### 1-5. LLM 에이전트 안전성

```
fdd/backend/app/agents/
  base.py, qoe_analyzer.py, coa_mapper.py, guardrails.py
```

- [ ] **가드레일**: LLM 응답에서 환각(hallucination) 검증이 있는지 — 금액 일치, 엔트리 ID 존재 확인, 신뢰도 임계값
- [ ] **프롬프트 주입 방어**: 사용자 입력이 프롬프트에 직접 삽입되지 않는지
- [ ] **비용 통제**: 토큰 사용량 추적, 최대 토큰 제한 설정
- [ ] **에러 복구**: LLM API 실패 시 재시도 또는 폴백 로직

---

## 2단계: 프론트엔드 품질 (Frontend Quality)

### 2-1. 페이지 구조 및 데이터 페칭

아래 11개 페이지를 **모두** 읽고 검증:
```
amic-platform/src/modules/fdd/pages/
  DealListPage.tsx, DealSetupPage.tsx, DealSetupWizardPage.tsx,
  DealWorkspacePage.tsx, WorkflowOverviewPage.tsx, UploadPage.tsx,
  DefinitionPage.tsx, MappingPage.tsx, QoEPage.tsx, NWCPage.tsx,
  NetDebtPage.tsx, IssuesPage.tsx, ReportPage.tsx, ChecklistReviewPage.tsx,
  VdrPage.tsx
```

각 페이지에 대해:
- [ ] 로딩 상태 처리: `isLoading` 시 Spinner 또는 Skeleton 렌더링
- [ ] 에러 상태 처리: 데이터 페칭 실패 시 사용자에게 적절한 피드백
- [ ] 빈 상태 처리: 데이터가 없을 때 EmptyState 컴포넌트 또는 안내 메시지
- [ ] 폼 유효성 검증: 클라이언트 사이드 검증 + 서버 에러 토스트
- [ ] 접근성: 인터랙티브 요소에 `aria-*` 속성, 키보드 내비게이션, 포커스 관리
- [ ] TypeScript 엄격성: `any` 사용 여부, 불필요한 type assertion (`as`) 여부
- [ ] 메모이제이션: 비용이 큰 계산에 `useMemo`, 콜백에 `useCallback` 적절 사용

### 2-2. 훅 패턴 및 캐시 전략

아래 12개 훅을 **모두** 읽고 검증:
```
amic-platform/src/modules/fdd/hooks/
  useDeals.ts, useUploads.ts, useDefinitions.ts, useMapping.ts,
  useQoE.ts, useDebt.ts, useNWC.ts, useIssues.ts, useVdr.ts,
  useReportVersions.ts, useAnalysis.ts, useRalphLoop.ts, useChecklist.ts
```

각 훅에 대해:
- [ ] **queryKey 고유성**: `["fdd", "{entity}", dealId, ...params]` 패턴 준수 여부
- [ ] **캐시 무효화**: mutation `onSuccess`에서 관련 쿼리 `invalidateQueries` 호출 여부
- [ ] **낙관적 업데이트**: 사용 시 `onError`에서 롤백 로직 존재 여부
- [ ] **에러 핸들링**: `onError`에서 `toast.error()` + `console.error()` 패턴
- [ ] **enabled 조건**: dealId가 없을 때 쿼리 실행 방지 (`enabled: !!dealId`)
- [ ] **staleTime 설정**: 참조 데이터(standard-line-items 등)에 긴 캐시 설정
- [ ] **폴링 패턴**: Ralph Loop 진행 상태처럼 폴링이 필요한 훅에서 `refetchInterval` 사용 및 완료 시 중단 로직

### 2-3. 타입 안전성 (FE ↔ BE 계약)

아래 9개 타입 파일을 **모두** 읽고, **대응하는 백엔드 Pydantic 스키마와 1:1 비교**:
```
FE 타입                              ↔  BE 스키마
types/deal.ts                        ↔  schemas/deal.py
types/qoe.ts                         ↔  schemas/qoe.py (또는 관련 파일)
types/nwc.ts                         ↔  schemas/nwc.py
types/debt.ts                        ↔  schemas/debt.py
types/mapping.ts                     ↔  schemas/mapping.py
types/issue.ts                       ↔  schemas/issue.py
types/evidence.ts                    ↔  schemas/evidence.py
types/report-version.ts              ↔  schemas/report_version.py
types/vdr.ts                         ↔  schemas/vdr.py
```

비교 항목:
- [ ] **필드명 일치**: snake_case(BE) → camelCase(FE) 자동 변환이 되는지, 아니면 동일한지
- [ ] **필드 타입 일치**: `Decimal`(BE) → `string`(FE) 패턴 준수 여부 (금액은 반드시 string)
- [ ] **nullable 일치**: BE에서 `Optional[X]`인 필드가 FE에서도 `X | null`인지
- [ ] **enum 값 일치**: BE의 `StrEnum` 값과 FE의 `type = "A" | "B"` 값이 완전히 동일한지
- [ ] **누락 필드**: BE 응답에 있는데 FE 타입에 없는 필드, 또는 그 반대
- [ ] **API 경로 일치**: 훅의 axios 호출 URL이 백엔드 라우터 데코레이터 경로와 일치하는지

### 2-4. 컴포넌트 품질

```
amic-platform/src/modules/fdd/components/
  deal/DealSetupWizard.tsx, deal/ScopeSelector.tsx,
  checklist/ChecklistItemCard.tsx, checklist/ChecklistCategorySection.tsx,
  checklist/ChecklistSummaryBar.tsx, checklist/VdrSourceLinks.tsx,
  report/ReportVersionList.tsx, report/ReportVersionCard.tsx,
  vdr/VdrFolderTree.tsx, vdr/VdrFolderItem.tsx
```

- [ ] Props 인터페이스 명확성 (모든 prop에 타입 + 설명)
- [ ] 컴포넌트 단일 책임 (하나의 관심사만 처리)
- [ ] 이벤트 핸들러 `useCallback` 래핑 여부 (리렌더링 최적화)
- [ ] 재귀 컴포넌트(VdrFolderTree) 깊이 제한 또는 가상화 적용

---

## 3단계: 도메인 특화 검증 (FDD Domain-Specific)

### 3-1. 재무 계산 정확성

FDD의 핵심은 재무 데이터 정확성. 아래를 집중 검증:

- [ ] **Decimal 일관성**: 전체 코드에서 금액 관련 연산이 `Decimal`로 수행되는지 (`float` 사용 시 Critical)
  - `Grep`으로 `float` 타입 사용처 검색: 모델, 스키마, 서비스에서 금액 필드에 `float` 사용 여부
- [ ] **반올림 규칙**: 계산 결과 반올림 시 `ROUND_HALF_UP` 또는 명시적 규칙 사용 여부
- [ ] **통화 변환**: 다중 통화 처리 시 환율 적용 순서, 반올림, 기준일 일관성
- [ ] **EBITDA Bridge 균형 검증**: QoE 계산에서 `reported_ebitda + total_adjustments == adjusted_ebitda` 검증 로직 존재 여부
- [ ] **NWC Peg 계산**: 기준값(target) 대비 실제 NWC 차이 계산의 정확성
- [ ] **Net Debt 분류**: 부채/현금 분류 기준의 명확성, 경계 사례(리스, 전환사채 등) 처리

### 3-2. 감사 추적 (Audit Trail)

FDD에서 모든 데이터 변경은 추적 가능해야 함:
- [ ] `AuditLog` 모델에 CRUD 모든 작업이 기록되는지
- [ ] 누가(actor), 언제(timestamp), 무엇을(entity), 어떻게(action), 이전값/이후값(old/new) 기록 여부
- [ ] 감사 로그가 삭제 불가능한지 (soft delete도 아닌 진짜 삭제 불가)
- [ ] 스냅샷 버전 관리: 계산 결과가 입력 데이터와 연결(evidence link)되는지

### 3-3. 한국 규제 로직

`fdd/backend/app/industry/korea/regulatory.py` 검증:
- [ ] 15개 규제 항목이 최신 법률을 반영하는지 (공정거래법, 개인정보보호법 등)
- [ ] 산업별 분류(tech, healthcare, manufacturing, financial_services, logistics)가 적절한지
- [ ] 규제 영향이 EBITDA/Net Debt 조정에 올바르게 매핑되는지

---

## 4단계: 보안 (Security)

### 4-1. 인증/인가 완전성

- [ ] **모든 API 엔드포인트에 인증 적용**: 공개 엔드포인트(`/health`, `/auth/login`)를 제외한 모든 라우터에 `get_current_user` 또는 `require_permission` 존재 확인
  - `Grep`으로 `@router.get`, `@router.post` 등에서 `Depends` 없는 엔드포인트 검색
- [ ] **RBAC 매트릭스 적절성**: 5개 역할(ADMIN/MANAGER/ANALYST/VIEWER/CLIENT)별 권한이 최소 권한 원칙을 준수하는지
- [ ] **CLIENT 역할 제한**: CLIENT는 `DEAL_READ_ASSIGNED`만 가능한지, 다른 딜 접근이 차단되는지
- [ ] **토큰 블랙리스트**: 로그아웃 시 JTI가 `TokenBlacklist`에 추가되는지, 블랙리스트 확인이 모든 인증 경로에서 수행되는지

### 4-2. 데이터 보호

- [ ] **하드코딩된 시크릿**: `Grep`으로 `password`, `secret`, `key`, `token` 등이 코드에 하드코딩되어 있지 않은지
- [ ] **JWT 설정**: `jwt_secret`이 환경변수에서 읽히는지, 기본값(`dev-secret`)이 프로덕션에서 사용되지 않도록 검증 로직 존재 여부
- [ ] **쿠키 보안**: `httponly=True`, `secure=True`(프로덕션), `samesite="lax"` 설정 확인
- [ ] **SQL 인젝션**: raw SQL 사용처가 있는지, 있다면 파라미터화 되었는지
- [ ] **파일 업로드 보안**: 파일명 검증, 확장자 화이트리스트, 파일 크기 제한, 경로 순회(path traversal) 방지
- [ ] **데이터 마스킹**: 민감 데이터(재무 수치, 고객 정보)가 로그에 노출되지 않는지

### 4-3. AUTH_ENABLED=False 리스크

- [ ] `AUTH_ENABLED=False` 시 DEV_USER(ADMIN 권한)가 반환되는 코드 경로 확인
- [ ] 프로덕션에서 `AUTH_ENABLED=False`가 불가능하도록 검증 로직 존재 여부
- [ ] DEV_USER가 모든 권한을 가지는 것의 테스트 환경 내 적절성

---

## 5단계: 안정성 및 인프라 (Stability & Infrastructure)

### 5-1. 에러 복원력

- [ ] **RFC 7807 일관성**: 모든 에러 응답이 `{type, title, status, detail, code, severity}` 형식인지
- [ ] **예외 핸들러 등록**: `main.py`에서 `FDDError`, `RateLimitExceeded` 핸들러가 등록되어 있는지
- [ ] **미처리 예외**: 서비스 레이어에서 발생할 수 있는 예외가 라우터에서 적절히 잡히는지
- [ ] **외부 서비스 장애**: LLM API, PPTX 서비스 호출 실패 시 적절한 폴백/에러 반환
- [ ] **Rate Limiting**: 60req/min 전역 제한의 적절성, 분석 엔드포인트에 별도 제한 필요 여부

### 5-2. 데이터베이스

- [ ] **Alembic 마이그레이션**: 17개 마이그레이션 파일 각각에 `upgrade()`와 `downgrade()` 존재 여부
- [ ] **마이그레이션 순서**: 의존 관계가 올바른지 (FK 대상 테이블이 먼저 생성되는지)
- [ ] **인덱스 전략**: `010_add_fk_indexes.py`의 인덱스가 주요 쿼리 패턴을 커버하는지
- [ ] **동기식 SQLAlchemy**: FDD는 sync SQLAlchemy인데, 다른 백엔드(deal-mgmt, kiis, im)는 async — 성능 병목 가능성 분석
- [ ] **커넥션 풀링**: 설정 존재 여부, 풀 사이즈 적절성

### 5-3. 테스트 커버리지

`fdd/backend/tests/` 전체를 읽고:
- [ ] **API 테스트**: 모든 주요 엔드포인트에 대한 테스트 존재 여부
- [ ] **인증 테스트**: 정상 로그인, 잘못된 비밀번호, 만료 토큰, 권한 부족 시나리오
- [ ] **엔진 테스트**: QoE/NWC/Debt 계산 엔진의 순수 함수 테스트 (엣지 케이스 포함)
- [ ] **Excel 파싱 테스트**: 다양한 형식의 Excel 파일 처리 (빈 행, 잘못된 타입, 인코딩 문제)
- [ ] **fixture 품질**: conftest.py의 25+ fixture가 독립적이고 재사용 가능한지

### 5-4. CI/CD 갭

- [ ] **FDD 백엔드 CI 부재**: `.github/workflows/ci.yml`에 FDD 전용 lint/test 작업이 있는지 확인
  - deal-mgmt, kiis는 CI에 있지만 FDD는 없을 수 있음 → 있다면 검증, 없다면 Critical 이슈로 보고

---

## 6단계: 코드 수준 및 깊이 (Code Quality & Depth)

### 6-1. 아키텍처 설계 품질

- [ ] **순수 엔진 함수 패턴**: QoE/NWC/Debt 엔진이 `(inputs) → (result, evidence_links)` 시그니처를 유지하는지 (DB 의존 없이 테스트 가능해야 함)
- [ ] **스냅샷 버전 관리**: 계산 결과가 입력 해시와 연결되어 재현 가능한지
- [ ] **Report IR 패턴**: 보고서가 중간 표현(IR)을 거쳐 최종 형식(PPTX/DOCX)으로 변환되는지
- [ ] **관심사 분리**: 서비스 모듈이 각자의 도메인에만 집중하는지 (예: QoE 엔진이 NWC 로직을 포함하지 않는지)
- [ ] **JSONB 활용**: deal definitions가 JSONB로 유연하게 저장되면서도 검증이 되는지

### 6-2. 코드 가독성

- [ ] 함수 길이: 50줄 초과 함수 식별 (분리 권장)
- [ ] 네이밍: 도메인 용어(EBITDA, QoE, NWC, Tie-out, Peg)가 일관되게 사용되는지
- [ ] 주석: 복잡한 재무 로직에 비즈니스 맥락 설명 주석이 있는지
- [ ] 타입 힌트: 모든 함수 시그니처에 타입 힌트 완비 여부 (mypy strict 준수)

### 6-3. 프론트엔드 UX 완성도

- [ ] **워크플로우 흐름**: DealPhase(MOU→VDR_SETUP→DATA_UPLOAD→ANALYSIS→CHECKLIST_REVIEW→REPORTING) 순서대로 사용자 안내가 되는지
- [ ] **파일 업로드 UX**: 드래그앤드롭, 진행률 표시, 업로드 실패 재시도
- [ ] **대용량 데이터**: GL 엔트리가 수만 건일 때 페이지네이션/가상 스크롤 적용 여부
- [ ] **낙관적 UI**: 승인/거부 같은 상태 변경에 즉시 UI 반영 + 실패 시 롤백

---

## 7단계: 허위 리뷰 방지 검증 (Anti-False-Positive)

**모든 이슈를 보고하기 전에 반드시 아래 5개 항목을 검증.**
하나라도 실패하면 해당 이슈를 삭제하거나 신뢰도를 LOW로 하향.

- [ ] **SC-1 도달 가능성**: 이 코드가 실제로 실행되는 경로에 있는가?
- [ ] **SC-2 부재 주장 검증**: "X가 없다"는 주장을 `Grep`으로 전체 코드베이스에서 확인했는가?
- [ ] **SC-3 프레임워크 처리**: FastAPI, SQLAlchemy, React Query가 이미 처리하는 부분을 지적하고 있지 않은가?
- [ ] **SC-4 의도된 패턴**: 기존 코드베이스에서 동일한 패턴이 사용되고 있지 않은가?
- [ ] **SC-5 수정 안전성**: 제안한 수정이 타입 에러, 런타임 에러, 다른 기능 파괴를 야기하지 않는가?

---

## 출력 형식

### 리뷰 요약
```
- 총 이슈 수: N개 (Critical: X, Major: Y, Moderate: Z, Minor: W)
- 카테고리별: 아키텍처 N, 도메인 N, 보안 N, 안정성 N, 타입계약 N, 코드품질 N
- 전체 평가: {한 줄 요약}
```

### 이슈 목록 (심각도 내림차순)

각 이슈:
```
### [{심각도}] {이슈 제목}
- **위치**: `파일경로:라인번호`
- **카테고리**: 아키텍처 / 도메인(재무) / 보안 / 안정성 / 타입계약 / 코드품질
- **신뢰도**: HIGH / MEDIUM / LOW
- **셀프 체크**: SC-1(✓) SC-2(✓) SC-3(✓) SC-4(✓) SC-5(✓)
- **근거**: (실제 Read로 읽은 코드 스니펫 — 기억이나 재구성 금지)
- **설명**: 무엇이 문제인지
- **영향**: 문제가 발생하면 어떤 일이 일어나는지
- **수정 제안**: 구체적인 코드 변경 방향
```

### FE ↔ BE 타입 계약 대조표

| FE 타입 파일 | BE 스키마 파일 | 일치 여부 | 불일치 필드 |
|-------------|-------------|---------|-----------|
| types/deal.ts | schemas/deal.py | ✅/⚠️/❌ | {상세} |
| ... | ... | ... | ... |

## 핵심 원칙
- **추측 금지**: 모든 주장은 `Read`/`Grep` 확인 기반
- **증거 첨부 필수**: 실제 코드 스니펫으로 근거 제시
- **허위 양성 방지**: SC-1~5 셀프 체크 통과한 이슈만 보고
- **FDD 도메인 우선**: 일반적 코드 품질보다 재무 계산 정확성, 감사 추적, 데이터 무결성을 더 높은 우선순위로 검증
- **실제 파일 전체 읽기**: 변경 줄만이 아니라 파일 전체 + 관련 의존 파일까지 읽기
````
