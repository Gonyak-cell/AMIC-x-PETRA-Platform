import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type { ReportVersion } from "@/types/report-version";

export function useReportVersions(dealId: string) {
  return useQuery<ReportVersion[]>({
    queryKey: ["report-versions", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/reports/versions`);
      return data;
    },
    enabled: !!dealId,
  });
}

export function useCreateReportVersion(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: { format: string; options: Record<string, boolean>; notes?: string }) => {
      const { data } = await api.post(`/deals/${dealId}/reports/versions`, body);
      return data as ReportVersion;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report-versions", dealId] });
    },
  });
}

export function useFinalizeReportVersion(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (version: number) => {
      const { data } = await api.put(`/deals/${dealId}/reports/versions/${version}/finalize`);
      return data as ReportVersion;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report-versions", dealId] });
    },
  });
}
