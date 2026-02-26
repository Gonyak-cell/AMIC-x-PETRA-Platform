# TM/DM VDR 기반 2-Pass Ralph Loop 적용 계획

> 작성: 2026-02-26 22:20 | 모듈: IM (TM/DM)

## Context

**문제**: TM(Teaser Memo)과 DM(Discussion Memo)은 현재 DART/Excel 입력만 지원하며, 1-pass 생성으로 출력물 품질이 Full IM 대비 부족하다. VDR 기반 입력과 2-pass Ralph Loop(Draft → 사용자 검토 → Final)를 적용하여 투자은행 수준의 PPTX 출력물 품질을 확보한다.

**현재 상태**:
- Full IM: VDR 체크리스트 80필드 + 2-pass Ralph Loop ✅ 이미 구현
- TM/DM: DART/Excel만 지원, Ralph Loop 없음 ❌ → 이번에 추가

**핵심 인사이트**: 기존 IM 인프라(VDR 파서, 체크리스트 모델, Ralph Loop 오케스트레이터)를 **재사용**하고, 스타일별 필드 필터링 + DM PRD만 추가하면 된다.

---

## Phase 1: 백엔드 스키마 + 필드 레지스트리 (핵심)

### 1-1. DM 스타일 검증 추가
**파일**: `im/src/api/schemas/checklist.py:130`

```python
# Before
_VALID_IM_STYLES = {"TITAN", "COVENANT", "FULL", "TEASER", "CUSTOM"}

# After
_VALID_IM_STYLES = {"TITAN", "COVENANT", "FULL", "TEASER", "DM", "CUSTOM"}
```

### 1-2. 스타일별 필드 필터링 함수 추가
**파일**: `im/src/api/services/checklist_field_registry.py`

기존 `get_all_fields()` (80필드)와 별도로 `get_fields_for_style(im_style)` 함수 추가:

| 스타일 | FINANCIAL | COMPANY | MARKET | DEAL | MANAGEMENT | SHAREHOLDERS | 합계 |
|--------|-----------|---------|--------|------|------------|--------------|------|
| FULL/CUSTOM | 30 (전체) | 12 | 8 | 10 | 10 | 10 | **80** |
| TM/TEASER | 12 (핵심 4지표×3yr) | 8 | 8 | 4 | 4 | 4 | **40** |
| DM | 18 (핵심 6지표×3yr) | 6 | 8 | 10 (전체) | 0 | 4 | **46** |

**TM 핵심 재무 지표**: revenue, operating_income, ebitda, net_income (×3년 = 12)
**DM 핵심 재무 지표**: revenue, cogs, gross_profit, operating_income, ebitda, net_income (×3년 = 18)

구현: `_TM_FINANCIAL_KEYS`, `_DM_FINANCIAL_KEYS` 등 스타일별 field_key 집합 정의 → 필터링

### 1-3. VDR 엔드포인트에서 스타일별 필드 적용
**파일**: `im/src/api/routes/checklist.py:127`

```python
# Before
fields = get_all_fields()

# After
from src.api.services.checklist_field_registry import get_fields_for_style
fields = get_fields_for_style(data.im_style)
```

---

## Phase 2: Ralph Loop DM PRD 추가

### 2-1. DM PRD 정의
**파일**: `im/src/ralph/prd.py`

기존 `IM_FULL_PRD` (30~80슬라이드, $5) 와 `IM_TEASER_PRD` (15~40슬라이드, $5) 외에 `IM_DM_PRD` 추가:

```python
IM_DM_PRD = {
    "memo_type": "DM",
    "min_slides": 8,
    "max_slides": 15,
    "required_slides": ["Cover", "Disclaimer"],
    "required_sections": [
        "dm_deal_structure",
        "dm_investment_thesis",
        "dm_valuation",
    ],
    "design_standards": {  # AMIC 공식 디자인 시스템 동일
        "font_heading": "SUITE",
        "font_body": "Pretendard",
        "color_primary": "#0F3A32",
        "color_secondary": "#1C8F57",
        "color_accent": "#26C260",
        "color_fresh": "#A3E96B",
        "color_light": "#E6FDD6",
    },
    "quality_dimensions": {
        "information_density": {"weight": 0.25},    # DM은 데이터 밀도 중요
        "visual_hierarchy": {"weight": 0.15},
        "chart_effectiveness": {"weight": 0.25},    # 차트/테이블 의존도 높음
        "slide_narrative_flow": {"weight": 0.15},
        "brand_consistency": {"weight": 0.05},      # 내부 문서, 브랜딩 비중 낮음
        "investor_readiness": {"weight": 0.15},
    },
    "pass_threshold": 3.5,   # 내부 문서이므로 기준 낮춤
    "max_iterations": 2,     # 짧은 문서이므로 반복 축소
    "budget_usd": 3.0,       # 비용 절감
}
```

레지스트리에 `"im_dm": IM_DM_PRD` 추가.

### 2-2. doc_type 매핑 수정
**파일**: `im/src/api/tasks/ralph_loop.py:92`

```python
# Before
doc_type = "im_teaser" if im_style in ("TEASER", "TM") else "im_full"

# After
if im_style in ("TEASER", "TM"):
    doc_type = "im_teaser"
elif im_style == "DM":
    doc_type = "im_dm"
else:
    doc_type = "im_full"
```

