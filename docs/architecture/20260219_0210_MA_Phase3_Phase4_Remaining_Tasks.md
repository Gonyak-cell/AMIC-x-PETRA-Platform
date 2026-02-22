# MA 워크플로우 — Phase 3 + Phase 4 남은 작업 상세

**작성일**: 2026-02-19 02:08
**기준 문서**: `docs/architecture/20260219_0046_MA_Workflow_Implementation_Plan.md`
**현재 브랜치**: `feat/ma-workflow`
**최신 커밋**: `618109a` (Phase 0~2 완료)

---

## 0. 현재 완료 상태

### Phase 0~2 완료 산출물

| Phase | 상태 | 핵심 산출물 |
|:---|:---:|:---|
| **Phase 0**: 아키텍처 준비 | ✅ | deal-mgmt 서비스, Docker/nginx/Vite 통합 |
| **Phase 1**: MVP Core | ✅ | Transaction CRUD, 7단계 워크플로우, 수임/WGL/매수자/타임라인, E2E 25/25 |
| **Phase 2**: NDA/Bids/DD | ✅ | NDA 관리, IOI/LOI 비교, DD 체크리스트, 인라인 편집, 85/85 테스트 |
| **Phase 2 UX 개선** | ✅ | styled `<Select>` 전환, 인라인 셀 편집 8개 필드, DD 워크스트림 필터 |

### 현재 파일 통계

- 백엔드: 47개 파일 (모델 11, 스키마 9, 라우터 9, 서비스 3, 코어 4, 마이그레이션 2, 테스트 9)
- 프론트엔드: 16개 파일 (타입 8, 훅 4, 페이지 3, 라우트 1)
- API 엔드포인트: ~38개
- DB 테이블: 9개
- Enum 타입: 14개
- UI 탭: 8개

### E2E 검증 결과 (2026-02-19)

- Docker: `amic-deal-mgmt-api` healthy, `amic-deal-mgmt-db` healthy
- `GET /health` → 200 ✅
- API 인증(JWT) 정상 동작 (401 for unauthenticated)

---

## 1. 이미 완료된 작업 (이번 세션)

**enums.py에 Phase 3+4 Enum 추가 완료** (파일 수정됨, 미커밋):

### Phase 3 Enums (5개)

| Enum | 값 |
|:---|:---|
| `ContractType` | SPA, AMENDMENT, SIDE_LETTER, SHAREHOLDERS_AGREEMENT, ESCROW_AGREEMENT, OTHER |
| `ContractStatus` | DRAFT, UNDER_REVIEW, PENDING_SIGNATURE, PARTIALLY_SIGNED, FULLY_EXECUTED, TERMINATED |
| `SignatureStatus` | NOT_REQUIRED, PENDING, SIGNED, DECLINED |
| `ClosingCategory` | REGULATORY, LEGAL, FINANCIAL, CORPORATE, CONDITION_PRECEDENT, FUND_FLOW, OTHER |
| `ClosingConditionStatus` | PENDING, IN_PROGRESS, COMPLETED, WAIVED, NOT_APPLICABLE |

### Phase 4 Enums (5개)

| Enum | 값 |
|:---|:---|
| `PMICategory` | INTEGRATION_PLAN, DAY_ONE, FIRST_100_DAYS, SYNERGY, CULTURE, IT_SYSTEMS, HR, COMMUNICATION, OTHER |
| `PMITaskStatus` | NOT_STARTED, IN_PROGRESS, COMPLETED, BLOCKED, DEFERRED |
| `PMIPriority` | CRITICAL, HIGH, MEDIUM, LOW |
| `EarnoutStatus` | PENDING, MEASUREMENT_PERIOD, ACHIEVED, PARTIALLY_ACHIEVED, MISSED, DISPUTED |
| `EarnoutMetric` | REVENUE, EBITDA, NET_INCOME, CUSTOMER_COUNT, CONTRACT_VALUE, WORKING_CAPITAL, OTHER |

---

