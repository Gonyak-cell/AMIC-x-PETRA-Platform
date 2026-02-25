# [a11y] PPTStylePicker label/input 연결 + CreateTransactionPage aria-expanded

> 2026-02-23 12:16:00

## 수정 1: PPTStylePicker label/input 연결 (D-005)

**파일**: `PPTStylePicker.tsx:226-237`

WCAG 2.1 Level A — `<label>`과 `<input>`을 `htmlFor`/`id`로 연결:

```tsx
// 수정 전
<label className="...">파트너명 <span>*</span></label>
<input ref={partnerInputRef} type="text" .../>

// 수정 후
<label htmlFor="ppt-partner-name" className="...">파트너명 <span>*</span></label>
<input id="ppt-partner-name" ref={partnerInputRef} type="text" .../>
```

## 수정 2: CreateTransactionPage 토글 버튼 aria-expanded (ISSUE-008)

**파일**: `CreateTransactionPage.tsx:131`

```tsx
// 수정 전
<button type="button" onClick={() => setShowOptional(!showOptional)} ...>

// 수정 후
<button type="button" aria-expanded={showOptional} onClick={() => setShowOptional(!showOptional)} ...>
```

WCAG 2.1 — 접기/펼치기 버튼은 `aria-expanded` 필수.
