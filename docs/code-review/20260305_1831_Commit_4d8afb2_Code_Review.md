# Code Review — 커밋 4d8afb2

> **Review Date**: 2026-03-05 18:31
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: 커밋 4d8afb2 — `fix(review): 코드 리뷰 C-1/I-1/I-2/I-3/M-1/M-2/M-3 전체 수정`
> **Method**: Review Gates + Quality Gates + Verified Multi-Agent Review + Cross-Verification
> **Quality Gates**: tsc(PASS) eslint(PASS) ruff(PASS) build(N/A)
> **Review Gates**: Backend(deal-mgmt ✓, FDD ✓, KIIS ✓, IM ✓) Agent-Filtering(5개 에이전트 호출)

## 대상 파일 (8개)

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx` | BothCompleteActions 이동, hasBizReg 수정, docCategoryHint 분리 |
| 2 | `amic-platform/src/modules/ma/types/document_extraction.ts` | REGISTRY_DOCS, BIZ_REG_DOCS 추가 |
| 3 | `deal-mgmt/app/models/enums.py` | DocExtractionCategory enum에 두 값 추가 |
| 4 | `deal-mgmt/app/schemas/pef_registry.py` | logo_url field_validator 추가 |
| 5 | `deal-mgmt/migrations/versions/066_add_doc_extraction_categories.py` | PostgreSQL ENUM ADD VALUE 마이그레이션 |
| 6 | `fdd/backend/app/api/ralph.py` | asyncio.run() → async def + await |
| 7 | `fdd/backend/app/api/reports.py` | asyncio.run() → async def + await |
| 8 | `fdd/backend/tests/conftest.py` | enable_auth 마커 추가 |

---

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Major    | 1     | HIGH: 1 / MEDIUM: 0 / LOW: 0 | P1: 1 |
| Moderate | 10    | HIGH: 7 / MEDIUM: 3 / LOW: 0 | P1: 1 / P2: 9 |
| Minor    | 9     | HIGH: 3 / MEDIUM: 4 / LOW: 2 | P3: 9 |
| **Total**| **20**| HIGH: **11** / MEDIUM: **7** / LOW: **2** | P1: **2** / P2: **9** / P3: **9** |

**FP Prevention**: 21건 검증, 1건 사전 거부 (거부율: 4.8%) | 교차 검증 4건 수행

**Priority Calculation**: 신뢰도 가중 우선순위 시스템 적용
- 교차 검증된 이슈(2+ 에이전트): +10 보너스
- review-verifier 확인된 이슈: +15 보너스
- MEDIUM 신뢰도 이슈 자동 하향 조정 적용

---

## Findings

---

### P1 — 즉시 대응 권장

---

#### [CR-1/API-1] `async def` 엔드포인트에서 sync DB 함수 직접 호출 — [Major/HIGH] — Priority: P1

> ⭐ 교차 확인: code-reviewer + api-auditor 독립 발견 + review-verifier 확인

**파일:**
- `fdd/backend/app/api/ralph.py:48` (`build_report_ir(db=db, deal_id=deal_id)`)
- `fdd/backend/app/api/reports.py:60-78` (`build_report_ir` 직접 호출)
- `fdd/backend/app/api/reports.py:458-468` (`create_report_version` 내 동기 DB 쿼리)

**증거:**
```python
# ralph.py:23-48
@router.post("/sessions", response_model=RalphSessionRead, status_code=201)
async def create_ralph_session(
    deal_id: UUID,
    body: RalphSessionCreate,
    current_user: CurrentUser = require_permission(Permission.REPORT_GENERATE),
    db: Session = Depends(get_db),
):
    # ↓ await 없이 동기 DB 집약 함수 직접 호출
    report_ir = build_report_ir(db=db, deal_id=deal_id)
    service = FDDRalphService(db)
    # ↓ LLM I/O 대기 (분 단위) 중에도 sync DB 세션을 열어둠
    refined_ir, session = await service.run_draft_pass(...)
