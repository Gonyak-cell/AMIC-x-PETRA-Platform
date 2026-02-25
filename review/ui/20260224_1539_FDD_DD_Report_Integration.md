# FDD → DD/Checklist 탭 연동 ("COMING SOON" 제거)

> 작성: 2026-02-24 15:39:00

## 문제

DD/Checklist 탭 → DD 리포트 섹션에서 FDD(재무실사) 카드가 `available: false`로 설정되어 "COMING SOON"으로 표시됨. FDD 모듈은 이미 완성되어 있고(딜 생성, QoE/NWC/NetDebt 분석, 보고서 생성/다운로드), MA 트랜잭션에 `fdd_deal_id` 필드도 존재하는 상태.

## 원인

`DDReportSection.tsx`의 `DD_REPORTS` 배열에서 FDD 항목의 `available: false` 하드코딩.

## 수정 내역

### 1. `amic-platform/src/modules/ma/components/DDReportSection.tsx` (수정)

| 변경 사항 | 상세 |
|-----------|------|
| `DDReportView` 타입 | `"overview" \| "ldd"` → `"overview" \| "ldd" \| "fdd"` |
| FDD `available` | `false` → `true` |
| view 분기 | `view === "fdd"` 시 `<FDDReportsTab txnId={txnId} />` 렌더링 |
| import | `FDDReportsTab` 추가 |

### 2. `amic-platform/src/modules/ma/components/FDDReportsTab.tsx` (신규)

LDDReportsTab 패턴 기반 FDD 보고서 탭 컴포넌트:

- `useTransaction(txnId)`로 `fdd_deal_id` 조회
- **fdd_deal_id 미연결**: 빈 상태 UI + "FDD 딜 생성" 버튼 → Document Studio 이동
- **fdd_deal_id 연결됨**:
  - `useReportVersions(fddDealId)` 훅으로 보고서 버전 목록 조회
  - KPI 카드: 초안(Draft) / 확정(Final) 건수
  - 테이블: 버전, 포맷(PPTX/DOCX/JSON), 포함 섹션, 상태, 생성일, 작업(다운로드/확정)
  - "FDD 워크스페이스" 바로가기 + "새 보고서" 생성 버튼

### 재사용한 기존 코드

- `useTransaction()` — `amic-platform/src/modules/ma/hooks/useTransactions.ts`
- `useReportVersions()` / `useFinalizeReportVersion()` — `amic-platform/src/modules/fdd/hooks/useReportVersions.ts`
- `ReportVersion` 타입 — `amic-platform/src/modules/fdd/types/report-version.ts`
- FDD API 클라이언트 (`/api/fdd`) — `amic-platform/src/api/client.ts`

## 검증

- [x] TypeScript `tsc --noEmit` 통과
- [x] Vite 프로덕션 빌드 성공 (6.89s)

## 심각도

UI 개선 (P3) — 기능 누락이 아닌 연동 미완료
