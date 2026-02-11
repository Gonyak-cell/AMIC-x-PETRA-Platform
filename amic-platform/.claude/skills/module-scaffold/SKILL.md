---
name: module-scaffold
description: 새 모듈 전체 스캐폴딩. FDD 구조 기반.
---
# 모듈 스캐폴딩 가이드

대상 모듈: $ARGUMENTS (예: `kiis`, `im`)

## 디렉토리 구조 생성
```
src/modules/{name}/
  {Name}Routes.tsx
  pages/
  components/
  hooks/
  types/
```

## 1단계: API 클라이언트 확인
`src/api/{name}Client.ts`가 이미 존재하는지 확인 (fdd, kiis, im은 이미 있음).

## 2단계: 라우트 파일 생성/수정
```tsx
// src/modules/{name}/{Name}Routes.tsx
import { Routes, Route, Navigate } from "react-router-dom";
import {MainPage}Page from "./pages/{MainPage}Page";

export default function {Name}Routes() {
  return (
    <Routes>
      <Route path="{main}" element={<{MainPage}Page />} />
      <Route index element={<Navigate to="{main}" replace />} />
    </Routes>
  );
}
```

## 3단계: 타입 정의
- 백엔드 Pydantic 모델을 TypeScript interface로 변환
- union literal type으로 status/enum 정의

## 4단계: API 훅 생성
- `api-hook` 스킬 참조하여 CRUD 훅 생성

## 5단계: 첫 페이지 생성
- `new-module-page` 스킬 참조하여 리스트 페이지 생성

## 6단계: App.tsx 확인
- lazy import가 이미 등록되어 있는지 확인

## 7단계: Sidebar 확인
- `src/components/layout/Sidebar.tsx`에 모듈 링크 확인

## 참조: FDD 모듈 전체 구조
- `src/modules/fdd/FddRoutes.tsx`
- `src/modules/fdd/pages/`
- `src/modules/fdd/hooks/`
- `src/modules/fdd/types/`
