import { useState, useMemo, useEffect, useRef } from "react";
import {
  useParams,
  useNavigate,
  useSearchParams,
  Navigate,
} from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { ArrowLeft, ArrowRight, Play, Pause, Trash2 } from "lucide-react";
import {
  useTransaction,
  useDeleteTransaction,
  usePhaseCompletion,
  useAdvancePhase,
  useAutoAdvanceNotification,
  useChangeStatus,
  useEngagements,
  useBuyers,
  useTimeline,
} from "@/modules/ma/hooks/useTransactions";
import type { TransactionPhase } from "@/modules/ma/types/transaction";
import { useNdas } from "@/modules/ma/hooks/useNdas";
import { useBids } from "@/modules/ma/hooks/useBids";
import { useDDChecklist } from "@/modules/ma/hooks/useDDChecklist";
import { useContracts } from "@/modules/ma/hooks/useContracts";
import { useClosingChecklist } from "@/modules/ma/hooks/useClosing";
import { usePMITasks } from "@/modules/ma/hooks/usePMI";
import { useEarnoutMilestones } from "@/modules/ma/hooks/useEarnout";
import { useMarketingMaterials } from "@/modules/ma/hooks/useMarketingMaterials";
import { useFinancialModels } from "@/modules/ma/hooks/useFinancialModels";
import { useLegalDocuments } from "@/modules/docs/hooks/useLegalDocuments";
import PipelineFlow from "@/modules/ma/components/PipelineFlow";
import PhaseActionPanel from "@/modules/ma/components/PhaseActionPanel";
import MilestoneUploadPopover from "@/modules/ma/components/MilestoneUploadPopover";
import { useAttachments } from "@/modules/ma/hooks/useAttachments";
import {
  PHASE_CONFIG,
  PHASE_MILESTONES,
  PHASE_TAB_MAP,
  type UploadableMilestone,
  PHASE_VISIBLE_TABS,
  TRANSACTION_STATUS_VARIANT,
} from "@/modules/ma/constants";

import ClientPortalDashboard from "@/modules/ma/components/ClientPortalDashboard";
import MeetingLogsTab from "@/modules/ma/components/meetings/MeetingLogsTab";
import VdrTab from "@/modules/ma/components/vdr/VdrTab";
import RFIPanel from "@/modules/ma/components/rfi/RFIPanel";
import TransactionOverviewTab from "@/modules/ma/components/overview/TransactionOverviewTab";

import { Badge, Button, Card, PageHero, Spinner, Tabs } from "@/components/ui";
import type { TabItem } from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-dark-round.jpg";

// ── Tab components ──────────────────────────────────────
import {
  BuyersTab,
  ContractsTab,
  RisksTab,
  ComplianceTab,
  ClosingTab,
  NdasTab,
  BidsTab,
  DDChecklistTab,
  PMITab,
  EarnoutTab,
  MarketingMaterialsTab,
  ModelsTab,
  NotesApprovalsTab,
  TimelineTab,
  QualityTab,
  EngagementTab,
} from "@/modules/ma/tabs";

// ── 상수/유틸 ──────────────────────────────────────────
const VALID_PHASES = PHASE_CONFIG.map((p) => p.phase);

