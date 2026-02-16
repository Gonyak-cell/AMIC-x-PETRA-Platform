import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  ReputationScore,
  ReputationListResponse,
  StatusTag,
} from "@/modules/kiis/types/analysis";

export function useReputationList(
  params: { status_tag?: StatusTag; page?: number; size?: number } = {},
) {
  return useQuery<ReputationListResponse>({
    queryKey: ["kiis", "analysis", "reputation", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/analysis/reputation", { params });
      return data;
    },
  });
}

export function useCalculateReputation(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation<
    ReputationScore,
    Error,
    { months?: number; save_history?: boolean } | void
  >({
    mutationFn: async (vars) => {
      const { data } = await kiisApi.post(
        `/analysis/reputation/${corpCode}/calculate`,
        vars ?? undefined,
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
