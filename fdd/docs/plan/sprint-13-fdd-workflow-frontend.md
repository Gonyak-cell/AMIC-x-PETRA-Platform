# Sprint 13: FDD 워크플로우 기반 프론트엔드 재설계

> 작성일: 2026년 02월 09일 00시 33분 55초
> 작성자: Claude Code
> 상태: PLANNING

---

## 1. 개요

### 1.1 목적

회계법인 FDD 실무 워크플로우 5단계에 맞춰 프론트엔드를 재구성하여, 딜 생성부터 보고서 작성까지 체계적인 프로세스 관리를 지원합니다.

### 1.2 FDD 워크플로우 5단계

```text
[1. MoU 체결] → [2. VDR 개설] → [3. 자료 업로드] → [4. 자료 검토] → [5. 보고서 작성]
     │              │               │                │               │
   Deal 생성    폴더 구조 설정   파일 업로드      분석 수행       보고서 생성
```

| 단계 | 설명 | 완료 조건 |
|------|------|-----------|
| 1. MoU 체결 | 클라이언트/타겟 회사 정보, 팀 구성, FDD 범위 설정 | 필수 정보 입력 완료 |
| 2. VDR 개설 | Virtual Data Room 폴더 구조 생성 | 기본 폴더 구조 생성 |
| 3. 자료 업로드 | 재무 자료(TB, GL 등) 업로드 | 필수 파일(TB/GL) 업로드 완료 |
| 4. 자료 검토 | 계정 매핑, QoE/NWC/Debt 분석, 이상치 탐지 | Definition 승인 완료 |
| 5. 보고서 작성 | 최종 FDD 보고서 생성 | 보고서 Final 확정 |

### 1.3 설계 원칙

- **VDR**: 폴더 구조 + 업로드 기능만 (접근 권한 관리 제외)
- **보고서**: 단순 버전 관리 (Draft/Final 상태만)
- **기존 활용**: 분석 페이지(QoE/NWC/Debt 등) 최대한 재사용

---

## 2. 신규 컴포넌트

### 2.1 워크플로우 컴포넌트

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| `WorkflowStepper` | `components/workflow/WorkflowStepper.tsx` | 5단계 워크플로우 진행 상태 시각화 |
| `StepIndicator` | `components/workflow/StepIndicator.tsx` | 개별 스텝 상태 표시 (완료/진행중/대기) |
| `StepContent` | `components/workflow/StepContent.tsx` | 스텝별 상세 내용 및 액션 버튼 |

### 2.2 VDR 컴포넌트

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| `VdrFolderTree` | `components/vdr/VdrFolderTree.tsx` | 폴더 트리 뷰 (계층 구조) |
| `VdrFolder` | `components/vdr/VdrFolder.tsx` | 개별 폴더 컴포넌트 |
| `VdrUploadZone` | `components/vdr/VdrUploadZone.tsx` | 폴더별 드래그앤드롭 업로드 영역 |
| `VdrFileList` | `components/vdr/VdrFileList.tsx` | 폴더 내 파일 목록 |

### 2.3 Deal Setup 컴포넌트

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| `DealSetupWizard` | `components/deal/DealSetupWizard.tsx` | 멀티스텝 딜 생성 마법사 |
| `TeamSelector` | `components/deal/TeamSelector.tsx` | 팀원(Partner/Manager) 선택 |
| `ScopeSelector` | `components/deal/ScopeSelector.tsx` | FDD 범위(QoE/NWC/Debt) 선택 |

### 2.4 Report 컴포넌트

| 컴포넌트 | 경로 | 용도 |
|----------|------|------|
| `ReportVersionList` | `components/report/ReportVersionList.tsx` | 보고서 버전 목록 |
| `ReportVersionCard` | `components/report/ReportVersionCard.tsx` | 버전별 카드 (상태, 다운로드) |

---

## 3. 신규 페이지

| 페이지 | 경로 | 용도 |
|--------|------|------|
| `DealSetupWizardPage` | `pages/DealSetupWizardPage.tsx` | 멀티스텝 딜 생성 (/deals/new) |
| `WorkflowOverviewPage` | `pages/WorkflowOverviewPage.tsx` | 워크플로우 대시보드 (기존 Overview 대체) |
| `VdrPage` | `pages/VdrPage.tsx` | VDR 메인 (폴더 트리 + 업로드) |
| `DealSetupPage` | `pages/DealSetupPage.tsx` | MoU 정보 수정 |

---

## 4. 라우팅 변경

### 4.1 신규 라우트

```typescript
// frontend/src/App.tsx

// 신규 추가
"/deals/new"                  → DealSetupWizardPage
"/deals/:dealId/setup"        → DealSetupPage
"/deals/:dealId/vdr"          → VdrPage

// 변경
"/deals/:dealId"              → WorkflowOverviewPage (기존 Overview 대체)
```

### 4.2 전체 라우트 구조

