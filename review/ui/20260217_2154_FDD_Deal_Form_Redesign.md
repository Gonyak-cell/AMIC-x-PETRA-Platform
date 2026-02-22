# FDD 딜 생성 폼 리디자인 — 필수/선택 분리 + 선택 안함 기본값

> 작성: 2026-02-17 21:53:41

## 요약

FDD 딜 생성 모달을 **최소 입력으로 즉시 생성** 가능하도록 리디자인.
필수 항목(딜 이름, 대상회사명)만 입력하면 바로 생성되며, 나머지는 "선택 안함" 상태로 생성 후 추후 설정 가능.

## 심각도

- **종류**: UI/UX 개선
- **우선순위**: P2 (Moderate)

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `amic-platform/src/modules/fdd/pages/DealListPage.tsx` | 폼 구조 리디자인 |
| `amic-platform/src/modules/fdd/constants.ts` | Select 옵션에 "선택 안함" 기본값 추가 |
| `amic-platform/vite.config.ts` | Docker HMR 지원 (`usePolling`, `host: true`) |

## 상세 변경 내역

### 1. 폼 구조 변경 (`DealListPage.tsx`)

**Before:**
- 모든 필드가 한 화면에 나열 (기본 정보, 의뢰인 정보, 거래 분류, 분석 설정)
- INITIAL_FORM에 deal_type, base_currency, industry 기본값 하드코딩

**After:**
- **필수 섹션** (상단 고정): 딜 이름, 대상회사명
- **안내 문구**: "위 두 항목만 입력하면 바로 생성됩니다."
- **"추가 정보 펼치기/접기"** 토글 버튼 (ChevronDown 아이콘)
- 토글 내부: 의뢰인 정보, 거래 분류, 분석 설정 (3개 fieldset)
- INITIAL_FORM에 name, target_company_name만 포함

### 2. handleSubmit 변경

**Before:** payload에 deal_type, base_currency, industry 항상 포함
**After:** 필수 필드(name, target_company_name)만 기본 포함, 나머지는 값이 있을 때만 추가 → 서버 기본값 사용

### 3. 테이블 표시 변경

- `deal_structure` 컬럼 추가 (null이면 "선택 안함" 표시)
- `reference_date`: "-" → "선택 안함"
- `team`: 미배정 시 "선택 안함"
- `base_currency` 컬럼 제거 (거래구조로 대체)
- `target_company_name`: null이면 "선택 안함"

### 4. Select 옵션 기본값 (`constants.ts`)

모든 Select 옵션 배열 첫 항목에 `{ value: "", label: "선택 안함" }` 추가:
- `DEAL_TYPE_OPTIONS`
- `CURRENCY_OPTIONS`
- `DEAL_STRUCTURE_OPTIONS`
- `INVESTMENT_TYPE_OPTIONS`
- `SELLER_TYPE_OPTIONS`

### 5. Vite 설정 (`vite.config.ts`)

Docker 컨테이너 내 Vite 개발 서버가 Windows 볼륨 마운트 파일 변경을 감지하도록:
```ts
server: {
  host: true,          // 0.0.0.0 바인딩 (Docker 외부 접근)
  watch: {
    usePolling: true,  // inotify 대신 폴링 (Windows Docker 호환)
    interval: 1000,
  },
}
```

## 검증

- [x] `npx tsc --noEmit` — 에러 없음
- [x] `npx vite build` — 빌드 성공
- [x] Docker frontend 컨테이너 재시작 완료
