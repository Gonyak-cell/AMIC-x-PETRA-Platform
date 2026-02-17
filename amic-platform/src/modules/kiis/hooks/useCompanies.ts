import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  Company,
  CompanyDetail,
  CompanyListParams,
  FinancialStatement,
  FinancialParams,
  FinancialListResponse,
  PaginatedResponse,
} from "@/modules/kiis/types/company";
import type {
  ReputationScore,
  ReputationHistoryItem,
  ReputationHistoryResponse,
  QualitativeReputationResponse,
} from "@/modules/kiis/types/analysis";

const CORP_CODE_RE = /^\d{8}$/;

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
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useCompanyFinancials(
  corpCode: string,
  params: FinancialParams,
) {
  return useQuery<FinancialStatement[]>({
    queryKey: ["kiis", "companies", corpCode, "financials", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<FinancialListResponse>(
        `/dart/companies/${corpCode}/financials`,
        { params },
      );
      return data.items;
    },
    enabled: CORP_CODE_RE.test(corpCode) && !!params.bsns_year,
  });
}

export function useReputationScore(corpCode: string) {
  return useQuery<ReputationScore>({
    queryKey: ["kiis", "analysis", "reputation", corpCode],
    queryFn: async () => {
      const { data } = await kiisApi.get(`/analysis/reputation/${corpCode}`);
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useReputationHistory(
  corpCode: string,
  params: { limit?: number } = {},
) {
  return useQuery<ReputationHistoryItem[]>({
    queryKey: ["kiis", "analysis", "reputation", corpCode, "history", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<ReputationHistoryResponse>(
        `/analysis/reputation/${corpCode}/history`,
        { params },
      );
      return data.items;
    },
    enabled: CORP_CODE_RE.test(corpCode),
  });
}

export function useQualitativeReputation(
  corpCode: string,
  params: { months?: number } = {},
  options?: { enabled?: boolean },
) {
  return useQuery<QualitativeReputationResponse>({
    queryKey: ["kiis", "analysis", "reputation", corpCode, "qualitative", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<QualitativeReputationResponse>(
        `/analysis/reputation/${corpCode}/qualitative`,
        { params },
      );
      return data;
    },
    enabled: (options?.enabled ?? true) && CORP_CODE_RE.test(corpCode),
  });
}