```text
/login                        → LoginPage
/deals                        → DealListPage
/deals/new                    → DealSetupWizardPage (신규)
/deals/:dealId                → DealWorkspacePage
  ├── /                       → WorkflowOverviewPage (변경)
  ├── /setup                  → DealSetupPage (신규)
  ├── /vdr                    → VdrPage (신규)
  ├── /definitions            → DefinitionPage (기존)
  ├── /mapping                → MappingPage (기존)
  ├── /qoe                    → QoEPage (기존)
  ├── /nwc                    → NWCPage (기존)
  ├── /netdebt                → NetDebtPage (기존)
  ├── /issues                 → IssuesPage (기존)
  └── /report                 → ReportPage (버전 관리 추가)
```

---

## 5. 사이드바 재구성

### 5.1 기존 구조

```text
[Current Deal]
  • Overview
  • Definitions
  • Uploads
  • Mapping
  • QoE Bridge
  • Net Working Capital
  • Net Debt
  • Issues
  • Report
```

### 5.2 신규 구조

```text
[Current Deal: {deal_name}]

  ─── Workflow ───
  • Overview (스텝퍼 대시보드)

  ─── Phase 1: Setup ───
  • Deal Setup (MoU 정보)
  • VDR (Data Room)

  ─── Phase 2: Analysis ───
  • Definitions
  • Mapping
  • QoE Analysis
  • NWC Analysis
  • Net Debt
  • Issues

  ─── Phase 3: Report ───
  • Report Generator
```

---

## 6. 백엔드 모델 변경

### 6.1 Deal 모델 확장

```python
# backend/app/models/deal.py

class DealPhase(str, enum.Enum):
    MOU = "MOU"                    # Phase 1: MoU 체결
    VDR_SETUP = "VDR_SETUP"        # Phase 2: VDR 개설
    DATA_UPLOAD = "DATA_UPLOAD"    # Phase 3: 자료 업로드
    ANALYSIS = "ANALYSIS"          # Phase 4: 자료 검토
    REPORTING = "REPORTING"        # Phase 5: 보고서 작성

class Deal(Base):
    # 기존 필드 유지...

    # 신규: 클라이언트/타겟 정보 (Phase 1)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    client_contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 신규: 팀 구성
    team_partner_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("user.id"), nullable=True)
    team_manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("user.id"), nullable=True)

    # 신규: FDD 범위
    scope_qoe: Mapped[bool] = mapped_column(default=True)
    scope_nwc: Mapped[bool] = mapped_column(default=True)
    scope_debt: Mapped[bool] = mapped_column(default=True)

    # 신규: 워크플로우 상태
    current_phase: Mapped[DealPhase] = mapped_column(Enum(DealPhase), default=DealPhase.MOU)
```

### 6.2 VDR 모델 (신규)

```python
# backend/app/models/vdr.py

class VdrFolderType(str, enum.Enum):
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"  # 재무제표
    ACCOUNTS_RECEIVABLE = "ACCOUNTS_RECEIVABLE"    # 매출채권
    ACCOUNTS_PAYABLE = "ACCOUNTS_PAYABLE"          # 매입채무
    BANK_DEBT = "BANK_DEBT"                        # 은행/차입금
    LEASE = "LEASE"                                # 리스
    OTHERS = "OTHERS"                              # 기타
    CUSTOM = "CUSTOM"                              # 사용자 정의

class VdrFolder(Base):
    __tablename__ = "vdr_folder"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("deal.id", ondelete="CASCADE"))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("vdr_folder.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    folder_type: Mapped[VdrFolderType] = mapped_column(Enum(VdrFolderType), default=VdrFolderType.CUSTOM)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_required: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 관계
    deal: Mapped["Deal"] = relationship(back_populates="vdr_folders")
    children: Mapped[list["VdrFolder"]] = relationship("VdrFolder", back_populates="parent")
    parent: Mapped["VdrFolder | None"] = relationship("VdrFolder", back_populates="children", remote_side=[id])
    files: Mapped[list["UploadFile"]] = relationship(back_populates="vdr_folder")
```

### 6.3 UploadFile 확장

```python
# backend/app/models/upload.py

class UploadFile(Base):
    # 기존 필드...

    # 신규: VDR 폴더 연결
    vdr_folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID, ForeignKey("vdr_folder.id", ondelete="SET NULL"), nullable=True
    )
    vdr_folder: Mapped["VdrFolder | None"] = relationship(back_populates="files")
```

### 6.4 ReportVersion 모델 (신규)

```python
# backend/app/models/report.py

class ReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"    # 초안
    FINAL = "FINAL"    # 최종 확정

class ReportVersion(Base):
    __tablename__ = "report_version"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("deal.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.DRAFT)
    file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_format: Mapped[str] = mapped_column(String(10), default="pptx")  # pptx, docx
    options: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # 관계
    deal: Mapped["Deal"] = relationship(back_populates="report_versions")
```

---

## 7. 백엔드 API 추가

### 7.1 워크플로우 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/deals/{deal_id}/workflow` | 워크플로우 진행 상태 조회 |
| PUT | `/api/v1/deals/{deal_id}/workflow/phase` | 현재 단계 업데이트 |

