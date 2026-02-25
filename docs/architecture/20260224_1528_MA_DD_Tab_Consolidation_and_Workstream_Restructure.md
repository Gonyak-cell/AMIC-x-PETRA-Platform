# MA DD 탭 통합 및 워크스트림 재구성

> 작성: 2026-02-24 15:28 | 브랜치: `feat/ma-workflow`

## 1. 작업 요약

MA Transaction Workspace의 DD 관련 탭 구조를 전면 재설계했다.

### 1A. 탭 통합 (3개 → 1개)

| Before | After |
|--------|-------|
| DD 체크리스트 (별도 탭) | **DD/Checklist** (통합 탭) |
| 법률실사(LDD) (별도 탭) | → DD/Checklist 내 "DD 리포트" 서브탭 |
| 법률 문서 (별도 탭) | → 계약/SPA 내 "법률 문서" 서브탭 |

### 1B. 워크스트림 재구성 (9개 flat → 20개 3-tier)

| Before | After |
|--------|-------|
| FINANCIAL, LEGAL, TAX, COMMERCIAL, IT, HR, ENVIRONMENTAL, INSURANCE, OTHER | FDD 5개 + LDD 9개 + TDD 5개 + OTHER |
| LEGAL_GROUP 하위: 법률, IT, HR, 환경, 보험 | FDD_GROUP / LDD_GROUP / TDD_GROUP / 기타 |

## 2. 변경 파일 목록

### 신규 파일 (2개)

| 파일 | 설명 |
|------|------|
| `amic-platform/src/modules/ma/components/DDReportSection.tsx` | FDD/LDD/TDD 리포트 카드 그리드. LDD→LDDReportsTab 연결, FDD·TDD→Coming Soon |
| `deal-mgmt/migrations/versions/013_dd_workstream_restructure.py` | PostgreSQL enum `ddworkstream` 재구성 마이그레이션 (upgrade + downgrade) |

### 수정 파일 (5개)

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/modules/ma/pages/TransactionWorkspacePage.tsx` | VALID_TABS에서 `ldd`, `legal_docs` 제거. DD/Checklist·계약/SPA 탭에 pill 서브탭 추가. ldd/legal_docs URL 리다이렉트. 범용 그룹 배지 로직. 기본 workstream 값 변경 |
| `amic-platform/src/modules/ma/constants.ts` | DD_WORKSTREAM_OPTIONS 20개, DD_WORKSTREAM_HIERARCHY 4그룹, DD_SUB_LABELS 19개. DD_WORKSTREAM_TO_GROUP·DD_LEGAL_SUB_LABELS 삭제 |
| `amic-platform/src/modules/ma/types/dd_checklist.ts` | DDWorkstream 유니언 타입 20개 값으로 교체 |
| `amic-platform/src/components/layout/Sidebar.tsx` | MA_DD_NAV에서 ldd 항목 제거, 라벨 "DD/Checklist". Gavel import 제거 |
| `deal-mgmt/app/models/enums.py` | DDWorkstream enum 20개 값 (FDD 5 + LDD 9 + TDD 5 + OTHER) |

## 3. 새 워크스트림 구조

### FDD (재무실사) — 5개
| Enum | 라벨 |
|------|------|
| FDD_FINANCIAL_STATEMENTS | 재무제표 분석 |
| FDD_REVENUE | 매출 및 수익성 |
| FDD_WORKING_CAPITAL | 운전자본 |
| FDD_DEBT_CASH | 차입금 및 현금 |
| FDD_PROJECTIONS | 사업계획 및 추정 |

### LDD (법률실사) — 9개
| Enum | 라벨 |
|------|------|
| LDD_CORPORATE | 회사일반 |
| LDD_PERMITS | 인허가 및 법령준수 |
| LDD_CONTRACTS | 계약 |
| LDD_ASSETS | 자산(부동산/기타 자산) |
| LDD_LABOR | 인사노무 |
| LDD_LITIGATION | 소송 및 분쟁 |
| LDD_IP | 지식재산권 |
| LDD_INSURANCE | 보험 |
| LDD_ENVIRONMENT | 환경 |

### TDD (세무실사) — 5개
| Enum | 라벨 |
|------|------|
| TDD_CORPORATE_TAX | 법인세 |
| TDD_VAT | 부가가치세 |
| TDD_TRANSFER_PRICING | 이전가격 |
| TDD_WITHHOLDING | 원천세 |
| TDD_TAX_INCENTIVES | 세제혜택 및 감면 |

### 기타 — 1개
| Enum | 라벨 |
|------|------|
| OTHER | 기타 |

## 4. UI 구조

### DD/Checklist 탭
```
[체크리스트]  [DD 리포트]   ← pill 서브탭

체크리스트:
  워크스트림 필터: [전체] [FDD ▾] [LDD ▾] [TDD ▾] [기타]
  하위 필터: (선택한 그룹의 하위 항목)
  DataTable (인라인 상태 변경)

DD 리포트:
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ FDD      │  │ LDD      │  │ TDD      │
  │ Coming   │  │ → 클릭   │  │ Coming   │
  │ Soon     │  │          │  │ Soon     │
  └──────────┘  └──────────┘  └──────────┘
```

### 계약/SPA 탭
```
[계약]  [법률 문서]   ← pill 서브탭
```

## 5. DB 마이그레이션 (013)

- PostgreSQL enum `ddworkstream` 재생성 (DROP + CREATE)
- 기존 데이터 매핑: FINANCIAL→FDD_FINANCIAL_STATEMENTS, LEGAL→LDD_CORPORATE, TAX→TDD_CORPORATE_TAX, HR→LDD_LABOR, ENVIRONMENTAL→LDD_ENVIRONMENT, INSURANCE→LDD_INSURANCE, COMMERCIAL/IT→OTHER
- downgrade() 지원 (역방향 매핑 포함)

## 6. URL 호환성

| 기존 URL | 리다이렉트 |
|----------|-----------|
| `/ma/transactions/{id}/ldd` | → `/dd-checklist` + 서브탭 "DD 리포트" |
| `/ma/transactions/{id}/legal_docs` | → `/contracts` + 서브탭 "법률 문서" |

## 7. 검증 결과

- TypeScript 컴파일: 통과 (`tsc --noEmit`)
- Vite 빌드: 통과 (`vite build` 6.15s)
- 코드 리뷰: 허위 양성 0건, Dead code 제거 완료, 라벨 불일치 수정 완료
