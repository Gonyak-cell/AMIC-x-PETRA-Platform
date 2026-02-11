import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import api from "@/api/client";
import type { NotificationItem } from "@/types/notification";

export function useNotifications() {
  const queryClient = useQueryClient();
  const endpointAvailableRef = useRef(true);

  const { data: notifications = [], isLoading } = useQuery<NotificationItem[]>({
    queryKey: ["notifications"],
    queryFn: async () => {
      try {
        const { data } = await api.get<NotificationItem[]>("/notifications");
        endpointAvailableRef.current = true;
        return data;
      } catch (error: unknown) {
        const status =
          error && typeof error === "object" && "response" in error
            ? (error as { response?: { status?: number } }).response?.status
            : undefined;
        if (status === 404 || status === 405) {
          endpointAvailableRef.current = false;
        }
        return [];
      }
    },
    staleTime: 30_000,
    refetchInterval: 30_000,
  });

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.is_read).length,
    [notifications],
  );

  const markAsRead = useMutation({
    mutationFn: async (id: string) => {
      await api.patch(`/notifications/${id}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllAsRead = useMutation({
    mutationFn: async () => {
      await api.patch("/notifications/read-all");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return {
    notifications,
    unreadCount,
    isLoading,
    endpointAvailable: endpointAvailableRef.current,
    markAsRead: markAsRead.mutate,
    markAllAsRead: markAllAsRead.mutate,
  };
}
