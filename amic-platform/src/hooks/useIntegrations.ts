import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  EmailNotificationPreference,
  WebhookConfig,
  WebhookCreate,
  WebhookUpdate,
} from "@/types/integrations";

// ── Email Preferences ──

export function useEmailPreferences() {
  return useQuery<EmailNotificationPreference>({
    queryKey: ["settings", "email-preferences"],
    queryFn: async () => {
      try {
        const { data } = await api.get<EmailNotificationPreference>(
          "/settings/email-preferences",
        );
        return data;
      } catch {
        // Fallback: backend may not support this yet
        return {
          deal_updates: false,
          watchlist_alerts: false,
          im_completion: false,
          weekly_digest: false,
        };
      }
    },
  });
}

export function useUpdateEmailPreferences() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (prefs: EmailNotificationPreference) => {
      const { data } = await api.put("/settings/email-preferences", prefs);
      return data as EmailNotificationPreference;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["settings", "email-preferences"],
      });
    },
  });
}

// ── Webhooks ──

export function useWebhooks() {
  return useQuery<WebhookConfig[]>({
    queryKey: ["webhooks"],
    queryFn: async () => {
      try {
        const { data } = await api.get<WebhookConfig[]>("/webhooks");
        return data;
      } catch {
        return [];
      }
    },
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: WebhookCreate) => {
      const { data } = await api.post("/webhooks", body);
      return data as WebhookConfig;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, body }: { id: string; body: WebhookUpdate }) => {
      const { data } = await api.put(`/webhooks/${id}`, body);
      return data as WebhookConfig;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/webhooks/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhooks"] });
    },
  });
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/webhooks/${id}/test`);
      return data;
    },
  });
}
