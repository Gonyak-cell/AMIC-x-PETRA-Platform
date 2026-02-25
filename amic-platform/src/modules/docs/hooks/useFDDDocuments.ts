import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { fddApi } from "@/api/fddClient";
import type { Deal, DealCreate } from "@/modules/fdd/types/deal";
import type { ReportVersion, ReportVersionCreate } from "@/modules/fdd/types/report-version";
import { isIndustryId } from "@/types/industry";

export interface FDDDocumentCreate {
  deal_name: string;
  target_company_name: string;
  industry?: string;
  include_qoe?: boolean;
  include_nwc?: boolean;
  include_debt?: boolean;
  file_format?: "pptx" | "docx";
}

export interface FDDDocumentResult {
  deal: Deal;
  version: ReportVersion;
}

export interface DealListResponse {
  items: Deal[];
  total: number;
  skip: number;
  limit: number;
}

/** Deal 생성 + 보고서 버전 생성을 한 번에 처리하는 mutation */
export function useCreateFDDDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (body: FDDDocumentCreate): Promise<FDDDocumentResult> => {
      const dealBody: DealCreate = {
        name: body.deal_name,
        target_company_name: body.target_company_name,
        industry:
          body.industry && isIndustryId(body.industry) ? body.industry : undefined,
        scope_qoe: body.include_qoe ?? true,
        scope_nwc: body.include_nwc ?? true,
        scope_debt: body.include_debt ?? true,
      };
      const { data: deal } = await fddApi.post<Deal>("/deals", dealBody);

      const versionBody: ReportVersionCreate = {
        file_format: body.file_format ?? "pptx",
        include_qoe: body.include_qoe ?? true,
        include_nwc: body.include_nwc ?? true,
        include_debt: body.include_debt ?? true,
        include_issues: true,
      };
      let version: ReportVersion;
      try {
        const { data } = await fddApi.post<ReportVersion>(
          `/deals/${deal.id}/reports/versions`,
          versionBody,
        );
        version = data;
      } catch (versionError) {
        console.error(
          "[useFDDDocuments] 보고서 버전 생성 실패, deal.id=",
          deal.id,
          versionError,
        );
        throw new Error(
          `FDD 버전 생성에 실패했습니다 (deal.id: ${deal.id}). 관리자에게 문의해 주세요.`,
        );
      }
      return { deal, version };
    },
    onSuccess: ({ deal }) => {
      queryClient.invalidateQueries({ queryKey: ["fdd", "deals"] });
      toast.success(`FDD '${deal.name}'이 생성되었습니다`);
    },
    onError: (error: Error) => {
      console.error("[useFDDDocuments] FDD 보고서 생성 실패:", error);
      toast.error(
        error.message.includes("deal.id")
          ? error.message
          : "FDD 보고서 생성에 실패했습니다. 잠시 후 다시 시도해 주세요.",
      );
    },
  });
}

/** FDD Deal 목록 조회 (Deal Documents Studio 홈 화면용) */
export function useFDDDeals(params?: { skip?: number; limit?: number }) {
  return useQuery<DealListResponse>({
    queryKey: ["fdd", "deals", params],
    queryFn: async () => {
      const { data } = await fddApi.get<DealListResponse>("/deals", { params });
      return data;
    },
  });
}