```

```python
# database.py:21-29
def get_db():          # ← sync generator (async 아님)
    db = SessionLocal()  # ← sync engine 기반
    try:
        yield db
    ...
```

**주장:**
`get_db()` Depends 자체는 FastAPI가 `run_in_threadpool`로 처리하여 안전하다. 그러나 `async def` 엔드포인트 본문에서 동기 DB 집약 함수 `build_report_ir(db=db, ...)` (내부적으로 수십 개의 `db.scalar()`, `db.scalars()` 동기 I/O 수행)를 `await` 없이 직접 호출하면, 이 함수 전체 실행이 event loop 스레드를 점유한다. 특히 `create_ralph_session`과 `generate_report`/`create_report_version`는 `build_report_ir` 완료 후 LLM API를 수십 초~수 분 대기하는 구조이므로, sync 세션이 장시간 커넥션 풀을 점유한다.

**영향:**
- Azure VM 2 vCPU 환경에서 보고서 생성 + Ralph Loop 동시 요청 2건 → 나머지 모든 요청(헬스체크 포함) 대기 상태 가능
- DB 커넥션 풀 (`pool_size=20, max_overflow=10`) 점유 → 고부하 시 `QueuePool limit reached` 오류

**수정 방향:**
1. (권장) `build_report_ir`을 `asyncio.get_event_loop().run_in_executor(None, build_report_ir, db, deal_id)`로 threadpool에서 실행
2. (장기) FDD 모듈 전체를 `AsyncSession` + `create_async_engine`으로 전환

---

#### [CR-2/API-3] `download_report_version` — 파일 핸들 예외 경로 미해제 — [Moderate/HIGH] — Priority: P1

> ⭐ 교차 확인: code-reviewer + api-auditor 독립 발견 + review-verifier 확인 (Starlette 정상 흐름에서는 자동 close 확인)

**파일:** `fdd/backend/app/api/reports.py:625-631`

**증거:**
```python
return StreamingResponse(
    open(file_path, "rb"),    # ← with 없이 raw open() — 예외 경로에서 FD 누수
    media_type=media_type,
    headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
    },
)
```

**같은 파일 내 다른 엔드포인트 패턴 (일관성 없음):**
```python
# generate_report (laion 149-158) — 올바른 패턴
docx_buffer = render_word_report(report_ir)   # io.BytesIO 반환
return StreamingResponse(docx_buffer, ...)

# generate_report (라인 203-209) — 올바른 패턴
return StreamingResponse(xlsx_buffer, ...)    # io.BytesIO
```

**주장:**
Starlette `StreamingResponse`는 정상 흐름(스트리밍 완료)에서는 파일 객체의 `close()`를 자동 호출한다. 그러나 클라이언트 조기 연결 종료, 미들웨어 예외, 타임아웃 등 비정상 흐름에서는 파일 핸들이 닫히지 않아 FD 누수가 발생할 수 있다. 또한 같은 파일의 다른 엔드포인트들이 모두 `io.BytesIO`를 사용하는 것과 일관성이 없다.

**수정 방향:**
```python
# 옵션 1: FileResponse 사용 (Starlette 내장 파일 핸들 관리)
from starlette.responses import FileResponse
return FileResponse(
    path=file_path,
    media_type=media_type,
    filename=filename,
)

# 옵션 2: BytesIO로 메모리 로드 (파일이 작은 경우)
with open(file_path, "rb") as f:
    return StreamingResponse(io.BytesIO(f.read()), ...)
```

---

### P2 — 개선 권장

---

#### [API-2] `reports.py` — `router` 로컬 변수가 module-level `router` 섀도잉 — [Moderate/HIGH] — Priority: P2

**파일:** `fdd/backend/app/api/reports.py:38, 110`

**증거:**
```python
# 파일 최상단 (라인 38)
router = APIRouter(prefix="/deals/{deal_id}/reports", tags=["reports"])

