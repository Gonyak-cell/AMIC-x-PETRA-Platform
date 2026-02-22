# KIIS 펀드 검색 핵심 기능 점검 및 수정

> 날짜: 2026-02-17 18:24
> 카테고리: review (기능 점검 + 수정)
> 심각도: High (P0 1건 + P1 1건 + P2 1건)
> 상태: **✅ 전체 수정 완료**

---

## 1. 점검 배경

IB 실무에서 펀드 검색 시 가장 중요한 3가지 기능의 구현 상태 점검:
1. IB 매체 리서치를 통한 펀드 평판
2. 투자성향
3. 최근 딜 소싱내역

---

## 2. 점검 결과 요약

| 기능 | 코드 존재 | 실동작 | 핵심 이슈 | 수정 후 |
|------|:--------:|:------:|----------|:------:|
| **펀드 평판** | ✅ | ❌ | NLP→뉴스 파이프라인 단절 (P0) | ✅ |
| **투자성향** | ✅ | ⚠️ 부분 | KOFIA 필터 프론트-백 불일치 (P1) | ✅ |
| **딜 소싱내역** | ✅ | ✅ | 없음 | ✅ |

---

## 3. 이슈 #1 — NLP 파이프라인 단절 (P0)

### 증상
- `FundDetailPage` Overview 탭의 Reputation Score가 항상 0.5(stable)
- DB `news_articles.sentiment_score` 전부 NULL
- 평판 계산 시 `AVG(sentiment_score)` = 0 → 기본값 수렴

### 근본 원인
`news_service.py:157-166`에서 뉴스 저장 시 NLPService를 호출하지 않음.
`nlp_service.py` (353줄)에 감성 분석/키워드 추출이 완전 구현되어 있으나 **수집 파이프라인에서 호출 미연결**.

### 수정 (`kiis/app/services/news_service.py`)
1. `NLPService` import + `__init__`에서 인스턴스 생성
2. `_analyze_article()` 메서드 추가 — 감성 분석 + 키워드 추출 (asyncio.to_thread 래핑)
3. `collect_from_source()`에서 저장 전 NLP 분석 결과 포함
4. `backfill_nlp()` 메서드 추가 — 기존 NULL 뉴스 일괄 업데이트

---

## 4. 이슈 #2 — KOFIA 펀드 필터 프론트-백 불일치 (P1)

### 증상
- 프론트엔드 `FundFilterPanel.tsx`에 `legal_type`, `asset_class`, `fund_status` 필터 UI 존재
- 백엔드 `kofia.py` 라우터에 해당 파라미터 없음 → 필터 선택해도 무반응

### 근본 원인
- `kofia_service.py`에 `classify_legal_type()`, `classify_asset_class()` 메서드 미존재
- `FundListItem` 스키마에 해당 필드 없음
- KOFIA API 응답 파싱 시 분류 미적용

### 수정 (3개 파일)

**`kiis/app/schemas/fund.py`:**
- `FundListItem`에 `legal_type`, `asset_class`, `fund_status` 필드 추가

**`kiis/app/services/kofia_service.py`:**
- 분류 키워드 상수 추가 (`PROFESSIONAL_PRIVATE_KEYWORDS`, `PUBLIC_FUND_KEYWORDS`, `ASSET_CLASS_KEYWORDS`)
- `classify_legal_type()` — 펀드명 → 법률 유형 자동 분류
- `classify_asset_class()` — 펀드명+카테고리 → 자산 클래스 분류 (6종)
- `determine_fund_status()` — 활성/회수기간/청산 결정
- `_parse_fund_list()` — 새 필드 포함
- `search_funds()` — `fund_types`, `legal_types`, `asset_classes`, `fund_statuses` 리스트 필터 추가
- `_apply_filters()` — 새 필터 적용 로직

**`kiis/app/routers/kofia.py`:**
- `list_funds()`에 `legal_type`, `asset_class`, `fund_status` 쿼리 파라미터 추가 (쉼표 구분 복수 선택)
- `_csv()` 헬퍼로 쉼표 문자열 → 리스트 변환

---

## 5. 이슈 #3 — 평판 재계산 수동 전용 (P2)

### 증상
- 뉴스 수집 후 평판 점수가 자동 갱신되지 않음
- 수동으로 `POST /analysis/reputation/{corp_code}/calculate` 호출 필요

### 수정 (`kiis/app/routers/news.py`)
- `collect_news()`에 `BackgroundTasks` 의존성 추가
- 신규 기사가 있으면 `_refresh_reputations()` 백그라운드 태스크 실행
- 뉴스에 연결된 기업의 평판 일괄 재계산

---

## 6. 수정 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `kiis/app/services/news_service.py` | 수정 | NLP 분석 연결 + backfill 메서드 |
| `kiis/app/schemas/fund.py` | 수정 | FundListItem에 3개 필드 추가 |
| `kiis/app/services/kofia_service.py` | 수정 | 분류 메서드 3개 + 필터 3개 추가 |
| `kiis/app/routers/kofia.py` | 수정 | 라우터 필터 파라미터 3개 추가 |
| `kiis/app/routers/news.py` | 수정 | 평판 자동 재계산 BackgroundTask |

---

## 7. 긍정적 측면 (변경 불필요)

- ✅ **딜 소싱 시스템** — 프론트-백 완전 일치 (NLP 추출, 트렌드, 통계)
- ✅ **NLP 엔진** (`nlp_service.py` 353줄) — kiwipiepy + 금융 감성 사전 완전 구현
- ✅ **평판 알고리즘** (`reputation_service.py` 323줄) — 가중 평균 완전 구현
- ✅ **FundDetailPage** — 4개 탭 모두 구현 (Overview/Deals/Tendency/Managers)
- ✅ TypeScript 타입 안전성 — 제네릭 100%, any 0건

---

## 8. 검증 방법

1. **NLP 파이프라인**: `POST /news/collect` → DB에서 `sentiment_score IS NOT NULL` 확인
2. **기존 뉴스 backfill**: `NewsService().backfill_nlp(db)` 호출
3. **KOFIA 필터**: `GET /kofia/funds?legal_type=professional_private&asset_class=vc`
4. **평판 자동 갱신**: 뉴스 수집 후 `GET /analysis/reputation/{corp_code}` 점수 변화 확인
5. **E2E**: FundDetailPage Overview 탭 Reputation Score 확인
