import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type { ReputationScore } from "@/modules/kiis/types/analysis";
import type { PaginatedResponse } from "@/modules/kiis/types/company";

export function useReputationList(
  params: { page?: number; size?: number } = {},
) {
  return useQuery<PaginatedResponse<ReputationScore>>({
    queryKey: ["kiis", "analysis", "reputation", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/analysis/reputation", { params });
      return data;
    },
  });
}

export function useCalculateReputation(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await kiisApi.post(
        `/analysis/reputation/${corpCode}/calculate`,
      );
      return data as ReputationScore;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "analysis", "reputation"],
      });
    },
  });
}
