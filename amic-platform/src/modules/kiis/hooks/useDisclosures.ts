import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  DisclosureListResponse,
  DisclosureListParams,
  DisclosureSyncResponse,
} from "@/modules/kiis/types/disclosure";

export function useDisclosures(
  corpCode: string,
  params: DisclosureListParams = {},
) {
  return useQuery<DisclosureListResponse>({
    queryKey: ["kiis", "disclosures", corpCode, params],
    queryFn: async () => {
      const { data } = await kiisApi.get<DisclosureListResponse>(
        `/disclosures/${corpCode}`,
        { params },
      );
      return data;
    },
    enabled: !!corpCode,
  });
}

export function useSyncDartDisclosures(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<DisclosureSyncResponse>({
    mutationFn: async () => {
      const { data } = await kiisApi.post(`/disclosures/${corpCode}/sync`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "disclosures", corpCode],
      });
    },
  });
}

export function useSyncKofiaDisclosures(fundCode: string) {
  const queryClient = useQueryClient();
  return useMutation<DisclosureSyncResponse>({
    mutationFn: async () => {
      const { data } = await kiisApi.post(
        `/disclosures/kofia/${fundCode}/sync`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "disclosures"],
      });
    },
  });
}
