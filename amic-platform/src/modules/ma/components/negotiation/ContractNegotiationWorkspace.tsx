import { useState, useCallback, useMemo } from "react";
import { FileText } from "lucide-react";
import { Skeleton } from "@/components/ui/Skeleton";
import { useContracts } from "@/modules/ma/hooks/useContracts";
import {
  useContractMarkups,
  useCreateContractMarkup,
  useDeleteContractMarkup,
} from "@/modules/ma/hooks/useContractMarkups";
import {
  useNegotiationIssues,
  useCreateNegotiationIssue,
  useUpdateNegotiationIssue,
  useDeleteNegotiationIssue,
  useBatchUpdateDecision,
  useAIClauseSuggestion,
} from "@/modules/ma/hooks/useNegotiationIssues";
import {
  useNegotiationGantt,
  useMarkupComparison,
} from "@/modules/ma/hooks/useNegotiationWorkspace";
import type { IssueDecisionStatus } from "@/modules/ma/types/negotiation_issue";

import { ContractSelector } from "./ContractSelector";
import { NegotiationVersionTimeline } from "./NegotiationVersionTimeline";
import { MarkupComparisonPanel } from "./MarkupComparisonPanel";
import { DisputedClausesTracker } from "./DisputedClausesTracker";
import { AIInsightCard } from "./AIInsightCard";
import { ContractNegotiationGantt } from "./ContractNegotiationGantt";

interface ContractNegotiationWorkspaceProps {
  txnId: string;
  canWrite?: boolean;
}

