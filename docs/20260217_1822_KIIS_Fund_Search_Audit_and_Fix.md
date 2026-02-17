# KIIS 펀드 검색 핵심 기능 점검 및 수정 보고서

> 작성일: 2026-02-17 18:22
> 대상: KIIS 모듈 — 펀드 검색 3대 핵심 기능

---

## 1. 점검 배경

IB 실무에서 펀드 검색 시 가장 중요한 3가지 기능의 구현 상태를 점검:

1. **IB 매체 리서치를 통한 펀드 평판**
2. **투자성향**
3. **최근 딜 소싱내역**

---

## 2. 점검 결과 요약

| 기능 | 코드 존재 | 실동작 여부 | 치명적 갭 |
|------|:--------:|:----------:|----------|
| **펀드 평판** | ✅ | ❌ 미동작 | NLP→뉴스 파이프라인 단절 |
| **투자성향** | ✅ | ⚠️ 부분 | KOFIA 필터 프론트-백 불일치 |
| **딜 소싱내역** | ✅ | ✅ 완전 | 없음 |

---

## 3. 상세 진단

### 3.1 펀드 평판 — 코드 O / 동작 X

**구현된 것:**
- `nlp_service.py` (353줄): kiwipiepy 형태소 분석, 금융 감성 사전, 키워드 추출, NER
- `reputation_service.py` (323줄): 가중 평균 알고리즘 (`트렌드×0.3 + 뉴스×0.4 + 성과×0.3`)
- `news_service.py` (200줄): Platum, DealSite, VentureSquare RSS 수집
- `FundDetailPage.tsx`: ReputationBadge + Trend/News/Performance KPI 3개

**치명적 갭:**
- `news_service.py:157-166`에서 뉴스 저장 시 `sentiment_score`, `keywords` 미설정 → **항상 NULL**
- NLP 엔진은 완전하지만 **수집 파이프라인에서 호출되지 않음**
- 평판 점수가 항상 기본값(0.5 stable)으로 수렴 → 사실상 무의미

### 3.2 투자성향 — 딜 기반 ✅ / 펀드 분류 필터 ⚠️

**완전 구현:**
- `FundDetailPage.tsx` "Investment Tendency" 탭: 섹터/스테이지 선호도 테이블
- `deal_service.py`: 섹터/스테이지 집계 완전 구현

**프론트-백 갭:**
- 프론트엔드 `FundFilterPanel.tsx`: `legal_type`, `asset_class`, `fund_status` 필터 UI 존재
- 백엔드 `kofia.py` 라우터: `company_name`, `fund_type` 파라미터만 존재
- `kofia_service.py`: `classify_legal_type()`, `classify_asset_class()` 메서드 **미존재**

### 3.3 딜 소싱내역 — ✅ 완전 구현

- `deal_service.py` (700+ 줄): NLP 기반 자동 추출, 섹터/스테이지 집계, 트렌드, 통계
- `FundDetailPage.tsx`: Deal History 탭 (Fund/Company 이중 레벨), 차트, KPI
- 프론트엔드-백엔드-데이터 모델 완전 일치

---

## 4. 수정 내역

### 4.1 Step 1: 뉴스 NLP 파이프라인 연결 (P0)

**파일:** `kiis/app/services/news_service.py`

**변경 사항:**
1. `NLPService` import 및 `__init__`에서 인스턴스 생성
2. `_analyze_article()` 메서드 추가 — 감성 분석 + 키워드 추출
3. `collect_from_source()`에서 뉴스 저장 시 `sentiment_score`, `keywords` 자동 채우기
4. `backfill_nlp()` 메서드 추가 — 기존 NULL 뉴스 일괄 업데이트

**핵심 코드:**
```python
# _analyze_article: 제목+본문 → (sentiment_score, keywords_json)
sentiment = await asyncio.to_thread(self.nlp.analyze_sentiment, text)
keywords = await asyncio.to_thread(self.nlp.extract_keywords, text, 10)

# collect_from_source: 저장 시 NLP 결과 포함
news_article = NewsArticle(
    ...,
    sentiment_score=sentiment_score,  # 신규 추가
    keywords=keywords_json,            # 신규 추가
)
```

