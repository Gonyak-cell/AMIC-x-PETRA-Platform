import { useState, useMemo, useEffect, useRef, lazy, Suspense } from "react";
import {
  useParams,
  useNavigate,
  useSearchParams,
  Navigate,
} from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import {
  useTransaction,
  useAutoAdvanceNotification,
  useBuyers,
} from "@/modules/ma/hooks/useTransactions";
import type { TransactionPhase } from "@/modules/ma/types/transaction";
import { useWorkspaceSummary } from "@/modules/ma/hooks/useWorkspaceSummary";
import { useLegalDocuments } from "@/modules/docs/hooks/useLegalDocuments";
import PipelineFlow from "@/modules/ma/components/PipelineFlow";
import MilestoneUploadPopover from "@/modules/ma/components/MilestoneUploadPopover";
import { useAttachments } from "@/modules/ma/hooks/useAttachments";
import {
  PHASE_CONFIG,
  PHASE_MILESTONES,
  PHASE_TAB_MAP,
  type UploadableMilestone,
  TRANSACTION_STATUS_VARIANT,
} from "@/modules/ma/constants";

import PhaseWorkspaceHeader from "@/modules/ma/pages/workspace/PhaseWorkspaceHeader";
import {
  VALID_TABS,
  useWorkspaceTabs,
} from "@/modules/ma/pages/workspace/useWorkspaceTabs";
import SecondaryRail from "@/modules/ma/components/SecondaryRail";
import { RAIL_TOOL_IDS, type RailToolId } from "@/modules/ma/constants";
import { buildRailClosePath } from "@/modules/ma/pages/workspace/railRouteHelpers";

import ClientPortalDashboard from "@/modules/ma/components/ClientPortalDashboard";
const MeetingLogsTab = lazy(
  () => import("@/modules/ma/components/meetings/MeetingLogsTab"),
);
const VdrTab = lazy(() => import("@/modules/ma/components/vdr/VdrTab"));
const RFIPanel = lazy(() => import("@/modules/ma/components/rfi/RFIPanel"));
const TransactionOverviewTab = lazy(
  () => import("@/modules/ma/components/overview/TransactionOverviewTab"),
);

import {
  Badge,
  Card,
  PageHero,
  SlidePanel,
  Spinner,
  Tabs,
} from "@/components/ui";
import heroImg from "@/assets/images/heroes/hero-arch-dark-round.jpg";

// ── Tab components (lazy-loaded) ────────────────────────
const BuyersTab = lazy(() => import("@/modules/ma/tabs/BuyersTab"));
const ContractsTab = lazy(() => import("@/modules/ma/tabs/ContractsTab"));
const RisksTab = lazy(() => import("@/modules/ma/tabs/RisksTab"));
const ComplianceTab = lazy(() => import("@/modules/ma/tabs/ComplianceTab"));
const ClosingTab = lazy(() => import("@/modules/ma/tabs/ClosingTab"));
const NdasTab = lazy(() => import("@/modules/ma/tabs/NdasTab"));
const BidsTab = lazy(() => import("@/modules/ma/tabs/BidsTab"));
const DDChecklistTab = lazy(() => import("@/modules/ma/tabs/DDChecklistTab"));
const PMITab = lazy(() => import("@/modules/ma/tabs/PMITab"));
const EarnoutTab = lazy(() => import("@/modules/ma/tabs/EarnoutTab"));
const MarketingMaterialsTab = lazy(
  () => import("@/modules/ma/tabs/MarketingMaterialsTab"),
);
const ModelsTab = lazy(() => import("@/modules/ma/tabs/ModelsTab"));
const NotesApprovalsTab = lazy(
  () => import("@/modules/ma/tabs/NotesApprovalsTab"),
);
const TimelineTab = lazy(() => import("@/modules/ma/tabs/TimelineTab"));
const QualityTab = lazy(() => import("@/modules/ma/tabs/QualityTab"));
const EngagementTab = lazy(() => import("@/modules/ma/tabs/EngagementTab"));

// ── 상수 ──────────────────────────────────────────
const VALID_PHASES = PHASE_CONFIG.map((p) => p.phase);

const RAIL_PANEL_TITLES: Record<RailToolId, string> = {
  risks: "리스크",
  compliance: "컴플라이언스",
  "notes-approvals": "노트/승인",
  timeline: "타임라인",
  "ai-quality": "AI 품질",
};

