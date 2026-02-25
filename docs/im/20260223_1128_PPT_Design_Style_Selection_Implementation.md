# PPT 디자인 스타일 선택 기능 구현 보고서

> 작성: 2026-02-23 11:28:00
> 브랜치: `feat/ma-workflow`
> 관련 플랜: `C:\Users\서지원\.claude\plans\dapper-doodling-scone.md`

---

## 개요

Deal Document Studio에서 IM/TM 문서를 생성할 때 PPT 브랜딩 디자인 스타일을 선택할 수 있는 기능을 추가했다.
이전에는 AMIC 단독 브랜딩만 고정 적용되었으나, 협업 파트너와의 공동 브랜딩(AMIC x [파트너]) 선택이 가능해졌다.

---

## 변경 사항

### 프론트엔드 (3개 파일)

#### 1. `amic-platform/src/modules/docs/types/document.ts`

```ts
// 신규 타입
export type PPTDesignStyle = "AMIC" | "AMIC_COLLAB";

// DocumentCreate 확장
export interface DocumentCreate {
  // ...기존 필드...
  ppt_design_style?: PPTDesignStyle;   // 기본값: "AMIC"
  collab_partner_name?: string;         // AMIC_COLLAB 선택 시 파트너명
}
```

---

#### 2. `amic-platform/src/modules/docs/components/PPTStylePicker.tsx` *(신규)*

미니 슬라이드 CSS 미리보기 + 컬러 스와치 + 특징 배지가 포함된 스타일 선택 카드 컴포넌트.

**구조**:
- `MiniSlidePreview` — 16:9 CSS 슬라이드, primary 색상 헤더 바, accent 스트립, 스켈레톤 콘텐츠
- `ColorSwatch` — primary/accent 원형 인디케이터 + hex 코드 표시
- `PPTStylePicker` — 두 장의 카드 (AMIC 스타일 / AMIC x 파트너)

**Props**:
```tsx
interface PPTStylePickerProps {
  selected: PPTDesignStyle | null;
  partnerName: string;
  onSelect: (style: PPTDesignStyle) => void;
  onPartnerNameChange: (name: string) => void;
}
```

**핵심 동작**:
- AMIC_COLLAB 카드 선택 시 파트너명 입력 인라인으로 자동 노출
- 카드 내 입력 클릭 시 `e.stopPropagation()`으로 버블링 차단
- `useRef` + `useEffect`로 AMIC_COLLAB 선택 즉시 파트너명 입력창에 자동 포커스
- 파트너명 입력 시 미니 슬라이드 미리보기에 실시간 반영

---

#### 3. `amic-platform/src/modules/docs/pages/CreateDocumentPage.tsx`

**Step 구조 변경 (IM/TM)**:

```
이전: 0 (유형) → 1 (정보) → 2 (설정)       [3단계]
이후: 0 (유형) → 1 (디자인) → 2 (정보) → 3 (설정)  [4단계]
```

**FDD는 디자인 스텝 건너뜀**:

```
FDD: 0 (유형) → 2 (정보) → 3 (설정)  [3단계 표시]
```

**handleNext/handleBack FDD 건너뜀 로직**:
```ts
const handleNext = () => {
  if (step === 0 && isFDD) setStep(2);   // FDD: Step 1 스킵
  else setStep((s) => Math.min(s + 1, 3));
};
const handleBack = () => {
  if (step === 2 && isFDD) setStep(0);   // FDD 역방향도 스킵
  else setStep((s) => Math.max(s - 1, 0));
};
```

**Step 1 진행 조건**:
```ts
const canProceedStep1 =
  formData.ppt_design_style !== null &&
  (formData.ppt_design_style !== "AMIC_COLLAB" ||
   formData.ppt_collab_partner_name.trim().length > 0);
```

**동적 진행 인디케이터**:
```ts
const stepLabels = isFDD
  ? ["유형 선택", "프로젝트 정보", "설정 확인"]
  : ["유형 선택", "디자인 스타일", "프로젝트 정보", "설정 확인"];

// FDD는 내부 step 0→2→3을 표시 0→1→2로 매핑
const displayStepIndex = isFDD && step >= 2 ? step - 1 : step;
```

**Review & Confirm 섹션에 PPT 디자인 표시 추가**:
```tsx
<div className="flex justify-between">
  <span className="text-text-secondary">PPT 디자인</span>
  <span className="text-text-dark font-medium">
    {formData.ppt_design_style === "AMIC_COLLAB"
      ? `AMIC x ${formData.ppt_collab_partner_name}`
      : "AMIC 스타일"}
  </span>
</div>
```

---

### 백엔드 (4개 파일)

#### 4. `IM Module/auto-im-generator/src/api/schemas/documents.py`

