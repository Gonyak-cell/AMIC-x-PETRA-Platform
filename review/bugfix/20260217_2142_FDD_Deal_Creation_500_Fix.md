# FDD Deal 생성 500 에러 수정 + 폼 리디자인

> 작성: 2026-02-17 21:40:00

## 요약

FDD 모듈에서 New Deal 생성 시 **500 Internal Server Error** 발생하는 버그 수정 및 Deal 생성 폼을 한국 PE/M&A 실무에 맞게 전면 리디자인.

## 근본 원인

### 500 에러 원인: IndustryType enum 이름/값 불일치

```
sqlalchemy.exc.DataError: invalid input value for enum industrytype: "TECH_SAAS"
```

- **Python enum**: `IndustryType.TECH_SAAS` → name=`"TECH_SAAS"`, value=`"tech"`
- **PostgreSQL ENUM**: `industrytype` → 허용 값: `general`, `tech`, `healthcare`, ...
- **SQLAlchemy 기본 동작**: `Enum(IndustryType)`는 enum의 **name**(대문자)을 DB에 전송
- **결과**: PostgreSQL이 `"TECH_SAAS"`를 거부 (DB에는 `"tech"`만 허용)

참고: `DealType` 등 다른 enum은 name과 value가 동일(`LOCKED_BOX = "LOCKED_BOX"`)하여 문제없었음.

### UX 문제

- "Period End"를 딜 시작 시점에 알 수 없음 (직관적이지 않음)
- 거래구조, 매도인 유형, 투자 유형 등 한국 PE/M&A 핵심 필드 누락
- 의뢰인/대상회사 정보가 폼에 없음 (백엔드에는 이미 존재)

## 수정 내역

### 1. 500 에러 해결 — `values_callable` 추가

**파일**: `fdd/backend/app/models/deal.py:96-103`

```python
# Before
industry: Mapped[IndustryType] = mapped_column(
    Enum(IndustryType), nullable=False, default=IndustryType.GENERAL
)

# After
industry: Mapped[IndustryType] = mapped_column(
    Enum(
        IndustryType,
        values_callable=lambda cls: [e.value for e in cls],
    ),
    nullable=False,
    default=IndustryType.GENERAL,
)
```

`values_callable`이 SQLAlchemy에 `.value`(소문자)를 사용하도록 지시 → DB ENUM과 일치.

### 2. 새 Enum 타입 3종 추가

**파일**: `fdd/backend/app/models/deal.py:54-83`

| Enum | 설명 | 값 |
|------|------|-----|
| `DealStructure` | 거래구조 | SHARE_ACQUISITION, ASSET_ACQUISITION, MERGER, CORPORATE_SPLIT, MBO, OTHER |
| `InvestmentType` | 투자 유형 | EQUITY, DEBT, MEZZANINE, CONVERTIBLE, OTHER |
| `SellerType` | 매도인 유형 | INDIVIDUAL, CORPORATE, INSTITUTIONAL, PE_FUND, MANAGEMENT, OTHER |

### 3. Deal 모델 컬럼 추가 + 날짜 nullable 변경

**파일**: `fdd/backend/app/models/deal.py`

- `deal_structure` (String(50), nullable) — 신규
- `investment_type` (String(50), nullable) — 신규
- `seller_type` (String(50), nullable) — 신규
- `reference_date` — NOT NULL → nullable
- `period_start` — NOT NULL → nullable
- `period_end` — NOT NULL → nullable

### 4. Pydantic 스키마 수정

**파일**: `fdd/backend/app/schemas/deal.py`

- `DealCreate.target_company_name` — 필수 필드로 변경
- `DealCreate.reference_date/period_start/period_end` — Optional로 변경
- `DealCreate/DealUpdate/DealRead`에 `deal_structure`, `investment_type`, `seller_type` 추가

### 5. API _UPDATABLE_FIELDS 업데이트

**파일**: `fdd/backend/app/api/deals.py:106-113`

`deal_structure`, `investment_type`, `seller_type` 3개 필드 추가.

