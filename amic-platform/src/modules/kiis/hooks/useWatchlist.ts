import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  WatchlistItem,
  Alert,
  WatchlistAddRequest,
  UnreadCount,
} from "@/modules/kiis/types/watchlist";

export function useWatchlist() {
  return useQuery<WatchlistItem[]>({
    queryKey: ["kiis", "watchlist"],
    queryFn: async () => {
      const { data } = await kiisApi.get("/watchlist");
      return data;
    },
  });
}

export function useAddToWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: WatchlistAddRequest) => {
      const { data } = await kiisApi.post("/watchlist", body);
      return data as WatchlistItem;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "watchlist"] });
    },
  });
}

export function useRemoveFromWatchlist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (companyId: string) => {
      await kiisApi.delete(`/watchlist/${companyId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kiis", "watchlist"] });
    },
  });
}

export function useAlerts() {
  return useQuery<Alert[]>({
    queryKey: ["kiis", "alerts"],
    queryFn: async () => {
      const { data } = await kiisApi.get("/alerts");
      return data;
    },
  });
}

export function useMarkAlertRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (alertId: string) => {
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
