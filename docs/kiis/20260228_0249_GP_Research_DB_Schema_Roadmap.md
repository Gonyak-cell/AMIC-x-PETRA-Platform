# GP 리서치 DB화 — 스키마 설계 및 구현 로드맵

> **작성일**: 2026-02-28 02:49
> **입력**: `kiis/deep-research-report.md` (국내 사모펀드 운용사 데이터 자동수집 조사)
> **목적**: 리서치 리포트의 5개 데이터 소스를 KIIS 모듈에 DB화하기 위한 스키마 설계 + Phase별 로드맵
> **전제**: API 키(DART_API_KEY, DATA_GO_KR_API_KEY) 발급 완료

---

## 1. GAP 분석 — 리서치 리포트 vs 기존 KIIS 모듈

### 1.1 데이터 모델 GAP

| 리포트 제안 | 기존 KIIS 대응 | 충족도 | GAP 상세 |
|---|---|---|---|
| `fund_manager` (운용사 마스터) | `Company` + `CompanyAlias` | ⚠️ 부분 | GP 전용 필드 없음. `is_gp`, `gp_aum`, `finance_company_code`, `gp_authorization_date`, `gp_strategy_tags` 등 미존재. `PublicDataService.search_gp_registry()`는 API 응답만 반환하고 **DB에 영속하지 않음** |
| `fund_vehicle` (펀드/조합/SPC) | `Fund` + `FundGP` + `FundManager` | ✅ 상당 | 빈티지/설정액/법형/전략/Co-GP 존재. 약정총액(committed_capital) vs 설정액(total_amount) 미구분. 통화(currency) 필드 없음. SPC 명칭→운용사 역매핑 구조 없음 |
| `portfolio_company` (피투자사) | `PortfolioCompany` | ✅ 상당 | 생존분석(감사보고서/해산/유니콘) 완비. 산업분류(`industry_code`), 상장여부(`is_listed`) 필드 부재 |
| `deal_event` (거래 이벤트) | `Deal` | ✅ 상당 | 투자사/피투자사/금액/라운드/섹터/날짜 존재. 거래유형(`deal_type`: acquisition/exit/holding_change), 종결일(`close_date`), DART 접수번호(`rcept_no`) 연결 없음 |
| `sanction_event` (제재) | `ClassifiedSanction` | ⚠️ 부분 | DART API 기반 제재만 저장. 금융위/증선위 **의결정보 PDF/ZIP 수집 파이프라인 없음**. 원문해시/저장경로 없음 |
| `source_document` (원문 메타) | **없음** | ❌ 미구현 | 원문 PDF/ZIP/HTML 보관 및 메타 추적 완전 부재. 증거보존(감사추적) 계층 없음 |

### 1.2 데이터 소스 GAP

| 소스 | API 형태 | 기존 구현 | GAP |
|---|---|---|---|
| **Open DART** 공시검색 (`list.json`) | REST JSON | `dart_service.py` `search_disclosures()` ✅ | `pblntf_detail_ty` 필터(D001 지분공시) 미활용. 지분공시 전용 수집 배치 없음 |
| **Open DART** 대량보유 (`majorstock.json`) | REST JSON | **없음** ❌ | 딜 신호 자동 생성의 **핵심 소스**. `repror`(대표보고자) → 운용사 매칭으로 GP의 피투자사 지분변동 추적 가능 |
| **Open DART** 임원주요주주 (`elestock.json`) | REST JSON | **없음** ❌ | Key Man 지분 변동 추적 보조 소스 |
| **Open DART** 원문 ZIP (`document.xml`) | ZIP binary | **없음** ❌ | 원문 파싱 파이프라인 없음. 딜 조건/금액 추출에 필요 |
| **Open DART** 회사개황 (`company.json`) | REST JSON | `dart_service.py` `get_company_info()` ✅ | `hm_url`/`ir_url` 활용 가능 |
| **Open DART** 고유번호 (`corpCode.xml`) | ZIP XML | `dart_service.py` `get_corp_codes()` ✅ | 완비 |
| **금융위 의결정보** (`fsc.go.kr/no020101`) | 웹 + PDF/ZIP | **없음** ❌ | 금융위원회 제재안건 의결서 수집 파이프라인 없음 |
| **증선위 의결정보** (`fsc.go.kr/no020102`) | 웹 + PDF/ZIP | **없음** ❌ | 증권선물위원회 제재안건 수집 없음 |
| **공공데이터포털** 자산운용사 통계 | REST JSON | `public_data_service.py` ⚠️ 부분 | API 호출+응답 반환만 구현. **Company 테이블에 영속화 안 됨** |
| **한국벤처투자** 펀드현황 (`kvic.or.kr/api`) | REST JSON | **없음** ❌ | 벤처/모태펀드 약정총액 확보 채널. API 키 별도 발급 필요 |
| **운용사 IR/웹사이트** | HTML/PDF | **없음** ❌ | 포트폴리오/뉴스 크롤링 없음. 20개 운용사 타깃 매핑 필요 |