# generate_report() 내부 (라인 110)
if qa_enabled:
    router = create_fdd_model_router()  # ← 로컬 변수로 module-level router 섀도잉
    qa_agent = ReportQAAgent(router=router)
```

**주장:** `generate_report()` 함수 내 `router = create_fdd_model_router()`는 의도적으로 LLM 모델 라우터 객체를 만들어 QA 에이전트에 전달하는 코드이나, module-level `router` (FastAPI APIRouter)와 동일한 이름을 사용하여 혼란을 유발한다. 현재 함수 내에서 APIRouter 목적으로 `router`를 재참조하는 코드가 없어 즉각적 버그는 없으나, 향후 이 함수에 `router.get(...)` 형태 코드 추가 시 예기치 않은 AttributeError가 발생한다.

**수정 방향:**
```python
# 변경 전
router = create_fdd_model_router()
qa_agent = ReportQAAgent(router=router)

# 변경 후
llm_router = create_fdd_model_router()
qa_agent = ReportQAAgent(router=llm_router)
```

---

#### [A11Y-3] `EngagementDocUpload` — 드롭존 div 키보드 접근성 미충족 — [Moderate/HIGH] — Priority: P2

> ⭐ review-verifier 확인: `<Button>` 대안 존재로 완전 차단 아님. 드롭존 div 자체의 키보드 접근성은 WCAG 4.1.2 위반.

**파일:** `amic-platform/src/modules/ma/components/overview/EngagementDocUpload.tsx:378-430`

**증거:**
```tsx
<div
  className="border-2 border-dashed ... cursor-pointer"
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onDrop={handleDrop}
  onClick={() => fileInputRef.current?.click()}
  // ← tabIndex 없음, role 없음, onKeyDown 없음
>
  <input
    ref={fileInputRef}
    type="file"
    className="hidden"   // ← 키보드 포커스 순서에서 제외됨
    ...
  />
  <Button ...>파일 선택</Button>   {/* ← 유일한 키보드 대안 */}
</div>
```

**주장:** `cursor-pointer`가 적용된 클릭 가능 div에 `tabIndex={0}`, `role="button"`, `onKeyDown` 처리가 없다. `<Button>` 컴포넌트가 대안으로 존재하지만, div의 `onClick`(파일 선택 트리거)은 키보드로 접근 불가. WCAG 4.1.2 (Name, Role, Value, Level A) 위반.

**수정 방향:**
```tsx
<div
  role="button"
  tabIndex={0}
  aria-label="파일을 드래그하거나 클릭하여 업로드"
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInputRef.current?.click();
    }
  }}
  onClick={() => fileInputRef.current?.click()}
  ...
>
```

---

#### [CR-3/API-4] Migration 066 — `downgrade()` pass — [Moderate/HIGH] — Priority: P2

**파일:** `deal-mgmt/migrations/versions/066_add_doc_extraction_categories.py:25-27`

**증거:**
```python
def downgrade() -> None:
    # PostgreSQL ENUM 값은 삭제 불가 — 롤백 시 애플리케이션 레이어에서 값을 사용하지 않도록 관리
    pass
```

**주장:** PostgreSQL `ALTER TYPE ... ADD VALUE`로 추가된 ENUM 값은 `ALTER TYPE ... DROP VALUE`가 없어 실제로 삭제 불가능하다(PostgreSQL 제약). `pass` 처리는 이를 인식한 의도적 선택이며 Alembic 관행상 허용된다. 그러나 `alembic downgrade 065` 실행 시 Alembic은 성공으로 처리하지만 DB ENUM에는 `REGISTRY_DOCS`, `BIZ_REG_DOCS`가 여전히 존재한다. 065 버전 코드(두 값 인식 불가)가 배포된 상태에서 DB에 해당 값이 있으면 ORM 파싱 오류가 발생할 수 있다.

**권고:** `downgrade()`에서 명시적 예외를 발생시켜 의도치 않은 다운그레이드를 방지하는 것이 더 안전하다:
```python
def downgrade() -> None:
    raise NotImplementedError(
        "PostgreSQL ENUM 값 삭제 불가 — downgrade 불지원. "
        "알림: DB에 REGISTRY_DOCS, BIZ_REG_DOCS 값이 잔류함."
    )