## 2. Phase 3: AI 계약분석 / 전자서명 / SPA / 클로징

### 2.1 백엔드 모델 (신규 3개 파일)

#### `deal-mgmt/app/models/contract.py`

```python
class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    id: UUID (PK)
    transaction_id: UUID (FK → transactions.id)
    contract_type: ContractType           # SPA, AMENDMENT, SIDE_LETTER, ...
    status: ContractStatus                # DRAFT → UNDER_REVIEW → PENDING_SIGNATURE → FULLY_EXECUTED
    title: str                            # 계약서 제목
    description: str | None
    counterparty_name: str | None         # 상대방 (매수자명 등)
    effective_date: str | None            # 발효일
    expiry_date: str | None               # 만료일
    current_version: int = 1              # 최신 버전 번호
    document_url: str | None              # 최신 문서 URL
    seller_signature: SignatureStatus     # 매도측 서명 상태
    buyer_signature: SignatureStatus      # 매수측 서명 상태
    ai_analysis_summary: Text | None      # AI 분석 결과 요약
    ai_risk_flags: JSONB | None           # AI 리스크 플래그 [{clause, risk_level, description}]
    notes: Text | None
```

#### `deal-mgmt/app/models/contract_version.py`

```python
class ContractVersion(Base, TimestampMixin):
    __tablename__ = "contract_versions"
    id: UUID (PK)
    contract_id: UUID (FK → contracts.id)
    version_number: int                   # 1, 2, 3, ...
    changes_summary: str | None           # 변경 요약
    document_url: str                     # 해당 버전 문서 URL
    created_by_email: str | None          # 업로드한 사람
    file_size_bytes: int | None
    file_name: str | None
```

#### `deal-mgmt/app/models/closing_checklist.py`

```python
class ClosingChecklist(Base, TimestampMixin):
    __tablename__ = "closing_checklists"
    id: UUID (PK)
    transaction_id: UUID (FK → transactions.id)
    category: ClosingCategory             # REGULATORY, LEGAL, FINANCIAL, ...
    title: str
    description: str | None
    status: ClosingConditionStatus        # PENDING → IN_PROGRESS → COMPLETED/WAIVED
    responsible_party: str | None         # 담당자/담당팀
    responsible_email: str | None
    due_date: str | None
    completed_date: str | None
    document_url: str | None              # 증빙 서류
    notes: Text | None
    sort_order: int = 0
```

### 2.2 백엔드 스키마 (신규 2개 파일)

#### `deal-mgmt/app/schemas/contract.py`

| Schema | 용도 |
|:---|:---|
| `ContractOut` | 계약서 조회 (all fields + timestamps) |
| `ContractCreate` | 계약서 생성 (title, contract_type, counterparty_name, ...) |
| `ContractUpdate` | 계약서 수정 (status, signatures, ai_analysis, ...) |
| `ContractVersionOut` | 버전 조회 |
| `ContractVersionCreate` | 버전 추가 (document_url, changes_summary) |
| `ContractSummary` | 계약서 요약 (total, by_type, by_status, pending_signatures) |
| `AIAnalysisResult` | AI 분석 결과 (clauses: [{clause, risk_level, description}]) |

#### `deal-mgmt/app/schemas/closing.py`

| Schema | 용도 |
|:---|:---|
| `ClosingChecklistOut` | 클로징 항목 조회 |
| `ClosingChecklistCreate` | 항목 생성 (category, title, responsible, due_date) |
| `ClosingChecklistUpdate` | 항목 수정 (status, completed_date, document_url) |
| `ClosingChecklistSummary` | 요약 (total, by_category, by_status, completion_rate) |

### 2.3 백엔드 라우터 (신규 2개 파일)

#### `deal-mgmt/app/routers/contracts.py`