### 1.3 기능 수준 GAP

| 기능 | 현재 | 필요 |
|---|---|---|
| 딜 신호 자동 생성 (공시 기반) | 뉴스 NLP에서 딜 추출 (`deal_service.py`) | **공시(대량보유/주요사항보고서) 기반** 자동 딜 레코드 생성 |
| 원문 보존/감사추적 | 없음 | 원문 ZIP/PDF 저장, SHA256 해시 무결성, 파서 버전 추적 |
| GP 프로파일 DB화 | 공공데이터포털 API 응답만 반환 | Company 테이블에 **is_gp 마킹 + GP 전용 필드 upsert** |
| 명칭 정규화/SPC 매핑 | `entity_resolver.py` (rapidfuzz) | 운용사 ↔ SPC ↔ 펀드 간 명칭 연결 고도화 |
| 금융위 제재 PDF 파싱 | DART API 제재만 (`sanction_service.py`) | PDF/ZIP 다운로드 + 텍스트 추출(pdfplumber) + 구조화 |
| 배치 수집 스케줄러 | 7개 작업 (`scheduler.py`) | 대량보유 수집, GP 동기화, 제재 수집, KVIC 동기화, IR 크롤링 추가 |

---

## 2. DB 스키마 설계

### 2.1 설계 원칙

1. **기존 테이블 우선 확장** — 새 테이블 최소화. Company에 GP 컬럼 추가하여 별도 `fund_manager` 테이블 불필요
2. **CI 호환** — `JSON().with_variant(JSONB, "postgresql")` 패턴 엄수 (SQLite CI 통과)
3. **감사추적 중심** — 모든 외부 데이터에 `source_document_id` FK로 원문 추적
4. **nullable FK** — 새 FK는 `nullable=True`로 추가 (기존 데이터 보호)

### 2.2 기존 테이블 확장 (ALTER TABLE)

#### 2.2.1 `companies` — GP 프로파일 필드 추가

| 컬럼 | 타입 | 설명 | 소스 |
|---|---|---|---|
| `is_gp` | `Boolean, default=False, index=True` | GP(운용사) 여부 마킹 | 공공데이터포털/KOFIA |
| `finance_company_code` | `String(50), unique=True, nullable=True` | 금융회사코드 (공공데이터포털 `fncoNo`) | 공공데이터포털 |
| `gp_authorization_date` | `String(10), nullable=True` | 인가일자 (YYYYMMDD) | 공공데이터포털 `authorizDt` |
| `gp_aum` | `Numeric(20, 0), nullable=True` | 운용자산 AUM (백만원) | 공공데이터포털 `oprtAssetAmt` |
| `gp_fund_count` | `Integer, nullable=True` | 운용 펀드수 | 공공데이터포털 `fundCnt` |
| `gp_employee_count` | `Integer, nullable=True` | 임직원수 | 공공데이터포털 `empcnt` |
| `gp_capital` | `Numeric(20, 0), nullable=True` | 자본금 (백만원) | 공공데이터포털 `cptlAmt` |
| `gp_total_assets` | `Numeric(20, 0), nullable=True` | 총자산 (백만원) | 공공데이터포털 `totalAsset` |
| `gp_operating_revenue` | `Numeric(20, 0), nullable=True` | 영업수익 (백만원) | 공공데이터포털 `oprtRevnAmt` |
| `gp_strategy_tags` | `JSON().with_variant(JSONB, "postgresql"), nullable=True` | 전략 태그 (`["pef", "vc", "real_estate"]`) | 자동 분류 |
| `gp_profile_synced_at` | `DateTime(timezone=True), nullable=True` | 마지막 GP 프로파일 동기화 시각 | 자동 |
| `gp_data_date` | `String(10), nullable=True` | 공공데이터포털 기준연월 (YYYYMM) | `baseYm` |

**결정 근거**: 리포트의 `fund_manager` 테이블을 별도 생성하지 않고 Company 확장. 이유:
- Company가 이미 `corp_code`, `corp_name`, `jurir_no`, `hm_url` 등 기업 마스터 역할
- 1:1 관계이므로 별도 테이블은 JOIN 오버헤드만 증가
- `is_gp=True` 필터로 GP 전용 쿼리 가능

#### 2.2.2 `deals` — 거래 유형/종결일/원문 연결

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `deal_type` | `String(30), nullable=True, index=True` | 거래 유형 (`investment`/`acquisition`/`exit`/`holding_change`) |
| `close_date` | `Date, nullable=True` | 종결일 (발표일 `deal_date`와 구분) |
| `rcept_no` | `String(20), nullable=True, index=True` | DART 접수번호 (원문 공시 연결) |

#### 2.2.3 `portfolio_companies` — 산업/상장 보강

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `industry_code` | `String(20), nullable=True` | 산업코드 (DART `induty_code`) |
| `is_listed` | `Boolean, nullable=True` | 상장 여부 |

