/** SPA 계약서 LLM 역분석 API 훅 */

import { useMutation } from "@tanstack/react-query";
import type { AxiosError } from "axios";
import { toast } from "sonner";
import { maApi } from "@/api/maClient";
import { extractApiError } from "@/api/errors";
import type {
  SpaStep1Request,
  SpaStep1Response,
  SpaStep2Request,
  SpaStep2Response,
  SpaStep3Request,
  SpaStep3Response,
} from "@/modules/docs/types/spa_analysis";

/** Axios 에러에서 HTTP 상태 코드를 추출한다. */
function getStatusCode(err: unknown): number | undefined {
  return (err as AxiosError)?.response?.status;
}

const BASE = (txnId: string) => `/transactions/${txnId}/spa-analysis`;

// ── Step 1: 변수 추출 ───────────────────────────────────────────────────────

export function useSpaStep1(txnId: string) {
  return useMutation<SpaStep1Response, Error, SpaStep1Request>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(`${BASE(txnId)}/step1-variables`, body);
      return data as SpaStep1Response;
    },
    onSuccess: (result) => {
      toast.success(
        `${result.variables.length}개 변수 추출 완료 (${result.discovered_booleans.length}개 특수 조항 발견)`,
      );
    },
    onError: (err) => {
      const code = getStatusCode(err);
      if (code === 429) {
        toast.error("요청이 너무 많습니다. 1분 후 다시 시도하세요.");
      } else if (code === 503) {
        toast.error("LLM 서비스를 사용할 수 없습니다. 나중에 다시 시도하세요.");
      } else {
        toast.error(extractApiError(err, "SPA 분석에 실패했습니다."));
      }
    },
  });
}

// ── Step 2: 조항 분해 ───────────────────────────────────────────────────────

export function useSpaStep2(txnId: string) {
  return useMutation<SpaStep2Response, Error, SpaStep2Request>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(`${BASE(txnId)}/step2-clauses`, body);
      return data as SpaStep2Response;
    },
    onSuccess: (result) => {
      toast.success(`${result.clauses.length}개 조항 분해 완료`);
    },
    onError: (err) => {
      const code = getStatusCode(err);
      if (code === 429) {
        toast.error("요청이 너무 많습니다. 1분 후 다시 시도하세요.");
      } else if (code === 422) {
        toast.error(
          extractApiError(
            err,
            "세션이 만료되었습니다. Step 1부터 다시 시작하세요.",
          ),
        );
      } else {
        toast.error(extractApiError(err, "조항 분해에 실패했습니다."));
      }
    },
  });
}

// ── Step 3: 템플릿 생성 ─────────────────────────────────────────────────────

export function useSpaStep3(txnId: string) {
  return useMutation<SpaStep3Response, Error, SpaStep3Request>({
    mutationFn: async (body) => {
      const { data } = await maApi.post(`${BASE(txnId)}/step3-seed`, body);
      return data as SpaStep3Response;
    },
    onSuccess: (result) => {
      toast.success(result.message);
    },
    onError: (err) => {
      toast.error(extractApiError(err, "템플릿 생성에 실패했습니다."));
    },
  });
}
