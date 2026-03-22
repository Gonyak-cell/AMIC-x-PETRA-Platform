# Code Review — MA 모듈 3개 미심층 관점 심층 리뷰 (API 계약 / 에러 처리 / 성능)

> **Review Date**: 2026-03-09 16:22 KST
> **Reviewer**: Claude Code (review-orchestrate)
> **Scope**: MA 모듈 전체 (feat/ma-workflow 브랜치)
> **Method**: 3-Agent Parallel Deep Review
> **Focus**: 이전 R1~R4에서 부분 커버리지만 있었던 3개 관점
> **Quality Gates**: `--skip-gates` (이전 세션에서 통과 확인됨)

## Summary

| Severity | Count | Confidence Distribution | Priority Distribution |
|----------|-------|------------------------|----------------------|
| Critical | 1     | HIGH: 1                | P1: 1               |
| Major    | 3     | HIGH: 3                | P1: 1 / P2: 2       |
| Moderate | 4     | HIGH: 3 / MEDIUM: 1   | P2: 2 / P3: 2       |
| Minor    | 8     | HIGH: 6 / MEDIUM: 2   | P3: 6 / P4: 2       |
| Info     | 4     | HIGH: 2 / MEDIUM: 2   | P4: 2 / P5: 2       |
| **Total**| **20**| HIGH: **15** / MEDIUM: **5** | P1: **2** / P2: **4** / P3: **8** / P4: **4** / P5: **2** |

**FP Prevention**: 가설 35건 검증, 15건 사전 거부 (거부율: 43%)

---

## 1. API 계약 심층 리뷰 — 8건

### [API-08] FE 다운로드 URL prefix 불일치 — [Major/HIGH] — P1 (점수: 85)

**파일**: `amic-platform/src/modules/ma/hooks/useContractMarkups.ts:67-68`, `useNdaMarkups.ts:122-127`, `useVdr.ts:289-291`

**증거**:
- ContractMarkup/NdaMarkup: `/api/v1/transactions/...`
- VDR: `/api/ma/transactions/...`

**문제**: 같은 모듈 내에서 다운로드 URL의 API prefix가 `/api/v1/`과 `/api/ma/`로 불일치. nginx 라우팅에 따라 하나가 404를 반환할 수 있음.

---

### [API-01] Buyers list 페이지네이션 메타데이터 미반환 — [Major/HIGH] — P2 (점수: 70)

**파일**: `deal-mgmt/app/routers/buyers.py:71-96`

**문제**: `limit`/`offset` 파라미터를 받지만 `list[BuyerCandidateOut]`로 raw 배열만 반환. 동일 모듈의 Transactions, ContractMarkups, NdaMarkups는 모두 `items + total` 래퍼 사용.

---

### [API-02] RFI Items list 페이지네이션 메타데이터 미반환 — [Major/HIGH] — P2 (점수: 70)

**파일**: `deal-mgmt/app/routers/rfi_v2.py:48-81`

**문제**: API-01과 동일 패턴. `limit`/`offset`을 받지만 total 없이 배열만 반환.

---

### [API-05] ContractMarkup file_path 서버 경로 노출 — [Moderate/HIGH] — P2 (점수: 40)

**파일**: `deal-mgmt/app/schemas/contract_markup.py:21`

**문제**: `file_path`가 서버 로컬 경로(`uploads/markups/...`)를 클라이언트에 노출. NdaMarkupOut은 `has_file: bool` 가상 필드로 대체한 반면 ContractMarkupOut은 실제 경로 반환.

---

### [API-03] suggest-category untyped dict 반환 — [Moderate/HIGH] — P3 (점수: 40)

**파일**: `deal-mgmt/app/routers/vdr.py:490-511`

**문제**: `response_model` 미지정, 반환 타입 `dict`. OpenAPI 스키마에 응답 구조 문서화 불가.

---

### [API-06] Transaction list 쿼리 파라미터 Enum 미적용 — [Moderate/MEDIUM] — P3 (점수: 24)

