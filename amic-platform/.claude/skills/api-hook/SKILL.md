---
name: api-hook
description: TanStack React Query API 훅 생성. 표준 CRUD 패턴.
---
# API 훅 생성 가이드

대상: $ARGUMENTS (형식: `{module}/use{Resource}`, 예: `kiis/useCompanies`)

## 파일 위치
`src/modules/{mod}/hooks/use{Resource}.ts`

## 표준 CRUD 패턴 (FDD useDeals.ts 참조)
```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { {mod}Api } from "@/api/{mod}Client";
import type { {Resource}, {Resource}Create } from "../types/{resource}";

// List
export function use{Resource}s() {
  return useQuery<{Resource}[]>({
    queryKey: ["{resource}s"],
    queryFn: async () => {
      const { data } = await {mod}Api.get("/{resource}s");
      return data;
    },
  });
}

// Detail
export function use{Resource}(id: string) {
  return useQuery<{Resource}>({
    queryKey: ["{resource}s", id],
    queryFn: async () => {
      const { data } = await {mod}Api.get(`/{resource}s/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

// Create
export function useCreate{Resource}() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: {Resource}Create) => {
      const { data } = await {mod}Api.post("/{resource}s", body);
      return data as {Resource};
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["{resource}s"] }),
  });
}

// Update
export function useUpdate{Resource}(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: Partial<{Resource}Create>) => {
      const { data } = await {mod}Api.put(`/{resource}s/${id}`, body);
      return data as {Resource};
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["{resource}s"] });
      qc.invalidateQueries({ queryKey: ["{resource}s", id] });
    },
  });
}

// Delete
export function useDelete{Resource}(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await {mod}Api.delete(`/{resource}s/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["{resource}s"] }),
  });
}
```

## 규칙
- `isPending` 사용 (v5에서 mutation에 `isLoading` 없음)
- paginated 응답: `useQuery<{ items: T[], total: number }>`
- 에러 핸들링은 사용하는 측(페이지)에서 `onError`로

## 참조 파일
- `src/modules/fdd/hooks/useDeals.ts` — 기본 CRUD 패턴