### 7.2 VDR API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/deals/{deal_id}/vdr/init` | 기본 폴더 구조 초기화 |
| GET | `/api/v1/deals/{deal_id}/vdr/folders` | 폴더 목록 조회 (트리) |
| POST | `/api/v1/deals/{deal_id}/vdr/folders` | 폴더 생성 |
| PUT | `/api/v1/deals/{deal_id}/vdr/folders/{folder_id}` | 폴더 수정 |
| DELETE | `/api/v1/deals/{deal_id}/vdr/folders/{folder_id}` | 폴더 삭제 |
| GET | `/api/v1/deals/{deal_id}/vdr/folders/{folder_id}/files` | 폴더별 파일 목록 |

### 7.3 Report Version API

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/deals/{deal_id}/reports/versions` | 버전 목록 조회 |
| POST | `/api/v1/deals/{deal_id}/reports/versions` | 새 버전 생성 |
| PUT | `/api/v1/deals/{deal_id}/reports/versions/{version}/finalize` | Final 확정 |
| GET | `/api/v1/deals/{deal_id}/reports/versions/{version}/download` | 다운로드 |

---

## 8. 수정할 주요 파일

### 8.1 프론트엔드

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/App.tsx` | 신규 라우트 추가 |
| `frontend/src/components/layout/Sidebar.tsx` | 섹션 그룹화, VDR 메뉴 추가 |
| `frontend/src/pages/DealWorkspacePage.tsx` | Overview → WorkflowOverviewPage |
| `frontend/src/pages/DealListPage.tsx` | New Deal 클릭 시 /deals/new 이동 |
| `frontend/src/pages/ReportPage.tsx` | 버전 관리 UI 추가 |

### 8.2 백엔드

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/models/deal.py` | DealPhase enum, 워크플로우 필드 추가 |
| `backend/app/models/vdr.py` | VdrFolder 모델 (신규) |
| `backend/app/models/report.py` | ReportVersion 모델 (신규) |
| `backend/app/models/upload.py` | vdr_folder_id FK 추가 |
| `backend/app/schemas/deal.py` | 스키마 확장 |
| `backend/app/schemas/vdr.py` | VDR 스키마 (신규) |
| `backend/app/schemas/report.py` | ReportVersion 스키마 (신규) |
| `backend/app/api/vdr.py` | VDR API (신규) |
| `backend/app/api/reports.py` | 버전 관리 API 추가 |
| `backend/app/main.py` | 라우터 등록 |

### 8.3 Alembic 마이그레이션

```bash
# 마이그레이션 파일 생성
alembic revision --autogenerate -m "add_workflow_vdr_report_version"
```

---

## 9. 구현 순서

| 순서 | 작업 | 예상 시간 | 우선순위 |
|------|------|-----------|----------|
| 1 | WorkflowStepper + WorkflowOverviewPage | 1일 | HIGH |
| 2 | Sidebar 섹션 그룹화 | 0.5일 | HIGH |
| 3 | Deal 모델 확장 (백엔드) | 0.5일 | HIGH |
| 4 | DealSetupWizardPage (멀티스텝 폼) | 1일 | HIGH |
| 5 | VDR 모델/API (백엔드) | 1일 | MEDIUM |
| 6 | VdrPage + 컴포넌트 | 1일 | MEDIUM |
| 7 | UploadPage → VDR 통합 | 0.5일 | MEDIUM |
| 8 | ReportVersion 모델/API | 0.5일 | LOW |
| 9 | ReportPage 버전 관리 UI | 0.5일 | LOW |

**총 예상: 6.5일**

---

## 10. 검증 방법

### 10.1 단위 테스트

```bash
# 백엔드 테스트
cd backend && python -m pytest tests/vdr/ tests/report/ -v

# 프론트엔드 린트
cd frontend && npm run lint && npm run tsc
```

### 10.2 E2E 테스트 시나리오

1. **딜 생성 플로우**: /deals → New Deal → 4스텝 위저드 완료
2. **VDR 플로우**: VDR 초기화 → 폴더 생성 → 파일 업로드
3. **워크플로우 진행**: 5단계 순차 진행 확인
4. **보고서 버전**: Draft 생성 → Final 확정

### 10.3 수동 검증

- 워크플로우 스텝퍼 UI 확인
- 사이드바 섹션 그룹화 확인
- VDR 폴더 트리 렌더링 확인
- 보고서 버전 목록 확인

---

## 11. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|--------|------|------|
| VDR 폴더 구조 복잡도 | 개발 지연 | 기본 6개 폴더만 지원, 커스텀 폴더 후순위 |
| 기존 UploadPage 호환성 | 기존 기능 손상 | VDR 통합은 선택적, 기존 업로드 유지 가능 |
| 워크플로우 상태 동기화 | 상태 불일치 | 백엔드에서 자동 계산, 프론트엔드는 표시만 |

---

## 12. 참고 문서

- 현재 프론트엔드 구조: `docs/design/frontend-redesign-amic-style.md`
- Sprint 12 완료 현황: `FDD_프로젝트_진행현황.md`
- Deal 모델 정의: `backend/app/models/deal.py`
- 기존 라우팅: `frontend/src/App.tsx`