**파일**: `deal-mgmt/app/routers/transactions.py:26-27`

**문제**: `side`, `phase` 파라미터가 `str` 타입. Enum이 존재하지만 쿼리 파라미터에 미적용. 잘못된 값 시 400이 아닌 빈 결과 반환.

---

### [API-04] generate-redline response_model 미지정 — [Minor/HIGH] — P4 (점수: 20)

**파일**: `deal-mgmt/app/routers/nda_markups.py:288-412`

**문제**: StreamingResponse + 커스텀 헤더(`X-Issues-Count`) 계약이 OpenAPI에 문서화되지 않음.

---

### [API-07] Markup ListResponse에 limit/offset 누락 — [Minor/HIGH] — P4 (점수: 20)

**파일**: `deal-mgmt/app/schemas/contract_markup.py:42-44`

**문제**: `ContractMarkupListResponse`/`NdaMarkupListResponse`에 `total`만 포함, `limit`/`offset` 미반환. TransactionListResponse와 패턴 불일치.

---

## 2. 에러 처리 심층 리뷰 — 7건

### [ERR-1] useDealSetup 3개 mutation onError 완전 누락 — [Critical/HIGH] — P1 (점수: 100)

**파일**: `amic-platform/src/modules/ma/hooks/useDealSetup.ts:12-55`

**문제**: 거래 생성 핵심 3단계(텍스트→미리보기, 엑셀→미리보기, 확정→DB)에 onError 없음. 글로벌 핸들러가 "Request failed with status code 400" 같은 기술적 메시지를 사용자에게 노출. BE가 보내는 사용자 친화적 `detail` 메시지를 추출하지 못함.

---

### [ERR-2] useSuggestVdrCategory onError/onSuccess 모두 누락 — [Moderate/HIGH] — P2 (점수: 40)

**파일**: `amic-platform/src/modules/ma/hooks/useVdr.ts:294-304`

**문제**: AI 카테고리 추천 mutation에 에러 핸들러 없음. 실패 시 글로벌 핸들러의 기술적 메시지가 불필요하게 표시.

---

### [ERR-3] BE deal_setup confirm try/except 누락 — [Moderate/HIGH] — P2 (점수: 40)

**파일**: `deal-mgmt/app/routers/deal_setup.py:94-101`

**문제**: 같은 파일의 다른 2개 엔드포인트는 `try/except`로 감싸지만, `confirm`만 미적용. 예외 발생 시 500 + 스택 트레이스 노출 가능. ERR-1과 이중 누락.

---

### [ERR-4] RuntimeError 글로벌 핸들러 미등록 — [Moderate/MEDIUM] — P3 (점수: 24)

**파일**: `deal-mgmt/app/services/transcription_service.py:104`, `spa_analysis_service.py:170,187`

**문제**: 8+곳에서 `RuntimeError`를 raise하지만 `core/exceptions.py`에 핸들러 미등록. 라우터에서 catch 안 되면 500 Internal Server Error로 전파.

---

### [ERR-5] onError 에러 메시지 추출 방식 3패턴 혼재 — [Minor/HIGH] — P3 (점수: 20)

**파일**: MA hooks 전체

**문제**: ~120개 mutation 중 패턴 A(`extractApiError`) 12.5%, 패턴 B(`err.message`) 16.7%, 패턴 C(고정 메시지) 68.3%. 패턴 B는 기술적 메시지 노출, 패턴 C는 BE detail 무시.

---

### [ERR-6] 글로벌 + 개별 onError 이중 toast — [Minor/HIGH] — P3 (점수: 20)

**파일**: `amic-platform/src/main.tsx:35-37`

**문제**: `MutationCache.onError`와 개별 mutation `onError`가 동시 실행되어 동일 에러에 toast 2번 표시.

---

### [ERR-7] BE integrations 라우터 str(e) 직접 노출 — [Minor/MEDIUM] — P4 (점수: 12)

**파일**: `deal-mgmt/app/routers/integrations.py:72,92,124,144,167`

