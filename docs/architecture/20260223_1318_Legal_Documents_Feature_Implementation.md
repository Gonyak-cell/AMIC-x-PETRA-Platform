# 법률 문서 생성 기능 구현 보고서

> 작성일: 2026-02-23 13:18:00
> 브랜치: `feat/ma-workflow`
> 세션: 34 (이전 세션 이어서)

---

## 개요

M&A 실무에서 사용되는 5종 법률 문서(SPA, SHA, BTA, SSA, MOU)를 Deal Document Studio에서 거래(Transaction)별로 생성·다운로드할 수 있는 기능을 구현했다. 백엔드는 `deal-mgmt` 서비스, 프론트엔드는 `amic-platform` Docs 모듈에 통합했다.

---

## 구현 범위

### 백엔드 (deal-mgmt) — Phase A (이전 세션 완료)

| 파일 | 유형 | 내용 |
|------|------|------|
| `pyproject.toml` | 수정 | `docxtpl>=0.16.0`, `python-docx>=1.1.0` 추가 |
| `app/models/enums.py` | 수정 | `LegalDocType`, `LegalDocStatus` Enum 추가 |
| `app/models/legal_document.py` | 신규 | SQLAlchemy 모델 (JSONB parameters) |
| `app/schemas/legal_document.py` | 신규 | Pydantic 스키마 + 타입별 파라미터 모델 |
| `app/services/legal_document_service.py` | 신규 | docxtpl 렌더링 서비스 (asyncio.to_thread) |
| `app/routers/legal_documents.py` | 신규 | CRUD + 다운로드 API |
| `app/main.py` | 수정 | 라우터 등록, openapi_tags 추가 |
| `migrations/versions/007_phase6_legal_documents.py` | 신규 | Alembic 마이그레이션 |
| `templates/legal/*.docx` | 신규 | 5종 docxtpl 템플릿 (python-docx로 생성) |
| `generated/legal/.gitkeep` | 신규 | 출력 디렉토리 플레이스홀더 |
| `scripts/create_legal_templates.py` | 신규 | 템플릿 생성 스크립트 |
| `tests/test_legal_documents.py` | 신규 | pytest 테스트 13개 |

### 프론트엔드 (amic-platform) — Phase B (이번 세션 완료)

| 파일 | 유형 | 내용 |
|------|------|------|
| `src/modules/docs/types/legal_document.ts` | 신규 | TS 타입 + LEGAL_DOC_META 상수 |
| `src/modules/docs/hooks/useLegalDocuments.ts` | 신규 | TanStack Query 훅 5개 + URL/포맷 헬퍼 |
| `src/modules/docs/components/LegalDocTypePicker.tsx` | 신규 | 5종 카드 선택 UI |
| `src/modules/docs/components/LegalParamsForm.tsx` | 신규 | 타입별 파라미터 입력 폼 (동적 리스트 포함) |
| `src/modules/docs/components/LegalDocumentsTab.tsx` | 신규 | TransactionWorkspace 탭 컴포넌트 |
| `src/modules/docs/pages/CreateLegalDocumentPage.tsx` | 신규 | 3-step wizard 생성 페이지 |
| `src/modules/docs/DocsRoutes.tsx` | 수정 | `legal/new` lazy Route 추가 |
| `src/modules/docs/pages/StudioHomePage.tsx` | 수정 | Legal Documents 섹션 (5종 카드) 추가 |
| `src/modules/ma/pages/TransactionWorkspacePage.tsx` | 수정 | "법률 문서" 탭 추가 |

---

## API 명세

```
Router prefix: /api/v1/transactions/{txn_id}/legal-documents

GET    /                         법률 문서 목록 조회
GET    /{doc_id}                 단건 조회
POST   /                         생성 + 즉시 docxtpl 렌더링 (→ 201)
POST   /{doc_id}/regenerate      파라미터 수정 후 재렌더링
GET    /{doc_id}/download        FileResponse (.docx 다운로드)
DELETE /{doc_id}                 삭제 (파일도 함께) → 204
```

---

## 데이터 모델

```python
class LegalDocument(Base, TimestampMixin):
    __tablename__ = "legal_documents"
    id: UUID (PK)
    transaction_id: UUID (FK→transactions, CASCADE)
    doc_type: LegalDocType   # SPA | SHA | BTA | SSA | MOU
    title: str(300)
    status: LegalDocStatus   # DRAFT | GENERATING | READY | FAILED
    parameters: JSONB        # 타입별 입력값
    template_version: str
    file_path: str(500)
    file_name: str(300)
    file_size_bytes: int
    error_message: text
    created_by_email: str
```

