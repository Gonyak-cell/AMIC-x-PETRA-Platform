import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { imApi } from "@/api/imClient";
import type { Company } from "@/modules/im/types/company";

export function useCompany(corpCode: string) {
  return useQuery<Company>({
    queryKey: ["im", "companies", corpCode],
    queryFn: async () => {
      const { data } = await imApi.get(`/companies/${corpCode}`);
      return data;
    },
    enabled: !!corpCode,
    refetchInterval: (query) => {
      const status = query.state.data?.fetch_status;
      return status && ["PENDING", "COLLECTING"].includes(status) ? 3000 : false;
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
