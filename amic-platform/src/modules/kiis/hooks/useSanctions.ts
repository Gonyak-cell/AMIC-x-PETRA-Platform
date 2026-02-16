import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  ClassifiedSanctionListResponse,
  SanctionClassifyResponse,
  SanctionListParams,
  SanctionSummaryResponse,
} from "@/modules/kiis/types/sanction";

const CORP_CODE_RE = /^\d{8}$/;

export function useClassifiedSanctions(
  corpCode: string,
  params: SanctionListParams = {},
) {
  return useQuery<ClassifiedSanctionListResponse>({
    queryKey: ["kiis", "sanctions", "classified", corpCode, params],
    queryFn: async () => {
      const { data } = await kiisApi.get<ClassifiedSanctionListResponse>(
        `/sanctions/classified/${corpCode}`,
        { params },
      );
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useSanctionSummary(corpCode: string) {
  return useQuery<SanctionSummaryResponse>({
    queryKey: ["kiis", "sanctions", "classified", corpCode, "summary"],
    queryFn: async () => {
      const { data } = await kiisApi.get<SanctionSummaryResponse>(
        `/sanctions/classified/${corpCode}/summary`,
      );
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useClassifySanctions(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<SanctionClassifyResponse>({
    mutationFn: async () => {
      const { data } = await kiisApi.post<SanctionClassifyResponse>(
        `/sanctions/classify/${corpCode}`,
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "sanctions", "classified", corpCode],
      });
    },
  });
}