---

## 프론트엔드 UX 흐름

### Deal Document Studio (StudioHomePage)
- Legal Documents 섹션: SPA/SHA/BTA/SSA/MOU 5종 빠른 생성 카드
- 클릭 → `/docs/legal/new?type={TYPE}`

### CreateLegalDocumentPage (3-step wizard)
```
URL: /docs/legal/new?txn_id={uuid}&type={SPA|SHA|...}

Step 0: 문서 유형 선택 (LegalDocTypePicker)
        → URL ?type= 파라미터 있으면 자동 선택 후 Step 1 이동

Step 1: 파라미터 입력 (LegalParamsForm)
        → txn_id 있으면 Transaction에서 자동 채우기:
          · target_company_name ← txn.target_company_name
          · total_purchase_price ← txn.estimated_deal_value
          · closing_date ← txn.target_close_date
          · SPA: seller/buyer ← txn.side + txn.client_name
          · MOU: party_a ← txn.client_name, party_b ← txn.target_company_name

Step 2: 확인 및 생성
        → POST /transactions/{txn_id}/legal-documents
        → READY: 다운로드 버튼 표시
        → FAILED: 오류 메시지 + 재시도 버튼
```

### TransactionWorkspacePage
- 15번째 탭 "법률 문서" 추가 (id: `legal_docs`)
- LegalDocumentsTab 컴포넌트: 목록 테이블 + 빠른 생성 버튼 + 다운로드/삭제

---

## 문서 유형별 파라미터 요약

| 유형 | 한국명 | 주요 파라미터 |
|------|--------|--------------|
| SPA | 주식매매계약 | seller/buyer 정보, 주식 수, 단가, 총가액, 계약/종결일, 에스크로 |
| SHA | 주주간계약 | 회사명, 주주 목록, 이사회 구성, ROFR/drag-along/tag-along, 락업 |
| BTA | 영업양수도계약 | 양도/양수인, 양도 자산 목록, 제외 자산, 총 대금, 직원 이전 |
| SSA | 신주인수계약 | 회사/투자자명, 신주 수, 인수가액, Pre-money 밸류에이션, 청산우선권 |
| MOU | 양해각서 | 당사자 갑/을, 목적, 독점협상기간, 비밀유지기간, 구속/비구속 조항 |

---

## 기술 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| 템플릿 방식 | python-docx 프로그래밍 생성 | 즉시 구현 가능, 외부 파일 의존 없음 |
| 렌더링 | docxtpl (Jinja2) + asyncio.to_thread | 표준적, 비동기 블로킹 회피 |
| 파일 저장 | 서버 로컬 (`generated/legal/`) | 현재 규모에서 S3 불필요 |
| 프론트 페이지 | 별도 CreateLegalDocumentPage | 기존 CreateDocumentPage가 1,095줄로 비대 |
| MA 연동 | TransactionWorkspace 새 탭 | txn_id URL 파라미터 기존 패턴 재사용 |
| 전역 법률문서 목록 | 미구현 (txn별 조회만) | 현재 사용 패턴상 불필요 |

---

## Alembic 마이그레이션

- 파일: `007_phase6_legal_documents.py`
- 다운 리비전: `006_phase5b_risk_compliance`
- PostgreSQL Enum 타입: `legaldoctype`, `legaldocstatus`
- 테이블: `legal_documents`

---

## 발생 이슈 및 해결

| 이슈 | 원인 | 해결 |
|------|------|------|
| `ModuleNotFoundError: docx.util.Cm` | import 경로 오류 | `from docx.shared import Cm, Pt, RGBColor` |
| Unicode 인코딩 오류 (Windows cp949) | 스크립트에 이모지 포함 | `[OK]`, `[DONE]` 등 ASCII로 교체 |
| `uv` 명령 없음 | 환경 미설치 | `python` 직접 호출 |
| python-docx 미설치 | 신규 의존성 | `pip install python-docx` 선행 실행 |

---

## 검증 결과

- `npx tsc --noEmit` → **오류 없음**
- 백엔드 테스트 파일: `deal-mgmt/tests/test_legal_documents.py` (13개 테스트)

---

## 다음 단계 (선택적)

- [ ] `scripts/convert_onedrive_templates.py` — OneDrive 샘플 .docx → docxtpl 변환 유틸
- [ ] 실제 샘플 파일로 템플릿 품질 개선 (변수 치환 방식으로 고도화)
- [ ] 법률 문서 전역 목록 API + StudioHomePage 연동 (페이징)
- [ ] 문서 상태 폴링 (GENERATING 중일 때 UI 자동 갱신)
