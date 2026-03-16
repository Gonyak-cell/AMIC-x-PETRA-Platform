/** 대시보드 MY PROJECTS 전용 훅 — ADMIN은 전체, 나머지는 assigned_to_me 필터 */

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { maApi } from "@/api/maClient";
import type {
  Transaction,
  TransactionStatus,
  TransactionListResponse,
} from "@/modules/ma/types/transaction";

const EXCLUDED_STATUSES = new Set<TransactionStatus>([
  "COMPLETED",
  "TERMINATED",
]);

export function useMyProjects() {
  const { user } = useAuth();
  const enabled = !!user?.email;
  const isAdmin = user?.role === "ADMIN";

  const params = isAdmin
    ? { limit: 100 }
    : { assigned_to_me: true, limit: 100 };

  const { data, isLoading, isError } = useQuery<TransactionListResponse>({
    queryKey: ["ma", "transactions", "my-projects", params],
    queryFn: async () => {
      const { data: resp } = await maApi.get("/transactions", { params });
      return resp;
    },
    staleTime: 30_000,
    enabled,
  });

  const projects = useMemo<Transaction[]>(() => {
    if (!data?.items) return [];
    return data.items
      .filter((t) => !EXCLUDED_STATUSES.has(t.status as TransactionStatus))
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
      );
  }, [data]);

  return {
    projects,
    isLoading: enabled && isLoading,
    isError: enabled && isError,
    email: user?.email ?? null,
  };
}
