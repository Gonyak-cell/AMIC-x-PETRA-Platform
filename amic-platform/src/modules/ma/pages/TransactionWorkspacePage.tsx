import { useState, useMemo, useEffect } from "react";
import {
  useParams,
  useNavigate,
  useSearchParams,
  Navigate,
} from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  ArrowLeft,
  ArrowRight,
  Play,
  Pause,
  FileText,
  AlertTriangle,
  Plus,
  Trash2,
  Scale,
  BarChart2,
  BookOpen,
  Building2,
  FileSignature,
  ExternalLink,
  CircleCheck,
  CircleDashed,
  ChevronRight,
  ChevronDown,
  Handshake,
  DollarSign,
} from "lucide-react";
import { cn } from "@/lib/cn";

import {
  useTransaction,
  useUpdateTransaction,
  useDeleteTransaction,
  usePhaseCompletion,
  useAdvancePhase,
  useAutoAdvanceNotification,
  useChangeStatus,
  useEngagements,
  useConflictCheck,
  useBuyers,
  useTimeline,
} from "@/modules/ma/hooks/useTransactions";
import type {
  TransactionPhase,
  TransactionSide,
  Currency,
  DealStructure,
  InvestmentType,
  SaleProcess,
  ControlTransfer,
  ValuationBasis,
  CrossBorder,
} from "@/modules/ma/types/transaction";
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
import CompanyInfoCard from "@/modules/ma/components/overview/CompanyInfoCard";
import EngagementDocUpload from "@/modules/ma/components/overview/EngagementDocUpload";
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
  TRANSACTION_SIDE_OPTIONS,
  DEAL_STRUCTURE_OPTIONS,
  INVESTMENT_TYPE_OPTIONS,
  CURRENCY_OPTIONS,
  SALE_PROCESS_OPTIONS,
  CONTROL_TRANSFER_OPTIONS,
  VALUATION_BASIS_OPTIONS,
  CROSS_BORDER_OPTIONS,
  TARGET_BUYER_TYPE_OPTIONS,
  TEAM_MEMBERS,
  TRANSACTION_STATUS_VARIANT,
} from "@/modules/ma/constants";

import ClientPortalDashboard from "@/modules/ma/components/ClientPortalDashboard";
import MeetingLogsTab from "@/modules/ma/components/meetings/MeetingLogsTab";
import VdrTab from "@/modules/ma/components/vdr/VdrTab";
import RFIPanel from "@/modules/ma/components/rfi/RFIPanel";

import {
  Badge,
  Button,
  Card,
  InlineSelect,
  InlineCombobox,
  INLINE_INPUT_CLS,
  PageHero,
  Spinner,
  Tabs,
} from "@/components/ui";
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

