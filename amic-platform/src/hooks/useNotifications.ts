import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import axios from "axios";
import api from "@/api/client";
import type { NotificationItem } from "@/types/notification";

const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";

export function useNotifications() {
  const queryClient = useQueryClient();
  const [endpointAvailable, setEndpointAvailable] = useState(
    !DEV_LOCAL_AUTH_ENABLED,
  );

  const { data: notifications = [], isLoading } = useQuery<NotificationItem[]>({
    queryKey: ["notifications"],
    queryFn: async () => {
      if (DEV_LOCAL_AUTH_ENABLED) {
        return [];
      }

      try {
        const { data } = await api.get<NotificationItem[]>("/notifications");
        setEndpointAvailable(true);
        return data;
      } catch (error: unknown) {
        const status = axios.isAxiosError(error) ? error.response?.status : undefined;
        if (
          status === 404 ||
          status === 405 ||
          (DEV_LOCAL_AUTH_ENABLED && (status === 401 || status === 403))
        ) {
          setEndpointAvailable(false);
        }
        return [];
      }
    },
    enabled: !DEV_LOCAL_AUTH_ENABLED && endpointAvailable,
    staleTime: 30_000,
    refetchInterval: endpointAvailable ? 30_000 : false,
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
    endpointAvailable,
    markAsRead: markAsRead.mutate,
    markAllAsRead: markAllAsRead.mutate,
  };
}
