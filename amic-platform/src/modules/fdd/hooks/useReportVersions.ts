import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import type {
  ReportVersion,
  ReportVersionCreate,
} from "@/modules/fdd/types/report-version";

export function useReportVersions(dealId: string) {
  return useQuery<ReportVersion[]>({
    queryKey: ["fdd", "report-versions", dealId],
    queryFn: async () => {
      const { data } = await api.get(`/deals/${dealId}/reports/versions`);
      return (data as ReportVersion[]).sort((a, b) => b.version - a.version);
    },
    enabled: !!dealId,
  });
}

export function useCreateReportVersion(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: ReportVersionCreate) => {
      const { data } = await api.post(`/deals/${dealId}/reports/versions`, body);
      return data as ReportVersion;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "report-versions", dealId] });
    },
    onError: (error: Error) => {
      console.error("useCreateReportVersion failed:", error);
    },
  });
}

export function useFinalizeReportVersion(dealId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ version, notes }: { version: number; notes?: string }) => {
      const { data } = await api.put(
        `/deals/${dealId}/reports/versions/${version}/finalize`,
        { notes: notes ?? null }
      );
      return data as ReportVersion;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "report-versions", dealId] });
    },
    onError: (error: Error) => {
      console.error("useFinalizeReportVersion failed:", error);
    },
  });
}