import { formatISODate as formatDate } from "@/modules/ma/utils/format";

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
  const { data: conflicts } = useConflictCheck(id);
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

  // Mutations — Transaction 기본 정보 (overview에서 사용)
  const updateTxn = useUpdateTransaction(id);
  const deleteTxn = useDeleteTransaction();

  // Mutations — Phase 전환 (hero에서 사용)
  const advancePhase = useAdvancePhase(id);
  const changeStatus = useChangeStatus(id);

  // 서비스 연동 아코디언 상태 (overview)
  const PHASE_TO_SVC_GROUP: Record<string, string> = {
    ENGAGEMENT: "PREPARATION",
    PREPARATION: "PREPARATION",
    MARKETING: "MARKETING",
    BIDDING: "BIDDING",
    MOU_SIGNED: "MAIN_DUE_DILIGENCE",
    MAIN_DUE_DILIGENCE: "MAIN_DUE_DILIGENCE",
    NEGOTIATION: "NEGOTIATION",
    CLOSING: "CLOSING",
    POST_CLOSING: "CLOSING",
  };
  const [openSvcGroups, setOpenSvcGroups] = useState<Set<string>>(
    () => new Set(["PREPARATION"]),
  );
  useEffect(() => {
    if (txn?.phase) {
      const g = PHASE_TO_SVC_GROUP[txn.phase] ?? "PREPARATION";
      setOpenSvcGroups(new Set([g]));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [txn?.phase]);
  const toggleSvcGroup = (key: string) =>
    setOpenSvcGroups((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

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
                      advancePhase.mutate({
                        to_phase: phaseStatus.previous_phase!,
                      })
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
                  <div className="flex items-center gap-2">
                    {phaseStatus.has_warnings && (
                      <span className="flex items-center gap-1 text-xs text-caution">
                        <AlertTriangle size={12} />
                        권장 항목 미완료
                      </span>
                    )}
                    <Button
                      icon={ArrowRight}
                      onClick={() =>
                        advancePhase.mutate({
                          to_phase: phaseStatus.next_phase!,
                        })
                      }
                      loading={advancePhase.isPending}
                    >
                      {PHASE_CONFIG.find(
                        (p) => p.phase === phaseStatus.next_phase,
                      )?.label ?? "다음"}{" "}
                      단계로
                    </Button>
                  </div>
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

      {/* 이해충돌 경고 */}
      {conflicts?.has_conflicts && (
        <Card padding="md" variant="accent-left">
          <div className="flex items-center gap-2 text-negative font-medium mb-2">
            <AlertTriangle size={16} />
            이해충돌 감지
          </div>
          {conflicts.conflicts.map((c, i) => (
            <div key={i} className="text-sm text-text-secondary">
              <Badge
                variant={c.severity === "CRITICAL" ? "error" : "warning"}
                pill
              >
                {c.severity}
              </Badge>{" "}
              {c.message}
            </div>
          ))}
        </Card>
      )}

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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 거래 정보 — 2-Column */}
          <Card title="거래 정보" headerBar className="lg:col-span-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-0 p-1 md:items-start">
              {/* ── 좌측 열: 기본 딜 정보 ── */}
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm items-center">
                <dt className="text-text-muted">거래명</dt>
                <dd>
                  <input
                    key={`name-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-64")}
                    defaultValue={txn.name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.name) updateTxn.mutate({ name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">코드네임</dt>
                <dd>
                  <input
                    key={`codename-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-40 font-mono")}
                    defaultValue={txn.code_name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.code_name)
                        updateTxn.mutate({ code_name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">대상기업</dt>
                <dd>
                  <input
                    key={`target-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-48")}
                    defaultValue={txn.target_company_name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.target_company_name)
                        updateTxn.mutate({ target_company_name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">클라이언트</dt>
                <dd>
                  <input
                    key={`client-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-48")}
                    defaultValue={txn.client_name}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v && v !== txn.client_name)
                        updateTxn.mutate({ client_name: v });
                    }}
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">유형</dt>
                <dd>
                  <InlineSelect
                    options={TRANSACTION_SIDE_OPTIONS.filter(
                      (o) => o.value !== "",
                    )}
                    value={txn.side}
                    onChange={(v) =>
                      updateTxn.mutate({ side: v as TransactionSide })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">딜 구조</dt>
                <dd>
                  <InlineSelect
                    options={DEAL_STRUCTURE_OPTIONS}
                    value={txn.deal_structure ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        deal_structure: (v || null) as DealStructure | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">투자 유형</dt>
                <dd>
                  <InlineSelect
                    options={INVESTMENT_TYPE_OPTIONS}
                    value={txn.investment_type ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        investment_type: (v || null) as InvestmentType | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">산업</dt>
                <dd>
                  <input
                    key={`industry-${txn.updated_at}`}
                    type="text"
                    className={cn(INLINE_INPUT_CLS, "w-40")}
                    defaultValue={txn.industry ?? ""}
                    onBlur={(e) => {
                      const v = e.target.value.trim();
                      if (v !== (txn.industry ?? ""))
                        updateTxn.mutate({ industry: v || null });
                    }}
                    disabled={!canWrite()}
                    placeholder="-"
                  />
                </dd>
                <dt className="text-text-muted">예상 금액</dt>
                <dd className="flex items-center gap-1">
                  <input
                    key={`deal-val-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-32 text-right font-mono",
                    )}
                    defaultValue={txn.estimated_deal_value ?? ""}
                    onBlur={(e) => {
                      const v = e.target.value || null;
                      if (v !== txn.estimated_deal_value)
                        updateTxn.mutate({ estimated_deal_value: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="-"
                  />
                  <InlineSelect
                    options={CURRENCY_OPTIONS}
                    value={txn.currency}
                    onChange={(v) =>
                      updateTxn.mutate({ currency: v as Currency })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">목표 종결일</dt>
                <dd>
                  <input
                    type="date"
                    className={cn(INLINE_INPUT_CLS, "w-36")}
                    value={txn.target_close_date ?? ""}
                    onChange={(e) =>
                      updateTxn.mutate({
                        target_close_date: e.target.value || null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">리드 어드바이저</dt>
                <dd>
                  <InlineCombobox
                    options={TEAM_MEMBERS.map((m) => ({
                      value: m.email,
                      label: `${m.name} (${m.title})`,
                      description: m.email,
                    }))}
                    value={txn.lead_advisor_email}
                    onChange={(v) => {
                      if (v && v !== txn.lead_advisor_email)
                        updateTxn.mutate({ lead_advisor_email: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="담당자 검색..."
                    clearable={false}
                  />
                </dd>
                <dt className="text-text-muted">딜 캡틴</dt>
                <dd>
                  <InlineCombobox
                    options={TEAM_MEMBERS.map((m) => ({
                      value: m.email,
                      label: `${m.name} (${m.title})`,
                      description: m.email,
                    }))}
                    value={txn.deal_captain_email ?? ""}
                    onChange={(v) => {
                      if (v !== (txn.deal_captain_email ?? ""))
                        updateTxn.mutate({ deal_captain_email: v || null });
                    }}
                    disabled={!canWrite()}
                    placeholder="담당자 검색..."
                  />
                </dd>
              </dl>

              {/* ── 우측 열: 딜 상세 구조 ── */}
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm items-center">
                <dt className="text-text-muted">매각 방식</dt>
                <dd>
                  <InlineSelect
                    options={SALE_PROCESS_OPTIONS}
                    value={txn.sale_process ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        sale_process: (v || null) as SaleProcess | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">경영권</dt>
                <dd>
                  <InlineSelect
                    options={CONTROL_TRANSFER_OPTIONS}
                    value={txn.control_transfer ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        control_transfer: (v || null) as ControlTransfer | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">대상 지분율</dt>
                <dd className="flex items-center gap-1">
                  <input
                    key={`stake-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-20 text-right font-mono",
                    )}
                    defaultValue={txn.target_stake ?? ""}
                    min={0}
                    max={100}
                    step={0.01}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.target_stake)
                        updateTxn.mutate({ target_stake: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="-"
                  />
                  <span className="text-xs text-text-muted">%</span>
                </dd>
                <dt className="text-text-muted">신주/구주</dt>
                <dd className="flex items-center gap-1">
                  <input
                    key={`new-share-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-16 text-right font-mono",
                    )}
                    defaultValue={txn.new_share_ratio ?? ""}
                    min={0}
                    max={100}
                    step={0.01}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.new_share_ratio)
                        updateTxn.mutate({ new_share_ratio: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="신주"
                  />
                  <span className="text-xs text-text-muted">/</span>
                  <input
                    key={`old-share-${txn.updated_at}`}
                    type="number"
                    className={cn(
                      INLINE_INPUT_CLS,
                      "w-16 text-right font-mono",
                    )}
                    defaultValue={txn.old_share_ratio ?? ""}
                    min={0}
                    max={100}
                    step={0.01}
                    onBlur={(e) => {
                      const v = e.target.value ? Number(e.target.value) : null;
                      if (v !== txn.old_share_ratio)
                        updateTxn.mutate({ old_share_ratio: v });
                    }}
                    disabled={!canWrite()}
                    placeholder="구주"
                  />
                  <span className="text-xs text-text-muted">%</span>
                </dd>
                <dt className="text-text-muted">밸류에이션 기준</dt>
                <dd>
                  <InlineSelect
                    options={VALUATION_BASIS_OPTIONS}
                    value={txn.valuation_basis ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        valuation_basis: (v || null) as ValuationBasis | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">Cross-border</dt>
                <dd>
                  <InlineSelect
                    options={CROSS_BORDER_OPTIONS}
                    value={txn.cross_border ?? ""}
                    onChange={(v) =>
                      updateTxn.mutate({
                        cross_border: (v || null) as CrossBorder | null,
                      })
                    }
                    disabled={!canWrite()}
                  />
                </dd>
                <dt className="text-text-muted">타겟 매수자</dt>
                <dd className="flex items-center gap-1.5 flex-wrap">
                  {TARGET_BUYER_TYPE_OPTIONS.map((opt) => {
                    const selected = (txn.target_buyer_types ?? []).includes(
                      opt.value as "STRATEGIC" | "FINANCIAL_SPONSOR",
                    );
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        disabled={!canWrite()}
                        className={cn(
                          "px-2 py-0.5 rounded-full text-xs border transition-colors",
                          selected
                            ? "bg-amic/10 border-amic text-amic font-medium"
                            : "bg-transparent border-gray-border text-text-secondary hover:border-amic/50",
                        )}
                        onClick={() => {
                          const current = txn.target_buyer_types ?? [];
                          const next = selected
                            ? current.filter((v) => v !== opt.value)
                            : [
                                ...current,
                                opt.value as "STRATEGIC" | "FINANCIAL_SPONSOR",
                              ];
                          updateTxn.mutate({
                            target_buyer_types: next.length > 0 ? next : null,
                          });
                        }}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </dd>
                <dt className="text-text-muted">배타적 협상권</dt>
                <dd className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={txn.exclusivity ?? false}
                    onChange={(e) => {
                      const checked = e.target.checked;
                      updateTxn.mutate({
                        exclusivity: checked,
                        ...(checked ? {} : { exclusivity_deadline: null }),
                      });
                    }}
                    disabled={!canWrite()}
                    className="h-3.5 w-3.5 rounded border-gray-border accent-amic"
                  />
                  {txn.exclusivity && (
                    <input
                      type="date"
                      className={cn(INLINE_INPUT_CLS, "w-36")}
                      value={txn.exclusivity_deadline ?? ""}
                      onChange={(e) =>
                        updateTxn.mutate({
                          exclusivity_deadline: e.target.value || null,
                        })
                      }
                      disabled={!canWrite()}
                    />
                  )}
                </dd>
              </dl>
            </div>
          </Card>
          {/* 회사 정보 — 전체 너비 */}
          <div className="lg:col-span-2">
            {txn.corporate_info ? (
              <CompanyInfoCard txn={txn} />
            ) : (
              <Card title="회사 정보" headerBar>
                <EngagementDocUpload
                  txnId={id}
                  docCategoryHint="CORPORATE_DOCS"
                />
              </Card>
            )}
          </div>

          {/* 서비스 연동 — 전체 너비 */}
          <div className="lg:col-span-2">
            <Card title="서비스 연동" headerBar>
              <div className="space-y-1.5 p-1">
                {(() => {
                  const enc = encodeURIComponent;
                  interface SvcItem {
                    key: string;
                    label: string;
                    icon: typeof Building2;
                    tab: string;
                    connected?: boolean;
                    viewUrl?: string;
                    createUrl?: string;
                    placeholder?: boolean;
                  }
                  const svcGroups: {
                    key: string;
                    phase: (typeof PHASE_CONFIG)[number]["phase"];
                    label: string;
                    items: SvcItem[];
                  }[] = [
                    {
                      key: "PREPARATION",
                      phase: "PREPARATION" as const,
                      label: "준비",
                      items: [
                        {
                          key: "kiis",
                          label: "KIIS 기업 인텔리전스",
                          icon: Building2,
                          tab: "",
                          connected: !!txn.target_corp_code,
                          viewUrl: txn.target_corp_code
                            ? `/kiis/companies/${txn.target_corp_code}`
                            : undefined,
                        },
                        {
                          key: "nda",
                          label: "NDA",
                          icon: FileText,
                          tab: "",
                          placeholder: true,
                        },
                      ],
                    },
                    {
                      key: "MARKETING",
                      phase: "MARKETING" as const,
                      label: "마케팅",
                      items: [
                        {
                          key: "tm",
                          label: "Teaser Memo (TM)",
                          icon: FileText,
                          tab: "marketing-materials",
                          createUrl: `/docs/new?type=teaser&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&industry=${enc(txn.industry ?? "")}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "dm",
                          label: "Discussion Memo (DM)",
                          icon: FileText,
                          tab: "marketing-materials",
                          createUrl: `/docs/new?type=dm&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&industry=${enc(txn.industry ?? "")}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "im",
                          label: "Information Memo (IM)",
                          icon: BookOpen,
                          tab: "marketing-materials",
                          connected: !!txn.im_document_id,
                          viewUrl: txn.im_document_id
                            ? `/docs/documents/${txn.im_document_id}`
                            : undefined,
                          createUrl: `/docs/new?type=im&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&industry=${enc(txn.industry ?? "")}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                      ],
                    },
                    {
                      key: "MOU",
                      phase: "MARKETING" as const,
                      label: "MOU",
                      items: [
                        {
                          key: "mou",
                          label: "양해각서 (MOU)",
                          icon: Handshake,
                          tab: "contracts",
                          connected: !!legalDocs?.some(
                            (d) => d.doc_type === "MOU",
                          ),
                          createUrl: `/docs/legal/new?txn_id=${id}&type=MOU&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                      ],
                    },
                    {
                      key: "BIDDING",
                      phase: "BIDDING" as const,
                      label: "입찰",
                      items: [],
                    },
                    {
                      key: "MAIN_DUE_DILIGENCE",
                      phase: "MAIN_DUE_DILIGENCE" as const,
                      label: "본실사",
                      items: [
                        {
                          key: "fdd",
                          label: "재무실사 (FDD)",
                          icon: BarChart2,
                          tab: "dd-checklist",
                          connected: !!txn.fdd_deal_id,
                          viewUrl: txn.fdd_deal_id
                            ? `/fdd/deals/${txn.fdd_deal_id}`
                            : undefined,
                          createUrl: `/docs/new?type=fdd&txn_id=${id}&company=${enc(txn.target_company_name)}&project=${enc(txn.code_name)}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "ldd",
                          label: "법률실사 (LDD)",
                          icon: Scale,
                          tab: "ldd",
                          createUrl: `/docs/ldd/new?txn_id=${id}&company=${enc(txn.target_company_name)}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                        {
                          key: "tdd",
                          label: "세무실사 (TDD)",
                          icon: DollarSign,
                          tab: "dd-checklist",
                        },
                      ],
                    },
                    {
                      key: "NEGOTIATION",
                      phase: "NEGOTIATION" as const,
                      label: "계약/협상",
                      items: [
                        {
                          key: "legal",
                          label: "법률 문서",
                          icon: FileSignature,
                          tab: "legal_docs",
                          createUrl: `/docs/legal/new?txn_id=${id}&return_url=${enc(`/ma/transactions/${id}`)}`,
                        },
                      ],
                    },
                    {
                      key: "CLOSING",
                      phase: "CLOSING" as const,
                      label: "Closing",
                      items: [],
                    },
                  ];

                  const currentIdx = PHASE_CONFIG.findIndex(
                    (p) => p.phase === txn.phase,
                  );

                  return svcGroups.map((group) => {
                    const groupIdx = PHASE_CONFIG.findIndex(
                      (p) => p.phase === group.phase,
                    );
                    const isCurrent = groupIdx === currentIdx;
                    const isPast = groupIdx < currentIdx;
                    const isOpen = openSvcGroups.has(group.key);
                    const isLeaf = group.items.length === 0;
                    const connectedCount = group.items.filter(
                      (s) => s.connected,
                    ).length;

                    return (
                      <div
                        key={group.key}
                        className={cn(
                          "rounded-lg border transition-all",
                          isCurrent &&
                            "border-accent bg-accent/[0.03] ring-1 ring-accent/20",
                          isPast && !isCurrent && "border-gray-border",
                          !isPast &&
                            !isCurrent &&
                            "border-dashed border-gray-border/60",
                        )}
                      >
                        <button
                          type="button"
                          className="flex items-center gap-2 w-full px-3 py-2.5 text-left"
                          onClick={() =>
                            isLeaf
                              ? handleTabChange("closing")
                              : toggleSvcGroup(group.key)
                          }
                        >
                          {isPast && (
                            <CircleCheck
                              size={14}
                              className="text-accent shrink-0"
                            />
                          )}
                          {isCurrent && (
                            <span className="relative flex h-2 w-2 shrink-0">
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent/60" />
                              <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
                            </span>
                          )}
                          {!isPast && !isCurrent && (
                            <CircleDashed
                              size={14}
                              className="text-text-muted/40 shrink-0"
                            />
                          )}
                          <span
                            className={cn(
                              "text-xs font-semibold uppercase tracking-wide flex-1",
                              isCurrent
                                ? "text-accent"
                                : isPast
                                  ? "text-text-secondary"
                                  : "text-text-muted",
                            )}
                          >
                            {group.label}
                          </span>
                          {isCurrent && (
                            <Badge variant="success" pill>
                              현재
                            </Badge>
                          )}
                          {!isLeaf && group.items.length > 0 && (
                            <span className="text-[10px] text-text-muted tabular-nums">
                              {connectedCount}/{group.items.length}
                            </span>
                          )}
                          {isLeaf ? (
                            <ChevronRight
                              size={14}
                              className="text-text-muted shrink-0"
                            />
                          ) : (
                            <ChevronDown
                              size={14}
                              className={cn(
                                "text-text-muted shrink-0 transition-transform duration-200",
                                !isOpen && "-rotate-90",
                              )}
                            />
                          )}
                        </button>

                        {!isLeaf && (
                          <div
                            className={cn(
                              "grid transition-all duration-200",
                              isOpen
                                ? "grid-rows-[1fr] opacity-100"
                                : "grid-rows-[0fr] opacity-0",
                            )}
                          >
                            <div className="overflow-hidden">
                              <div className="space-y-1.5 px-3 pb-2.5">
                                {group.items.map((svc) => (
                                  <div
                                    key={svc.key}
                                    className="flex items-center gap-2.5"
                                  >
                                    <div
                                      className={cn(
                                        "flex items-center justify-center w-7 h-7 rounded-md shrink-0",
                                        svc.connected
                                          ? "bg-accent/10 text-accent"
                                          : "bg-bg-cool text-text-muted",
                                      )}
                                    >
                                      <svc.icon size={14} />
                                    </div>
                                    <span className="text-sm font-medium truncate flex-1 min-w-0">
                                      {svc.label}
                                    </span>
                                    <div className="flex items-center gap-1 shrink-0">
                                      {svc.placeholder && (
                                        <span className="text-[10px] text-text-muted">
                                          준비 중
                                        </span>
                                      )}
                                      {svc.connected && (
                                        <Badge variant="success" pill>
                                          연결됨
                                        </Badge>
                                      )}
                                      {svc.connected && svc.viewUrl && (
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          icon={ExternalLink}
                                          onClick={() => navigate(svc.viewUrl!)}
                                        >
                                          열기
                                        </Button>
                                      )}
                                      {canWrite() &&
                                        !svc.connected &&
                                        !svc.placeholder &&
                                        svc.createUrl && (
                                          <Button
                                            variant="ghost"
                                            size="sm"
                                            icon={Plus}
                                            onClick={() =>
                                              navigate(svc.createUrl!)
                                            }
                                          >
                                            생성
                                          </Button>
                                        )}
                                      {svc.tab && (
                                        <button
                                          type="button"
                                          onClick={() =>
                                            handleTabChange(svc.tab)
                                          }
                                          className="p-1 rounded hover:bg-bg-cool text-text-muted hover:text-text-secondary transition-colors"
                                        >
                                          <ChevronRight size={12} />
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}

                {/* Metadata */}
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm pt-2 border-t border-gray-border">
                  <dt className="text-text-muted">DART Corp Code</dt>
                  <dd className="font-mono text-xs">
                    {txn.target_corp_code ?? "-"}
                  </dd>
                  <dt className="text-text-muted">생성일</dt>
                  <dd>{formatDate(txn.created_at)}</dd>
                  <dt className="text-text-muted">수정일</dt>
                  <dd>{formatDate(txn.updated_at)}</dd>
                </dl>
              </div>
            </Card>
          </div>
        </div>
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