### 4.2 Step 2: KOFIA 펀드 필터 백엔드 연결 (P1)

**파일:** `kiis/app/schemas/fund.py`, `kiis/app/services/kofia_service.py`, `kiis/app/routers/kofia.py`

**변경 사항:**

1. **스키마** (`fund.py`):
   - `FundListItem`에 `legal_type`, `asset_class`, `fund_status` 필드 추가

2. **서비스** (`kofia_service.py`):
   - 분류 키워드 상수 추가: `PROFESSIONAL_PRIVATE_KEYWORDS`, `PUBLIC_FUND_KEYWORDS`, `ASSET_CLASS_KEYWORDS`
   - `classify_legal_type()` 메서드 추가 — 펀드명 → 법률 유형 자동 분류
   - `classify_asset_class()` 메서드 추가 — 펀드명+카테고리 → 자산 클래스 분류
   - `determine_fund_status()` 메서드 추가 — 활성/회수기간/청산 결정
   - `_parse_fund_list()` 수정 — 새 필드 포함
   - `search_funds()` 수정 — `legal_types`, `asset_classes`, `fund_statuses` 파라미터 추가
   - `_apply_filters()` 수정 — 새 필터 적용 로직 추가

3. **라우터** (`kofia.py`):
   - `list_funds()`에 `legal_types`, `asset_classes`, `fund_statuses` 쿼리 파라미터 추가
   - 쉼표 구분 문자열 → 리스트 변환 로직

### 4.3 Step 3: 평판 자동 업데이트 트리거 (P2)

**파일:** `kiis/app/routers/news.py`

**변경 사항:**
1. `BackgroundTasks`, `ReputationService` import 추가
2. `collect_news()` 엔드포인트에 `BackgroundTasks` 의존성 추가
3. 신규 기사가 있으면 `_refresh_reputations()` 백그라운드 태스크 실행
4. `_refresh_reputations()` 함수 — company_id가 있는 기업의 평판 일괄 재계산

---

## 5. 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `kiis/app/services/news_service.py` | 수정 | NLP 파이프라인 연결, backfill 메서드 |
| `kiis/app/schemas/fund.py` | 수정 | FundListItem에 3개 필드 추가 |
| `kiis/app/services/kofia_service.py` | 수정 | 분류 메서드 3개 + 필터 3개 추가 |
| `kiis/app/routers/kofia.py` | 수정 | 라우터 필터 파라미터 3개 추가 |
| `kiis/app/routers/news.py` | 수정 | 평판 자동 재계산 백그라운드 태스크 |

---

## 6. 검증 방법

1. **NLP 파이프라인**: `POST /news/collect` → DB에서 `sentiment_score IS NOT NULL` 확인
2. **기존 뉴스 backfill**: `NewsService().backfill_nlp(db)` 호출 → 업데이트된 건수 확인
3. **KOFIA 필터**: `GET /kofia/funds?legal_types=professional_private&asset_classes=vc` 호출
4. **평판 자동 갱신**: 뉴스 수집 후 `GET /analysis/reputation/{corp_code}`에서 점수 변화 확인
5. **E2E**: FundDetailPage Overview 탭에서 Reputation Score가 의미 있는 값 표시

---

## 7. 긍정적 측면 (변경 불필요)

- ✅ **딜 소싱 시스템** — 완전 구현, 프론트-백 일치
- ✅ **NLP 엔진** (`nlp_service.py`) — kiwipiepy + 금융 감성 사전 완전 구현
- ✅ **평판 알고리즘** (`reputation_service.py`) — 3점수 가중 평균 완전 구현
- ✅ **프론트엔드 UI** — 4개 탭 구조, 차트, KPI 모두 구현
- ✅ **TypeScript 타입 안전성** — 제네릭 100%, any 0건
