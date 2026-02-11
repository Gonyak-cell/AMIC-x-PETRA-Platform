import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  EntityResolveRequest,
  EntityResolveResponse,
  AliasItem,
  AliasCreateRequest,
  AliasListResponse,
  AliasListParams,
} from "@/modules/kiis/types/entity";

export function useResolveEntity() {
  return useMutation<EntityResolveResponse, Error, EntityResolveRequest>({
    mutationFn: async (body) => {
      const { data } = await kiisApi.post("/entities/resolve", body);
      return data;
    },
  });
}

export function useAliases(params: AliasListParams = {}) {
  return useQuery<AliasListResponse>({
    queryKey: ["kiis", "entities", "aliases", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<AliasListResponse>(
        "/entities/aliases",
        { params },
      );
      return data;
    },
  });
}

export function useCreateAlias() {
  const queryClient = useQueryClient();
  return useMutation<AliasItem, Error, AliasCreateRequest>({
    mutationFn: async (body) => {
      const { data } = await kiisApi.post("/entities/aliases", body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "entities", "aliases"],
      });
    },
  });
}

export function useDeleteAlias() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (aliasId) => {
      await kiisApi.delete(`/entities/aliases/${aliasId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "entities", "aliases"],
      });
    },
  });
}
