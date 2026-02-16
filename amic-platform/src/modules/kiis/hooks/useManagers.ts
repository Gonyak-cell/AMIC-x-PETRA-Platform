import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  ManagerMovementListResponse,
  ManagerMovementParams,
  ManagerProfile,
  TrackResponse,
} from "@/modules/kiis/types/manager";

const CORP_CODE_RE = /^\d{8}$/;

export function useManagerMovements(params: ManagerMovementParams = {}) {
  return useQuery<ManagerMovementListResponse>({
    queryKey: ["kiis", "managers", "movements", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<ManagerMovementListResponse>(
        "/managers/movements",
        { params },
      );
      return data;
    },
  });
}

export function useManagerMovementsByCompany(
  corpCode: string,
  params: { page?: number; size?: number } = {},
) {
  return useQuery<ManagerMovementListResponse>({
    queryKey: ["kiis", "managers", "movements", "by-company", corpCode, params],
    queryFn: async () => {
      const { data } = await kiisApi.get<ManagerMovementListResponse>(
        `/managers/movements/by-company/${corpCode}`,
        { params },
      );
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useManagerProfile(managerName: string) {
  return useQuery<ManagerProfile>({
    queryKey: ["kiis", "managers", managerName, "profile"],
    queryFn: async () => {
      const { data } = await kiisApi.get<ManagerProfile>(
        `/managers/${encodeURIComponent(managerName)}/profile`,
      );
      return data;
    },
    enabled: !!managerName,
  });
}

export function useTrackManagers() {
  const queryClient = useQueryClient();
  return useMutation<TrackResponse, Error, void>({
    mutationFn: async () => {
      const { data } = await kiisApi.post("/managers/track");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "managers"],
      });
    },
  });
}
