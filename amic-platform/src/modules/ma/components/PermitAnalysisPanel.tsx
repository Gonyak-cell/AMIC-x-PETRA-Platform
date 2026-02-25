import { useState } from "react";
import { ShieldCheck, RefreshCw, RotateCcw } from "lucide-react";
import { Badge, Button, Card, Spinner } from "@/components/ui";
import {
  usePermitAnalysis,
  usePermitRequirements,
  usePermitIndustries,
  useAnalyzePermits,
  useReanalyzePermits,
  useUpdatePermitRequirement,
} from "@/modules/ma/hooks/usePermits";
import type { ExistingPermit } from "@/modules/ma/types/permit";
import PermitInputForm from "./PermitInputForm";
import PermitRequirementTable from "./PermitRequirementTable";

interface PermitAnalysisPanelProps {
  txnId: string;
  canWrite?: boolean;
}

export default function PermitAnalysisPanel({
  txnId,
  canWrite = true,
}: PermitAnalysisPanelProps) {
  const { data: analysis, isLoading: analysisLoading } =
    usePermitAnalysis(txnId);
  const { data: requirements, isLoading: reqLoading } =
    usePermitRequirements(txnId);
  const { data: industries } = usePermitIndustries();
  const analyzeMut = useAnalyzePermits(txnId);
  const reanalyzeMut = useReanalyzePermits(txnId);
  const updateReqMut = useUpdatePermitRequirement(txnId);

  const [showInput, setShowInput] = useState(false);
  const [isReanalyze, setIsReanalyze] = useState(false);

  const isLoading = analysisLoading || reqLoading;
  const hasAnalysis = !!analysis;

  const handleAnalyze = (
    businessTypes: string[],
    existingPermits: ExistingPermit[],
  ) => {
    const body = {
      business_types: businessTypes,
      existing_permits: existingPermits,
    };
    if (isReanalyze) {
      reanalyzeMut.mutate(body, {
        onSuccess: () => {
          setShowInput(false);
          setIsReanalyze(false);
        },
      });
    } else {
      analyzeMut.mutate(body, {
        onSuccess: () => setShowInput(false),
      });
    }
  };

  const handleReanalyze = () => {
    setIsReanalyze(true);
    setShowInput(true);
  };

  if (isLoading) {
    return (
      <Card title="인허가 분석" headerBar>
        <div className="flex items-center justify-center py-12">
          <Spinner size="md" />
        </div>
      </Card>
    );
  }

  return (
    <Card
      title="인허가 분석"
      headerBar
      actions={
        hasAnalysis && canWrite ? (
          <Button
            size="sm"
            variant="secondary"
            onClick={handleReanalyze}
            disabled={reanalyzeMut.isPending}
          >
            <RotateCcw size={14} className="mr-1" />
            재분석
          </Button>
        ) : undefined
      }
    >
      {/* Analysis summary badges */}
      {hasAnalysis && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <Badge variant="success">
            {analysis.analysis_method === "KB_ONLY" ? "KB 기반" : analysis.analysis_method}
          </Badge>
          <Badge variant="neutral">{analysis.status}</Badge>
          {analysis.business_types?.map((bt) => (
            <Badge key={bt} variant="info">
              {bt}
            </Badge>
          ))}
          {requirements && (
            <span className="text-xs text-text-muted ml-2">
              {requirements.length}개 인허가 요건
            </span>
          )}
        </div>
      )}

      {/* No analysis yet — show start button or input form */}
      {!hasAnalysis && !showInput && (
        <div className="text-center py-8">
          <ShieldCheck
            size={40}
            className="mx-auto mb-3 text-text-muted/50"
          />
          <p className="text-sm text-text-muted mb-4">
            대상기업의 업종을 입력하면 필요한 인허가를 자동으로 분석합니다.
          </p>
          {canWrite && (
            <Button onClick={() => setShowInput(true)}>
              인허가 분석 시작
            </Button>
          )}
        </div>
      )}

      {/* Input form */}
      {showInput && industries && (
        <div className="mb-4 p-4 border border-gray-border rounded-dr-sm bg-bg-cool/30">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-text-body">
              {isReanalyze ? "인허가 재분석" : "인허가 분석 입력"}
            </h4>
            <button
              onClick={() => {
                setShowInput(false);
                setIsReanalyze(false);
              }}
              className="text-xs text-text-muted hover:text-text-body transition-colors"
            >
              취소
            </button>
          </div>
          <PermitInputForm
            industries={industries}
            onSubmit={handleAnalyze}
            isPending={analyzeMut.isPending || reanalyzeMut.isPending}
          />
        </div>
      )}

      {/* Results table */}
      {hasAnalysis && requirements && requirements.length > 0 && (
        <PermitRequirementTable
          requirements={requirements}
          onUpdateStatus={(reqId, body) =>
            updateReqMut.mutate({ reqId, body })
          }
          disabled={!canWrite}
        />
      )}

      {/* Analysis exists but no requirements */}
      {hasAnalysis && requirements && requirements.length === 0 && (
        <div className="text-center py-6">
          <RefreshCw size={24} className="mx-auto mb-2 text-text-muted/50" />
          <p className="text-sm text-text-muted">
            해당 업종에 대한 인허가 요건이 없습니다.
          </p>
          {canWrite && (
            <Button
              size="sm"
              variant="secondary"
              className="mt-2"
              onClick={handleReanalyze}
            >
              다른 업종으로 재분석
            </Button>
          )}
        </div>
      )}
    </Card>
  );
}
