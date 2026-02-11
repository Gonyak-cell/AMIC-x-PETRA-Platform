import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  Company,
  CompanyDetail,
  CompanyListParams,
  FinancialStatement,
  FinancialParams,
  Disclosure,
  PaginatedResponse,
} from "@/modules/kiis/types/company";
import type { ReputationScore } from "@/modules/kiis/types/analysis";

export function useCompanies(params: CompanyListParams = {}) {
  return useQuery<PaginatedResponse<Company>>({
    queryKey: ["kiis", "companies", params],
    queryFn: async () => {
      const { data } = await kiisApi.get("/companies", { params });
      return data;
    },
  });
}

export function useCompanyDetail(corpCode: string) {
  return useQuery<CompanyDetail>({
    queryKey: ["kiis", "companies", corpCode],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/companies/${corpCode}`);
      return data;
    },
    enabled: !!corpCode,
  });
}

export function useCompanyFinancials(
  corpCode: string,
  params: FinancialParams = {},
) {
  return useQuery<FinancialStatement[]>({
    queryKey: ["kiis", "companies", corpCode, "financials", params],
    queryFn: async () => {
      const { data } = await kiisApi.get(
        `/dart/companies/${corpCode}/financials`,
        { params },
      );
      return data;
    },
    enabled: !!corpCode,
  });
}

export function useCompanyDisclosures(corpCode: string) {
  return useQuery<Disclosure[]>({
    queryKey: ["kiis", "companies", corpCode, "disclosures"],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/disclosures/${corpCode}`);
      return data;
    },
    enabled: !!corpCode,
  });
}

export function useDisclosureLink(rceptNo: string) {
  return useQuery<{ viewer_url: string; pdf_url: string | null }>({
    queryKey: ["kiis", "disclosures", "link", rceptNo],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/disclosures/link/${rceptNo}`);
      return {
        viewer_url: data.dart_viewer_url,
        pdf_url: data.dart_pdf_url ?? null,
      };
    },
    enabled: !!rceptNo,
  });
}

export function useSyncDisclosures(corpCode: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await kiisApi.post(`/disclosures/${corpCode}/sync`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["kiis", "companies", corpCode, "disclosures"],
      });
    },
  });
}

export function useReputationScore(corpCode: string) {
  return useQuery<ReputationScore>({
    queryKey: ["kiis", "analysis", "reputation", corpCode],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/analysis/reputation/${corpCode}`);
      return data;
    },
    enabled: !!corpCode,
  });
}

export function useReputationHistory(corpCode: string) {
  return useQuery<ReputationScore[]>({
    queryKey: ["kiis", "analysis", "reputation", corpCode, "history"],
    queryFn: async () => {
      const { data } = await kiisApi.get(
        `/analysis/reputation/${corpCode}/history`,
      );
      return data;
    },
    enabled: !!corpCode,
  });
}