```

---

#### [CR-4] `GpProfileListItemOut` — 잘못된 `logo_url` silent None 처리 — [Moderate/MEDIUM] — Priority: P2

**파일:** `deal-mgmt/app/schemas/pef_registry.py:67-75`

**증거:**
```python
@field_validator("logo_url", mode="before")
@classmethod
def validate_logo_url(cls, v: str | None) -> str | None:
    if v is None:
        return None
    v = str(v).strip()
    if not v.startswith(("http://", "https://")):
        return None   # ← 비정상 URL을 에러 없이 None으로 드롭
    return v
```

**주장:** 출력 스키마에서 DB에 저장된 값을 silently `None`으로 변환하면, `logo_url = "invalid-path"` 형태로 DB에 오염된 데이터가 있을 때 API 응답에서 `null`로 보이며 데이터 품질 이슈가 가려진다. 보안 측면(XSS 방지)에서 필터링 자체는 올바르나, 로깅 또는 경고 없이 드롭하는 것은 운영 가시성을 저하시킨다.

**권고:** 비정상 URL 드롭 시 최소한 경고 로그를 남기도록 개선:
```python
import logging
logger = logging.getLogger(__name__)

if not v.startswith(("http://", "https://")):
    logger.warning("GpProfile logo_url 비정상 값 드롭: %r", v)
    return None
```

---

#### [SEC-2] `Content-Disposition` 헤더에 비검증 `deal_name` 삽입 — [Moderate/MEDIUM] — Priority: P2

**파일:** `fdd/backend/app/api/reports.py:150, 201, 215, 303`

**증거:**
```python
# 4개 엔드포인트에서 동일 패턴
filename = f"FDD_Report_{report_ir.metadata.deal_name}.docx"
return StreamingResponse(
    docx_buffer,
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
)
```

**주장:** `deal_name`은 DB에서 읽어온 사용자 입력 데이터다. `deal_name`에 `"`, `\r\n` 등이 포함되면 HTTP 헤더 파싱 오류 또는 헤더 인젝션이 이론적으로 가능하다. 현대 브라우저와 uvicorn/Starlette 스택이 일부 방어하지만 완전히 보장되지는 않는다.

**수정 방향:**
```python
# RFC 5987 인코딩 적용
from urllib.parse import quote
safe_filename = quote(filename, safe='- _.()[]')
headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"}
```

---

#### [A11Y-2] 업로드 토글 버튼 `aria-expanded` 누락 — [Moderate/HIGH] — Priority: P2

**파일:** `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx:69-77`

**증거:**
```tsx
<button
  type="button"
  onClick={onUploadToggle}
  // ← aria-expanded 없음, UploadCloud 아이콘 aria-hidden 없음
>
  <UploadCloud className="h-3 w-3" />
  {uploadOpen ? "닫기" : `${docName}를 업로드하세요`}
</button>
```

**주장:** WCAG 4.1.2 (Name, Role, Value, Level A) — 확장/축소 토글 컨트롤에 `aria-expanded` 속성이 없어 스크린 리더 사용자가 현재 상태를 프로그래매틱하게 알 수 없다. 법인등기부/사업자등록증 두 섹션 모두 동일 패턴.

**수정 방향:**
```tsx
<button
  aria-expanded={uploadOpen}
  aria-controls={`upload-panel-${docName}`}
  type="button"
  onClick={onUploadToggle}
>
  <UploadCloud className="h-3 w-3" aria-hidden="true" />
  {uploadOpen ? "닫기" : `${docName}를 업로드하세요`}
</button>
```