// ── 메인 컴포넌트 ──────────────────────────────────────
export default function TransactionWorkspacePage() {
  const { txnId, "*": splat } = useParams<{ txnId: string; "*": string }>();
  const navigate = useNavigate();
  const { canWrite, isClient } = useAuth();
  const id = txnId ?? "";

  // URL 기반 탭 결정
  const VALID_TABS = [
    "engagement",
    "buyers",
    "timeline",
    "marketing-materials",
    "models",
    "ndas",
    "vdr",
    "bids",
    "dd-checklist",
    "contracts",
    "closing",
    "pmi",
    "earnout",
    "risks",
    "compliance",
    "notes-approvals",
    "marketing-logs",
    "negotiation-logs",
    "rfi",
  ];
  const activeTab = VALID_TABS.includes(splat ?? "") ? splat! : "overview";

  // 파이프라인에서 클릭한 단계 (URL search param 기반, 리마운트 안전)
  const [searchParams, setSearchParams] = useSearchParams();
  const viewedPhase: TransactionPhase | null = (() => {
    const raw = searchParams.get("viewPhase");
    return raw && VALID_PHASES.includes(raw as TransactionPhase)
      ? (raw as TransactionPhase)
      : null;
  })();

  // 매수자 필터 (buyers 탭에서 클릭 시 전달)
  const buyerIdParam = searchParams.get("buyerId") || undefined;

  // URL 호환성: 삭제된 탭 → 통합 탭으로 리다이렉트 (viewPhase 보존)
  useEffect(() => {
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    if (splat === "ldd") {
      navigate(`/ma/transactions/${id}/dd-checklist${qs}`, { replace: true });
    }
    if (splat === "legal_docs") {
      navigate(`/ma/transactions/${id}/contracts${qs}`, { replace: true });
    }
  }, [splat, id, navigate, viewedPhase]);

  // 마일스톤 업로드 팝오버 상태
  const [activeMilestone, setActiveMilestone] =
    useState<UploadableMilestone | null>(null);

  // 데이터 로드 — Phase 1
  const { data: txn, isLoading } = useTransaction(id);
  const { data: phaseStatus } = usePhaseCompletion(id);
  useAutoAdvanceNotification(id);

  // 단계 전환 시 viewPhase 자동 정리 + 새 단계 기본 탭으로 이동
  const prevPhaseRef = useRef<string | null>(null);
  useEffect(() => {
    if (!txn?.phase) return;
    if (prevPhaseRef.current !== null && txn.phase !== prevPhaseRef.current) {
      const newPhase = txn.phase as TransactionPhase;
      const defaultTab = PHASE_TAB_MAP[newPhase];
      const tabPath = defaultTab === "overview" ? "" : `/${defaultTab}`;
      navigate(`/ma/transactions/${id}${tabPath}`, { replace: true });
    }
    prevPhaseRef.current = txn.phase;
  }, [txn?.phase, id, navigate]);

  // 초기 로드 시: URL에 탭 미지정 + ENGAGEMENT 아닌 단계 → 기본 탭으로 리다이렉트
  const initialRedirectDone = useRef(false);
  useEffect(() => {
    if (!txn?.phase) return;
    if (initialRedirectDone.current) return;
    if (splat) {
      initialRedirectDone.current = true;
      return;
    }
    if (viewedPhase) return;
    const phase = txn.phase as TransactionPhase;
    const defaultTab = PHASE_TAB_MAP[phase];
    if (defaultTab && defaultTab !== "overview") {
      initialRedirectDone.current = true;
      navigate(`/ma/transactions/${id}/${defaultTab}`, { replace: true });
    }
    initialRedirectDone.current = true;
  }, [txn?.phase, id, navigate, splat, viewedPhase]);

  // 마일스톤 문서 존재 여부 조회
  const { data: milestoneAttachments } = useAttachments(id, "MILESTONE");
  const milestoneDocuments = useMemo(() => {
    const map: Record<string, boolean> = {};
    for (const m of PHASE_MILESTONES) {
      if (m.milestoneKey) {
        map[m.milestoneKey] =
          milestoneAttachments?.items?.some(
            (a) => a.entity_id === m.milestoneKey,
          ) ?? false;
      }
    }
    return map;
  }, [milestoneAttachments]);
  const { data: engagements } = useEngagements(id);
  const { data: buyers } = useBuyers(id);
  const { data: timeline } = useTimeline(id);

  // 탭별 데이터 (배지 카운트 표시용만 — 탭 내부에서 자체 fetch)
  const { data: ndas } = useNdas(id, undefined, activeTab === "ndas");
  const { data: bids } = useBids(
    id,
    undefined,
    undefined,
    activeTab === "bids",
  );
  const { data: ddItems } = useDDChecklist(
    id,
    undefined,
    undefined,
    activeTab === "dd-checklist",
  );
  const { data: contracts } = useContracts(id, activeTab === "contracts");
  const { data: closingItems } = useClosingChecklist(
    id,
    undefined,
    activeTab === "closing",
  );
  const { data: pmiTasks } = usePMITasks(
    id,
    undefined,
    undefined,
    activeTab === "pmi",
  );
  const { data: earnoutMilestones } = useEarnoutMilestones(
    id,
    activeTab === "earnout",
  );
  const { data: marketingMaterials } = useMarketingMaterials(
    id,
    activeTab === "marketing-materials",
  );
  const { data: financialModels } = useFinancialModels(
    id,
    activeTab === "models",
  );

  // Legal docs (overview 서비스 연동에서 MOU 상태 확인용)
  const { data: legalDocs } = useLegalDocuments(
    id,
    activeTab === "contracts" || activeTab === "overview",
  );

  // Mutations — Transaction 삭제 (hero에서 사용)
  const deleteTxn = useDeleteTransaction();

  // Mutations — Phase 전환 (hero에서 사용)
  const advancePhase = useAdvancePhase(id);
  const changeStatus = useChangeStatus(id);

  // URL 기반 탭 전환 (viewPhase search param 유지하여 탭 필터링 보존)
  const handleTabChange = (tab: string) => {
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    if (tab === "overview") {
      navigate(`/ma/transactions/${id}${qs}`);
    } else {
      navigate(`/ma/transactions/${id}/${tab}${qs}`);
    }
  };

  const allTabs: TabItem[] = [
    { id: "overview", label: "Overview" },
    { id: "engagement", label: "수임", badge: engagements?.length },
    { id: "buyers", label: "매수자", badge: buyers?.length },
    { id: "timeline", label: "타임라인", badge: timeline?.total },
    {
      id: "marketing-materials",
      label: "마케팅 자료",
      badge: marketingMaterials?.length,
    },
    { id: "models", label: "재무모델", badge: financialModels?.length },
    { id: "ndas", label: "NDA", badge: ndas?.length },
    { id: "bids", label: "입찰", badge: bids?.length },
    { id: "dd-checklist", label: "DD/Checklist", badge: ddItems?.length },
    { id: "contracts", label: "계약/SPA", badge: contracts?.length },
    { id: "closing", label: "Closing", badge: closingItems?.length },
    { id: "pmi", label: "PMI", badge: pmiTasks?.length },
    { id: "earnout", label: "어닝아웃", badge: earnoutMilestones?.length },
    { id: "marketing-logs", label: "마케팅 로그" },
    { id: "negotiation-logs", label: "협상 로그" },
    { id: "vdr", label: "VDR" },
    { id: "rfi", label: "RFI" },
  ];

  // 탭 필터링: viewedPhase가 있으면 해당 단계 탭, 없으면 현재 단계 탭
  const effectivePhase = (viewedPhase ?? txn?.phase) as
    | TransactionPhase
    | undefined;
  const visibleTabIds = effectivePhase
    ? PHASE_VISIBLE_TABS[effectivePhase]
    : allTabs.map((t) => t.id);
  const tabs = isClient
    ? [{ id: "overview", label: "대시보드" }]
    : allTabs.filter((t) => visibleTabIds.includes(t.id));

  // 사이드바 Tools에서만 접근하는 탭 (파이프라인 탭 바에는 미표시)
  const SIDEBAR_ONLY_TABS = [
    "risks",
    "compliance",
    "notes-approvals",
    "timeline",
  ];

  // activeTab이 현재 보이는 탭에 없으면 PHASE_TAB_MAP 폴백
  const safeActiveTab =
    activeTab === "overview" ||
    visibleTabIds.includes(activeTab) ||
    SIDEBAR_ONLY_TABS.includes(activeTab)
      ? activeTab
      : viewedPhase
        ? (PHASE_TAB_MAP[viewedPhase] ?? "overview")
        : "overview";

  if (!txnId) return <Navigate to="/ma/transactions" replace />;
  if (isLoading) return <Spinner size="lg" />;
  if (!txn)
    return (
      <div className="text-center py-20 text-text-muted">
        거래를 찾을 수 없습니다
      </div>
    );

  const phaseLabel =
    PHASE_CONFIG.find((p) => p.phase === txn.phase)?.label ?? txn.phase;

  return (
    <div className="space-y-6">
      {/* Hero */}
      <PageHero
        title={txn.name}
        subtitle={`${txn.code_name} | ${txn.target_company_name} | ${txn.client_name}`}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ghost"
              icon={ArrowLeft}
              onClick={() => navigate("/ma/transactions")}
              className="!text-white/80 hover:!text-white hover:!bg-white/10"
            >
              목록
            </Button>
            {canWrite() && txn.status === "DRAFT" && (
              <Button
                icon={Play}
                onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
                loading={changeStatus.isPending}
              >
                시작
              </Button>
            )}
            {canWrite() && txn.status === "ACTIVE" && (
              <>
                {phaseStatus?.previous_phase && (
                  <Button
                    variant="ghost"
                    icon={ArrowLeft}
                    onClick={() =>
                      advancePhase.mutate(
                        { to_phase: phaseStatus.previous_phase! },
                        {
                          onSuccess: (updatedTxn) => {
                            const phase = updatedTxn.phase as TransactionPhase;
                            const defaultTab = PHASE_TAB_MAP[phase];
                            const tabPath =
                              defaultTab === "overview" ? "" : `/${defaultTab}`;
                            navigate(`/ma/transactions/${id}${tabPath}`, {
                              replace: true,
                            });
                          },
                        },
                      )
                    }
                    loading={advancePhase.isPending}
                    className="!text-white/80 hover:!text-white hover:!bg-white/10"
                  >
                    {PHASE_CONFIG.find(
                      (p) => p.phase === phaseStatus.previous_phase,
                    )?.label ?? "이전"}{" "}
                    단계로
                  </Button>
                )}
                {phaseStatus?.can_advance && phaseStatus.next_phase && (
                  <Button
                    icon={ArrowRight}
                    onClick={() =>
                      advancePhase.mutate(
                        { to_phase: phaseStatus.next_phase! },
                        {
                          onSuccess: (updatedTxn) => {
                            const phase = updatedTxn.phase as TransactionPhase;
                            const defaultTab = PHASE_TAB_MAP[phase];
                            const tabPath =
                              defaultTab === "overview" ? "" : `/${defaultTab}`;
                            navigate(`/ma/transactions/${id}${tabPath}`, {
                              replace: true,
                            });
                          },
                        },
                      )
                    }
                    loading={advancePhase.isPending}
                  >
                    {PHASE_CONFIG.find(
                      (p) => p.phase === phaseStatus.next_phase,
                    )?.label ?? "다음"}{" "}
                    단계로
                  </Button>
                )}
                <Button
                  variant="ghost"
                  icon={Pause}
                  onClick={() => changeStatus.mutate({ to_status: "ON_HOLD" })}
                  className="!text-white/80 hover:!text-white hover:!bg-white/10"
                >
                  보류
                </Button>
              </>
            )}
            {canWrite() && txn.status === "ON_HOLD" && (
              <Button
                icon={Play}
                onClick={() => changeStatus.mutate({ to_status: "ACTIVE" })}
              >
                재개
              </Button>
            )}
            {canWrite() && !isClient && (
              <Button
                variant="ghost"
                icon={Trash2}
                onClick={() => {
                  if (confirm("이 거래를 삭제하시겠습니까?")) {
                    deleteTxn.mutate(id, {
                      onSuccess: () => navigate("/ma/transactions"),
                    });
                  }
                }}
                loading={deleteTxn.isPending}
                className="!text-white/60 hover:!text-negative hover:!bg-white/10"
              >
                삭제
              </Button>
            )}
          </div>
        }
      />

      {/* Pipeline Flow */}
      <Card padding="md">
        <div className="flex items-center gap-3 mb-3">
          <Badge variant={TRANSACTION_STATUS_VARIANT[txn.status]}>
            {txn.status}
          </Badge>
          <span className="text-sm text-text-muted">
            현재: <strong>{phaseLabel}</strong>
          </span>
        </div>
        <div className="relative">
          <PipelineFlow
            currentPhase={txn.phase}
            onPhaseClick={(phase) => {
              setActiveMilestone(null);
              const currentIdx = PHASE_CONFIG.findIndex(
                (p) => p.phase === txn.phase,
              );
              const clickedIdx = PHASE_CONFIG.findIndex(
                (p) => p.phase === phase,
              );
              if (clickedIdx > currentIdx) return;
              if (phase === viewedPhase) return;
              const defaultTab = PHASE_TAB_MAP[phase];
              const tabPath = defaultTab === "overview" ? "" : `/${defaultTab}`;
              navigate(`/ma/transactions/${id}${tabPath}?viewPhase=${phase}`);
            }}
            onMilestoneClick={(milestone) =>
              setActiveMilestone((prev) =>
                prev?.milestoneKey === milestone.milestoneKey
                  ? null
                  : (milestone as UploadableMilestone),
              )
            }
            milestoneDocuments={milestoneDocuments}
          />
          {activeMilestone && (
            <MilestoneUploadPopover
              txnId={id}
              milestone={activeMilestone}
              existingFile={
                activeMilestone.milestoneKey
                  ? milestoneAttachments?.items?.find(
                      (a) => a.entity_id === activeMilestone.milestoneKey,
                    )
                  : undefined
              }
              onClose={() => setActiveMilestone(null)}
            />
          )}
        </div>
      </Card>

      {/* Phase Action Panel */}
      <PhaseActionPanel txnId={id} />

      {/* 탭 */}
      <Tabs
        tabs={tabs}
        activeTab={safeActiveTab}
        onTabChange={handleTabChange}
        variant="underline"
      />

      {/* ── Overview 탭 ───────────────────────────────── */}
      {safeActiveTab === "overview" && isClient && (
        <ClientPortalDashboard txnId={id} />
      )}
      {safeActiveTab === "overview" && !isClient && (
        <TransactionOverviewTab
          txnId={id}
          txn={txn}
          legalDocs={legalDocs}
          onTabChange={handleTabChange}
        />
      )}

      {/* ── Tab Components ──────────────────────────────── */}
      {safeActiveTab === "engagement" && (
        <EngagementTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "buyers" && (
        <BuyersTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "vdr" && <VdrTab txnId={id} />}
      {safeActiveTab === "rfi" && <RFIPanel txnId={id} />}
      {safeActiveTab === "ndas" && <NdasTab txnId={id} canWrite={canWrite()} />}
      {safeActiveTab === "bids" && <BidsTab txnId={id} canWrite={canWrite()} />}
      {safeActiveTab === "dd-checklist" && (
        <DDChecklistTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "contracts" && (
        <ContractsTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "closing" && (
        <ClosingTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "pmi" && <PMITab txnId={id} canWrite={canWrite()} />}
      {safeActiveTab === "earnout" && (
        <EarnoutTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "risks" && (
        <RisksTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "compliance" && (
        <ComplianceTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "marketing-materials" && (
        <MarketingMaterialsTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "models" && (
        <ModelsTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "ai-quality" && (
        <QualityTab txnId={id} canWrite={canWrite()} />
      )}
      {safeActiveTab === "timeline" && <TimelineTab txnId={id} />}
      {safeActiveTab === "marketing-logs" && (
        <MeetingLogsTab
          txnId={id}
          meetingPhase="MARKETING"
          buyerId={buyerIdParam}
          buyerName={
            buyerIdParam
              ? buyers?.find((b) => b.id === buyerIdParam)?.company_name
              : undefined
          }
          onClearBuyerFilter={() => {
            const next = new URLSearchParams(searchParams);
            next.delete("buyerId");
            setSearchParams(next, { replace: true });
          }}
        />
      )}
      {safeActiveTab === "negotiation-logs" && (
        <MeetingLogsTab txnId={id} meetingPhase="NEGOTIATION" />
      )}
      {safeActiveTab === "notes-approvals" && (
        <NotesApprovalsTab txnId={id} canWrite={canWrite()} />
      )}
    </div>
  );
}