#### 2.2.4 `classified_sanctions` — 원문 메타 연결

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `source_document_id` | `Integer, FK→source_documents, nullable=True` | 원문 메타 ID |

### 2.3 새 테이블 (CREATE TABLE)

#### 2.3.1 `source_documents` — 원문 메타 (감사추적 핵심)

> 모든 외부 수집 데이터의 원문 추적을 위한 중앙 테이블

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | `Integer, PK` | |
| `source_url` | `String(1000), NOT NULL` | 출처 URL |
| `source_type` | `String(30), NOT NULL, index` | 소스 유형 (`dart`/`fsc`/`sfc`/`website`/`kvic`/`data_go_kr`/`news`) |
| `collected_at` | `DateTime(tz), NOT NULL` | 수집 시각 |
| `content_hash` | `String(64), unique, index` | SHA-256 해시 (중복 수집 방지 + 무결성 검증) |
| `storage_path` | `String(500), nullable` | 로컬/클라우드 저장 경로 |
| `parser_version` | `String(20), nullable` | 파서 버전 (데이터 재처리 시 버전 추적) |
| `raw_content_type` | `String(20), nullable` | 원문 유형 (`pdf`/`zip`/`html`/`xml`/`json`) |
| `file_size_bytes` | `Integer, nullable` | 파일 크기 |
| `created_at` / `updated_at` | `DateTime(tz)` | TimestampMixin |

**패턴 참조**: `kiis/app/models/audit.py` — `JSON().with_variant(JSONB, "postgresql")`, `Uuid` 패턴

#### 2.3.2 `dart_major_holdings` — DART 대량보유 데이터

> Open DART `majorstock.json` API 응답을 DB에 영속

| 컬럼 | 타입 | 설명 | API 필드 |
|---|---|---|---|
| `id` | `Integer, PK` | | |
| `corp_code` | `String(20), index` | 피보유 기업 DART 고유번호 | `corp_code` |
| `corp_name` | `String(300)` | 피보유 기업명 | `corp_name` |
| `rcept_no` | `String(20), unique, index` | 접수번호 (중복 방지 키) | `rcept_no` |
| `rcept_dt` | `String(10)` | 접수일자 (YYYYMMDD) | `rcept_dt` |
| `report_tp` | `String(20)` | 보고유형 (신규/변경/종료) | `report_tp` |
| `repror` | `String(300), index` | 대표보고자명 (운용사/SPC/개인) | `repror` |
| `stkqy` | `String(50)` | 보유주식수 | `stkqy` |
| `stkrt` | `String(20)` | 보유비율 (%) | `stkrt` |
| `report_resn` | `String(200)` | 보고사유 (주식취득/처분 등) | `report_resn` |
| `company_id` | `Integer, FK→companies, nullable, index` | 피보유 기업 ID | |
| `reporter_company_id` | `Integer, FK→companies, nullable` | 보고자(투자사) 기업 ID (entity resolution 결과) | |
| `source_document_id` | `Integer, FK→source_documents, nullable` | 원문 메타 ID | |

**활용**: `repror` 필드를 `entity_resolver`로 Company에 매칭 → `reporter_company_id` 설정 → 이 GP가 어떤 회사 지분을 얼마나 보유/변경했는지 자동 추적

#### 2.3.3 `dart_executive_holdings` — DART 임원·주요주주 소유

> Open DART `elestock.json` API 응답

| 컬럼 | 타입 | 설명 | API 필드 |
|---|---|---|---|
| `id` | `Integer, PK` | | |
| `corp_code` | `String(20), index` | DART 고유번호 | `corp_code` |
| `rcept_no` | `String(20), index` | 접수번호 | `rcept_no` |
| `repror` | `String(200)` | 보고자 | `repror` |
| `isu_exctv_nm` | `String(100)` | 임원명 | `isu_exctv_nm` |
| `isu_exctv_rgist_at` | `String(10)` | 등록일 | |
| `stkqy` | `String(50)` | 소유주식수 | `stkqy` |
| `stkrt` | `String(20)` | 소유비율 | `stkrt` |
| `company_id` | `Integer, FK→companies, nullable` | 기업 ID | |
| `source_document_id` | `Integer, FK→source_documents, nullable` | 원문 메타 ID | |

#### 2.3.4 `fsc_decisions` — 금융위/증선위 의결정보