---

#### [A11Y-4] 완료 배지 등장 시 `aria-live` 알림 없음 — [Moderate/MEDIUM] — Priority: P2

**파일:** `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx:259-265`

**증거:**
```tsx
<Card
  actions={bothComplete ? <BothCompleteActions /> : undefined}
  ...
>
```

**주장:** `bothComplete`가 `false → true`로 전환될 때 카드 헤더에 `<BothCompleteActions />`가 나타나지만 `aria-live` 영역이 없어 스크린 리더에게 알림이 전달되지 않는다. WCAG 4.1.3 (Status Messages, Level AA).

**수정 방향:**
```tsx
<div aria-live="polite" aria-atomic="true" className="sr-only">
  {bothComplete ? "법인등기부 및 사업자등록증 업로드가 완료되었습니다." : ""}
</div>
```

---

#### [A11Y-6] 업로드 진행 스텝 인디케이터 — `aria-live` / `role="alert"` 누락 — [Moderate/HIGH] — Priority: P2

**파일:** `amic-platform/src/modules/ma/components/overview/EngagementDocUpload.tsx:296-373`

**증거:**
```tsx
{step === "failed" ? (
  <div className="text-center py-2">
    <AlertCircle ... />
    <p className="text-sm text-negative mb-3">{errorMsg}</p>
    {/* ← role="alert" 없음 — 스크린 리더에게 즉시 알림 없음 */}
  </div>
) : (
  <div className="space-y-2.5">
    {steps.map((s, i) => (
      <div key={s.key} className="flex items-center gap-2.5">
        {/* ← aria-live 없음 — 스텝 전환 스크린 리더 인식 불가 */}
        <span>{s.label}</span>
      </div>
    ))}
  </div>
)}
```

**주장:** 파일 업로드 후 `UPLOADING → CLASSIFYING → EXTRACTING → COMPLETED/FAILED` 전환이 발생하나 `aria-live` 영역 없어 스크린 리더 사용자는 진행 상태 파악 불가. 실패 시 에러 메시지에 `role="alert"`도 없다. WCAG 4.1.3 (Status Messages, Level AA).

**수정 방향:**
```tsx
<div aria-live="polite" aria-atomic="true">
  {step === "failed" ? (
    <div role="alert">
      <p>{errorMsg}</p>
    </div>
  ) : (
    <p className="sr-only">{activeStep?.label} 진행 중...</p>
  )}
</div>
```

---

#### [API-5] `enable_auth` 마커 사용 테스트 부재 — RBAC 테스트 공백 — [Moderate/MEDIUM] — Priority: P2

**파일:** `fdd/backend/tests/conftest.py:133-147`

**증거:**
```python
@pytest.fixture(autouse=True)
def _disable_auth(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """모든 테스트에서 인증을 비활성화."""
    if request.node.get_closest_marker("enable_auth"):
        return
    monkeypatch.setattr(settings, "auth_enabled", False)
```

**주장:** `_disable_auth`가 모든 테스트에서 autouse로 인증을 비활성화한다. `@pytest.mark.enable_auth` 마커로 opt-out 가능하지만 현재 이 마커를 사용하는 테스트가 없다면, `require_permission(Permission.REPORT_GENERATE)` 등 RBAC 로직이 테스트되지 않아 권한 우회 회귀가 발생해도 감지 불가.

**권고:** 핵심 보안 엔드포인트 최소 1개에 `@pytest.mark.enable_auth`를 적용한 인증 테스트 추가:
```python
@pytest.mark.enable_auth
def test_ralph_session_requires_auth(client: TestClient):
    resp = client.post(f"/deals/{deal_id}/ralph/sessions", ...)
    assert resp.status_code == 401
```

---

### P3 — 개선 가능 (기술 부채)

---

