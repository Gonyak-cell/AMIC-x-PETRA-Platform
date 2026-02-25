# MA 워크플로우 — 마케팅 자료 (TM / DM / IM) 구현 보고서

> 최종 업데이트: 2026-02-23 16:37:10

---

## 1. 배경 및 목적

실제 M&A 프로세스에서 Engagement(수임계약) 이후, Buyer 후보를 접촉하기 전에 반드시 작성해야 하는 3종의 마케팅 자료가 존재한다.

| 문서 | 역할 | 생성 시점 |
|------|------|---------|
| **TM** (Teaser Memorandum) | 익명으로 거래를 소개하는 요약 자료 — 대상 기업 정보를 드러내지 않고 투자 매력을 부각 | Buyer 접촉 전 (MARKETING 단계) |
| **DM** (Discussion Memo) | 특정 논의 사항 정리 — 단계 무관, 필요한 시점 어디서나 생성 가능 | 단계 무관 (논의 발생 시) |
| **IM** (Information Memorandum) | NDA 서명 후 제공하는 상세 투자 안내서 — 재무, 시장, 밸류에이션 포함 | NDA 서명 후 (BIDDING_DD 전후) |

모두 PPTX 형식으로 생성되며, 실제 샘플 파일을 기반으로 디자인이 구성된다.

---

## 2. 샘플 파일 기반

`C:\Users\서지원\OneDrive - 주식회사 페트라브릿지파트너스\AMIC의 파일\5. 기업 인수&합병\98_References\Memorandum` 폴더의 실제 샘플 파일을 분석하여 슬라이드 구조를 정립했다.

| 유형 | 샘플 파일 | 슬라이드 수 | 주요 구성 |
|------|----------|-----------|---------|
| TM | SPICY TM (260219).pptx | 25슬라이드 | Cover, Disclaimer, TOC, Exec Summary, Target Positioning, Investment Highlights, Market Analysis, Target Highlights, Pro-Forma Financials, Contact |
| DM | NX3 Games DM (260116).pptx | 7슬라이드 | Cover (Discussion Memo), 논의 주제별 콘텐츠 슬라이드 |
| IM | GENESIS IM (251207).pptx | 36슬라이드 | Cover, Disclaimer, TOC, Transaction Overview, Investment Highlights, Market Analysis, Company Overview, Valuation, Exit Strategy, Term Sheet |

---

## 3. 핵심 설계: memo_generator.py 차용

기존 `C:\...\AMIC의 파일\5. 기업 인수&합병\.claude\scripts\memo_generator.py`를 deal-mgmt 백엔드에 **그대로 차용 + 개선**하여 통합했다.

### 원본 코드 vs 개선 사항

| 항목 | 원본 | 개선 |
|------|------|------|
| 경로 | 하드코딩된 스크립트 디렉토리 기준 | `app/pptx/` 패키지 기준 동적 경로 |
| 반환값 | `print()` 출력 | `GenerationResult` 데이터클래스 반환 |
| 실행 방식 | CLI (`python memo_generator.py tm ALPHA out.pptx`) | `generate_memo()` 함수 직접 호출 |
| 비동기 | 동기 전용 | `asyncio.get_event_loop().run_in_executor()` 스레드풀 실행 |
| 오류 처리 | `sys.exit(1)` | `Exception` raise → DB FAILED 상태 기록 |
| DM 구조 | `Deal Memo` (4슬라이드) | `Discussion Memo` (4슬라이드, 논의 배경/포인트/Next Steps) |

---

## 4. 구현 파일 목록

### 4-1. 백엔드 (deal-mgmt)

```
deal-mgmt/
├── app/
│   ├── pptx/
│   │   ├── __init__.py              # GenerationResult, generate_memo export
│   │   └── memo_generator.py        # 통합 PPTX 생성 엔진 (TM/DM/IM/Proposal)
│   ├── models/
│   │   ├── enums.py                 # MarketingDocType, MarketingDocStatus 추가
│   │   ├── marketing_material.py    # DB 모델
│   │   └── __init__.py              # MarketingMaterial, MarketingDocType/Status export
│   ├── schemas/
│   │   └── marketing_material.py    # Create / DistributionUpdate / Out 스키마
│   ├── services/
│   │   └── marketing_material_service.py  # CRUD + 비동기 PPTX 생성
│   ├── routers/
│   │   └── marketing_materials.py   # REST API 라우터
│   └── main.py                      # marketing_materials.router 등록
├── templates/
│   └── memorandum/
│       ├── memorandum_master.pptx   # Forest 테마 마스터 템플릿 (복사)
│       └── logo.png                 # AMIC×PETRA 로고 (복사)
├── generated/
│   └── memorandum/                  # 생성된 PPTX 저장 디렉토리
│       └── {transaction_id}/
│           └── {type}_{mat_id}.pptx
├── migrations/
│   └── versions/
│       └── 009_marketing_materials.py  # marketing_materials 테이블 + 인덱스
└── tests/
    └── test_marketing_materials.py  # 10개 테스트 케이스
```

### 4-2. 프론트엔드 (amic-platform)

```
src/modules/ma/
├── types/
│   └── marketing_material.ts        # MarketingMaterial, Create, DistributionUpdate + 레이블 상수
├── hooks/
│   └── useMarketingMaterials.ts     # 목록/생성/재생성/배포/삭제 훅 + 폴링
└── pages/
    └── TransactionWorkspacePage.tsx # "마케팅 자료" 탭 추가 (team ↔ buyers 사이)
```

---

## 5. DB 스키마 (`marketing_materials` 테이블)

