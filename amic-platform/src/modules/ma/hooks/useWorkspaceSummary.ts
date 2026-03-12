import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type { WorkspaceSummary } from "@/modules/ma/types/workspace";

/**
 * 워크스페이스 탭 배지 카운트를 단일 API 호출로 가져옴.
 * 기존 12개 개별 목록 fetch를 대체하여 초기 로드 네트워크 요청을 절감.
 */
export function useWorkspaceSummary(txnId: string) {
  return useQuery<WorkspaceSummary>({
    queryKey: ["ma", "transactions", txnId, "workspace-summary"],
    queryFn: async () => {
      const { data } = await maApi.get(
        `/transactions/${txnId}/workspace-summary`,
      );
      return data;
    },
    enabled: !!txnId,
    staleTime: 30_000,
  });
}