> `fsc.go.kr/no020101` (금융위), `fsc.go.kr/no020102` (증선위) 게시판 크롤링 결과

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | `Integer, PK` | |
| `decision_date` | `String(10), index` | 의결일자 |
| `decision_no` | `String(50), unique` | 의결번호 (중복 방지) |
| `subject` | `String(500), index` | 안건명 |
| `decision_type` | `String(30), index` | 유형 (`sanction`/`policy`/`other`) |
| `agency` | `String(10), index` | 기관 (`fsc`=금융위, `sfc`=증선위) |
| `document_url` | `String(1000)` | 원문 PDF/ZIP URL |
| `parsed_text` | `Text, nullable` | PDF 추출 텍스트 (전문) |
| `parsed_sanctions` | `JSON().with_variant(JSONB, "postgresql"), nullable` | 파싱된 제재 정보 (구조화 JSON) |
| `company_id` | `Integer, FK→companies, nullable, index` | 관련 기업 ID (entity resolution) |
| `source_document_id` | `Integer, FK→source_documents, nullable` | 원문 메타 ID |

**`parsed_sanctions` JSON 구조 예시**:
```json
{
  "targets": [
    {"name": "OO운용사", "type": "법인", "matched_company_id": 123},
    {"name": "홍길동", "type": "개인", "position": "대표이사"}
  ],
  "sanction_type": "과징금",
  "amount": "5000만원",
  "basis": "자본시장법 제XX조",
  "effective_date": "20260301"
}
```

#### 2.3.5 `kvic_funds` — 한국벤처투자 펀드현황

> KVIC Open API (`kvic.or.kr/api/businessType`, `/api/fundType`) 응답

| 컬럼 | 타입 | 설명 | API 필드 |
|---|---|---|---|
| `id` | `Integer, PK` | | |
| `kvic_fund_code` | `String(50), unique, index` | KVIC 펀드코드 | `fundCode` |
| `fund_name` | `String(300), index` | 펀드명 | `fundName` |
| `fund_type_code` | `String(10)` | 펀드종류코드 | API param `bType` |
| `fund_type_name` | `String(100)` | 펀드종류명 | |
| `business_type` | `String(50)` | 업종구분 | |
| `commitment_amount` | `Numeric(20, 0), nullable` | 약정총액 (원) | |
| `vintage_year` | `Integer, nullable` | 빈티지 연도 | |
| `gp_name` | `String(200), nullable` | 운용사명 (API 응답) | |
| `kvic_synced_at` | `DateTime(tz)` | 동기화 시각 | |
| `company_id` | `Integer, FK→companies, nullable, index` | 운용사 기업 ID (entity resolution) | |
| `fund_id` | `Integer, FK→funds, nullable, index` | 매칭된 Fund ID | |

#### 2.3.6 `gp_ir_snapshots` — 운용사 IR 페이지 스냅샷

> 운용사 웹사이트 크롤링 결과 (Phase 5, 선택)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | `Integer, PK` | |
| `company_id` | `Integer, FK→companies, index` | 운용사 기업 ID |
| `snapshot_url` | `String(1000)` | 크롤링 URL |
| `snapshot_type` | `String(20), index` | 유형 (`portfolio`/`news`/`ir`) |
| `collected_at` | `DateTime(tz)` | 수집 시각 |
| `content_hash` | `String(64), index` | 내용 SHA-256 (변경 감지) |
| `portfolio_companies` | `JSON().with_variant(JSONB, "postgresql"), nullable` | 파싱된 포트폴리오 기업 목록 |
| `news_items` | `JSON().with_variant(JSONB, "postgresql"), nullable` | 파싱된 뉴스/프레스 목록 |
| `parsed_at` | `DateTime(tz), nullable` | 파싱 완료 시각 |
| `source_document_id` | `Integer, FK→source_documents, nullable` | 원문 스냅샷 메타 |