```sql
CREATE TABLE marketing_materials (
  id              UUID PRIMARY KEY,
  transaction_id  UUID NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  doc_type        marketingdoctype NOT NULL,   -- TM / DM / IM
  title           VARCHAR(300) NOT NULL,
  project_code    VARCHAR(100),                -- 예: ALPHA
  status          marketingdocstatus NOT NULL DEFAULT 'DRAFT',
  error_message   TEXT,
  parameters      JSONB,                       -- memo_generator content JSON
  file_path       VARCHAR(500),
  file_name       VARCHAR(300),
  file_size_bytes INTEGER,
  distributed_to  JSONB,                       -- ["A투자사", "b@example.com", ...]
  distributed_at  VARCHAR(50),
  created_by_email VARCHAR(255),
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX ix_marketing_materials_transaction_id ON marketing_materials(transaction_id);
CREATE INDEX ix_marketing_materials_doc_type_status ON marketing_materials(doc_type, status);
CREATE INDEX ix_marketing_materials_created_at ON marketing_materials(created_at);
```

---

## 6. API 엔드포인트

| Method | 경로 | 설명 |
|--------|------|------|
| `GET` | `/api/v1/transactions/{txn_id}/marketing-materials` | 목록 조회 |
| `POST` | `/api/v1/transactions/{txn_id}/marketing-materials` | 생성 (GENERATING 상태 즉시 반환) |
| `GET` | `/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}` | 단건 조회 |
| `POST` | `/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/regenerate` | 재생성 |
| `PUT` | `/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/distribute` | 배포 대상 업데이트 |
| `GET` | `/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}/download` | PPTX 다운로드 |
| `DELETE` | `/api/v1/transactions/{txn_id}/marketing-materials/{mat_id}` | 삭제 (파일 포함) |

---

## 7. 생성 요청 예시

### 기본 (플레이스홀더 사용)
```json
POST /api/v1/transactions/{txn_id}/marketing-materials
{
  "doc_type": "TM",
  "title": "Project Alpha — Teaser Memo",
  "project_code": "ALPHA"
}
```

### 커스텀 콘텐츠
```json
POST /api/v1/transactions/{txn_id}/marketing-materials
{
  "doc_type": "IM",
  "title": "Project Alpha — Information Memorandum",
  "project_code": "ALPHA",
  "parameters": {
    "project_name": "PROJECT ALPHA",
    "memo_type": "Information Memorandum",
    "date": "March 2026",
    "disclaimer": "본 자료는 기밀입니다.",
    "slides": [
      {
        "layout": "MAIN",
        "title": "Investment Highlights",
        "body": [
          { "type": "bullet", "items": ["강점 1", "강점 2", "강점 3"] }
        ]
      }
    ]
  }
}
```

---

## 8. memo_generator.py 콘텐츠 body 요소 타입

| 타입 | 설명 | 필드 |
|------|------|------|
| `text` | 일반 텍스트 단락 | `content`, `font_size?`, `bold?` |
| `section_header` | 녹색 배경 섹션 제목 박스 | `content`, `width?` |
| `bullet` | 불릿 리스트 | `items[]`, `prefix?` |
| `table` | 표 (헤더 + 데이터 행) | `headers[]`, `rows[][]` |
| `rich_text` | 혼합 서식 텍스트 | `runs[{text, bold?, color?, underline?}]` |
| `info_block` | 라벨 + 필드 테이블 (회사 기본정보용) | `label`, `fields[["필드명","값"]]`, `financial?` |
| `ownership_diagram` | 지분구조 다이어그램 | `owners[]`, `subsidiaries[]` |
| `two_column` | 2단 레이아웃 | `left[]`, `right[]` (중첩 요소 지원) |

---

## 9. 프론트엔드 탭 구조 변경

```
Before: overview → engagement → team → buyers → ndas → ...
After:  overview → engagement → team → [마케팅 자료] → buyers → ndas → ...
```

### 탭 UI 동작
- **TM/DM/IM 버튼** 클릭 시 즉시 GENERATING 상태로 레코드 생성
- **GENERATING 상태** 감지 시 5초 폴링 자동 활성화
- **READY 상태** 도달 시 "다운로드" 버튼 활성화
- **배포 기록** — 배포된 회사 수 표시

---

## 10. 디자인 시스템 (Forest 테마)

```python
# 마스터 색상 팔레트
COLOR_GREEN_PRIMARY  = '0F3A32'  # 섹션 헤더 배경 (가장 진한 녹색)
COLOR_GREEN_ACCENT   = '1C8F57'  # 필드명·라벨 강조 텍스트
COLOR_GREEN_BRIGHT   = '26C260'  # 자회사 박스
COLOR_GRAY_MID       = '6A6A6A'  # 테이블 테두리
COLOR_DARK           = '3D3D3D'  # 일반 본문 텍스트

# 슬라이드 레이아웃
COVER   → Forest 레이아웃 (진한 녹색 배경)
FOREST  → Forest 레이아웃 (TOC, 섹션 구분, Closing)
MAIN    → 흰 배경 + 제목/노트 플레이스홀더 (일반 콘텐츠)
```

---

## 11. 관련 파일

- **원본 memo_generator**: `M&A .claude/scripts/memo_generator.py`
- **마스터 템플릿**: `deal-mgmt/templates/memorandum/memorandum_master.pptx`
- **마이그레이션**: `deal-mgmt/migrations/versions/009_marketing_materials.py`
- **플랜 파일**: `C:\Users\서지원\.claude\plans\jiggly-wondering-diffie.md`
