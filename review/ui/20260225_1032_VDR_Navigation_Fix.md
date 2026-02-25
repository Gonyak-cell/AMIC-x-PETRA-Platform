# VDR 사이드바 네비게이션 수정

> 작성: 2026-02-25 10:32

## 수정 내역

### 1. VDR Overview → 워크스페이스 VDR 탭 네비게이션 경로 수정
- **파일**: `amic-platform/src/modules/vdr/pages/VdrOverviewPage.tsx:175`
- **문제**: `?tab=vdr` 쿼리 파라미터 사용 → TransactionWorkspacePage는 splat 기반 라우팅이라 VDR 탭 활성화 안 됨
- **수정**: `navigate(\`/ma/transactions/${id}?tab=vdr\`)` → `navigate(\`/ma/transactions/${id}/vdr\`)`

### 2. VDR 탭 단계별 가시성 확장
- **파일**: `amic-platform/src/modules/ma/constants.ts:553-557`
- **문제**: VDR 탭이 `PREPARATION` 단계에서만 visible → 다른 단계의 거래 클릭 시 폴백으로 overview 이동
- **수정**: `MARKETING` ~ `POST_CLOSING` 모든 단계에 `"vdr"` 추가
- **변경 전**: PREPARATION만 vdr 포함
- **변경 후**: PREPARATION, MARKETING, BIDDING_DD, NEGOTIATION, CLOSING, POST_CLOSING 모두 vdr 포함