| Method | Path | 설명 |
|:---|:---|:---|
| GET | `/transactions/{txn_id}/contracts` | 계약서 목록 |
| GET | `/transactions/{txn_id}/contracts/summary` | 계약서 요약 |
| POST | `/transactions/{txn_id}/contracts` | 계약서 생성 |
| PATCH | `/transactions/{txn_id}/contracts/{id}` | 계약서 수정 |
| DELETE | `/transactions/{txn_id}/contracts/{id}` | 계약서 삭제 |
| GET | `/transactions/{txn_id}/contracts/{id}/versions` | 버전 목록 |
| POST | `/transactions/{txn_id}/contracts/{id}/versions` | 새 버전 추가 |
| POST | `/transactions/{txn_id}/contracts/{id}/analyze` | AI 분석 트리거 |

#### `deal-mgmt/app/routers/closing.py`

| Method | Path | 설명 |
|:---|:---|:---|
| GET | `/transactions/{txn_id}/closing` | 클로징 항목 목록 |
| GET | `/transactions/{txn_id}/closing/summary` | 클로징 요약 |
| POST | `/transactions/{txn_id}/closing` | 항목 생성 |
| PATCH | `/transactions/{txn_id}/closing/{id}` | 항목 수정 |
| DELETE | `/transactions/{txn_id}/closing/{id}` | 항목 삭제 |

### 2.4 백엔드 서비스 (신규 1개 파일)

#### `deal-mgmt/app/services/contract_analysis_service.py`

```python
async def analyze_contract(contract_id: UUID, document_url: str) -> AIAnalysisResult:
    """
    MVP: 계약서 텍스트에서 핵심 조항 추출 + 리스크 플래깅 (stub).
    향후: OpenAI/Claude API 연동하여 실제 AI 분석 수행.

    분석 항목:
    - 핵심 조항 식별 (가격, 진술보증, 면책, 해제조건)
    - 리스크 플래깅 (불리한 조항, 누락 조항)
    - 조항별 요약 생성
    """
    # MVP: stub 반환 — "AI 분석 기능은 향후 연동 예정입니다"
    return AIAnalysisResult(
        status="PENDING",
        message="AI 계약 분석 기능은 향후 업데이트에서 제공됩니다.",
        clauses=[]
    )
```

### 2.5 Alembic 마이그레이션

#### `deal-mgmt/migrations/versions/003_phase3_contracts_closing.py`

- **신규 테이블**: `contracts`, `contract_versions`, `closing_checklists`
- **신규 Enum 타입**: contracttype, contractstatus, signaturestatus, closingcategory, closingconditionstatus
- **FK 관계**: contracts → transactions, contract_versions → contracts, closing_checklists → transactions

### 2.6 프론트엔드 타입 (신규 2개 파일)

#### `amic-platform/src/modules/ma/types/contract.ts`

```typescript
export type ContractType = "SPA" | "AMENDMENT" | "SIDE_LETTER" | "SHAREHOLDERS_AGREEMENT" | "ESCROW_AGREEMENT" | "OTHER";
export type ContractStatus = "DRAFT" | "UNDER_REVIEW" | "PENDING_SIGNATURE" | "PARTIALLY_SIGNED" | "FULLY_EXECUTED" | "TERMINATED";
export type SignatureStatus = "NOT_REQUIRED" | "PENDING" | "SIGNED" | "DECLINED";

export interface Contract {
  id: string;
  transaction_id: string;
  contract_type: ContractType;
  status: ContractStatus;
  title: string;
  description: string | null;
  counterparty_name: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  current_version: number;
  document_url: string | null;
  seller_signature: SignatureStatus;
  buyer_signature: SignatureStatus;
  ai_analysis_summary: string | null;
  ai_risk_flags: AIRiskFlag[] | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContractVersion { ... }
export interface ContractCreate { ... }
export interface ContractUpdate { ... }
export interface ContractSummary { ... }
export interface AIRiskFlag { clause: string; risk_level: string; description: string; }
export interface AIAnalysisResult { status: string; message: string; clauses: AIRiskFlag[]; }
```

#### `amic-platform/src/modules/ma/types/closing.ts`