#### [TC-1] `docCategoryHint` prop/hook 타입이 `string`으로 느슨하게 선언 — [Minor/MEDIUM] — Priority: P3

**파일:**
- `amic-platform/src/modules/ma/components/overview/EngagementDocUpload.tsx:29` (`docCategoryHint?: string`)
- 참조 hook에도 동일 패턴

**주장:** `docCategoryHint`가 `string` 대신 `DocExtractionCategory | undefined`로 선언되어야 컴파일 타임에 잘못된 카테고리 값 전달을 방지한다. BE `ExtractionCreateRequest.doc_category_hint`는 `DocExtractionCategory`로 엄격하게 선언되어 있어 BE↔FE 타입 정합성이 미흡하다.

---

#### [API-6] `Decimal → float` 직렬화 — Money Rules 위반 — [Minor/HIGH] — Priority: P3

**파일:** `deal-mgmt/app/schemas/pef_registry.py:79, 97`

**증거:**
```python
# GpProfileListItemOut (라인 79)
def _serialize_sum(cls, v: Decimal | None) -> float | None:
    return float(v) if v is not None else None   # ← Money Rules 위반

# FIRecommendationV2 (라인 97)
def _serialize_decimal(cls, v: Decimal) -> float:
    return float(v)                               # ← 동일 위반

# 올바른 패턴 (같은 파일 라인 27, 48)
def _serialize_capital(cls, v: Decimal | None) -> str | None:
    return str(v) if v is not None else None     # ← str 변환이 정확
```

**주장:** Python Money Rules: "ALL monetary values: `string` (JSON/TypeScript). NEVER `float`." 위반. `float("123456789012.1234")` 변환 시 정밀도 손실 가능. 같은 파일의 다른 serializer들이 `str()` 변환을 사용하여 일관성도 없다.

---

#### [CR-5] `hasBizReg` — 번호 추출 실패 엣지 케이스 — [Minor/HIGH] — Priority: P3

**파일:** `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx:256`

**증거:**
```tsx
const hasBizReg = !!ci?.business_registration_number;
```

**주장:** 사업자등록증 파일이 업로드됐으나 OCR/추출에서 `business_registration_number`가 `null`로 저장된 경우, 문서가 실제로 존재해도 `hasBizReg=false`가 되어 업로드 버튼이 재표시된다. 이전 로직(`business_type` 포함)의 false positive를 제거한 것은 올바르나, 이 엣지 케이스가 잔존한다.

---

#### [CR-6] `CORPORATE_DOCS` 레거시 처리 — 장기 기술 부채 — [Minor/HIGH] — Priority: P3

**파일:** `deal-mgmt/app/models/enums.py:770`

**주장:** `CORPORATE_DOCS`를 레거시로 유지하는 것은 올바른 선택이다. 단, 기존 데이터를 `REGISTRY_DOCS`/`BIZ_REG_DOCS`로 재분류하는 마이그레이션 계획이 없으면 레거시 분기가 코드베이스에 영구 잔류한다. 데이터 마이그레이션 태스크를 백로그에 추가 권고.

---

#### [A11Y-1] 완료 아이콘 `aria-hidden` 누락 — [Minor/HIGH] — Priority: P3

**파일:** `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx:63-67`

**증거:**
```tsx
<CheckCircle2 className="h-3.5 w-3.5" />   {/* aria-hidden 없음 */}
업로드 완료
```

**주장:** 아이콘이 시각적 장식 요소이며 인접 텍스트가 의미를 완전히 전달하므로 `aria-hidden="true"` 추가 권장. WCAG 1.1.1 (Non-text Content, Level A).

---

#### [A11Y-5] 하위 섹션 헤딩 계층 오류 (h4→h4) — [Minor/MEDIUM] — Priority: P3

**파일:** `amic-platform/src/modules/ma/components/overview/CompanyInfoCard.tsx:120, 191, 217`

