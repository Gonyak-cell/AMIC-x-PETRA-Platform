import { useQuery } from "@tanstack/react-query";
import { maApi } from "@/api/maClient";
import type { ClientPortalDashboard } from "@/modules/ma/types/client_portal";

export function useClientDashboard(txnId: string) {
  return useQuery<ClientPortalDashboard>({
    queryKey: ["ma", "transactions", txnId, "client-portal", "dashboard"],
    queryFn: async () => {
      const { data } = await maApi.get(`/transactions/${txnId}/client-portal/dashboard`);
      return data;
    },
    enabled: !!txnId,
    staleTime: 30_000,
  });
}
