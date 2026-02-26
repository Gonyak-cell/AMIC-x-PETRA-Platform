import { useQuery } from "@tanstack/react-query";
import { kiisApi } from "@/api/kiisClient";
import type {
  Company,
  CompanyDetail,
  CompanyListParams,
  CorpBasicInfo,
  FinancialParams,
  FinancialListResponseWithSource,
  FinancialSummary,
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
  return useQuery<FinancialListResponseWithSource>({
    queryKey: ["kiis", "companies", corpCode, "financials", params],
    queryFn: async () => {
      const { data } = await kiisApi.get<FinancialListResponseWithSource>(
        `/dart/companies/${corpCode}/financials`,
        { params },
      );
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode) && !!params.bsns_year,
  });
}

export function useFinancialSummary(corpCode: string, bizYear: string) {
  return useQuery<FinancialSummary>({
    queryKey: ["kiis", "companies", corpCode, "financial-summary", bizYear],
    queryFn: async () => {
      const { data } = await kiisApi.get<FinancialSummary>(
        `/dart/companies/${corpCode}/financial-summary`,
        { params: { bsns_year: bizYear } },
      );
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode) && !!bizYear,
  });
}

export function useCorpBasicInfo(corpCode: string) {
  return useQuery<CorpBasicInfo>({
    queryKey: ["kiis", "companies", corpCode, "basic-info"],
    queryFn: async () => {
      const { data } = await kiisApi.get<CorpBasicInfo>(
        `/dart/companies/${corpCode}/basic-info`,
      );
      return data;
    },
    enabled: CORP_CODE_RE.test(corpCode),
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
        `/analysis/reputation/${corpCode}/themes`,
        { params },
      );
      return data;
    },
    enabled: (options?.enabled ?? true) && CORP_CODE_RE.test(corpCode),
  });
}