**주장:** `SectionHeader`(h4) 하위에 `CapitalSection`/`DirectorsSection`/`PurposeSection`이 동일한 h4로 렌더링되어 계층이 `h3 > h4 > h4`(동일 레벨 중첩) 구조다. `h5`로 변경하거나 `<section>` 사용 권장.

---

#### [TC-4] `mode="before"` validator 인자 타입 부정확 — [Minor/LOW] — Priority: P3

**파일:** `deal-mgmt/app/schemas/pef_registry.py:69`

**주장:** Pydantic v2 `mode="before"` validator는 Pydantic 타입 변환 전에 호출되므로 실제 입력 타입은 `Any`일 수 있다. `v: str | None` 선언은 기술적으로 부정확하나, `str(v).strip()` 호출로 런타임에서 안전하게 처리됨. Pyright/mypy 엄격 모드에서 경고 발생 가능.

---

#### [CR-7] `enable_auth` + `monkeypatch` 병렬 테스트 flaky 가능성 — [Minor/MEDIUM] — Priority: P3

**파일:** `fdd/backend/tests/conftest.py:133-147`

**주장:** `settings` 싱글턴에 `monkeypatch.setattr`을 적용하므로 `pytest-xdist` 병렬 실행 시 동일 프로세스 워커 간 설정 레이스 컨디션 가능성. 현재 순차 실행 환경에서는 문제없음.

---

#### [SEC-3] `logo_url` — 내부 네트워크 URL 예방적 차단 권고 — [Minor/MEDIUM] — Priority: P3

**파일:** `deal-mgmt/app/schemas/pef_registry.py:67-75`

**주장:** 현재 `http://`/`https://` 시작 여부만 확인하므로 `http://localhost/`, `http://169.254.169.254/` (Azure 메타데이터 엔드포인트) 등이 통과된다. 현재 코드에서 `logo_url`을 서버에서 fetch하는 경로가 없어 즉각적 SSRF 위험은 없다. 향후 프록시/캐싱 기능 추가 시 내부 IP 필터링 추가 필요.

---

## Priority Matrix

### P1 — 즉시 대응 권장 (점수: 90+)

1. **[CR-1/API-1]** [Major/HIGH ⭐교차검증+verifier]: `async def` 내 `build_report_ir()` 동기 호출 → event loop 블로킹 — `ralph.py:48`, `reports.py:60-78, 458-468` (점수: 95)
2. **[CR-2/API-3]** [Moderate/HIGH ⭐교차검증+verifier]: `open(file_path, "rb")` FD 누수 위험 — `reports.py:626` (점수: 65 → P1 보정: 교차검증 두 에이전트)

### P2 — 개선 권장 (점수: 30-89)

1. **[API-2]** [Moderate/HIGH]: `router` 이름 충돌 (APIRouter 섀도잉) — `reports.py:110` (점수: 40)
2. **[A11Y-3]** [Moderate/HIGH ⭐verifier]: 드롭존 div 키보드 접근성 미충족 — `EngagementDocUpload.tsx:378-430` (점수: 55)
3. **[CR-3/API-4]** [Moderate/HIGH]: `downgrade() → pass` — `066_migration.py:25-27` (점수: 40)
4. **[A11Y-2]** [Moderate/HIGH]: 업로드 토글 `aria-expanded` 누락 — `CompanyInfoCard.tsx:69-77` (점수: 40)
5. **[A11Y-6]** [Moderate/HIGH]: 업로드 진행 `aria-live` 누락 — `EngagementDocUpload.tsx:296-373` (점수: 40)
6. **[CR-4]** [Moderate/MEDIUM]: `logo_url` silent None — `pef_registry.py:67-75` (점수: 24 → P2 보정)
7. **[SEC-2]** [Moderate/MEDIUM]: `Content-Disposition` 헤더 인젝션 — `reports.py:150, 201, 215, 303` (점수: 24)
8. **[A11Y-4]** [Moderate/MEDIUM]: 완료 배지 `aria-live` 누락 — `CompanyInfoCard.tsx:259-265` (점수: 24)
9. **[API-5]** [Moderate/MEDIUM]: `enable_auth` 테스트 커버리지 공백 — `conftest.py:133-147` (점수: 24)