```typescript
export type ClosingCategory = "REGULATORY" | "LEGAL" | "FINANCIAL" | "CORPORATE" | "CONDITION_PRECEDENT" | "FUND_FLOW" | "OTHER";
export type ClosingConditionStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "WAIVED" | "NOT_APPLICABLE";

export interface ClosingChecklistItem { ... }
export interface ClosingChecklistCreate { ... }
export interface ClosingChecklistUpdate { ... }
export interface ClosingChecklistSummary { total; by_category; by_status; completion_rate; }
```

### 2.7 프론트엔드 훅 (신규 2개 파일)

#### `amic-platform/src/modules/ma/hooks/useContracts.ts`

| 훅 | 설명 |
|:---|:---|
| `useContracts(txnId)` | 계약서 목록 조회 |
| `useContractSummary(txnId)` | 계약서 요약 |
| `useContractVersions(txnId, contractId)` | 버전 목록 |
| `useCreateContract(txnId)` | 계약서 생성 mutation |
| `useUpdateContract(txnId)` | 계약서 수정 mutation |
| `useDeleteContract(txnId)` | 계약서 삭제 mutation |
| `useCreateContractVersion(txnId, contractId)` | 버전 추가 mutation |
| `useAnalyzeContract(txnId)` | AI 분석 트리거 mutation |

#### `amic-platform/src/modules/ma/hooks/useClosing.ts`

| 훅 | 설명 |
|:---|:---|
| `useClosingChecklist(txnId)` | 클로징 항목 목록 |
| `useClosingSummary(txnId)` | 클로징 요약 |
| `useCreateClosingItem(txnId)` | 항목 생성 mutation |
| `useUpdateClosingItem(txnId)` | 항목 수정 mutation |
| `useDeleteClosingItem(txnId)` | 항목 삭제 mutation |

### 2.8 TransactionWorkspacePage 탭 추가

| 탭 ID | 라벨 | 배지 | Phase |
|:---|:---|:---|:---:|
| `contracts` | 계약/SPA | contracts.length | **3** |
| `closing` | 클로징 | closingItems.length | **3** |

**계약/SPA 탭 UI**:
- KPI 요약 카드 (총 계약서, 서명 대기, 실행 완료, AI 분석 대기)
- DataTable: title, contract_type, status (인라인 Select), counterparty, version, signatures (sell/buy 배지), effective_date
- 버전 히스토리 (확장 패널 or 모달)
- AI 분석 트리거 버튼 + 결과 표시 (risk flags 배지)

**클로징 탭 UI**:
- KPI 요약 카드 (총 항목, 완료율 진행바, 카테고리별 현황)
- 카테고리 필터 칩 바 (DD 워크스트림 필터와 동일 패턴)
- DataTable: title, category, status (인라인 Select), responsible, due_date (인라인 date), completed_date, document_url
- 진행률 바 (전체 + 카테고리별)

---

## 3. Phase 4: PMI / 어닝아웃 / 연계 포인트

### 3.1 백엔드 모델 (신규 2개 파일)

#### `deal-mgmt/app/models/pmi_task.py`

```python
class PMITask(Base, TimestampMixin):
    __tablename__ = "pmi_tasks"
    id: UUID (PK)
    transaction_id: UUID (FK → transactions.id)
    category: PMICategory
    title: str
    description: str | None
    status: PMITaskStatus                 # NOT_STARTED → IN_PROGRESS → COMPLETED
    priority: PMIPriority                 # CRITICAL, HIGH, MEDIUM, LOW
    assignee_name: str | None
    assignee_email: str | None
    start_date: str | None
    due_date: str | None
    completed_date: str | None
    dependency_ids: JSONB | None          # [task_id, ...] 의존 관계
    notes: Text | None
    sort_order: int = 0
```

#### `deal-mgmt/app/models/earnout.py`