export function ContractNegotiationWorkspace({
  txnId,
  canWrite = true,
}: ContractNegotiationWorkspaceProps) {
  // ── State ──────────────────────────────────────────────
  const [selectedContractId, setSelectedContractId] = useState<string | null>(
    null,
  );
  const [selectedVersions, setSelectedVersions] = useState<number[]>([]);
  const [aiInsightTarget, setAIInsightTarget] = useState<string | null>(null);

  // ── Data Hooks ─────────────────────────────────────────
  const { data: contracts = [], isLoading: contractsLoading } =
    useContracts(txnId);
  const { data: ganttData, isLoading: ganttLoading } =
    useNegotiationGantt(txnId);

  const selectedContract =
    contracts.find((c) => c.id === selectedContractId) ?? null;

  // 마크업
  const { data: markupData, isLoading: markupsLoading } = useContractMarkups(
    txnId,
    selectedContractId ?? "",
  );
  const markups = markupData?.items ?? [];

  const createMarkup = useCreateContractMarkup(txnId, selectedContractId ?? "");
  const deleteMarkup = useDeleteContractMarkup(txnId, selectedContractId ?? "");

  // 비교
  const versionA =
    selectedVersions.length >= 2 ? Math.min(...selectedVersions) : null;
  const versionB =
    selectedVersions.length >= 2 ? Math.max(...selectedVersions) : null;
  const { data: comparison, isLoading: comparisonLoading } =
    useMarkupComparison(txnId, selectedContractId, versionA, versionB);

  // 마크업 A / B 객체
  const markupA =
    versionA != null
      ? (markups.find((m) => m.version_number === versionA) ?? null)
      : null;
  const markupB =
    versionB != null
      ? (markups.find((m) => m.version_number === versionB) ?? null)
      : null;

  // 이견
  const { data: issueData, isLoading: issuesLoading } = useNegotiationIssues(
    txnId,
    {
      contractId: selectedContractId ?? undefined,
    },
  );
  const issues = useMemo(() => issueData?.items ?? [], [issueData?.items]);

  const createIssue = useCreateNegotiationIssue(txnId);
  const updateIssue = useUpdateNegotiationIssue(txnId);
  const deleteIssue = useDeleteNegotiationIssue(txnId);
  const batchDecision = useBatchUpdateDecision(txnId);
  const aiSuggest = useAIClauseSuggestion(txnId);

  // 계약별 이견 수 집계
  const issueCountByContract = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const issue of issues) {
      if (issue.contract_id) {
        counts[issue.contract_id] = (counts[issue.contract_id] || 0) + 1;
      }
    }
    return counts;
  }, [issues]);

  // ── Handlers ───────────────────────────────────────────
  const handleSelectContract = useCallback((id: string) => {
    setSelectedContractId(id);
    setSelectedVersions([]);
    setAIInsightTarget(null);
  }, []);

  const handleSelectVersion = useCallback((vn: number) => {
    setSelectedVersions((prev) => {
      if (prev.includes(vn)) return prev.filter((v) => v !== vn);
      if (prev.length >= 2) return [prev[1], vn];
      return [...prev, vn];
    });
  }, []);

  const handleUploadMarkup = useCallback(
    (formData: FormData) => {
      createMarkup.mutate(formData);
    },
    [createMarkup],
  );

  const handleDeleteMarkup = useCallback(
    (markupId: string) => {
      deleteMarkup.mutate(markupId);
    },
    [deleteMarkup],
  );

  const handleUpdateDecision = useCallback(
    (issueId: string, decision: IssueDecisionStatus) => {
      batchDecision.mutate([{ issue_id: issueId, decision_status: decision }]);
    },
    [batchDecision],
  );

  const handleRequestAIInsight = useCallback((clauseRef: string) => {
    setAIInsightTarget(clauseRef);
  }, []);

  // AI insight 관련 이슈 찾기
  const aiInsightIssue = aiInsightTarget
    ? issues.find(
        (i) =>
          i.clause_reference === aiInsightTarget || i.title === aiInsightTarget,
      )
    : null;

  // ── Loading ────────────────────────────────────────────
  if (contractsLoading) {
    return (
      <div className="space-y-4 p-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (contracts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <FileText className="mb-3 h-12 w-12 text-text-muted" />
        <p className="text-sm text-text-secondary">등록된 계약서가 없습니다.</p>
        <p className="mt-1 text-xs text-text-muted">
          계약 목록 탭에서 계약서를 먼저 등록하세요.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {/* 계약 선택기 */}
      <div className="px-4 pt-2">
        <ContractSelector
          contracts={contracts}
          selectedContractId={selectedContractId}
          onSelect={handleSelectContract}
          issueCountByContract={issueCountByContract}
        />
      </div>

      {/* 계약 선택 전: Gantt 차트만 표시 */}
      {!selectedContractId ? (
        <div className="px-4 pb-4">
          <h3 className="mb-3 text-sm font-heading font-semibold text-text-dark">
            전체 계약 협상 진행도
          </h3>
          <ContractNegotiationGantt
            data={ganttData ?? null}
            isLoading={ganttLoading}
            onContractClick={handleSelectContract}
            selectedContractId={null}
          />
        </div>
      ) : (
        <>
          {/* 3-패널 레이아웃 */}
          <div className="relative flex flex-1 gap-0 overflow-hidden border-t border-gray-border">
            {/* Left: 버전 타임라인 (~25%) */}
            <div className="w-1/4 min-w-[240px] border-r border-gray-border overflow-y-auto">
              {selectedContract && (
                <NegotiationVersionTimeline
                  txnId={txnId}
                  contractId={selectedContractId}
                  contract={selectedContract}
                  markups={markups}
                  selectedVersions={selectedVersions}
                  onSelectVersion={handleSelectVersion}
                  canWrite={canWrite}
                  onUpload={handleUploadMarkup}
                  onDelete={handleDeleteMarkup}
                  isUploading={createMarkup.isPending}
                />
              )}
              {markupsLoading && (
                <div className="space-y-3 p-4">
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </div>
              )}
            </div>

            {/* Center: 비교 뷰어 (~50%) */}
            <div className="relative flex-1 overflow-hidden">
              <MarkupComparisonPanel
                txnId={txnId}
                contractId={selectedContractId}
                comparison={comparison ?? null}
                markupA={markupA}
                markupB={markupB}
                isLoading={comparisonLoading && selectedVersions.length >= 2}
                onRequestAIInsight={handleRequestAIInsight}
              />

              {/* AI 인사이트 플로팅 카드 */}
              {aiInsightTarget && (
                <AIInsightCard
                  issueTitle={aiInsightIssue?.title ?? aiInsightTarget}
                  clauseReference={aiInsightIssue?.clause_reference ?? null}
                  aiSuggestion={aiInsightIssue?.ai_suggestion ?? null}
                  aiRationale={aiInsightIssue?.ai_suggestion_rationale ?? null}
                  isLoading={aiSuggest.isPending}
                  onClose={() => setAIInsightTarget(null)}
                />
              )}
            </div>

            {/* Right: 쟁점 트래커 (~25%) */}
            <div className="w-1/4 min-w-[260px] border-l border-gray-border overflow-hidden">
              <DisputedClausesTracker
                txnId={txnId}
                contractId={selectedContractId}
                issues={issues}
                isLoading={issuesLoading}
                canWrite={canWrite}
                onUpdateDecision={handleUpdateDecision}
                onUpdate={(issueId, body) =>
                  updateIssue.mutate({ issueId, body })
                }
                onCreate={(body) => createIssue.mutate(body)}
                onDelete={(issueId) => deleteIssue.mutate(issueId)}
                onAISuggest={(issueId) => aiSuggest.mutate(issueId)}
                isAISuggestPending={aiSuggest.isPending}
              />
            </div>
          </div>

          {/* 하단: Gantt 차트 */}
          <div className="border-t border-gray-border px-4 py-3">
            <ContractNegotiationGantt
              data={ganttData ?? null}
              isLoading={ganttLoading}
              onContractClick={handleSelectContract}
              selectedContractId={selectedContractId}
            />
          </div>
        </>
      )}
    </div>
  );
}
