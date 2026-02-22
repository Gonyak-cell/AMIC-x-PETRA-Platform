# KIIS FundDetailPage 정성적 전환 플랜

## Context

FundDetailPage의 **평판(Reputation)**과 **투자성향(Tendency)** 두 섹션을 점수/테이블 기반에서 **IB 실무자를 위한 정성적 텍스트 + 원문 링크** 방식으로 전환한다.

**현재 문제**:
- 평판: 숫자 점수(0.71) + 상태 태그(rising)만 표시 → IB 실무자가 "왜?"를 알 수 없음
- 투자성향: 섹터/스테이지 테이블만 표시 → 투자 전략의 맥락을 파악하기 어려움

**목표 형태**:
- 평판: "최근 6개월간 포트폴리오 엑시트 성과 호평 — Platum, DealSite" + 원문 링크
- 투자성향: "AI/딥테크, 바이오/헬스케어 섹터에 집중 투자 (전체의 65%) — Series A~B 중심 전략" + 딜 상세

---

## 변경 범위

### A. 평판 → 정성적 요약 + 원문 기사 링크

#### A1. DB 마이그레이션 — NewsArticle 컬럼 추가
**파일**: `kiis/app/models/news.py`
- `sentiment_label: Mapped[str | None]` (positive/negative/neutral) 추가
- `sentiment_matches: Mapped[str | None]` (JSON: {positive_matches, negative_matches}) 추가

#### A2. 뉴스 수집 시 matches 저장
**파일**: `kiis/app/services/news_service.py`
- `_analyze_article()`에서 `nlp.analyze_sentiment()` 반환값의 `label`, `positive_matches`, `negative_matches`를 함께 저장
- 기존에 `score`만 저장 → `score` + `label` + `matches` 저장으로 확장

#### A3. 테마 매핑 상수
**파일**: `kiis/app/services/reputation_themes.py` (신규)
- IB 실무 관점 테마 그룹: 엑시트/상장, 펀드레이징/LP, M&A, 실적 성과, 경영 리스크, 재무 리스크, 법적 리스크 등
- 감성 사전 용어 → 테마 매핑 딕셔너리

#### A4. 정성적 요약 생성 서비스
**파일**: `kiis/app/services/reputation_service.py`
- `get_qualitative_summary()` 메서드 추가
  - 최근 N개월 뉴스 조회 (company_id 기준)
  - `sentiment_matches`에서 matched_terms 추출
  - 테마별 그룹핑 → 정성적 description 문구 자동 생성
  - 원문 기사 정보(title, url, source, published_at) 포함
- description 생성 규칙:
  - 1건: `"{기사 제목 요약} — {source}"`
  - 2~3건: `"최근 {기간} {테마} 관련 보도 {N}건 — {sources}"`
  - 4건+: `"최근 {기간} {테마} 관련 긍정/부정 보도 다수"`
  - 부정 0건: `"부정적 보도 없음"` 표시

#### A5. API 스키마 + 엔드포인트
**파일**: `kiis/app/schemas/analysis.py`, `kiis/app/routers/analysis.py`
- 새 스키마: `ReputationArticle`, `ReputationTheme`, `QualitativeReputationResponse`
- 새 엔드포인트: `GET /analysis/reputation/{corp_code}/qualitative`
- 기존 점수 API는 하위 호환용 유지

#### A6. 프론트엔드
**파일 수정**: `FundDetailPage.tsx` L267-297 교체, `useCompanies.ts` 훅 추가, `types/analysis.ts` 타입 추가
**파일 신규**: `ReputationSummary.tsx`, `ThemeCard.tsx`
- `ReputationSummary`: 한줄 요약 + 테마별 카드 목록
- `ThemeCard`: 테마 헤더 + 정성적 설명 + 접기/펼치기 기사 목록 (원문 링크)

---

### B. 투자성향 → 정성적 텍스트 + 딜 상세

