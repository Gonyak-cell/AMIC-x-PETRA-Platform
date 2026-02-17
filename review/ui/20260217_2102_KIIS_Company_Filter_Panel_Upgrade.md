# KIIS Companies 필터 패널 UI 개선

> **작성**: 2026-02-17 21:02
> **카테고리**: UI
> **심각도**: Moderate (P2)
> **상태**: ✅ 수정 완료

---

## 문제

| 항목 | 내용 |
|------|------|
| **위치** | `http://localhost:3000/kiis/companies` |
| **증상** | 검색창이 너무 작고(`max-w-sm`), Market 드롭다운이 지나치게 넓음. Funds 페이지 대비 필터 UX 불균형 |
| **원인** | Companies 페이지가 단순 `Input` + `Select` 조합으로 구현됨. Funds의 `FundFilterPanel` 패턴 미적용 |

---

## 변경 내역

### 1. 백엔드 — 다중 시장 구분 필터 지원

**파일**: `kiis/app/routers/company.py`

| 변경 전 | 변경 후 |
|---------|---------|
| `search`: 기업명만 검색 | `search`: **기업명 + 종목명** 모두 검색 |
| `corp_cls`: 단일 값만 지원 (예: `Y`) | `corp_cls`: **쉼표 구분 복수 선택** 지원 (예: `Y,K`) |

### 2. 프론트엔드 — 신규 파일 3개

| 파일 | 역할 |
|------|------|
| `amic-platform/src/modules/kiis/constants/companyFilters.ts` | 시장 구분 옵션, Badge variant, 라벨 매핑 |
| `amic-platform/src/modules/kiis/hooks/useCompanyFilters.ts` | URL search params 기반 필터 상태 관리 (useFundFilters 패턴) |
| `amic-platform/src/modules/kiis/components/CompanyFilterPanel.tsx` | FundFilterPanel과 동일 구조의 필터 패널 |

### 3. 프론트엔드 — 수정 파일 2개

| 파일 | 변경 |
|------|------|
| `amic-platform/src/modules/kiis/pages/CompanyListPage.tsx` | 기존 `Input` + `Select` 제거 → `CompanyFilterPanel` 적용 |
| `amic-platform/src/modules/kiis/types/company.ts` | `CompanyListParams.corp_cls` 타입: `CorpCls` → `string` (쉼표 구분 지원) |

---

## CompanyFilterPanel 기능

| 기능 | 설명 |
|------|------|
| **검색** | 돋보기 아이콘 포함 전체 너비 입력창, 300ms 디바운스 |
| **상세 필터 토글** | 접기/펼치기 애니메이션, 활성 필터 카운트 배지 |
| **시장 구분 Chip** | KOSPI, KOSDAQ, KONEX, 기타 — 다중 선택 가능 |
| **적용 필터 태그** | 선택된 필터 태그 표시 + X 버튼 개별 제거 |
| **초기화** | 전체 필터 초기화 버튼 |
| **URL 동기화** | search params로 상태 관리 (새로고침 시 필터 유지) |

---

## Badge 스타일 매핑

| 시장 | 값 | Badge Variant |
|------|----|---------------|
| KOSPI | Y | info (파란색) |
| KOSDAQ | K | success (초록색) |
| KONEX | N | warning (주황색) |
| 기타 | E | neutral (회색) |

---

## 디버깅 노트

- Docker 컨테이너(`amic-frontend`)가 Vite 서버를 실행하고 있어 로컬 Vite 서버와 별개로 동작
- 변경 반영을 위해 `docker compose restart frontend` 실행 필요
- Docker 볼륨 마운트(`./amic-platform:/app`)로 소스 동기화, 단 `node_modules`는 별도 볼륨
