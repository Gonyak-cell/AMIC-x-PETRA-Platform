# KIIS 정성적 평판·투자성향 분석 구현 완료 보고서

> 작성일: 2026-02-17 19:04
> 계획 문서: `docs/kiis/20260217_1848_KIIS_Qualitative_Reputation_Tendency_Plan.md`

## 개요

FundDetailPage의 Reputation(평판) 및 Tendency(투자성향) 섹션을 **점수/테이블 기반**에서 **정성적 텍스트 + 원문 링크** 형식으로 전환했습니다. IB 실무자가 운용사의 시장 평판과 투자 패턴을 직관적으로 파악할 수 있도록 개선했습니다.

---

## 구현 내역

### A. 백엔드 (KIIS)

#### A1. 감성 레이블/매칭 컬럼 추가 — `kiis/app/models/news.py`
- `sentiment_label` (String(20)): 감성 레이블 (positive/negative/neutral)
- `sentiment_matches` (Text): 감성 매칭 결과 JSON (`{positive_matches, negative_matches}`)

#### A2. NLP 파이프라인 확장 — `kiis/app/services/news_service.py`
- `_analyze_article()` 반환 타입 확장: `(score, label, matches_json, keywords_json)`
- `collect_from_source()` 및 `backfill_nlp()`에서 새 필드 저장

#### A3. 테마 매핑 시스템 — `kiis/app/services/reputation_themes.py` (신규)
- POSITIVE_THEME_MAP: exit_ipo, fundraising, mna, performance, investment_expansion (5개 긍정 테마)
- NEGATIVE_THEME_MAP: financial_risk, management_risk, legal_risk, market_risk (4개 부정 테마)
- THEME_DISPLAY_NAMES, THEME_SENTIMENT, RISK_ABSENCE_THEMES 상수
- `get_theme_for_term()` 헬퍼 함수

#### A4. 정성적 평판 서비스 — `kiis/app/services/reputation_service.py`
- `get_qualitative_summary(db, corp_code, months=6)` 추가
- `_build_themes(articles)` — 기사 목록을 테마별로 그룹핑
- `_generate_theme_description(theme_name, articles, sentiment)` — 한국어 테마 설명 자동 생성

#### A5. 정성적 평판 API 엔드포인트 — `kiis/app/routers/analysis.py`
- `GET /analysis/reputation/{corp_code}/qualitative`
- 응답: `QualitativeReputationResponse` (themes, risk_absences, 통계)

#### B1. 투자성향 요약 서비스 — `kiis/app/services/deal_service.py`
- `get_tendency_summary(db, corp_code, years=3)` 추가
- `_get_top_deals()` — 금액 기준 상위 딜 조회
- `_generate_sector_description()` / `_generate_stage_description()` — 정성적 설명 생성

#### B2. 투자성향 API 엔드포인트 — `kiis/app/routers/deals.py`
- `GET /deals/tendency-summary?corp_code={corpCode}&years=3`
- 응답: `TendencySummaryResponse` (sectors, stages, summary_text)

### B. 스키마 (Pydantic v2)

| 파일 | 추가된 모델 |
|------|------------|
| `kiis/app/schemas/analysis.py` | `ReputationArticle`, `ReputationTheme`, `QualitativeReputationResponse` |
| `kiis/app/schemas/deal.py` | `TendencyDealItem`, `TendencySectorDetail`, `TendencyStageDetail`, `TendencySummaryResponse` |

### C. DB 마이그레이션

| 파일 | 설명 |
|------|------|
| `kiis/migrations/versions/a3b7c9d1e4f2_add_sentiment_label_matches_to_news.py` | news_articles 테이블에 sentiment_label, sentiment_matches 컬럼 추가 |

### D. 프론트엔드

#### D1. 타입 정의
- `amic-platform/src/modules/kiis/types/analysis.ts` — `ReputationArticle`, `ReputationTheme`, `QualitativeReputationResponse`
- `amic-platform/src/modules/kiis/types/deal.ts` — `TendencyDealItem`, `TendencySectorDetail`, `TendencyStageDetail`, `TendencySummaryResponse`