```python
class EarnoutMilestone(Base, TimestampMixin):
    __tablename__ = "earnout_milestones"
    id: UUID (PK)
    transaction_id: UUID (FK → transactions.id)
    title: str
    description: str | None
    metric: EarnoutMetric                 # REVENUE, EBITDA, NET_INCOME, ...
    target_value: Numeric                 # 목표 수치
    actual_value: Numeric | None          # 실제 수치
    currency: str = "KRW"
    measurement_start: str | None         # 측정 시작일
    measurement_end: str | None           # 측정 종료일
    payment_amount: Numeric | None        # 지급 금액
    payment_date: str | None              # 지급일
    status: EarnoutStatus                 # PENDING → MEASUREMENT_PERIOD → ACHIEVED/MISSED
    notes: Text | None
```

### 3.2 백엔드 스키마 (신규 2개 파일)

#### `deal-mgmt/app/schemas/pmi.py`

| Schema | 용도 |
|:---|:---|
| `PMITaskOut` | PMI 태스크 조회 |
| `PMITaskCreate` | 태스크 생성 (category, title, priority, assignee, dates) |
| `PMITaskUpdate` | 태스크 수정 (status, priority, dates, assignee) |
| `PMISummary` | 요약 (total, by_category, by_status, by_priority, completion_rate) |

#### `deal-mgmt/app/schemas/earnout.py`

| Schema | 용도 |
|:---|:---|
| `EarnoutOut` | 어닝아웃 조회 |
| `EarnoutCreate` | 마일스톤 생성 (metric, target_value, measurement_period) |
| `EarnoutUpdate` | 마일스톤 수정 (actual_value, status, payment) |
| `EarnoutSummary` | 요약 (total, total_target, total_actual, total_payment, by_status) |

### 3.3 백엔드 라우터 (신규 2개 파일)

#### `deal-mgmt/app/routers/pmi.py`

| Method | Path | 설명 |
|:---|:---|:---|
| GET | `/transactions/{txn_id}/pmi` | PMI 태스크 목록 |
| GET | `/transactions/{txn_id}/pmi/summary` | PMI 요약 |
| POST | `/transactions/{txn_id}/pmi` | 태스크 생성 |
| PATCH | `/transactions/{txn_id}/pmi/{id}` | 태스크 수정 |
| DELETE | `/transactions/{txn_id}/pmi/{id}` | 태스크 삭제 |

#### `deal-mgmt/app/routers/earnout.py`

| Method | Path | 설명 |
|:---|:---|:---|
| GET | `/transactions/{txn_id}/earnout` | 어닝아웃 목록 |
| GET | `/transactions/{txn_id}/earnout/summary` | 어닝아웃 요약 |
| POST | `/transactions/{txn_id}/earnout` | 마일스톤 생성 |
| PATCH | `/transactions/{txn_id}/earnout/{id}` | 마일스톤 수정 |
| DELETE | `/transactions/{txn_id}/earnout/{id}` | 마일스톤 삭제 |

### 3.4 백엔드 서비스 — 연계 포인트 (신규 4개 파일)

#### `deal-mgmt/app/services/fdd_client.py`

```python
class FDDClient:
    """FDD 백엔드(:8000) API 호출 래퍼"""
    base_url = settings.FDD_API_URL  # http://fdd-api:8000/api/v1

    async def create_deal(self, transaction: Transaction) -> dict:
        """Transaction → FDD Deal 생성, fdd_deal_id 반환"""

    async def get_deal_status(self, fdd_deal_id: UUID) -> dict:
        """FDD Deal 상태 조회 (QoE/NWC/Debt 분석 진행률)"""

    async def trigger_analysis(self, fdd_deal_id: UUID, analysis_type: str) -> dict:
        """QoE/NWC/Debt 분석 트리거"""
```

#### `deal-mgmt/app/services/im_client.py`

```python
class IMClient:
    """IM 백엔드(:8002) API 호출 래퍼"""
    base_url = settings.IM_API_URL  # http://im-api:8000/api/v1

    async def create_document(self, transaction: Transaction) -> dict:
        """Transaction → IM Document(CIM) 생성, im_document_id 반환"""

    async def get_document_status(self, im_document_id: UUID) -> dict:
        """CIM 생성 상태 조회"""

    async def trigger_generation(self, im_document_id: UUID) -> dict:
        """CIM 재생성 트리거"""
```