### 2.4 ER 다이어그램

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  COMPANIES   │────<│  DART_MAJOR_HOLDINGS │>────│ SOURCE_DOCUMENTS │
│              │     │                     │     │                  │
│ + is_gp      │     │ corp_code           │     │ source_url       │
│ + gp_aum     │     │ rcept_no (unique)   │     │ source_type      │
│ + gp_fund_   │     │ repror (보고자)     │     │ content_hash     │
│   count      │     │ stkrt (보유비율)    │     │ storage_path     │
│ + finance_   │     │ report_resn (사유)  │     │ parser_version   │
│   company_   │     └─────────────────────┘     └──────────────────┘
│   code       │                                         ▲
│              │     ┌─────────────────────┐             │
│              │────<│ DART_EXEC_HOLDINGS  │>────────────┘
│              │     └─────────────────────┘             │
│              │                                         │
│              │     ┌─────────────────────┐             │
│              │────<│   FSC_DECISIONS     │>────────────┘
│              │     │                     │
│              │     │ decision_no (unique) │
│              │     │ agency (fsc/sfc)    │
│              │     │ parsed_sanctions    │
│              │     └─────────────────────┘
│              │
│              │     ┌─────────────────────┐     ┌──────────┐
│              │────<│    KVIC_FUNDS       │>────│  FUNDS   │
│              │     │                     │     │          │
│              │     │ kvic_fund_code      │     │ fund_    │
│              │     │ commitment_amount   │     │   code   │
│              │     └─────────────────────┘     └──────────┘
│              │
│              │     ┌─────────────────────┐
│              │────<│  GP_IR_SNAPSHOTS    │>────(SOURCE_DOCUMENTS)
│              │     │                     │
│              │     │ snapshot_type       │
│              │     │ portfolio_companies │
│              │     └─────────────────────┘
│              │
│              │     ┌─────────────────────┐
│              │────<│      DEALS          │
│              │     │                     │
│              │     │ + deal_type (신규)  │
│              │     │ + close_date (신규) │
│              │     │ + rcept_no (신규)   │
│              │     └─────────────────────┘
└──────────────┘
```

---

## 3. 서비스 계층 설계

### 3.1 기존 서비스 확장

| 서비스 | 파일 | 변경 내용 | 재사용 패턴 |
|---|---|---|---|
| `DARTService` | `kiis/app/services/dart_service.py` | `get_major_holdings(corp_code)`, `get_executive_holdings(corp_code)` 메서드 추가 | `_request()` + `_check_response()` 패턴 그대로 |
| `PublicDataService` | `kiis/app/services/public_data_service.py` | `sync_gp_profiles(db: AsyncSession)` 메서드 추가 — API 결과를 Company에 upsert | `search_gp_registry()` + `_parse_items()` 재사용 |

### 3.2 신규 서비스

| 서비스 | 파일 | 핵심 메서드 | 의존성 |
|---|---|---|---|
| `SourceDocumentService` | `kiis/app/services/source_document_service.py` | `store_document(url, content, source_type) → SourceDocument` | hashlib(SHA-256), pathlib |
| `HoldingSignalService` | `kiis/app/services/holding_signal_service.py` | `sync_major_holdings(db, corp_code)`, `generate_deal_signals(db, corp_code)` | DARTService, EntityResolverService |
| `FSCDecisionService` | `kiis/app/services/fsc_decision_service.py` | `crawl_decisions(agency, since_date)`, `extract_text_from_pdf(bytes)`, `parse_sanctions(text)` | httpx, BeautifulSoup4, pdfplumber |
| `KVICService` | `kiis/app/services/kvic_service.py` | `get_fund_types()`, `sync_kvic_funds(db)` | httpx, EntityResolverService |
| `GPIRCrawlerService` | `kiis/app/services/gp_ir_crawler_service.py` | `crawl_gp_site(company_id, url)`, 어댑터 패턴 | httpx/Playwright, BeautifulSoup4 |

### 3.3 데이터 흐름 (수집→저장→서빙)

```
[수집층 — Ingestion]
  ┌─ Open DART API ─────────→ DARTService._request()
  ├─ DART 대량보유 ──────────→ HoldingSignalService.sync_major_holdings()
  ├─ 공공데이터포털 ─────────→ PublicDataService.sync_gp_profiles()
  ├─ 금융위/증선위 게시판 ───→ FSCDecisionService.crawl_decisions()
  ├─ 한국벤처투자 API ───────→ KVICService.sync_kvic_funds()
  └─ 운용사 IR/웹 ──────────→ GPIRCrawlerService.crawl_gp_site()
                │
                ▼
[원문 보관 — Raw Storage]
  SourceDocumentService.store_document()
  → SHA-256 해시 생성 (중복 수집 방지)
  → 파일 저장 (SOURCE_DOCUMENT_STORAGE_PATH)
  → source_documents 테이블에 메타 기록
                │
                ▼
[추출/정규화 — Processing]
  ├─ PDF 텍스트 추출: pdfplumber → 텍스트 → 구조화 JSON
  ├─ 명칭 정규화: entity_resolver.py (rapidfuzz + CompanyAlias)
  ├─ SPC/펀드 매칭: repror → Company (reporter_company_id)
  ├─ 딜 신호 생성: 대량보유 stkrt ↑↓ → Deal 레코드 자동 생성
  └─ 제재 분류: parsed_sanctions → ClassifiedSanction 연결
                │
                ▼
[저장 — Persistence]
  PostgreSQL: companies(GP 확장), funds, deals(확장),
              dart_major_holdings, dart_executive_holdings,
              fsc_decisions, kvic_funds, gp_ir_snapshots,
              source_documents, classified_sanctions(확장)
  Redis: 캐싱 (TTL 24h 기본)
                │
                ▼
