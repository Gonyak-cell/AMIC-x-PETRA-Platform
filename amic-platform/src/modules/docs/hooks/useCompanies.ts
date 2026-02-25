import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { imApi } from "@/api/imClient";
import type { Company } from "@/modules/docs/types/company";

const POLL_INTERVAL_MS = 3_000;

export function useCompany(corpCode: string) {
  return useQuery<Company>({
    queryKey: ["im", "companies", corpCode],
    queryFn: async () => {
      const { data } = await imApi.get(`/companies/${corpCode}`);
      return data;
    },
    enabled: !!corpCode,
    refetchInterval: (query): number | false => {
      const status = query.state.data?.fetch_status;
      return status && ["PENDING", "REFRESHING"].includes(status) ? POLL_INTERVAL_MS : false;
    },
  });
}

export function useFetchCompany() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (corpCode: string) => {
      const { data } = await imApi.post("/companies", { corp_code: corpCode });
      return data as Company;
    },
    onSuccess: (_data, corpCode) => {
      queryClient.invalidateQueries({
        queryKey: ["im", "companies", corpCode],
      });
    },
  });
}
