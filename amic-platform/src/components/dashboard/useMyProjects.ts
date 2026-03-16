/** 대시보드 MY PROJECTS 전용 훅 — 서버 assigned_to_me 필터 사용 */

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

  const { data, isLoading, isError } = useQuery<TransactionListResponse>({
    queryKey: ["ma", "transactions", { assigned_to_me: true, limit: 100 }],
    queryFn: async () => {
      const { data: resp } = await maApi.get("/transactions", {
        params: { assigned_to_me: true, limit: 100 },
      });
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