### 6. Alembic 마이그레이션 012

**파일**: `fdd/backend/alembic/versions/012_add_deal_classification_fields.py`

```sql
-- 새 컬럼
ALTER TABLE deal ADD COLUMN deal_structure VARCHAR(50);
ALTER TABLE deal ADD COLUMN investment_type VARCHAR(50);
ALTER TABLE deal ADD COLUMN seller_type VARCHAR(50);

-- 날짜 nullable 변경
ALTER TABLE deal ALTER COLUMN reference_date DROP NOT NULL;
ALTER TABLE deal ALTER COLUMN period_start DROP NOT NULL;
ALTER TABLE deal ALTER COLUMN period_end DROP NOT NULL;
```

### 7. 프론트엔드 타입 + 상수

**파일**: `amic-platform/src/modules/fdd/types/deal.ts`
- `DealStructure`, `InvestmentType`, `SellerType` 타입 추가
- `Deal.reference_date/period_start/period_end` → `string | null`
- `DealCreate.target_company_name` 필수 추가

**파일**: `amic-platform/src/modules/fdd/constants.ts`
- `DEAL_STRUCTURE_OPTIONS` — 한국어 라벨 (지분인수, 자산인수, 합병, 분할, MBO, 기타)
- `INVESTMENT_TYPE_OPTIONS` — 한국어 라벨 (지분투자, 채권투자, 메자닌, 전환사채, 기타)
- `SELLER_TYPE_OPTIONS` — 한국어 라벨 (개인, 법인, 기관투자자, PE펀드, 경영진, 기타)
- `DEAL_TYPE_OPTIONS` — 한국어 라벨로 변경 (가격조정, 잠금박스)

### 8. DealListPage 폼 전면 리디자인

**파일**: `amic-platform/src/modules/fdd/pages/DealListPage.tsx`

**이전 폼**: Deal Name → Deal Type → Currency → Industry → Reference Date → Period Start/End

**새 폼 (4개 섹션)**:
```
━━━ 기본 정보 ━━━
딜 이름 (필수) / 대상회사명 (필수)

━━━ 의뢰인 정보 ━━━
의뢰인명 / 의뢰인 이메일

━━━ 거래 분류 ━━━
거래구조 / 투자 유형 / 매도인 유형 / 가격조정 방식

━━━ 분석 설정 ━━━
업종 / 통화 / 기준일(선택) / 분석기간 시작·종료(선택)
```

추가 변경:
- 모든 라벨 한국어화
- KPI 카드, 테이블 헤더, EmptyState 텍스트 한국어화
- 빈 optional 필드는 payload에서 제거 (서버에 빈 문자열 전송 방지)

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `fdd/backend/app/models/deal.py` | values_callable + 새 enum 3종 + 컬럼 추가 + 날짜 nullable |
| `fdd/backend/app/schemas/deal.py` | DealCreate/Update/Read 새 필드 + 날짜 optional |
| `fdd/backend/app/api/deals.py` | _UPDATABLE_FIELDS 3개 추가 |
| `fdd/backend/alembic/versions/012_*.py` | 신규 마이그레이션 |
| `amic-platform/src/modules/fdd/types/deal.ts` | 새 타입 3종 + Deal/DealCreate 수정 |
| `amic-platform/src/modules/fdd/constants.ts` | 한국어 옵션 4종 추가/수정 |
| `amic-platform/src/modules/fdd/pages/DealListPage.tsx` | 폼 전면 리디자인 |

## 검증

- [x] Docker alembic 마이그레이션 012 적용 완료
- [x] DB 컬럼 확인: deal_structure, investment_type, seller_type 존재
- [x] DB 날짜 컬럼 nullable 확인
- [x] IndustryType enums: `['general', 'tech', ...]` (소문자 — DB 일치)
- [x] TypeScript 빌드: `npx tsc --noEmit` 에러 없음
- [x] 단독 FDD 리포 동기화 완료
- [x] FDD API 재시작 후 정상 기동 (500 → 401 정상 인증 에러)