---

## Phase 3: 검증 불필요 (기존 코드가 이미 처리)

아래 파일들은 수정 불필요 — 코드 검증 완료:

| 파일 | 이유 |
|------|------|
| `checklist_to_imdata.py` | 카테고리 무관하게 모든 확정 아이템을 변환. TM/DM은 아이템 수만 적을 뿐 동일 로직 적용 |
| `vdr_extraction.py` | 체크리스트 아이템 수와 무관하게 동작 |
| `generate_im_from_checklist.py` | `doc.im_style`로 분기, Ralph Loop Pass 2 이미 트리거 |
| `generate_im.py` (DART/Excel 경로) | Ralph Loop Pass 1 이미 모든 스타일에 트리거 |
| `CreateFromVdrPage.tsx` | TEASER/DM 옵션 이미 포함 |
| `ChecklistReviewPage.tsx` | 스타일 무관 범용 UI |
| `document.ts` (타입) | `IMStyle`에 "DM" 이미 포함 |

---

## Phase 4: 테스트

### 새 테스트 파일 4개

**1. `im/tests/test_field_registry_style.py`** (~60줄)
- `get_fields_for_style("FULL")` → 80개
- `get_fields_for_style("TEASER")` → ~40개 (FINANCIAL 12 + COMPANY 8 + ...)
- `get_fields_for_style("DM")` → ~46개 (FINANCIAL 18 + DEAL 10 + ...)
- TM 필드에 revenue/ebitda 포함, total_assets 미포함 확인
- DM 필드에 MANAGEMENT 카테고리 0개 확인

**2. `im/tests/test_ralph_prd_dm.py`** (~30줄)
- `get_prd("im_dm")` → 유효한 PRD 반환
- PRD `memo_type == "DM"`, `min_slides == 8`, `max_slides == 15`
- quality_dimensions weight 합계 == 1.0

**3. `im/tests/test_ralph_loop_doc_type.py`** (~25줄)
- TEASER → "im_teaser"
- TM → "im_teaser"
- DM → "im_dm"
- FULL → "im_full"

**4. `im/tests/test_checklist_schema_dm.py`** (~20줄)
- `CreateFromVdrRequest(im_style="DM", ...)` → 검증 통과
- `CreateFromVdrRequest(im_style="INVALID", ...)` → ValidationError

---

## 수정 파일 요약

| 파일 | 변경 유형 | LOC |
|------|-----------|-----|
| `im/src/api/schemas/checklist.py` | 1줄 수정 (DM 추가) | ~1 |
| `im/src/api/services/checklist_field_registry.py` | 함수 추가 (`get_fields_for_style`) | ~60 |
| `im/src/api/routes/checklist.py` | import 변경 + 1줄 수정 | ~3 |
| `im/src/ralph/prd.py` | PRD 추가 + 레지스트리 등록 | ~40 |
| `im/src/api/tasks/ralph_loop.py` | doc_type 매핑 분기 확장 | ~5 |
| `im/tests/test_field_registry_style.py` | 신규 | ~60 |
| `im/tests/test_ralph_prd_dm.py` | 신규 | ~30 |
| `im/tests/test_ralph_loop_doc_type.py` | 신규 | ~25 |
| `im/tests/test_checklist_schema_dm.py` | 신규 | ~20 |
| **합계** | **5개 수정 + 4개 신규** | **~244** |

---

## 데이터 흐름 (TM 예시)

```
사용자: CreateFromVdrPage (Style: TEASER 선택)
  │
  ▼ POST /im/documents/from-vdr {im_style: "TEASER"}
  │
  ├─ 1. Document 생성 (im_style=TEASER)
  ├─ 2. get_fields_for_style("TEASER") → 40필드    ← 핵심 변경
  ├─ 3. IMChecklist + 40개 ChecklistItem 생성
  └─ 4. vdr_extraction_task.delay() → VDR 파싱
          │
          ▼ Celery: VDR 문서 파싱 (40개 필드만 추출)
          │
          ▼ 사용자: ChecklistReviewPage (40개 아이템 검토/수정)
          │
          ▼ POST /im/documents/{id}/checklist/confirm
          │
          ├─ 5. generate_im_from_checklist_task → IMDocumentData → PPTX
          └─ 6. run_im_ralph_loop_task(pass_number=2, doc_type="im_teaser")
                  │
                  ▼ Ralph Loop: PRD=IM_TEASER_PRD, 게이트 3종 평가
                  │  (PPTX 프로그래밍 검증 → Vision 게이트 → LLM 디자인 판정)
                  │
                  ▼ 최종 PPTX 출력 (품질 보증 완료)
```

---

## 검증 방법

1. **단위 테스트**: `cd im && python -m pytest tests/test_field_registry_style.py tests/test_ralph_prd_dm.py tests/test_ralph_loop_doc_type.py tests/test_checklist_schema_dm.py -v`
2. **기존 테스트 회귀**: `cd im && python -m pytest tests/ -v --tb=short` (기존 1,289개 통과 확인)
3. **타입 체크**: `cd amic-platform && npx tsc --noEmit` (프론트엔드 변경 없으므로 통과 예상)
4. **빌드 검증**: `cd amic-platform && npx vite build`