// ── 메인 컴포넌트 ──────────────────────────────────────
export default function TransactionWorkspacePage() {
  const { txnId, "*": splat } = useParams<{ txnId: string; "*": string }>();
  const navigate = useNavigate();
  const { canWrite, isClient } = useAuth();
  const id = txnId ?? "";

  // URL 기반 탭 결정
  const activeTab = VALID_TABS.includes(splat ?? "") ? splat! : "overview";

  // 파이프라인에서 클릭한 단계 (URL search param 기반, 리마운트 안전)
  const [searchParams, setSearchParams] = useSearchParams();
  const viewedPhase: TransactionPhase | null = (() => {
    const raw = searchParams.get("viewPhase");
    return raw && VALID_PHASES.includes(raw as TransactionPhase)
      ? (raw as TransactionPhase)
      : null;
  })();

  // rail tool URL 접근 시 primary content로 표시할 탭 (?baseTab= query)
  const baseTab = searchParams.get("baseTab") ?? undefined;

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

  // 데이터 로드
  const { data: txn, isLoading } = useTransaction(id);
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

  // 초기 로드 시: URL에 탭 미지정 + ENGAGEMENT 아닌 단계 → 기본 탭으로 리다이렉트 (1회만)
  const initialRedirectDone = useRef(false);
  useEffect(() => {
    if (!txn?.phase) return;
    if (initialRedirectDone.current) return;
    initialRedirectDone.current = true;
    // URL에 이미 탭이 있거나 다른 단계를 보는 중이면 리다이렉트 안 함
    if (splat || viewedPhase) return;
    const phase = txn.phase as TransactionPhase;
    const defaultTab = PHASE_TAB_MAP[phase];
    if (defaultTab && defaultTab !== "overview") {
      navigate(`/ma/transactions/${id}/${defaultTab}`, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [txn?.phase, id, navigate]);

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
  // 워크스페이스 요약 — 탭 배지 카운트용 (단일 쿼리)
  const { data: summary } = useWorkspaceSummary(id);

  // 매수자 목록 — marketing-logs 탭 buyer name lookup용
  const { data: buyers } = useBuyers(id, !!buyerIdParam);

  // Legal docs (overview 서비스 연동에서 MOU 상태 확인용)
  const { data: legalDocs } = useLegalDocuments(
    id,
    activeTab === "contracts" || activeTab === "overview",
  );

  // URL 기반 탭 전환 (viewPhase search param 유지하여 탭 필터링 보존)
  const handleTabChange = (tab: string) => {
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    if (tab === "overview") {
      navigate(`/ma/transactions/${id}${qs}`);
    } else {
      navigate(`/ma/transactions/${id}/${tab}${qs}`);
    }
  };

  const { tabs, safeActiveTab, isRailTool } = useWorkspaceTabs({
    summary,
    txnPhase: txn?.phase,
    viewedPhase,
    activeTab,
    baseTab,
    isClient: isClient ?? false,
  });

  const activeRailTool = isRailTool
    ? (RAIL_TOOL_IDS as readonly string[]).includes(activeTab)
      ? (activeTab as RailToolId)
      : null
    : null;

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
            viewedPhase={viewedPhase}
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

      {/* Phase Workspace Header — 단계 진행 CTA + 필수 조건 */}
      <PhaseWorkspaceHeader
        txnId={id}
        txn={txn}
        canWrite={canWrite()}
        isClient={isClient ?? false}
      />

      {/* 탭 + SecondaryRail (flex-row) */}
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0 space-y-6">
          <Tabs
            tabs={tabs}
            activeTab={safeActiveTab}
            onTabChange={handleTabChange}
            variant="underline"
          />

          {/* ── Overview 탭 ─────────────────────────────── */}
          {safeActiveTab === "overview" && isClient && (
            <ClientPortalDashboard txnId={id} />
          )}
          {safeActiveTab === "overview" && !isClient && (
            <Suspense fallback={<Spinner size="lg" />}>
              <TransactionOverviewTab
                txnId={id}
                txn={txn}
                legalDocs={legalDocs}
                onTabChange={handleTabChange}
              />
            </Suspense>
          )}

          {/* ── Tab Components (lazy-loaded with Suspense) ── */}
          <Suspense fallback={<Spinner size="lg" />}>
            {safeActiveTab === "engagement" && (
              <EngagementTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "buyers" && (
              <BuyersTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "vdr" && <VdrTab txnId={id} />}
            {safeActiveTab === "rfi" && <RFIPanel txnId={id} />}
            {safeActiveTab === "ndas" && (
              <NdasTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "bids" && (
              <BidsTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "dd-checklist" && (
              <DDChecklistTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "contracts" && (
              <ContractsTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "closing" && (
              <ClosingTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "pmi" && (
              <PMITab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "earnout" && (
              <EarnoutTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "marketing-materials" && (
              <MarketingMaterialsTab txnId={id} canWrite={canWrite()} />
            )}
            {safeActiveTab === "models" && (
              <ModelsTab txnId={id} canWrite={canWrite()} />
            )}
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
          </Suspense>
        </div>

        {/* SecondaryRail — cross-phase tools 아이콘 바 (클라이언트 제외) */}
        {!isClient && (
          <SecondaryRail
            txnId={id}
            txnPhase={txn.phase as TransactionPhase}
            activeRailTool={activeRailTool}
            baseTab={safeActiveTab}
          />
        )}
      </div>

      {/* Rail Tool SlidePanel */}
      <SlidePanel
        open={!!activeRailTool}
        onClose={() => {
          navigate(buildRailClosePath(id, safeActiveTab, searchParams), {
            replace: true,
          });
        }}
        title={activeRailTool ? RAIL_PANEL_TITLES[activeRailTool] : ""}
        width="xl"
      >
        <Suspense fallback={<Spinner size="lg" />}>
          {activeRailTool === "risks" && (
            <RisksTab txnId={id} canWrite={canWrite()} />
          )}
          {activeRailTool === "compliance" && (
            <ComplianceTab txnId={id} canWrite={canWrite()} />
          )}
          {activeRailTool === "notes-approvals" && (
            <NotesApprovalsTab txnId={id} canWrite={canWrite()} />
          )}
          {activeRailTool === "timeline" && <TimelineTab txnId={id} />}
          {activeRailTool === "ai-quality" && (
            <QualityTab txnId={id} canWrite={canWrite()} />
          )}
        </Suspense>
      </SlidePanel>
    </div>
  );
}