#### D2. API 훅
- `useQualitativeReputation(corpCode, params, options)` — `kiis/hooks/useCompanies.ts`
- `useTendencySummary(corpCode, years, options)` — `kiis/hooks/useDeals.ts`

#### D3. 컴포넌트 (신규)
- `ThemeCard.tsx` — 접이식 테마 카드 (긍정/부정 아이콘, 기사 수, 설명, 기사 목록)
- `ReputationSummary.tsx` — 정성적 평판 요약 (긍정/부정 통계, 테마 카드, 리스크 부재)
- `TendencySummary.tsx` — 투자성향 요약 (섹터별, 스테이지별 카드 + 딜 목록)

#### D4. FundDetailPage 리팩토링
- **삭제**: `useReputationScore`, `useDealsBySector`, `useDealsByStage`, `ReputationBadge` 등 점수/테이블 관련 코드
- **추가**: `useQualitativeReputation`, `useTendencySummary`, `ReputationSummary`, `TendencySummary`
- Overview 탭: ReputationBadge → `<ReputationSummary>`
- Tendency 탭: sector/stage DataTable → `<TendencySummary>`

---

## 수정 파일 목록 (18개)

### 백엔드 (9개)
1. `kiis/app/models/news.py` — 컬럼 추가
2. `kiis/app/services/news_service.py` — NLP 파이프라인 확장
3. `kiis/app/services/reputation_themes.py` — **신규** (테마 매핑)
4. `kiis/app/services/reputation_service.py` — 정성적 요약 함수 추가
5. `kiis/app/schemas/analysis.py` — Pydantic 모델 추가
6. `kiis/app/routers/analysis.py` — API 엔드포인트 추가
7. `kiis/app/services/deal_service.py` — 투자성향 요약 함수 추가
8. `kiis/app/schemas/deal.py` — Pydantic 모델 추가
9. `kiis/app/routers/deals.py` — API 엔드포인트 추가

### DB 마이그레이션 (1개)
10. `kiis/migrations/versions/a3b7c9d1e4f2_...py` — sentiment 컬럼 마이그레이션

### 프론트엔드 (8개)
11. `amic-platform/src/modules/kiis/types/analysis.ts` — 타입 추가
12. `amic-platform/src/modules/kiis/types/deal.ts` — 타입 추가
13. `amic-platform/src/modules/kiis/hooks/useCompanies.ts` — 훅 추가
14. `amic-platform/src/modules/kiis/hooks/useDeals.ts` — 훅 추가
15. `amic-platform/src/modules/kiis/components/ThemeCard.tsx` — **신규**
16. `amic-platform/src/modules/kiis/components/ReputationSummary.tsx` — **신규**
17. `amic-platform/src/modules/kiis/components/TendencySummary.tsx` — **신규**
18. `amic-platform/src/modules/kiis/pages/FundDetailPage.tsx` — 리팩토링

---

## 데이터 흐름

```
[뉴스 수집] → news_service._analyze_article()
    ↓ sentiment_label + sentiment_matches (JSON)
[DB] news_articles 테이블
    ↓
[정성 분석] reputation_service.get_qualitative_summary()
    ↓ reputation_themes.py 테마 매핑
[API] GET /analysis/reputation/{corp_code}/qualitative
    ↓
[프론트엔드] useQualitativeReputation() → <ReputationSummary>
    └→ <ThemeCard> (접이식 테마별 기사 목록)
```

```
[딜 데이터] deal_service.get_tendency_summary()
    ↓ 섹터/스테이지별 집계 + 정성적 설명 생성
[API] GET /deals/tendency-summary?corp_code={corpCode}
    ↓
[프론트엔드] useTendencySummary() → <TendencySummary>
    └→ <SectionCard> (섹터/스테이지별 딜 목록)
```

---

## 배포 전 필수 작업

1. **DB 마이그레이션 실행**: `alembic upgrade head` (kiis 디렉토리)
2. **NLP 백필**: 기존 뉴스 기사에 sentiment_label/matches 채우기
   - `backfill_nlp()` 실행 또는 관리자 엔드포인트 호출
3. **환경변수 확인**: NLP 서비스(kiwipiepy) 의존성 설치
