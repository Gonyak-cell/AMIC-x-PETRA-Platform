import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";

export type TableStyleTheme = "DEFAULT" | "MODERN_GREEN";

export interface PlatformSettings {
  site_name: string;
  contact_email: string | null;
  table_style: TableStyleTheme;
}

export interface PlatformSettingsUpdate {
  site_name?: string;
  contact_email?: string | null;
  legal_terms?: string | null;
  privacy_policy?: string | null;
  table_style?: TableStyleTheme;
}

const QUERY_KEY = ["platform-settings"] as const;

export function usePlatformSettings() {
  return useQuery<PlatformSettings>({
    queryKey: QUERY_KEY,
    queryFn: async () => {
      const { data } = await maApi.get<PlatformSettings>("/settings");
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdatePlatformSettings() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body: PlatformSettingsUpdate) => {
      const { data } = await maApi.put<PlatformSettings>(
        "/admin/settings",
        body,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("설정이 저장되었습니다.");
    },
    onError: () => {
      toast.error("설정 저장에 실패했습니다.");
    },
  });
}
