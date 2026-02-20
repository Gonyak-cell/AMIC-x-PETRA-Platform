# 7단계 M&A 워크플로우 — 적용 가능성 평가 및 상세 구현 계획

**작성일**: 2026-02-17 23:04
**최종 수정**: 2026-02-20 14:12
**아키텍처 결정**: 새 `deal-mgmt` 서비스 신설 (port 8003)
**통합 방향**: FDD + IM → 워크플로우 내부 흡수, KIIS → 독립 데이터 모듈 유지
**참조 문서**: `new_workflow/AMIC_M&A_워크플로우_설계.md`, `compass_artifact_...md`, `new_workflow_system_dealroom.md`

---

## 1. Context

AMIC Platform에 DealRoom.net 스타일의 **7단계 M&A 자문 라이프사이클**(47개 세부 프로세스, 120+ 자동화 업무)을 도입한다. 핵심 설계 결정:

- **FDD**(재무 실사)와 **IM**(투자제안서 생성)은 워크플로우 내부에 녹여 통합
- **KIIS**만 독립 데이터 모듈로 유지 (기업/펀드/GP 데이터 소스)
- 새 `deal-mgmt` 백엔드 서비스가 전체 딜 라이프사이클을 관장
- FDD/IM/KIIS 백엔드는 하위 서비스로 API 호출을 통해 연동

---

## 2. 적용 가능성 평가

### 2.1 현재 커버율

| 단계 | 현재 | FDD/IM 통합 후 | 핵심 누락 기능 |
|:---|:---:|:---:|:---|
| 1. 수임/전략 (1~4주) | 25% | **30%** | 피치북 생성, 이해충돌 심사, WGL 관리 |
| 2. 준비/개발 (3~10주) | 35% | **50%** | 고급 VDR (권한/워터마크), 매수자 CRM |
| 3. 마케팅/접근 (8~14주) | 15% | **15%** | NDA 관리, 전자서명, IOI 수집, 배포 추적 |
| 4. 입찰/실사 (12~24주) | 40% | **55%** | 비재무 DD 6개, AI 계약 분석, IOI/LOI 비교 |
| 5. 협상/문서 (20~30주) | 5% | **5%** | SPA, R&W, 규제 신고, 전자서명 — 전면 신규 |
| 6. 클로징 (28~36주) | 5% | **5%** | 선행조건, 자금흐름표, 클로징 바인더 |
| 7. PMI (36~88주+) | 10% | **15%** | 어닝아웃, PMI 대시보드, 100일 계획 |
| **전체** | **~20%** | **~28%** | |

### 2.2 종합 판정

**적용 가능하다. 단, 단계적 접근 필수.**

- **강점**: Financial DD 엔진(4단계), CIM 자동 생성(2단계), 시장 인텔리전스(KIIS)
- **약점**: 거래 관리 축(NDA, IOI/LOI, SPA, 클로징, PMI) 거의 부재
- **정체성 전환**: "분석 도구" → "M&A 거래 관리 플랫폼"

### 2.3 FDD 통합 매핑

| FDD 기존 기능 | 통합 위치 | 통합 방식 |
|:---|:---|:---|
| Deal 생성/관리 | 1단계 → 전체 | MasterDeal(Transaction) 모델로 확장 |
| VDR 폴더/업로드 | 2~4단계 | 범용 VDR로 확장 (권한, Q&A 추가) |
| QoE/NWC/Debt 엔진 | 4단계 Financial DD | 그대로 재사용 |
| Anomaly/Delta 엔진 | 4단계 DD 이상 탐지 | 그대로 재사용 |
| Issue 관리 | 4단계 DD 이슈 | 범용 이슈 트래커로 확장 |
| Report 생성 | 4단계 DD 보고서 | PPTX Service 그대로 활용 |
| 워크플로우 5단계 | 7단계로 확장 | `TransactionPhase` enum 재정의 |

### 2.4 IM 통합 매핑

| IM 기존 기능 | 통합 위치 | 통합 방식 |
|:---|:---|:---|
| 14섹션 IM 자동 생성 | 2단계 CIM/티저 | CIM 전용 섹션 구조로 재구성 |
| PPTX/PDF 렌더링 | 전 단계 문서 출력 | 공용 렌더링 서비스로 승격 |
| DART 데이터 수집 | 1~2단계 타겟 정보 | KIIS와 공유 데이터 레이어 |
| 재무 엔진 | 2단계 재무 모델 기초 | FDD 엔진과 통합 |
| Celery 비동기 작업 | 장시간 작업 (AI, 문서) | 공용 작업 큐로 활용 |
| 차트 엔진 (Plotly) | 대시보드/보고서 | 공용 차트 서비스 |