#### B1. 투자성향 요약 생성 서비스
**파일**: `kiis/app/services/deal_service.py`
- `get_tendency_summary()` 메서드 추가
  - 기존 `aggregate_by_sector()`, `aggregate_by_stage()` 활용
  - 집계 결과에서 정성적 텍스트 자동 생성:
    - 상위 3개 섹터 요약: `"AI/딥테크(35%), 바이오(20%), 핀테크(15%) 섹터에 집중"`
    - 주력 스테이지 요약: `"Series A~B 중심 전략 (전체 딜의 65%)"`
    - 총 투자 규모 요약: `"최근 3년간 총 28건, 약 2,400억원 투자"`
  - 각 섹터/스테이지별 대표 딜 목록 포함 (target_company, amount, deal_date, source_url)

#### B2. API 스키마 + 엔드포인트
**파일**: `kiis/app/schemas/deal.py`, `kiis/app/routers/deals.py`
- 새 스키마: `TendencyDealItem`, `TendencySectorDetail`, `TendencyStageDetail`, `TendencySummaryResponse`
- 새 엔드포인트: `GET /deals/tendency-summary?corp_code={corpCode}`
- 기존 `/by-sector`, `/by-stage` API는 유지

#### B3. 프론트엔드
**파일 수정**: `FundDetailPage.tsx` L416-468 교체, `useDeals.ts` 훅 추가, `types/deal.ts` 타입 추가
**파일 신규**: `TendencySummary.tsx`
- 전체 투자 전략 한줄 요약
- 섹터별 카드: 섹터명 + 비중 + 정성적 설명 + 대표 딜 목록
- 스테이지별 카드: 스테이지명 + 비중 + 정성적 설명 + 대표 딜 목록

---

## 파일 변경 목록

### 백엔드 (kiis/)

| # | 파일 | 유형 | 내용 |
|---|------|------|------|
| 1 | `app/models/news.py` | 수정 | `sentiment_label`, `sentiment_matches` 컬럼 추가 |
| 2 | `app/services/news_service.py` | 수정 | `_analyze_article()`에서 matches 함께 저장 |
| 3 | `app/services/reputation_themes.py` | 신규 | 테마 매핑 상수 (POSITIVE_THEME_MAP, NEGATIVE_THEME_MAP) |
| 4 | `app/services/reputation_service.py` | 수정 | `get_qualitative_summary()`, `_build_themes()` 추가 |
| 5 | `app/schemas/analysis.py` | 수정 | 정성적 평판 응답 스키마 추가 |
| 6 | `app/routers/analysis.py` | 수정 | `GET .../qualitative` 엔드포인트 추가 |
| 7 | `app/services/deal_service.py` | 수정 | `get_tendency_summary()` 추가 |
| 8 | `app/schemas/deal.py` | 수정 | 투자성향 요약 스키마 추가 |
| 9 | `app/routers/deals.py` | 수정 | `GET /tendency-summary` 엔드포인트 추가 |

### 프론트엔드 (amic-platform/)

| # | 파일 | 유형 | 내용 |
|---|------|------|------|
| 10 | `src/modules/kiis/types/analysis.ts` | 수정 | 정성적 평판 타입 추가 |
| 11 | `src/modules/kiis/types/deal.ts` | 수정 | 투자성향 요약 타입 추가 |
| 12 | `src/modules/kiis/hooks/useCompanies.ts` | 수정 | `useQualitativeReputation()` 훅 추가 |
| 13 | `src/modules/kiis/hooks/useDeals.ts` | 수정 | `useTendencySummary()` 훅 추가 |
| 14 | `src/modules/kiis/components/ReputationSummary.tsx` | 신규 | 정성적 평판 메인 컴포넌트 |
| 15 | `src/modules/kiis/components/ThemeCard.tsx` | 신규 | 테마별 기사 카드 (접기/펼치기) |
| 16 | `src/modules/kiis/components/TendencySummary.tsx` | 신규 | 투자성향 정성적 요약 컴포넌트 |
| 17 | `src/modules/kiis/pages/FundDetailPage.tsx` | 수정 | Overview L267-297 교체 + Tendency L416-468 교체 |