[서빙 — API]
  FastAPI REST (/api/v1/*)
  ├─ GET /kofia/gp — GP 목록 (KOFIA + 공공데이터 통합, is_gp=True)
  ├─ GET /dart/companies/{corp_code}/major-holdings — 대량보유 이력
  ├─ GET /sanctions/fsc-decisions — 금융위/증선위 의결정보
  ├─ GET /kvic/funds — 벤처펀드 현황
  └─ POST /public-data/sync-gp-profiles — 수동 GP 동기화 트리거
```

---

## 4. Phase별 구현 로드맵

### Phase 1: GP 프로파일 DB 영속화 + 원문 메타 기반 (1주)

**목표**: 공공데이터포털 GPRegistryItem을 Company 테이블에 영속화. source_documents 원문 메타 테이블 도입.

| # | 작업 | 파일 | 비고 |
|---|---|---|---|
| 1 | Alembic: companies GP 컬럼 추가 | `migrations/versions/xxx_add_gp_profile.py` | 12개 컬럼, nullable |
| 2 | Alembic: source_documents 생성 | `migrations/versions/xxx_create_source_documents.py` | 새 테이블 |
| 3 | Company 모델 수정 | `app/models/company.py` | GP 컬럼 추가 |
| 4 | SourceDocument 모델 | `app/models/source_document.py` | 새 파일 |
| 5 | models/__init__.py | `app/models/__init__.py` | import 추가 |
| 6 | source_document_service.py | `app/services/source_document_service.py` | 새 서비스 |
| 7 | public_data_service.py 확장 | `app/services/public_data_service.py` | `sync_gp_profiles(db)` 추가 |
| 8 | config.py 수정 | `app/core/config.py` | `SOURCE_DOCUMENT_STORAGE_PATH`, `GP_PROFILE_SYNC_DAY_OF_WEEK` |
| 9 | 라우터 수정 | `app/routers/public_data.py` | `POST /sync-gp-profiles` |
| 10 | 스키마 수정 | `app/schemas/company.py` | GP 필드 응답 추가 |
| 11 | 스케줄러 등록 | `app/tasks/scheduler.py` | `gp_profile_sync` (주간) |
| 12 | 배치 태스크 | `app/tasks/gp_profile_sync.py` | 새 파일 |
| 13 | 테스트 | `tests/test_gp_profile_sync.py` | API 모킹 + upsert 검증 |

**의존성**: `DATA_GO_KR_API_KEY` (발급 완료)

---

### Phase 2: DART 대량보유/지분공시 딜 신호 (1주)

**목표**: `majorstock.json`, `elestock.json` 연동 → 지분 변동 자동 수집 → Deal 테이블에 딜 신호 자동 생성.

| # | 작업 | 파일 | 비고 |
|---|---|---|---|
| 1 | Alembic: dart_major_holdings, dart_executive_holdings 생성 | `migrations/versions/xxx_create_dart_holdings.py` | Phase 1 source_documents 의존 |
| 2 | Alembic: deals 컬럼 추가 | `migrations/versions/xxx_add_deal_type_columns.py` | deal_type, close_date, rcept_no |
| 3 | DartMajorHolding, DartExecutiveHolding 모델 | `app/models/holding.py` | 새 파일 |
| 4 | Deal 모델 수정 | `app/models/deal.py` | 3개 컬럼 추가 |
| 5 | models/__init__.py | `app/models/__init__.py` | import 추가 |
| 6 | dart_service.py 확장 | `app/services/dart_service.py` | `get_major_holdings()`, `get_executive_holdings()` |
| 7 | holding_signal_service.py | `app/services/holding_signal_service.py` | 새 서비스 — sync + deal signal 생성 |
| 8 | 스키마 추가 | `app/schemas/dart.py` | MajorHoldingItem, ExecutiveHoldingItem |
| 9 | 라우터 수정 | `app/routers/dart.py` | 대량보유/임원주주 엔드포인트 |
| 10 | 스케줄러 등록 | `app/tasks/scheduler.py` | `holding_sync` (일간) |
| 11 | 배치 태스크 | `app/tasks/holding_sync.py` | 새 파일 |
| 12 | 테스트 | `tests/test_holding_signal_service.py` | DART 모킹 + entity resolution 검증 |

**의존성**: `DART_API_KEY` (발급 완료), Phase 1 (`source_documents` 테이블)

**딜 신호 생성 로직**:
```
1. majorstock.json에서 report_resn="주식취득" → deal_type="holding_change"
2. repror(대표보고자)를 entity_resolver로 Company 매칭 → reporter_company_id
3. is_gp=True인 Company면 → GP의 새 투자 신호로 Deal 자동 생성
4. stkrt 변화량 추적 → 지분 증가/감소 이벤트 기록
```

---

### Phase 3: 금융위/증선위 제재 수집 (1주)

**목표**: 금융위(`fsc.go.kr/no020101`)/증선위(`no020102`) 의결정보 게시판에서 제재안건 PDF/ZIP 자동 수집 + 텍스트 추출.

| # | 작업 | 파일 | 비고 |
|---|---|---|---|
| 1 | Alembic: fsc_decisions 생성 | `migrations/versions/xxx_create_fsc_decisions.py` | Phase 1 의존 |
| 2 | Alembic: classified_sanctions 컬럼 추가 | `migrations/versions/xxx_add_sanction_source.py` | source_document_id FK |
| 3 | FSCDecision 모델 | `app/models/fsc_decision.py` | 새 파일 |
| 4 | ClassifiedSanction 수정 | `app/models/sanction.py` | source_document_id 추가 |
| 5 | fsc_decision_service.py | `app/services/fsc_decision_service.py` | 크롤링 + PDF 추출 + 구조화 |
| 6 | pyproject.toml | `kiis/pyproject.toml` | `pdfplumber>=0.11.0` 추가 |
| 7 | 라우터 수정 | `app/routers/sanctions.py` | FSC 의결정보 엔드포인트 |
| 8 | 스케줄러 등록 | `app/tasks/scheduler.py` | `fsc_decision_sync` (주간) |
| 9 | 테스트 | `tests/test_fsc_decision_service.py` | HTML/PDF 모킹 |

**의존성**: Phase 1 (`source_documents` 테이블)

**PDF 파싱 전략** (리서치 리포트 권고):
```
1단계: pdfplumber 텍스트 추출 (대부분 성공)
2단계: pdfplumber 표 추출 (제재 테이블)
3단계: OCR(Tesseract) — 스캔 PDF인 경우에만 (비용/오류 최소화)
```

---

### Phase 4: 한국벤처투자 펀드현황 (3~5일)

**목표**: KVIC Open API 연동 → 벤처/모태펀드 약정총액 수집 → Fund 테이블과 연계.

| # | 작업 | 파일 | 비고 |
|---|---|---|---|
| 1 | Alembic: kvic_funds 생성 | `migrations/versions/xxx_create_kvic_funds.py` | |
| 2 | KVICFund 모델 | `app/models/kvic_fund.py` | 새 파일 |
| 3 | config.py 수정 | `app/core/config.py` | `KVIC_API_KEY`, `KVIC_BASE_URL`, `KVIC_RATE_LIMIT_PER_MINUTE` |
| 4 | kvic_service.py | `app/services/kvic_service.py` | API 연동 + Fund 매칭 |
| 5 | 라우터 | `app/routers/kvic.py` | 새 라우터 |
| 6 | main.py 수정 | `app/main.py` | 라우터 등록, openapi_tags 추가 |
| 7 | 스케줄러 등록 | `app/tasks/scheduler.py` | `kvic_fund_sync` (월간) |
| 8 | 테스트 | `tests/test_kvic_service.py` | API 모킹 |

**의존성**: KVIC API 키 **별도 발급 필요** (`kvic.or.kr` 신청)

---

### Phase 5: 운용사 IR 크롤링 프로토타입 (1주, 선택)

**목표**: 상위 5~10개 운용사 웹사이트에서 포트폴리오/뉴스 자동 수집. 어댑터 패턴으로 사이트별 파서 외부화.

| # | 작업 | 파일 | 비고 |
|---|---|---|---|
| 1 | Alembic: gp_ir_snapshots 생성 | `migrations/versions/xxx_create_gp_ir_snapshots.py` | |
| 2 | GPIRSnapshot 모델 | `app/models/gp_ir_snapshot.py` | 새 파일 |
| 3 | gp_ir_crawler_service.py | `app/services/gp_ir_crawler_service.py` | BaseSiteCrawler ABC + 어댑터 |
| 4 | gp_site_adapters.json | `app/data/gp_site_adapters.json` | 운용사별 CSS 셀렉터 설정 |
| 5 | 스케줄러 등록 | `app/tasks/scheduler.py` | `gp_ir_crawl` (주간) |
| 6 | 테스트 | `tests/test_gp_ir_crawler.py` | HTML fixture 기반 |

**주의사항**:
- `robots.txt` 준수 필수 (3초 간격, 허용 경로만)
- 로고 그리드(이미지) 형태 포트폴리오는 `alt` 텍스트 + 링크 구조 분석 필요
- 동적 로딩 사이트는 Playwright 렌더링 필요 (리소스 부담)

---

## 5. 마이그레이션 전략

### 5.1 마이그레이션 순서 (의존성 기반)

```
Migration 1: add_gp_profile_to_companies      ← Phase 1
    ↓ (독립)
Migration 2: create_source_documents           ← Phase 1
    ↓ (source_documents FK 의존)
Migration 3: create_dart_holdings              ← Phase 2
    ↓ (독립)
Migration 4: add_deal_type_columns             ← Phase 2
    ↓ (source_documents FK 의존)
Migration 5: create_fsc_decisions              ← Phase 3
    ↓ (독립)
Migration 6: add_sanction_source_doc_fk        ← Phase 3
    ↓ (독립)
Migration 7: create_kvic_funds                 ← Phase 4
    ↓ (독립)
Migration 8: create_gp_ir_snapshots            ← Phase 5
```

### 5.2 CI 호환성 체크리스트

- [ ] JSON 컬럼: `JSON().with_variant(JSONB, "postgresql")` 패턴 적용
- [ ] UUID 컬럼: `from sqlalchemy import Uuid` 사용 (PostgreSQL 전용 `UUID(as_uuid=True)` 금지)
- [ ] 새 FK 컬럼: `nullable=True` (기존 데이터 보호)
- [ ] 모든 마이그레이션: `downgrade()` 구현 필수
- [ ] hatchling 빌드: `[tool.hatch.build.targets.wheel] packages = ["app"]` 유지
- [ ] dev 의존성: `[project.optional-dependencies]` 사용 (`[dependency-groups]` 금지)
- [ ] 함수 타입 힌트: 모든 새 함수에 매개변수 + 반환값 타입 필수
- [ ] ruff check/format: 제로 경고

---

## 6. 설정 추가 목록

`kiis/app/core/config.py`에 추가할 환경변수:

| 변수 | 기본값 | Phase | 설명 |
|---|---|---|---|
| `SOURCE_DOCUMENT_STORAGE_PATH` | `"/tmp/kiis_sources"` | 1 | 원문 파일 저장 경로 |
| `GP_PROFILE_SYNC_DAY_OF_WEEK` | `"tue"` | 1 | GP 프로파일 동기화 요일 |
| `FSC_CRAWL_BASE_URL` | `"https://www.fsc.go.kr"` | 3 | 금융위원회 베이스 URL |
| `FSC_CRAWL_RATE_LIMIT_PER_MINUTE` | `10` | 3 | 금융위 크롤링 속도 제한 |
| `KVIC_API_KEY` | `""` | 4 | 한국벤처투자 API 키 |
| `KVIC_BASE_URL` | `"https://www.kvic.or.kr/api"` | 4 | KVIC API 베이스 URL |
| `KVIC_RATE_LIMIT_PER_MINUTE` | `30` | 4 | KVIC 속도 제한 |
| `GP_IR_CRAWL_DAY_OF_WEEK` | `"wed"` | 5 | IR 크롤링 요일 |
| `GP_IR_CRAWL_DELAY_SECONDS` | `3.0` | 5 | 크롤링 간격 (robots.txt 준수) |

---

## 7. 스케줄러 등록 계획

`kiis/app/tasks/scheduler.py`에 추가할 배치 작업:

| 작업 ID | 스케줄 | 함수 | Phase |
|---|---|---|---|
| `gp_profile_sync` | 주간 (화 07:00) | `run_gp_profile_sync()` | 1 |
| `holding_sync` | 일간 (10:00) | `run_holding_sync()` | 2 |
| `fsc_decision_sync` | 주간 (수 08:00) | `run_fsc_decision_sync()` | 3 |
| `kvic_fund_sync` | 월간 (1일 06:00) | `run_kvic_fund_sync()` | 4 |
| `gp_ir_crawl` | 주간 (목 09:00) | `run_gp_ir_crawl()` | 5 |

---

## 8. 법적/기술적 제약 (리서치 리포트 요약)

| 제약 | 대응 |
|---|---|
| **robots.txt/이용약관** | 크롤링 대상 사이트별 사전 체크. "허용되지 않는 대량수집"은 API/계약으로 전환 |
| **저작권 (뉴스/리서치)** | "링크+메타데이터(제목/일자/요약 1~2문장)" 수준으로 제한. 원문 저장 최소화 |
| **개인정보** | 제재문서 내 개인(임직원) 실명 마스킹 정책. 외부 공유 시 법무 검토 |
| **금융규제** | 제재 데이터: 원문 링크/해시 보존, 정정/변경 추적, '진행중/확정' 상태 분리 |
| **Open DART 요청 제한** | 에러코드 020(요청초과), 012(IP 차단). Rate limiter + 백오프 필수 |
| **corp_code 없으면 3개월 제한** | list.json 검색 시 corp_code 필수화하거나 기간 분할 |

---

## 9. 비용 추정 (리서치 리포트 기반)

| 단계 | 기간 | 클라우드 비용(월) | 상업데이터 | 범위 |
|---|---|---|---|---|
| **PoC** (Phase 1~2) | 2주 | 수만원~수십만원 | 0 | DART 딜신호 + GP 프로파일 DB화 |
| **상용화 기본** (Phase 3~4) | +2주 | 수십만원 | 선택 | 제재 수집 + KVIC 연동 |
| **상용화 고급** (Phase 5+) | +1주 | 수십만원 | Preqin/PitchBook 검토 | IR 크롤링 + 상업 데이터 도입 |

---

## 10. 참조 문서

| 문서 | 경로 |
|---|---|
| 리서치 리포트 (입력) | `kiis/deep-research-report.md` |
| 기존 GP 데이터소스 조사 | `docs/kiis/20260222_1635_Private_Fund_GP_Datasource_Research.md` |
| KIIS 모듈 구현 계획 | `docs/kiis/20260210_2250_Phase2_KIIS_Implementation_Plan.md` |
| GP 중심 검색 구현 | `docs/kiis/20260217_2154_GP_Centric_Search_Implementation.md` |
| CI 회귀 방지 규칙 | `.claude/rules/ci-regression-prevention.md` |
