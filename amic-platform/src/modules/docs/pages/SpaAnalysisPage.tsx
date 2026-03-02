/** SPA 계약서 LLM 역분석 페이지 */

import { useSearchParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import SpaAnalysisWizard from "@/modules/docs/components/SpaAnalysisWizard";

export default function SpaAnalysisPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const txnId = searchParams.get("txn_id") ?? "";

  if (!txnId) {
    return (
      <div
        className="flex h-40 items-center justify-center text-sm text-text-secondary"
        role="alert"
      >
        거래 ID가 지정되지 않았습니다.
      </div>
    );
  }

  return (
    <section
      aria-label="SPA 계약서 역분석"
      className="mx-auto max-w-4xl px-4 py-6"
    >
      {/* 헤더 */}
      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="rounded-lg p-1.5 text-text-tertiary hover:bg-white-elevated hover:text-text-primary"
          title="뒤로 가기"
          aria-label="이전 페이지로 돌아가기"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-lg font-semibold text-text-primary">
            SPA 계약서 역분석
          </h1>
          <p className="text-xs text-text-secondary">
            SPA 원문을 AI로 분석하여 재사용 가능한 계약서 템플릿을 자동
            생성합니다
          </p>
        </div>
      </div>

      {/* 위저드 */}
      <SpaAnalysisWizard txnId={txnId} />
    </section>
  );
}
