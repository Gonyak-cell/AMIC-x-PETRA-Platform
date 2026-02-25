# Deal Contracts 카드 UI 리디자인 — DocuSign CLM 스타일

> 2026-02-25 15:05 작성

## Context

Deal Doc Studio의 법률 문서 유형 선택 카드(SPA, SHA, BTA, SSA)가 타입별 5가지 다른 색상을 사용하고, 아이콘이 컬러 원형 배경에 들어가 이모지 느낌을 줌. DocuSign CLM의 Olive 디자인 시스템 (절제된 단일 브랜드 컬러, 모노크롬 아이콘, 넉넉한 여백)을 참고하여 세련된 enterprise UI로 개선.

## 수정 파일

### 1. `amic-platform/src/modules/docs/components/LegalDocTypePicker.tsx`

- `COLORS` 상수 삭제 (타입별 5색 제거)
- `BG_SELECTED` 상수 삭제 (타입별 선택 배경 제거)
- `cn` import 추가, `DocumentTypePicker.tsx` 패턴으로 통일

| 요소 | Before | After |
|------|--------|-------|
| 그리드 | `gap-3 lg:grid-cols-3` | `gap-4 sm:grid-cols-2` (2x2) |
| 카드 패딩 | `p-5 gap-3` | `p-6 gap-4` |
| 카드 선택 | 타입별 5색 | `border-amic bg-amic/5 ring-1 ring-amic/20 shadow-dr-sm` |
| 아이콘 | 타입별 컬러 + `bg-white` | 선택: `bg-amic text-white` / 미선택: `bg-bg-cool text-text-secondary` |
| 제목 | `text-sm` | `text-base font-heading` + 선택 시 `text-amic` |
| 설명 | `text-xs` | `text-sm` |
| 배지 | `text-[10px] bg-white rounded-full` | `text-xs rounded` + 상태 반응형 |

### 2. `amic-platform/src/modules/docs/pages/CreateLegalDocumentPage.tsx`

StepIndicator 미세 조정:
- `bg-accent-primary` → `bg-amic`
- 현재 스텝에 `ring-2 ring-amic/20 ring-offset-2` 추가
- `h-6 w-6` → `h-7 w-7`

## 코드 리뷰 결과

- LegalDocTypePicker.tsx: 16개 항목 검증 ✅
- StepIndicator: 7개 항목 검증 ✅
- 허위 클레임: 0건

### 잠재 이슈

| 이슈 | 위치 | 심각도 |
|------|------|--------|
| 미사용 import `Handshake` + `ICONS.MOU` | LegalDocTypePicker.tsx:1 | 낮음 (기존 코드) |
