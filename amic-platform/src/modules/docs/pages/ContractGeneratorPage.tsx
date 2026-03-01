/** AI 계약서 자동 생성 페이지 */

import { useSearchParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import ContractGeneratorWizard from "@/modules/docs/components/ContractGeneratorWizard";

export default function ContractGeneratorPage() {
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
    <main className="mx-auto max-w-4xl px-4 py-6">
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
            AI 계약서 생성
          </h1>
          <p className="text-xs text-text-secondary">
            템플릿 기반 자동 계약서 조립 + AI 다듬기 + DOCX 다운로드
          </p>
        </div>
      </div>

      {/* 위저드 */}
      <ContractGeneratorWizard txnId={txnId} />
    </main>
  );
}