#### `deal-mgmt/app/services/kiis_client.py`

```python
class KIISClient:
    """KIIS 백엔드(:8001) API 호출 래퍼"""
    base_url = settings.KIIS_API_URL  # http://kiis-api:8000/api/v1

    async def search_company(self, name: str) -> list[dict]:
        """회사명으로 DART 기업 검색"""

    async def get_company_detail(self, corp_code: str) -> dict:
        """기업 상세 정보 조회"""

    async def search_gps(self, query: str) -> list[dict]:
        """GP(운용사) 검색"""
```

#### `deal-mgmt/app/routers/integrations.py`

| Method | Path | 설명 |
|:---|:---|:---|
| POST | `/transactions/{txn_id}/integrations/fdd/link` | FDD Deal 연결/생성 |
| GET | `/transactions/{txn_id}/integrations/fdd/status` | FDD 분석 상태 |
| POST | `/transactions/{txn_id}/integrations/im/link` | IM Document 연결/생성 |
| GET | `/transactions/{txn_id}/integrations/im/status` | CIM 생성 상태 |
| GET | `/transactions/{txn_id}/integrations/kiis/company` | KIIS 기업 검색 |

### 3.5 Alembic 마이그레이션

#### `deal-mgmt/migrations/versions/004_phase4_pmi_earnout.py`

- **신규 테이블**: `pmi_tasks`, `earnout_milestones`
- **신규 Enum 타입**: pmicategory, pmitaskstatus, pmipriority, earnoutstatus, earnoutmetric

### 3.6 프론트엔드 타입 (신규 2개 파일)

#### `amic-platform/src/modules/ma/types/pmi.ts`

```typescript
export type PMICategory = "INTEGRATION_PLAN" | "DAY_ONE" | "FIRST_100_DAYS" | ...;
export type PMITaskStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED" | "DEFERRED";
export type PMIPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface PMITask { id; transaction_id; category; title; status; priority; assignee; dates; ... }
export interface PMITaskCreate { ... }
export interface PMITaskUpdate { ... }
export interface PMISummary { total; by_category; by_status; by_priority; completion_rate; }
```

#### `amic-platform/src/modules/ma/types/earnout.ts`

```typescript
export type EarnoutStatus = "PENDING" | "MEASUREMENT_PERIOD" | "ACHIEVED" | ...;
export type EarnoutMetric = "REVENUE" | "EBITDA" | "NET_INCOME" | ...;

export interface EarnoutMilestone { id; transaction_id; metric; target_value; actual_value; status; ... }
export interface EarnoutCreate { ... }
export interface EarnoutUpdate { ... }
export interface EarnoutSummary { total; total_target; total_actual; total_payment; by_status; }
```

### 3.7 프론트엔드 훅 (신규 2개 파일)

#### `amic-platform/src/modules/ma/hooks/usePMI.ts`

| 훅 | 설명 |
|:---|:---|
| `usePMITasks(txnId)` | PMI 태스크 목록 |
| `usePMISummary(txnId)` | PMI 요약 |
| `useCreatePMITask(txnId)` | 태스크 생성 |
| `useUpdatePMITask(txnId)` | 태스크 수정 |
| `useDeletePMITask(txnId)` | 태스크 삭제 |

#### `amic-platform/src/modules/ma/hooks/useEarnout.ts`

| 훅 | 설명 |
|:---|:---|
| `useEarnoutMilestones(txnId)` | 어닝아웃 목록 |
| `useEarnoutSummary(txnId)` | 어닝아웃 요약 |
| `useCreateEarnout(txnId)` | 마일스톤 생성 |
| `useUpdateEarnout(txnId)` | 마일스톤 수정 |
| `useDeleteEarnout(txnId)` | 마일스톤 삭제 |

### 3.8 TransactionWorkspacePage 탭 추가

