import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  WatchlistItem,
  WatchlistListResponse,
  AlertListResponse,
  WatchlistAddRequest,
  UnreadCount,
} from "@/modules/kiis/types/watchlist";

export function useWatchlist() {
  return useQuery<WatchlistListResponse>({
    queryKey: ["kiis", "watchlist"],
    queryFn: async () => {
      const { data } = await kiisApi.get<WatchlistListResponse>("/watchlist");
      return data;
    },
  });
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient();
  return useMutation<WatchlistItem, Error, WatchlistAddRequest>({
    mutationFn: async (body) => {
      const { data } = await kiisApi.post("/watchlist", body);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "watchlist"] });
      queryClient.invalidateQueries({ queryKey: ["kiis", "alerts"] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: async (companyId) => {
      await kiisApi.delete(`/watchlist/${companyId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "watchlist"] });
      // Prefix-match invalidates both alerts list and unread-count
      queryClient.invalidateQueries({ queryKey: ["kiis", "alerts"] });
    },
  });
}

export function useAlerts(params: { page?: number; size?: number } = {}) {
  return useQuery<AlertListResponse>({
    queryKey: ["kiis", "alerts", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<AlertListResponse>("/alerts", {
        params,
      });
      return data;
    },
  });
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (alertId: number) => {
      await kiisApi.post(`/alerts/${alertId}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "alerts"] });
      queryClient.invalidateQueries({
        queryKey: ["kiis", "alerts", "unread-count"],
      });
    },
  });
}

export function useUnreadAlertCount() {
  return useQuery<UnreadCount>({
    queryKey: ["kiis", "alerts", "unread-count"],
    queryFn: async () => {
      const { data } = await kiisApi.get("/alerts/unread-count");
      return data;
    },
  });
}
