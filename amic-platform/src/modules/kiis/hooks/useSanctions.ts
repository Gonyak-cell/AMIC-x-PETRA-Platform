import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  ClassifiedSanctionItem,
  ClassifiedSanctionListResponse,
  SanctionSummaryResponse,
} from "@/modules/kiis/types/sanction";

export function useClassifiedSanctions(corpCode: string) {
  return useQuery<ClassifiedSanctionItem[]>({
    queryKey: ["kiis", "sanctions", "classified", corpCode],
    queryFn: async () => {
      const { data } = await kiisApi.get<ClassifiedSanctionListResponse>(
        `/sanctions/classified/${corpCode}`,
      );
      return data.items;
    },
    enabled: !!corpCode,
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
    enabled: !!corpCode,
  });
}

export function useClassifySanctions(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await kiisApi.post(
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