**문제**: 외부 서비스 연동 실패 시 `str(e)`를 응답에 그대로 포함. 내부 URL, 연결 정보 노출 가능.

---

## 3. 성능 심층 리뷰 — 5건

### [PERF-R7-01] 비활성 탭 데이터 과잉 fetch — [Minor/HIGH] — P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx:187-189`

**문제**: `engagements`, `buyers`, `timeline` 3개 쿼리가 탭 조건 없이 항상 fetch. 배지 카운트용이지만, 다른 탭은 조건부 fetch하여 일관성 없음.

---

### [PERF-R7-02] 16개 탭 컴포넌트 정적 import (코드 분할 미적용) — [Minor/HIGH] — P3 (점수: 20)

**파일**: `amic-platform/src/modules/ma/tabs/index.ts:1-16`, `TransactionWorkspacePage.tsx:56-73`

**문제**: 16개 탭 전부 정적 import. 사용자는 한 번에 1개 탭만 사용하므로 불필요한 초기 번들 크기 증가.

---

### [PERF-R7-03] DataTable GSAP 스태거 대량 행 성능 — [Minor/MEDIUM] — P3 (점수: 12)

**파일**: `amic-platform/src/components/ui/DataTable.tsx:71-88`

**문제**: 500행에 `stagger: 0.03`이면 마지막 행 애니메이션 시작까지 15초. SI 일괄 등록으로 100건 추가 시 체감 가능.

---

### [PERF-R7-04] DataTable 가상 스크롤 미적용 — [Info/HIGH] — P5 (점수: 10)

**파일**: `amic-platform/src/components/ui/DataTable.tsx:280-359`

**문제**: `data.map()`으로 500~1000행 전체 DOM 렌더링. 현재 규모에서는 문제없으나 향후 고려 필요.

---

### [PERF-R7-05] BuyersTab useMemo 의존성 무력화 — [Info/MEDIUM] — P5 (점수: 10)

**파일**: `amic-platform/src/modules/ma/tabs/BuyersTab.tsx:137-234`

**문제**: `buyerColumns` useMemo의 의존성에 `updateBuyer`(렌더마다 새 객체)가 포함되어 매 렌더 재계산. 실질적 영향은 미미.

---

## Priority Matrix

### P1 — 즉시 수정 (2건)
1. [ERR-1] [Critical/HIGH]: useDealSetup 3개 mutation onError 완전 누락 (점수: 100)
2. [API-08] [Major/HIGH]: FE 다운로드 URL prefix 불일치 `/api/v1/` vs `/api/ma/` (점수: 85)

### P2 — 스프린트 우선 (4건)
1. [API-01] [Major/HIGH]: Buyers list pagination 메타 미반환 (점수: 70)
2. [API-02] [Major/HIGH]: RFI Items list pagination 메타 미반환 (점수: 70)
3. [API-05] [Moderate/HIGH]: ContractMarkup file_path 서버 경로 노출 (점수: 40)
4. [ERR-2] [Moderate/HIGH]: useSuggestVdrCategory onError 누락 (점수: 40)
5. [ERR-3] [Moderate/HIGH]: BE deal_setup confirm try/except 누락 (점수: 40)

### P3 — 개선 권장 (8건)
1. [API-03] [Moderate/HIGH]: suggest-category untyped dict (점수: 40)
2. [API-06] [Moderate/MEDIUM]: Transaction list Enum 미적용 (점수: 24)
3. [ERR-4] [Moderate/MEDIUM]: RuntimeError 핸들러 미등록 (점수: 24)
4. [ERR-5] [Minor/HIGH]: onError 3패턴 혼재 (점수: 20)
5. [ERR-6] [Minor/HIGH]: 이중 toast (점수: 20)
6. [PERF-R7-01] [Minor/HIGH]: 비활성 탭 과잉 fetch (점수: 20)
7. [PERF-R7-02] [Minor/HIGH]: 16개 탭 코드 분할 미적용 (점수: 20)
8. [PERF-R7-03] [Minor/MEDIUM]: GSAP 스태거 대량행 (점수: 12)

