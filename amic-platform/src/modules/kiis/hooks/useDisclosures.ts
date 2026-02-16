import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  DisclosureListResponse,
  DisclosureListParams,
  DisclosureSyncResponse,
} from "@/modules/kiis/types/disclosure";

const CORP_CODE_RE = /^\d{8}$/;

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
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useSyncDartDisclosures(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<
    DisclosureSyncResponse,
    Error,
    { bgn_de?: string; end_de?: string } | void
  >({
    mutationFn: async (vars) => {
      const { data } = await kiisApi.post(
        `/disclosures/${corpCode}/sync`,
        null,
        { params: vars ?? {} },
      );
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
  return useMutation<DisclosureSyncResponse, Error, void>({
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