### P3 — 기술 부채 (점수: <30)

1. **[TC-1]** [Minor/MEDIUM]: `docCategoryHint` 느슨한 `string` 타입 — `EngagementDocUpload.tsx:29`
2. **[API-6]** [Minor/HIGH]: `Decimal → float` 직렬화 Money Rules 위반 — `pef_registry.py:79, 97`
3. **[CR-5]** [Minor/HIGH]: `hasBizReg` 번호 추출 실패 엣지 케이스 — `CompanyInfoCard.tsx:256`
4. **[CR-6]** [Minor/HIGH]: `CORPORATE_DOCS` 레거시 기술 부채 — `enums.py:770`
5. **[A11Y-1]** [Minor/HIGH]: 완료 아이콘 `aria-hidden` 누락 — `CompanyInfoCard.tsx:63-67`
6. **[A11Y-5]** [Minor/MEDIUM]: 헤딩 계층 오류 h4→h4 — `CompanyInfoCard.tsx:120, 191, 217`
7. **[TC-4]** [Minor/LOW]: `mode="before"` validator 인자 타입 부정확 — `pef_registry.py:69`
8. **[CR-7]** [Minor/MEDIUM]: `enable_auth` 병렬 테스트 flaky — `conftest.py:133-147`
9. **[SEC-3]** [Minor/MEDIUM]: `logo_url` 내부 IP 예방적 차단 권고 — `pef_registry.py:67-75`

---

## 허위 양성 (제거됨)

| 이슈 | 제거 사유 | 분류 |
|------|----------|------|
| SEC-1: DB 경로 기반 파일 접근 | `file_path`는 서버 내부 고정 패턴(`uploads/{uuid}/reports/v{n}.{ext}`)으로만 생성. 외부 주입 벡터 없음. UUID FastAPI 파싱으로 경로 조작 차단. | FP-CTX (맥락 오해) |

---

## Methodology

- **Agents**: code-reviewer, type-checker, api-auditor, security-auditor, a11y-auditor (5개)
- **Excluded Agents**: 없음 (모든 백엔드 available, 8개 파일 스코프에 모든 에이전트 적용)
- **Files scanned**: 8개
- **Protocol**: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- **Cross-verification**: 4개 Major 이슈 교차 검증 (CR-1/API-1, CR-2/API-3, SEC-1, A11Y-3)
- **Backend availability**: deal-mgmt ✓, FDD ✓, KIIS ✓, IM ✓

---

## 검증 투명성

### 검증 통계
- 검증한 가설: 21건
- 거부된 가설: 1건 (SEC-1)
- 보고된 이슈: 20건
- 거부율: 4.8%

### 거부 사유 분류

| 사유 | 건수 | 예시 |
|------|------|------|
| FP-CTX (맥락 오해) | 1 | SEC-1: DB 경로 외부 주입 벡터 없음 |

### 교차 검증 결과

| 이슈 | Phase 1 심각도 | 검증 판정 | 확정 심각도 | 조정 내용 |
|------|-------------|---------|-----------|---------|
| CR-1/API-1 | Major (Critical) | PARTIAL | Major | Depends threadpool 오프로드 확인. 실제 문제는 `build_report_ir()` 직접 호출 |
| CR-2/API-3 | Major | PARTIAL | Moderate | Starlette 정상 흐름 자동 close 확인. 예외 경로에만 위험 |
| SEC-1 | Moderate | FALSE_POSITIVE | (제거) | 경로 생성이 서버 내부 고정 패턴임 확인 |
| A11Y-3 | Major | CONFIRMED | Moderate | `<Button>` 대안 존재로 완전 차단 아님 |