```python
class DocumentCreate(BaseModel):
    # ...기존 필드...
    ppt_design_style: str = Field(
        default="AMIC",
        description="PPT 디자인 스타일: AMIC | AMIC_COLLAB",
    )
    collab_partner_name: str | None = Field(
        default=None,
        max_length=100,
        description="협업 파트너명 (AMIC_COLLAB 선택 시)",
    )

    @field_validator("ppt_design_style")
    @classmethod
    def validate_ppt_design_style(cls, v: str) -> str:
        valid = {"AMIC", "AMIC_COLLAB"}
        if v not in valid:
            raise ValueError(f"ppt_design_style은 {valid} 중 하나여야 합니다")
        return v

    @model_validator(mode="after")
    def validate_collab_requires_partner_name(self) -> DocumentCreate:
        if self.ppt_design_style == "AMIC_COLLAB" and not self.collab_partner_name:
            raise ValueError("AMIC_COLLAB 선택 시 collab_partner_name 필수")
        return self
```

---

#### 5. `IM Module/auto-im-generator/src/api/services/document_service.py`

`generation_config` JSONB에 신규 필드 추가 저장 (DB 마이그레이션 불필요):

```python
generation_config={
    "industry": create_data.industry,
    "webhook_url": create_data.webhook_url,
    "pdf_password": create_data.pdf_password,
    "ppt_design_style": create_data.ppt_design_style,      # 신규
    "collab_partner_name": create_data.collab_partner_name, # 신규
},
```

---

#### 6. `IM Module/auto-im-generator/src/design_renderer/design_tokens.py`

`IMDesignTokens.amic_collab()` classmethod 추가:

```python
@classmethod
def amic_collab(cls, partner_name: str) -> IMDesignTokens:
    """AMIC x Partner 협업 스타일 — AMIC 색상/로고 유지, 브랜딩 텍스트 변경."""
    return cls(
        colors=IMColorPalette(),       # AMIC 기본 색상 유지
        typography=IMTypography(),
        font_sizes=IMFontSizes(),
        layout=IMPageLayout(),
        pptx_layouts=IMPPTXLayouts(),
        company_name=f"AMIC Law & {partner_name}",
        logo_text=f"AMIC x {partner_name.upper()}",
        footer_note=(
            f"본 자료는 기밀 정보를 포함하고 있으며, AMIC Law & {partner_name}가 "
            "공동 작성하였습니다. 수신인 이외의 자에 대한 공개, 배포 또는 복사를 금합니다."
        ),
        logo_dark_path="amic_logo_dark.png",
        logo_white_path="amic_logo_white.png",
        cover_bg_path="amic_cover_bg.jpeg",
    )
```

**설계 원칙**: 컬러·폰트·레이아웃은 AMIC 기본값 그대로 유지, `company_name` / `logo_text` / `footer_note` 브랜딩 텍스트만 변경.

---

#### 7. `IM Module/auto-im-generator/src/api/tasks/generate_im.py`

`render_document_task` (line ~431) — DB에서 `generation_config` 읽어 tokens 선택 후 `IMPipeline` 호출:

```python
# PPT 디자인 스타일 → design tokens 선택
from src.design_renderer.pipeline import IMPipeline
from src.design_renderer.design_tokens import IMDesignTokens
from src.api.db.session import get_sync_session
from src.api.db.models.document import Document

tokens: IMDesignTokens | None = None
with get_sync_session() as session:
    doc = session.get(Document, document_id)
    if doc is not None:
        cfg = doc.generation_config or {}
        ppt_design_style = cfg.get("ppt_design_style", "AMIC")
        collab_partner_name = cfg.get("collab_partner_name")
        if ppt_design_style == "AMIC_COLLAB" and collab_partner_name:
            tokens = IMDesignTokens.amic_collab(collab_partner_name)

# Design Renderer 호출
pipeline_result = IMPipeline(tokens=tokens).generate(data)
```

**설계 노트**: `IMPipeline(tokens=None)`이면 내부에서 `DEFAULT_TOKENS`를 사용하므로, `AMIC` 스타일에서 별도 분기 불필요.

---

## 아키텍처 결정

| 항목 | 결정 | 이유 |
|------|------|------|
| DB 마이그레이션 | 불필요 | `generation_config`가 이미 JSONB 컬럼 |
| `_generation_config` 체인 전파 | ❌ 미사용 | `render_document_task`에서 DB 직접 조회 (기존 `get_sync_session` 패턴 재사용) |
| 파트너 컬러 자동 추출 | Phase 2 과제 | 이번 구현은 AMIC 색상 유지, 텍스트만 변경 |
| 파트너 로고 교체 | Phase 2 과제 | 로고 경로는 AMIC 기본값 유지 |

---

## 검증

| 항목 | 결과 |
|------|------|
| `tsc --noEmit` | ✅ 오류 없음 |
| E2E (수동 예정) | 미실시 — 백엔드 실행 환경 필요 |

---

## 향후 과제 (Phase 2)

1. **파트너 도메인 입력 → 로고 자동 추출**: `brand_extractor` 모듈 연동
2. **파트너 컬러 팔레트 자동 적용**: `IMDesignTokens.from_brand_assets()` 확장
3. **DM(Debt Memorandum) 문서 타입 추가**: 현재 IM/TM만 지원
4. **디자인 스타일 미리보기 실제 슬라이드 생성**: 현재는 CSS 스켈레톤만 표시