### P4 — 저우선 (4건)
1. [API-04] [Minor/HIGH]: generate-redline response_model 미지정 (점수: 20)
2. [API-07] [Minor/HIGH]: Markup ListResponse limit/offset 누락 (점수: 20)
3. [ERR-7] [Minor/MEDIUM]: integrations str(e) 노출 (점수: 12)

### P5 — 참고 (2건)
1. [PERF-R7-04] [Info/HIGH]: DataTable 가상 스크롤 미적용 (점수: 10)
2. [PERF-R7-05] [Info/MEDIUM]: BuyersTab useMemo 의존성 무력화 (점수: 10)

---

## 13개 관점 최종 커버리지 (R1~R5 통합)

| # | 관점 | R1 | R2 | R3 | R4 | R5 (이번) | 상태 |
|---|------|----|----|----|----|-----------|----|
| 1 | 보안 | SEC-01~07 | SEC-D1~D5 | — | R3-02 | — | ✅ 심층 완료 |
| 2 | 위협 모델링 | ⚠️ | — | THREAT-1~7 | — | — | ✅ 심층 완료 |
| 3 | 데이터 흐름 | CR-8 | — | DF-1~4 | — | — | ✅ 심층 완료 |
| 4 | **API 계약** | SEC-03/04/06 | — | — | R3-02 | **API-01~08** | ✅ 심층 완료 |
| 5 | **에러 처리** | CR-2, OBS-1~4 | — | — | R4-05/08/09 | **ERR-1~7** | ✅ 심층 완료 |
| 6 | 관찰 가능성 | ⚠️ | ✅ | — | R4-04/05 | — | ✅ 심층 완료 |
| 7 | **성능** | PERF-P1~P4 | — | — | R5-01, R6-012 | **PERF-R7-01~05** | ✅ 심층 완료 |
| 8 | 배포 안전성 | ✅ | DEPLOY-1/2 | — | — | — | ✅ 심층 완료 |
| 9 | 의존성 | ✅ | ✅ | — | — | — | ✅ 심층 완료 |
| 10 | 도메인 로직 | — | R6-001 | — | R6-004~016 | — | ✅ 심층 완료 |
| 11 | 테스트 품질 | — | TEST-1/2 | — | — | — | ✅ 심층 완료 |
| 12 | 인지 복잡도 | CR-3 | ✅ | — | — | — | ✅ 심층 완료 |
| 13 | 접근성 & UX | — | — | A11Y/UX | R6-015/016 | — | ✅ 심층 완료 |

**결론**: 13개 관점 모두 심층 리뷰 완료.

---

## Methodology

- Agents: API 계약 전문 에이전트, 에러 처리 전문 에이전트, 성능 전문 에이전트
- Protocol: Verified Claim Protocol v1.1 (신뢰도 가중 우선순위)
- 검증: 모든 이슈 Read 기반 코드 확인, Grep 기반 패턴 검증
- 이전 리뷰(R1~R4) 중복 제거: 15건 사전 거부

## 긍정적 관찰

### API 계약
- HTTP 상태코드 전반적으로 적절 (POST→201, DELETE→204, 404, 422, 413)
- 에러 응답 포맷 `{"detail": "..."}` 일관성 유지
- 파일 업로드 검증(확장자, MIME, 크기, 경로 탐색 방어) 체계적

### 에러 처리
- Error Boundary 2단계 구성 (SentryErrorBoundary + MaErrorBoundary)
- 401 자동 재시도 + 토큰 갱신 구현
- BE 커스텀 예외 5개 + RFC 7807 핸들러 체계적
- API 클라이언트 30초 타임아웃 설정

### 성능
- React Query staleTime/gcTime 일관적 적용
- BuyersTab 하위 뷰 lazy loading 적용
- SI 매핑 세마포어 + defer 최적화
- useMemo/useDeferredValue 적절 활용
- DB 커넥션 풀 설정 완비