### 2.5 핵심 리스크

| 리스크 | 영향 | 완화 방안 |
|:---|:---|:---|
| **범위 폭발** (47프로세스 × 120업무) | 매우 높음 | MVP에서 핵심 20프로세스만, 나머지는 체크리스트 |
| **FDD/IM 통합 시 기존 기능 파괴** | 높음 | Transaction 상위 모델로 감싸고, 기존 Deal은 하위 유지 |
| **워크플로우 엔진 복잡도** | 높음 | 상태 머신 라이브러리 도입, 단계별 점진 구현 |
| **3개 DB 간 조인 불가** | 중간 | API 조합 패턴으로 해결 |
| **전자서명 외부 의존** | 중간 | MVP에서 수동 업로드로 대체, Phase 2에서 통합 |

---

## 3. 목표 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React 19)                                            │
│  /ma/*  → M&A Workflow Module (신규)                            │
│  /kiis/* → KIIS Module (기존 유지)                               │
│  /fdd/*  → 기존 FDD (점진적 /ma/ 리다이렉트)                      │
│  /im/*   → 기존 IM  (점진적 /ma/ 리다이렉트)                      │
└─────────────────────────────────────────────────────────────────┘
                    │  Nginx Proxy
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│  deal-mgmt API (:8003) — 신규 마스터 서비스                        │
│  ├── /api/v1/transactions       → MasterDeal CRUD               │
│  ├── /api/v1/transactions/{id}/workflow  → 7단계 상태 머신        │
│  ├── /api/v1/transactions/{id}/engagement → 수임 관리            │
│  ├── /api/v1/transactions/{id}/buyers    → 매수자 관리           │
│  ├── /api/v1/transactions/{id}/nda       → NDA 관리             │
│  ├── /api/v1/transactions/{id}/bids      → IOI/LOI 관리         │
│  ├── /api/v1/transactions/{id}/dd        → DD 워크스트림 관리     │
│  ├── /api/v1/transactions/{id}/timeline  → 마일스톤/일정         │
│  └── /api/v1/transactions/{id}/documents → 문서 통합 관리        │
│                                                                  │
│  내부 호출:                                                       │
│  → FDD API (:8000)  — QoE/NWC/Debt 분석 위임                    │
│  → IM API (:8002)   — CIM/피치북 생성 위임                       │
│  → KIIS API (:8001) — 기업/GP/펀드 데이터 조회                    │
└──────────────────────────────────────────────────────────────────┘
         │              │              │              │
    deal-mgmt-db   FDD API(:8000)  IM API(:8002)  KIIS API(:8001)
    PostgreSQL     + fdd-db        + im-db         + kiis-db
    :5436          :5433           :5435           :5434
```

**용어 정리**: `transaction` = 전체 M&A 거래 (기존 FDD `deal`과의 네이밍 충돌 방지)

---

## 4. Phase 0: 아키텍처 준비 (2~3주)

### 4.1 deal-mgmt 백엔드 서비스 스캐폴딩

#### 디렉토리 구조

```
deal-mgmt/                          # 신규 백엔드 서비스 루트
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 앱 + 라우터 등록
│   ├── config.py                   # 설정 (DB URL, JWT, 서비스 URL)
│   ├── database.py                 # SQLAlchemy async engine + session
│   ├── models/
│   │   ├── transaction.py          # MasterDeal (= Transaction)
│   │   ├── engagement.py           # 수임계약
│   │   ├── working_group.py        # WGL 멤버
│   │   ├── buyer_candidate.py      # 잠재 매수자
│   │   ├── timeline.py             # 마일스톤/일정
│   │   ├── user.py                 # User (공유 JWT)
│   │   └── audit.py                # AuditLog
│   ├── schemas/
│   │   ├── transaction.py
│   │   ├── workflow.py
│   │   ├── engagement.py
│   │   ├── buyer.py
│   │   └── timeline.py
│   ├── routers/
│   │   ├── transactions.py         # CRUD + 목록/검색
│   │   ├── workflow.py             # 7단계 상태 머신
│   │   ├── engagement.py           # 수임 관리
│   │   ├── buyers.py               # 매수자 후보 관리
│   │   ├── timeline.py             # 일정/마일스톤
│   │   └── health.py               # 헬스 체크
│   ├── services/
│   │   ├── workflow_engine.py      # 7단계 상태 전환 + 완료 조건
│   │   ├── fdd_client.py           # FDD API 호출 래퍼
│   │   ├── im_client.py            # IM API 호출 래퍼
│   │   └── kiis_client.py          # KIIS API 호출 래퍼
│   └── auth/
│       ├── dependencies.py         # get_current_user
│       └── jwt.py                  # JWT 검증 (공유 SECRET)
├── alembic/
│   └── versions/
│       └── 001_initial_schema.py
├── tests/
├── Dockerfile
├── requirements.txt
└── pyproject.toml
```

#### 핵심 데이터 모델

**Transaction (MasterDeal)**

```python
class TransactionSide(str, enum.Enum):
    SELL = "SELL"          # 매도자문
    BUY = "BUY"           # 매수자문
    DUAL = "DUAL"         # 양측 (Phase 2 이후)

class TransactionPhase(str, enum.Enum):
    ENGAGEMENT = "ENGAGEMENT"           # 1단계: 수임/전략
    PREPARATION = "PREPARATION"         # 2단계: 준비/개발
    MARKETING = "MARKETING"             # 3단계: 마케팅/접근
    BIDDING_DD = "BIDDING_DD"          # 4단계: 입찰/실사
    NEGOTIATION = "NEGOTIATION"         # 5단계: 협상/문서
    CLOSING = "CLOSING"                 # 6단계: 클로징
    POST_CLOSING = "POST_CLOSING"       # 7단계: PMI

class TransactionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"

class Transaction(Base):
    __tablename__ = "transaction"
    id: UUID (PK)
    code_name: str                      # 딜 코드네임 (보안)
    name: str                           # 딜 공식 명칭
    side: TransactionSide               # 매도/매수/양측
    status: TransactionStatus
    current_phase: TransactionPhase
    client_name: str
    target_company_name: str
    target_corp_code: str | None        # KIIS corp_code 연결
    target_industry: str
    target_revenue: Decimal | None
    target_ebitda: Decimal | None
    deal_type: str                      # COMPLETION_ACCOUNTS / LOCKED_BOX
    deal_structure: str | None
    estimated_value: Decimal | None
    currency: str = "KRW"
    lead_partner_id: UUID | None
    deal_captain_id: UUID | None
    fdd_deal_id: UUID | None            # FDD 백엔드 Deal.id 연결
    im_document_id: UUID | None         # IM 백엔드 Document.id 연결
    engagement_date: date | None
    target_close_date: date | None
    actual_close_date: date | None
```

**Engagement, WorkingGroupMember, BuyerCandidate, DealTimeline** — 각각 수임계약, WGL, 매수자 후보, 마일스톤 관리

#### Docker 인프라

```yaml
# docker-compose.yml 추가 서비스
deal-mgmt-api:
  build: ./deal-mgmt
  ports: ["8003:8000"]
  environment:
    DATABASE_URL: postgresql+asyncpg://deal_mgmt:${DEAL_MGMT_DB_PASSWORD}@deal-mgmt-db:5432/deal_mgmt
    FDD_API_URL: http://fdd-api:8000/api/v1
    IM_API_URL: http://im-api:8000/api/v1
    KIIS_API_URL: http://kiis-api:8000/api/v1

deal-mgmt-db:
  image: postgres:16-alpine
  ports: ["5436:5432"]
```

### 4.2 프론트엔드 모듈 스캐폴딩

```
amic-platform/src/modules/ma/           # 신규 M&A 워크플로우 모듈
├── MaRoutes.tsx
├── pages/ (7개)
├── hooks/ (5개)
├── components/ (12개)
├── types/ (5개)
└── constants.ts
```

**라우팅**: `/ma/*` → Transaction 목록, 생성, 작업 영역 (7단계 탭)
**API 클라이언트**: `src/api/maClient.ts` → `createApiClient("/api/ma")`

---

## 5. Phase 1: MVP Core (16~20주)

### Sprint 1~2: Transaction CRUD + 7단계 워크플로우 (4주)

- 백엔드: Transaction 모델, CRUD API, 워크플로우 상태 머신
- 프론트엔드: 파이프라인 뷰, 생성 마법사, 7단계 WorkflowStepper

### Sprint 3~4: 1단계 수임 관리 + WGL (4주)

- 백엔드: Engagement CRUD, 이해충돌 체크 (KIIS Entity Resolution 연동), WGL 관리
- 프론트엔드: 수임계약 폼, 이해충돌 심사 패널, WGL 멤버 관리

### Sprint 5~7: 2단계 CIM 연동 + 매수자 리스트 (6주)

- 백엔드: BuyerCandidate CRUD, IM API 래퍼 (CIM 생성 트리거)
- 프론트엔드: 매수자 파이프라인 뷰, CIM 생성 UI, KIIS GP 가져오기

### Sprint 8~9: 4단계 DD 허브 + FDD 통합 (4주)

- 백엔드: DDWorkstream 모델, FDD API 래퍼 (딜 생성 + 분석 위임)
- 프론트엔드: DD 허브 (9개 워크스트림 카드), Generic 체크리스트, FDD 분석 임베드

### Sprint 10: 타임라인 + 대시보드 (2주)

- 마일스톤 타임라인 뷰, 간트 차트
- 대시보드 KPI + 파이프라인 위젯

---

## 6. Phase 1 완료 시 결과물

### 백엔드

- **deal-mgmt 서비스**: ~15 API 엔드포인트, ~8 DB 모델
- **FDD/IM/KIIS**: 기존 유지, deal-mgmt에서 API 호출로 연동

### 프론트엔드 라우트

```
/ma                  → 딜 목록 (파이프라인 뷰)
/ma/new              → 딜 생성 마법사
/ma/:txnId           → 워크플로우 대시보드
/ma/:txnId/engagement → 1단계 수임 관리
/ma/:txnId/buyers    → 2~3단계 매수자 관리
/ma/:txnId/dd        → 4단계 DD 허브
/ma/:txnId/dd/fdd/*  → FDD 분석 (기존 페이지 임베드)
/ma/:txnId/documents/cim → CIM 생성 (IM 연동)
```

### E2E 흐름

```
딜 생성 → 수임계약 → 이해충돌 체크 → WGL 구성
→ CIM 자동 생성 (IM) → 매수자 추가 (KIIS GP)
→ DD 시작 → FDD 분석 (QoE/NWC/Debt)
→ 워크플로우 대시보드에서 진행 확인
```

---

## 7. 이후 로드맵 (Phase 2~4)

| Phase | 기간 | 주요 내용 |
|:---|:---|:---|
| **Phase 2** | 16~20주 | NDA 관리, IOI/LOI 비교 매트릭스, 비재무 DD, 듀얼 레인 기초 |
| **Phase 3** | 16~24주 | AI 계약 분석, 전자서명 (DocuSign), SPA 버전 관리, 클로징 체크리스트 |
| **Phase 4** | 12~16주 | PMI 대시보드, 어닝아웃, 운전자본 정산, 7개 연계 포인트 완성 |
| **총 예상** | 60~80주 | 풀스케일 7단계 M&A 워크플로우 |

---

## 8. 수정 대상 기존 파일

| 파일 | 변경 내용 | 상태 |
|:---|:---|:---:|

| `docker-compose.yml` | deal-mgmt-api + deal-mgmt-db 추가 | ✅ |
| `docker-compose.prod.yml` | 동일 | ✅ |
| `nginx/dev.conf` | `/api/ma/` 프록시 + health 추가 | ✅ |
| `nginx/prod-nossl.conf` | `/api/ma/` 프록시 추가 | ✅ |
| `amic-platform/vite.config.ts` | `/api/ma` 프록시 + health 추가 | ✅ |
| `amic-platform/src/App.tsx` | `/ma/*` 라우트 (lazy load) 추가 | ✅ |
| `amic-platform/src/components/layout/Sidebar.tsx` | M&A Pipeline 네비게이션 추가 | ✅ |
| `amic-platform/src/api/maClient.ts` | MA API 클라이언트 생성 | ✅ |
| `amic-platform/src/hooks/useHealthCheck.ts` | MA 서비스 헬스 체크 추가 | ✅ |
| `amic-platform/src/pages/DashboardPage.tsx` | M&A 파이프라인 위젯 추가 | ✅ |

---

## 9. 검증 방법

1. **백엔드 테스트**: `pytest deal-mgmt/tests/ -v`
2. **타입 검증**: `npx tsc --noEmit` — 에러 0
3. **E2E 시나리오**: 딜 생성 → 1단계 → 2단계 (CIM) → 4단계 (FDD) 흐름
4. **회귀 테스트**: `/fdd/*`, `/kiis/*`, `/im/*` 기존 라우트 정상 작동

---

## 10. 구현 진행 상황

### Phase 0: 아키텍처 준비 — ✅ 완료 (Session 27, 2026-02-18)

| 항목 | 상태 | 비고 |
|:---|:---:|:---|
| deal-mgmt 디렉토리 구조 | ✅ | 44개 파일 생성 |
| FastAPI 앱 + main.py | ✅ | 6개 라우터 등록 |
| SQLAlchemy 모델 (6개) | ✅ | transaction, engagement, working_group, buyer_candidate, timeline, audit |
| Alembic 마이그레이션 | ✅ | `001_initial_schema.py` 생성 |
| Dockerfile + docker-entrypoint.sh | ✅ | |
| docker-compose.yml 통합 | ✅ | deal-mgmt-api(:8003) + deal-mgmt-db(:5436) |
| docker-compose.prod.yml 통합 | ✅ | prod 오버라이드 완료 |
| nginx dev/prod 프록시 | ✅ | `/api/ma/` → deal-mgmt-api |
| Vite 프록시 | ✅ | `/api/ma` → localhost:8003 |
| 프론트엔드 라우팅 | ✅ | `App.tsx` MaRoutes lazy load |
| Sidebar 네비게이션 | ✅ | M&A Pipeline + New Transaction |
| API 클라이언트 | ✅ | `maClient.ts` → `/api/ma` |
| 헬스 체크 통합 | ✅ | useHealthCheck에 MA 서비스 추가 |

### Phase 1: MVP Core — ✅ 완료 (Session 27, 2026-02-18)

**Backend (deal-mgmt) — 신규 17개 파일**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Schemas** | `transaction.py` | CRUD + List response |
| | `workflow.py` | Phase completion, transition, status change |
| | `engagement.py` | Engagement + WGL + Conflict check |
| | `buyer.py` | Buyer CRUD + Pipeline summary |
| | `timeline.py` | Timeline event CRUD |
| | `dashboard.py` | Dashboard stats |
| **Services** | `transaction_service.py` | CRUD + soft delete + audit logging |
| | `workflow_engine.py` | 7단계 상태 머신 (전제 조건, 1단계 앞/뒤 전환) |
| | `audit_service.py` | 감사 로그 기록 |
| **Routers** | `transactions.py` | `GET/POST/PATCH/DELETE /transactions` |
| | `workflow.py` | `GET phase-status`, `POST advance`, `POST status` |
| | `engagements.py` | Engagement CRUD + WGL CRUD + Conflict check |
| | `buyers.py` | Buyer pipeline CRUD + summary |
| | `timeline.py` | Timeline events CRUD |
| | `dashboard.py` | Dashboard stats KPI |

총 ~15 API 엔드포인트 등록 완료 (`main.py`).

**Frontend (MA Module) — 신규 1개, 수정 3개 파일**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Hooks** | `useTransactions.ts` | 20+ TanStack Query 훅 (Transactions, Workflow, Engagement, WGL, Conflict, Buyers, Timeline, Dashboard) |
| **Pages** | `TransactionListPage.tsx` | Pipeline view (KPI 카드, 필터/검색, DataTable, 페이지네이션) |
| | `CreateTransactionPage.tsx` | 생성 폼 (필수/선택 필드 토글, 유효성 검사) |
| | `TransactionWorkspacePage.tsx` | 5탭 워크스페이스 (Overview, 수임, 팀, 매수자, 타임라인) + WorkflowStepper + 모달 3개 |

**검증 결과**

- `tsc --noEmit`: 에러 0건 ✅
- `vite build`: 성공 (4.82s, 2959 modules) ✅

### 다음 단계 (Phase 1 후속)

| 우선순위 | 작업 | 상태 |
|:---:|:---|:---:|
| 1 | Docker 컨테이너 빌드 + 헬스 체크 검증 | ✅ (Session 29) |
| 2 | Alembic 마이그레이션 실행 (deal-mgmt-db) | ✅ (Session 29, auto-upgrade lifespan) |
| 3 | MA Sidebar 워크스페이스 네비게이션 확장 | ✅ (Session 28) |
| 4 | DashboardPage M&A 파이프라인 위젯 추가 | ✅ (이미 존재 확인) |
| 5 | E2E 검증: 생성 → 목록 → 워크스페이스 흐름 | ✅ (Session 29, httpx 스크립트) |
| 6 | 백엔드 pytest 기본 테스트 작성 | ✅ (Session 29, 25/25 통과) |

### Phase 2: NDA / Bids / DD Checklist — ✅ 완료 (Session 30, 2026-02-19)

**Backend (deal-mgmt) — Phase 2 추가 파일**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Models** | `nda.py` | NDA 모델 (ONE_WAY/MUTUAL, 5단계 상태) |
| | `bid.py` | Bid 모델 (IOI/LOI/FINAL_OFFER, 6단계 상태, 6가지 밸류에이션) |
| | `dd_checklist.py` | DD Checklist 모델 (9개 워크스트림, 4단계 상태) |
| **Enums** | `enums.py` 확장 | NdaType, NdaStatus, BidType, BidStatus, ValuationMethod, DDWorkstream, DDChecklistStatus |
| **Schemas** | `nda.py` | NDA CRUD 스키마 + Summary |
| | `bid.py` | Bid CRUD 스키마 + Comparison Matrix |
| | `dd_checklist.py` | DD Checklist CRUD 스키마 + Progress Summary |
| **Routers** | `ndas.py` | `GET/POST/PATCH/DELETE /ndas` + Summary |
| | `bids.py` | `GET/POST/PATCH/DELETE /bids` + Comparison |
| | `dd_checklists.py` | `GET/POST/PATCH/DELETE /dd-checklists` + Summary |
| **Migration** | `002_phase2_nda_bids_dd.py` | 3 테이블 + 7 enum 타입 생성 |

**Frontend (MA Module) — Phase 2 추가/수정**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Types** | `nda.ts` | NDA, NDACreate, NDAUpdate, NDASummary |
| | `bid.ts` | Bid, BidCreate, BidUpdate, BidComparison |
| | `dd_checklist.ts` | DDChecklistItem, DDChecklistCreate, DDChecklistUpdate, DDChecklistSummary |
| **Hooks** | `useNdas.ts` | 5개 훅 (list, summary, create, update, delete) |
| | `useBids.ts` | 5개 훅 (list, comparison, create, update, delete) |
| | `useDDChecklist.ts` | 5개 훅 (list, summary, create, update, delete) |
| **Pages** | `TransactionWorkspacePage.tsx` | 5탭 → 8탭 확장 (NDA, Bids, DD Checklist 추가), 인라인 상태 편집, 삭제, 요약 KPI |
| **Constants** | `constants.ts` | NDA/Bid/DD 상태 옵션 배열, 배지 색상 매핑 |

**TransactionWorkspacePage 8탭 구성**

| 탭 | 내용 | Phase |
|:---|:---|:---:|
| Overview | 거래 요약, WorkflowStepper | 1 |
| 수임(Engagement) | 수임계약 CRUD, 이해충돌 체크 | 1 |
| 팀(WGL) | Working Group 멤버 관리 | 1 |
| 매수자(Buyers) | 매수자 후보 파이프라인 | 1 |
| NDA | NDA 관리 — KPI 요약, 인라인 상태 편집, 삭제 | **2** |
| Bids | IOI/LOI/최종오퍼 — 비교 매트릭스, 인라인 상태 편집, 삭제 | **2** |
| DD Checklist | 9개 워크스트림 — 진행률, 인라인 상태 편집, 삭제 | **2** |
| 타임라인(Timeline) | 마일스톤/일정 관리 | 1 |

**검증 결과**

- `pytest deal-mgmt/tests/ -v`: **85/85 통과** (1.94s) ✅
  - NDA: 10건, Bids: 12건, DD Checklist: 10건, Buyers: 13건, Engagements: 15건
  - Transactions: 12건, Workflow: 13건
- `tsc --noEmit`: 에러 0건 ✅
- `vite build`: 성공 (4.09s, 2962 modules) ✅

**Git**: `618109a` feat/ma-workflow → origin 푸시 완료 (129 files, +12,188 lines)

### Phase 3: 계약 관리 / 클로징 — ✅ 완료 (Session 31, 2026-02-20)

**Backend (deal-mgmt) — Phase 3 추가 파일**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Models** | `contract.py` | Contract 모델 (SPA/SHA/NDA 등 8종, 7단계 상태, 서명자 JSONB) |
| | `contract_version.py` | ContractVersion 모델 (계약 버전 관리, diff 추적) |
| | `closing_checklist.py` | ClosingChecklist 모델 (6개 카테고리, 4단계 상태, 책임자/기한) |
| **Enums** | `enums.py` 확장 | ContractType, ContractStatus, ClosingCategory, ClosingStatus |
| **Schemas** | `contract.py` | Contract CRUD 스키마 + Version + Summary + AI 분석 요청 |
| | `closing.py` | Closing Checklist CRUD 스키마 + Summary (카테고리별 진행률) |
| **Routers** | `contracts.py` | `GET/POST/PATCH/DELETE /contracts` + Versions + Summary + AI 분석(stub) |
| | `closing.py` | `GET/POST/PATCH/DELETE /closing` + Summary |
| **Services** | `contract_analysis_service.py` | AI 계약 분석 서비스 (stub — 향후 LLM 연동) |
| **Migration** | `003_phase3_contracts_closing.py` | 3 테이블 (contracts, contract_versions, closing_checklists) + 4 enum 타입 |

**Frontend (MA Module) — Phase 3 추가/수정**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Types** | `contract.ts` | Contract, ContractVersion, ContractCreate, ContractUpdate, ContractSummary |
| | `closing.ts` | ClosingItem, ClosingCreate, ClosingUpdate, ClosingSummary |
| **Hooks** | `useContracts.ts` | 7개 훅 (list, summary, versions, create, update, delete, analyze) |
| | `useClosing.ts` | 5개 훅 (list, summary, create, update, delete) |
| **Pages** | `TransactionWorkspacePage.tsx` | 8탭 → 10탭 확장 (Contracts, Closing 추가) |
| **Constants** | `constants.ts` | Contract/Closing 상태 옵션, 배지 색상 매핑 추가 |

### Phase 4: PMI / 어닝아웃 / 외부 연동 — ✅ 완료 (Session 31, 2026-02-20)

**Backend (deal-mgmt) — Phase 4 추가 파일**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Models** | `pmi_task.py` | PMI Task 모델 (5개 카테고리, 우선순위, 진행률, 책임자) |
| | `earnout.py` | Earnout 모델 (4종 메트릭, 4단계 상태, 목표/실적/지급금액) |
| **Enums** | `enums.py` 확장 | PMICategory, PMIPriority, PMIStatus, EarnoutMetric, EarnoutStatus |
| **Schemas** | `pmi.py` | PMI CRUD 스키마 + Summary (카테고리별 진행률) |
| | `earnout.py` | Earnout CRUD 스키마 + Summary (총 목표/실적/지급) |
| **Routers** | `pmi.py` | `GET/POST/PATCH/DELETE /pmi` + Summary |
| | `earnout.py` | `GET/POST/PATCH/DELETE /earnout` + Summary |
| | `integrations.py` | FDD/IM/KIIS 외부 연동 엔드포인트 (link, search) |
| **Services** | `fdd_client.py` | FDD API 호출 래퍼 (딜 생성 + 분석 결과 조회) |
| | `im_client.py` | IM API 호출 래퍼 (문서 생성 트리거 + 상태 조회) |
| | `kiis_client.py` | KIIS API 호출 래퍼 (기업 검색 + 상세 조회) |
| **Migration** | `004_phase4_pmi_earnout.py` | 2 테이블 (pmi_tasks, earnouts) + 5 enum 타입 |

**Frontend (MA Module) — Phase 4 추가/수정**

| 카테고리 | 파일 | 내용 |
|:---|:---|:---|
| **Types** | `pmi.ts` | PMITask, PMICreate, PMIUpdate, PMISummary |
| | `earnout.ts` | Earnout, EarnoutCreate, EarnoutUpdate, EarnoutSummary |
| **Hooks** | `usePMI.ts` | 5개 훅 (list, summary, create, update, delete) |
| | `useEarnout.ts` | 5개 훅 (list, summary, create, update, delete) |
| **Pages** | `TransactionWorkspacePage.tsx` | 10탭 → 12탭 확장 (PMI, Earnout 추가) |
| **Constants** | `constants.ts` | PMI/Earnout 상태 옵션, 배지 색상 매핑 추가 |

**TransactionWorkspacePage 최종 12탭 구성**

| 탭 | 내용 | Phase |
|:---|:---|:---:|
| Overview | 거래 요약, WorkflowStepper | 1 |
| 수임(Engagement) | 수임계약 CRUD, 이해충돌 체크 | 1 |
| 팀(WGL) | Working Group 멤버 관리 | 1 |
| 매수자(Buyers) | 매수자 후보 파이프라인 | 1 |
| NDA | NDA 관리 — KPI 요약, 인라인 상태 편집 | 2 |
| Bids | IOI/LOI/최종오퍼 — 비교 매트릭스 | 2 |
| DD Checklist | 9개 워크스트림 — 진행률 | 2 |
| Contracts | 계약 관리 — 버전, 서명자, AI 분석(stub) | **3** |
| Closing | 클로징 체크리스트 — 6개 카테고리 | **3** |
| PMI | PMI 태스크 — 5개 카테고리, 우선순위, 진행률 | **4** |
| Earnout | 어닝아웃 — 메트릭, 목표/실적/지급 추적 | **4** |
| 타임라인(Timeline) | 마일스톤/일정 관리 | 1 |

**검증 결과 (Phase 0~4 전체)**

- `pytest deal-mgmt/tests/ -v`: **127/127 통과** (12.28s) ✅
  - Phase 3: Contracts 11건, Closing 10건
  - Phase 4: PMI 9건, Earnout 9건, Integrations 3건
  - Phase 2: NDA 10건, Bids 9건 (Phase 2에서 12→9 정리), DD Checklist 9건
  - Phase 1: Buyers 18건, Engagements 16건, Transactions 12건, Workflow 13건, Health 1건
- `tsc --noEmit`: 에러 0건 ✅
- `vite build`: 성공 (6.20s, 2971 modules) ✅

**Git**: `6603591` feat/ma-workflow → origin 푸시 완료 (Phase 0~4 전체 포함)

### 전체 진행률 요약

| Phase | 상태 | 세션 | 핵심 산출물 |
|:---|:---:|:---:|:---|
| **Phase 0**: 아키텍처 준비 | ✅ 완료 | 27 | deal-mgmt 서비스 스캐폴딩, Docker/nginx/Vite 통합 |
| **Phase 1**: MVP Core | ✅ 완료 | 27~29 | Transaction CRUD, 7단계 워크플로우, 수임/WGL/매수자/타임라인, E2E |
| **Phase 2**: NDA/Bids/DD | ✅ 완료 | 30 | NDA 관리, IOI/LOI 비교, DD 체크리스트, 인라인 편집 |
| **Phase 3**: 계약/클로징 | ✅ 완료 | 31 | 계약 버전관리, AI 분석(stub), 클로징 체크리스트 |
| **Phase 4**: PMI/어닝아웃 | ✅ 완료 | 31 | PMI 태스크, 어닝아웃 추적, FDD/IM/KIIS 외부 연동 |

### 파일 통계 (전체)

| 카테고리 | 파일 수 | 비고 |
|:---|:---:|:---|
| 백엔드 모델 | 16 | transaction, engagement, working_group, buyer_candidate, timeline, audit, nda, bid, dd_checklist, contract, contract_version, closing_checklist, pmi_task, earnout, base, enums |
| 백엔드 스키마 | 14 | transaction, workflow, engagement, buyer, timeline, dashboard, nda, bid, dd_checklist, contract, closing, pmi, earnout |
| 백엔드 라우터 | 13 | transactions, workflow, engagements, buyers, timeline, dashboard, ndas, bids, dd_checklists, contracts, closing, pmi, earnout, integrations |
| 백엔드 서비스 | 7 | transaction_service, workflow_engine, audit_service, contract_analysis_service, fdd_client, im_client, kiis_client |
| 백엔드 코어 | 4 | config, database, exceptions, security |
| 마이그레이션 | 4 | 001_initial (6 tables), 002_phase2 (3 tables), 003_phase3 (3 tables), 004_phase4 (2 tables) |
| 테스트 | 14 | 127 test cases |
| 프론트엔드 타입 | 12 | transaction, workflow, engagement, buyer, timeline, nda, bid, dd_checklist, contract, closing, pmi, earnout |
| 프론트엔드 훅 | 8 | useTransactions, useNdas, useBids, useDDChecklist, useContracts, useClosing, usePMI, useEarnout |
| 프론트엔드 페이지 | 3 | TransactionList, CreateTransaction, TransactionWorkspace (12탭) |
| **총계** | **~95** | 백엔드 72 + 프론트엔드 24 + 인프라 2 |

### 다음 단계

| 우선순위 | 작업 | 상태 |
|:---:|:---|:---:|
| 1 | 브라우저 E2E 시각 확인 (12탭 전체 동작) | ⬜ |
| 2 | native `<select>` → styled `<Select>` 컴포넌트 전환 (UX 개선) | ⬜ |
| 3 | AI 계약 분석 LLM 연동 (contract_analysis_service stub 구현) | ⬜ |
| 4 | 전자서명 (DocuSign) 외부 연동 | ⬜ |
| 5 | FDD/IM/KIIS 실제 API 연동 테스트 (Docker 환경) | ⬜ |
