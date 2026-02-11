---
name: new-module-page
description: 모듈 내 새 페이지 생성. FDD 패턴 기반 스캐폴딩.
---
# 새 모듈 페이지 생성 가이드

대상: $ARGUMENTS (형식: `{module}/{PageName}`, 예: `kiis/CompanyList`)

## 생성할 파일
1. `src/modules/{mod}/pages/{PageName}Page.tsx` — 페이지 컴포넌트
2. `src/modules/{mod}/types/{resource}.ts` — 타입 정의 (없는 경우)
3. `src/modules/{mod}/hooks/use{Resource}.ts` — API 훅 (없는 경우)
4. `src/modules/{mod}/{Mod}Routes.tsx`에 라우트 추가

## 페이지 표준 구조 (FDD DealListPage 참조)
```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { use{Resource}s } from "../hooks/use{Resource}";
import type { {Resource} } from "../types/{resource}";
import { Button, Card, DataTable, KpiCard, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";

export default function {PageName}Page() {
  const { data, isLoading } = use{Resource}s();

  const columns: Column<{Resource}>[] = [
    { key: "name", header: "Name" },
    { key: "status", header: "Status" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-bold text-text-dark">{Title}</h1>
        <Button variant="accent">New {Resource}</Button>
      </div>
      <Card title="All {Resource}s" headerBar padding="none">
        {!isLoading && (!data || data.length === 0) ? (
          <EmptyState title="No {resource}s yet" description="..." />
        ) : (
          <DataTable columns={columns} data={data || []} keyField="id" loading={isLoading} striped />
        )}
      </Card>
    </div>
  );
}
```

## 참조 파일
- `src/modules/fdd/pages/DealListPage.tsx` — 리스트 페이지 패턴
- `src/modules/fdd/FddRoutes.tsx` — 라우트 등록 패턴

## 체크리스트
- [ ] default export
- [ ] 로딩/빈 상태 처리
- [ ] toast로 성공/에러 피드백
- [ ] Routes에 라우트 등록
- [ ] Tailwind 클래스만 사용 (amic 테마 토큰)