---

## UI 목표 형태

### 평판 (Overview 탭)

```
┌──────────────────────────────────────────────────────────────┐
│  업계 평판                                                    │
│                                                              │
│  최근 6개월간 긍정 보도 12건, 부정 보도 1건 (15건 분석)         │
│                                                              │
│  ┌── ▲ 포트폴리오 엑시트/상장 ──────────────── 3건 ──── ▼ ──┐ │
│  │ 2025년 포트폴리오 엑시트 성과 호평 — Platum, DealSite      │ │
│  │                                                          │ │
│  │  ↗ 스틱인베스트먼트, 포트폴리오사 코스닥 상장 성공          │ │
│  │    Platum | 2025-11-15  [성공적 엑시트] [코스닥 상장]      │ │
│  │  ↗ 스틱 투자 3호 펀드, IPO 포트폴리오 2건 달성             │ │
│  │    DealSite | 2025-10-22  [IPO 성공]                      │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌── ▼ 재무/수익성 악화 ────────────────────── 1건 ──── ▼ ──┐ │
│  │ 일부 펀드 수익률 하락 우려 보도                             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ✓ 법적/규제 리스크 보도 없음                                  │
│  ✓ 경영/인력 리스크 보도 없음                                  │
└──────────────────────────────────────────────────────────────┘
```

### 투자성향 (Tendency 탭)

```
┌──────────────────────────────────────────────────────────────┐
│  투자 전략 분석                                                │
│                                                              │
│  AI/딥테크(35%), 바이오/헬스케어(20%), 핀테크(15%) 섹터에 집중  │
│  Series A~B 중심 전략 (전체 딜의 65%)                          │
│  최근 3년간 총 28건, 약 2,400억원 투자                         │
│                                                              │
│  ── 섹터별 투자 현황 ────────────────────────────────────────  │
│                                                              │
│  ┌── AI/딥테크 ─────────────── 10건 · 840억원 · 35% ────────┐ │
│  │ AI/딥테크 섹터에 최다 투자, Series B 위주 대형 딜 중심       │ │
│  │                                                          │ │
│  │  • 에이아이스페라 — 200억원 · Series B · 2025-08           │ │
│  │  • 딥노이드 — 150억원 · Series A · 2025-05                │ │
│  │  • 뷰노 — 120억원 · Pre-IPO · 2025-03                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌── 바이오/헬스케어 ────────── 6건 · 480억원 · 20% ────────┐  │
│  │ 바이오/헬스케어 섹터 안정적 투자, 시드~시리즈A 초기 단계     │ │
│  │                                                          │ │
│  │  • 레몬헬스케어 — 80억원 · Series A · 2025-07             │ │
│  │  • 프리시젼바이오 — 60억원 · Seed · 2025-02               │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ── 스테이지별 분포 ─────────────────────────────────────────  │
│                                                              │
│  ┌── Series B ──────────────── 12건 · 1,200억원 · 43% ─────┐  │
│  │ 주력 투자 단계 — 성장기 기업 대형 투자에 집중               │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌── Series A ──────────────── 8건 · 640억원 · 29% ────────┐  │
│  │ 초기 투자 비중도 상당 — 유망 초기 기업 발굴 역량            │ │
│  └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 구현 순서

1. **백엔드 A**: DB 마이그레이션 → news_service matches 저장 → 테마 매핑 → 정성적 평판 서비스 → API
2. **백엔드 B**: 투자성향 요약 서비스 → API
3. **프론트엔드**: 타입 → 훅 → 컴포넌트 → FundDetailPage 교체

---

## 검증 방법

1. `GET /analysis/reputation/{corp_code}/qualitative` → 테마별 기사 + 정성적 문구 확인
2. `GET /deals/tendency-summary?corp_code={corpCode}` → 섹터/스테이지별 요약 텍스트 확인
3. `npx tsc --noEmit` → 타입 에러 없음
4. `npm run build` → 빌드 성공
5. FundDetailPage Overview 탭 + Tendency 탭 UI 렌더링 확인
