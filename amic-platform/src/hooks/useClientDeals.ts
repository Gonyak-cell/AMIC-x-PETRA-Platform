import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";

export interface ClientDealAssignment {
  id: string;
  transaction_id: string;
  transaction_name: string;
  codename: string;
  created_at: string;
}

/** CLIENT 사용자에게 배정된 딜 목록을 조회한다 (관리자용). */
export function useClientDeals(email: string | undefined) {
  return useQuery<ClientDealAssignment[]>({
    queryKey: ["admin", "client-deals", email],
    queryFn: async () => {
      const { data } = await maApi.get("/deal-clients/by-email", {
        params: { email },
      });
      return data;
    },
    enabled: !!email,
  });
}

/** Admin: 특정 거래에 CLIENT 사용자를 배정한다. */
export function useAdminAssignDeal(email: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      txnId: string;
      display_name: string;
      organization?: string;
    }) => {
      const { data } = await maApi.post(
        `/transactions/${params.txnId}/clients`,
        {
          email,
          display_name: params.display_name,
          organization: params.organization,
        },
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "client-deals", email] });
      toast.success("딜이 배정되었습니다.");
    },
    onError: () => {
      toast.error("딜 배정에 실패했습니다.");
    },
  });
}

/** Admin: CLIENT 사용자의 딜 배정을 해제한다. */
export function useAdminUnassignDeal(email: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: { txnId: string; clientId: string }) => {
      await maApi.delete(
        `/transactions/${params.txnId}/clients/${params.clientId}`,
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "client-deals", email] });
      toast.success("딜 배정이 해제되었습니다.");
    },
    onError: () => {
      toast.error("딜 배정 해제에 실패했습니다.");
    },
  });
}