| 탭 ID | 라벨 | 배지 | Phase |
|:---|:---|:---|:---:|
| `pmi` | PMI | pmiTasks.length | **4** |
| `earnout` | 어닝아웃 | earnoutMilestones.length | **4** |

---

## 4. 전체 구현 작업 목록

### Batch 1: 백엔드 모델 (Phase 3+4 병렬 가능)

| # | 파일 | Phase | 의존성 |
|:---:|:---|:---:|:---|
| 1 | `deal-mgmt/app/models/contract.py` | 3 | enums.py ✅ |
| 2 | `deal-mgmt/app/models/contract_version.py` | 3 | enums.py ✅ |
| 3 | `deal-mgmt/app/models/closing_checklist.py` | 3 | enums.py ✅ |
| 4 | `deal-mgmt/app/models/pmi_task.py` | 4 | enums.py ✅ |
| 5 | `deal-mgmt/app/models/earnout.py` | 4 | enums.py ✅ |
| 6 | `deal-mgmt/app/models/__init__.py` | — | 1~5 완료 후 |

### Batch 2: 백엔드 스키마 (Phase 3+4 병렬 가능)

| # | 파일 | Phase | 의존성 |
|:---:|:---|:---:|:---|
| 7 | `deal-mgmt/app/schemas/contract.py` | 3 | 없음 |
| 8 | `deal-mgmt/app/schemas/closing.py` | 3 | 없음 |
| 9 | `deal-mgmt/app/schemas/pmi.py` | 4 | 없음 |
| 10 | `deal-mgmt/app/schemas/earnout.py` | 4 | 없음 |

### Batch 3: 백엔드 라우터 + 서비스 (스키마 완료 후)

| # | 파일 | Phase | 의존성 |
|:---:|:---|:---:|:---|
| 11 | `deal-mgmt/app/routers/contracts.py` | 3 | 1, 7 |
| 12 | `deal-mgmt/app/routers/closing.py` | 3 | 3, 8 |
| 13 | `deal-mgmt/app/routers/pmi.py` | 4 | 4, 9 |
| 14 | `deal-mgmt/app/routers/earnout.py` | 4 | 5, 10 |
| 15 | `deal-mgmt/app/services/contract_analysis_service.py` | 3 | 없음 |
| 16 | `deal-mgmt/app/services/fdd_client.py` | 4 | 없음 |
| 17 | `deal-mgmt/app/services/im_client.py` | 4 | 없음 |
| 18 | `deal-mgmt/app/services/kiis_client.py` | 4 | 없음 |
| 19 | `deal-mgmt/app/routers/integrations.py` | 4 | 16, 17, 18 |

### Batch 4: 인프라 업데이트

| # | 파일 | 작업 |
|:---:|:---|:---|
| 20 | `deal-mgmt/app/main.py` | 신규 라우터 등록 (contracts, closing, pmi, earnout, integrations) |
| 21 | `deal-mgmt/migrations/versions/003_phase3_contracts_closing.py` | 마이그레이션 |
| 22 | `deal-mgmt/migrations/versions/004_phase4_pmi_earnout.py` | 마이그레이션 |

### Batch 5: 프론트엔드 타입 + 훅 (Phase 3+4 병렬 가능)

| # | 파일 | Phase |
|:---:|:---|:---:|
| 23 | `amic-platform/src/modules/ma/types/contract.ts` | 3 |
| 24 | `amic-platform/src/modules/ma/types/closing.ts` | 3 |
| 25 | `amic-platform/src/modules/ma/types/pmi.ts` | 4 |
| 26 | `amic-platform/src/modules/ma/types/earnout.ts` | 4 |
| 27 | `amic-platform/src/modules/ma/hooks/useContracts.ts` | 3 |
| 28 | `amic-platform/src/modules/ma/hooks/useClosing.ts` | 3 |
| 29 | `amic-platform/src/modules/ma/hooks/usePMI.ts` | 4 |
| 30 | `amic-platform/src/modules/ma/hooks/useEarnout.ts` | 4 |

### Batch 6: TransactionWorkspacePage 확장

| # | 파일 | 작업 |
|:---:|:---|:---|
| 31 | `TransactionWorkspacePage.tsx` | 8탭 → 12탭 (contracts, closing, pmi, earnout) |
| 32 | `amic-platform/src/modules/ma/constants.ts` | Phase 3+4 상태 옵션, 배지 색상 추가 |

### Batch 7: 테스트

| # | 파일 | 예상 테스트 수 |
|:---:|:---|:---:|
| 33 | `deal-mgmt/tests/test_contracts.py` | ~15 |
| 34 | `deal-mgmt/tests/test_closing.py` | ~10 |
| 35 | `deal-mgmt/tests/test_pmi.py` | ~10 |
| 36 | `deal-mgmt/tests/test_earnout.py` | ~10 |
| 37 | `deal-mgmt/tests/test_integrations.py` | ~5 |

### Batch 8: 검증 + 문서 + 커밋

| # | 작업 |
|:---:|:---|
| 38 | `pytest deal-mgmt/tests/ -v` — 전체 테스트 통과 |
| 39 | `npx tsc --noEmit` — TypeScript 에러 0 |
| 40 | `npx vite build` — 빌드 성공 |
| 41 | 구현 계획 문서 업데이트 (Phase 3+4 완료 섹션) |
| 42 | Git 커밋 + 푸시 |

---

## 5. 병렬화 전략

```
Batch 1 (모델 5개) ──────┐
Batch 2 (스키마 4개) ─────┼──→ Batch 3 (라우터 5개 + 서비스 4개) ──→ Batch 4 (인프라)
Batch 5a (타입 4개) ──────┘                                            │
                                                                       ▼
Batch 5b (훅 4개) ────────────→ Batch 6 (WorkspacePage + constants) ──→ Batch 7 (테스트)
                                                                       │
                                                                       ▼
                                                                    Batch 8 (검증/커밋)
```

**병렬 가능**:
- Batch 1 + 2 + 5a → 동시 작성 (모두 독립 파일)
- Phase 3 라우터 + Phase 4 라우터 → 동시 작성
- Phase 3 훅 + Phase 4 훅 → 동시 작성
- 프론트엔드 테스트와 백엔드 테스트 → 동시 실행

**순차 필수**:
- 모델 → 마이그레이션 (모델 확정 후)
- 스키마 → 라우터 (import 의존)
- 타입 → 훅 → WorkspacePage (import 의존)
- 모든 코드 → 테스트 → 검증 → 커밋

---

## 6. 예상 산출물 요약

| 항목 | Phase 3 | Phase 4 | 합계 |
|:---|:---:|:---:|:---:|
| 백엔드 모델 | 3 | 2 | **5** |
| 백엔드 스키마 | 2 | 2 | **4** |
| 백엔드 라우터 | 2 | 3 | **5** |
| 백엔드 서비스 | 1 | 3 | **4** |
| 마이그레이션 | 1 | 1 | **2** |
| 프론트엔드 타입 | 2 | 2 | **4** |
| 프론트엔드 훅 | 2 | 2 | **4** |
| 테스트 파일 | 2 | 3 | **5** |
| **신규 파일 합계** | 12 | 15 | **~29** |
| **수정 파일** | — | — | **~5** (main.py, __init__.py, WorkspacePage, constants.ts, enums.py✅) |

### 최종 시스템 통계 (Phase 4 완료 후 예상)

| 항목 | 현재 (Phase 2) | Phase 4 완료 후 |
|:---|:---:|:---:|
| DB 테이블 | 9 | **14** (+5) |
| Enum 타입 | 14 | **24** (+10) |
| API 엔드포인트 | ~38 | **~61** (+23) |
| UI 탭 | 8 | **12** (+4) |
| 백엔드 파일 | 47 | **~76** (+29) |
| 프론트엔드 파일 | 16 | **~29** (+13) |
| 테스트 케이스 | 85 | **~135** (+50) |
