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
import WorkspaceHeaderActionButton from "@/modules/ma/pages/workspace/WorkspaceHeaderActionButton";
import WorkspaceHeroShortcutRow from "@/modules/ma/pages/workspace/WorkspaceHeroShortcutRow";
import {
  VALID_TABS,
  useWorkspaceTabs,
} from "@/modules/ma/pages/workspace/useWorkspaceTabs";
import { useOpenVdrUpload } from "@/modules/ma/hooks/useVdrUploadNavigation";
import { RAIL_TOOL_IDS, type RailToolId } from "@/modules/ma/constants";
import {
  buildRailClosePath,
  buildRailOpenPath,
} from "@/modules/ma/pages/workspace/railRouteHelpers";

import {
  useOnboarding,
  OnboardingOverlay,
  CLIENT_OVERVIEW_STEPS,
} from "@/components/onboarding";
import { CalendarDays, HelpCircle } from "lucide-react";
const MeetingLogsTab = lazy(
  () => import("@/modules/ma/components/meetings/MeetingLogsTab"),
);
const VdrTab = lazy(() => import("@/modules/ma/components/vdr/VdrTab"));
const RFIPanel = lazy(() => import("@/modules/ma/components/rfi/RFIPanel"));
const TransactionOverviewTab = lazy(
  () => import("@/modules/ma/components/overview/TransactionOverviewTab"),
);
const TransactionCompletionOverview = lazy(
  () => import("@/modules/ma/components/overview/TransactionCompletionOverview"),
);

import {
  Badge,
  Card,
  PageHero,
  SlidePanel,
  Spinner,
  Tabs,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import heroImg from "@/assets/images/heroes/hero-arch-dark-round.jpg";
import TimelineTab from "@/modules/ma/tabs/TimelineTab";

// ── Tab components (lazy-loaded) ────────────────────────
const BuyersTab = lazy(() => import("@/modules/ma/tabs/BuyersTab"));
const ContractsTab = lazy(() => import("@/modules/ma/tabs/ContractsTab"));
const ClosingTab = lazy(() => import("@/modules/ma/tabs/ClosingTab"));
const NdasTab = lazy(() => import("@/modules/ma/tabs/NdasTab"));
const BidsTab = lazy(() => import("@/modules/ma/tabs/BidsTab"));
const DDChecklistTab = lazy(() => import("@/modules/ma/tabs/DDChecklistTab"));
const MarketingMaterialsTab = lazy(
  () => import("@/modules/ma/tabs/MarketingMaterialsTab"),
);
const ModelsTab = lazy(() => import("@/modules/ma/tabs/ModelsTab"));
const EngagementTab = lazy(() => import("@/modules/ma/tabs/EngagementTab"));

const REMOVED_WORKSPACE_TOOLS = [
  "risks",
  "compliance",
  "notes-approvals",
  "ai-quality",
] as const;
const REMOVED_WORKSPACE_TAB_ROUTES = ["pmi", "earnout"] as const;

const WORKSPACE_TAB_HEADER_ACTION_PORTAL_ID = "workspace-tab-header-actions";

// ── 상수 ──────────────────────────────────────────
const VALID_PHASES = PHASE_CONFIG.map((p) => p.phase);

const RAIL_PANEL_TITLES: Record<RailToolId, string> = {
  timeline: "타임라인",
};

// 초기 리다이렉트 이력 — 컴포넌트 리마운트에도 유지 (세션 내 txn당 1회)
const _redirectedTxnIds = new Set<string>();

// ── 메인 컴포넌트 ──────────────────────────────────────
export default function TransactionWorkspacePage() {
  const { txnId, "*": splat } = useParams<{ txnId: string; "*": string }>();
  const navigate = useNavigate();
  const { user, canWrite, isClient } = useAuth();
  const id = txnId ?? "";

  // CLIENT 온보딩 (Overview 탭에서만 활성화)
  const onboarding = useOnboarding(user?.id ?? "", id, CLIENT_OVERVIEW_STEPS);

  // URL 기반 탭 결정
  const activeTab = (VALID_TABS as readonly string[]).includes(splat ?? "")
    ? splat!
    : "overview";
  const isRemovedWorkspaceToolRoute = REMOVED_WORKSPACE_TOOLS.includes(
    (splat ?? "") as (typeof REMOVED_WORKSPACE_TOOLS)[number],
  );
  const isRemovedWorkspaceTabRoute = REMOVED_WORKSPACE_TAB_ROUTES.includes(
    (splat ?? "") as (typeof REMOVED_WORKSPACE_TAB_ROUTES)[number],
  );

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

  useEffect(() => {
    if (!isRemovedWorkspaceTabRoute) return;
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    navigate(`/ma/transactions/${id}${qs}`, { replace: true });
  }, [id, isRemovedWorkspaceTabRoute, navigate, viewedPhase]);

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

  // 초기 로드 시: URL에 탭 미지정 + ENGAGEMENT 아닌 단계 → 기본 탭으로 리다이렉트 (세션 내 txn당 1회)
  useEffect(() => {
    if (!txn?.phase) return;
    if (_redirectedTxnIds.has(id)) return;
    _redirectedTxnIds.add(id);
    // CLIENT는 첫 접속 시 Overview에 머무르되, 이후 phase 기본 탭으로 이동 가능
    // URL에 이미 탭이 있거나 다른 단계를 보는 중이면 리다이렉트 안 함
    if (splat || viewedPhase) return;
    const phase = txn.phase as TransactionPhase;
    const defaultTab = PHASE_TAB_MAP[phase];
    if (defaultTab && defaultTab !== "overview") {
      navigate(`/ma/transactions/${id}/${defaultTab}`, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [txn?.phase, id, navigate, isClient]);

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
  // URL 기반 탭 전환 (viewPhase search param 유지하여 탭 필터링 보존)
  const handleTabChange = (tab: string) => {
    const qs = viewedPhase ? `?viewPhase=${viewedPhase}` : "";
    if (tab === "overview") {
      navigate(`/ma/transactions/${id}${qs}`);
    } else {
      navigate(`/ma/transactions/${id}/${tab}${qs}`);
    }
  };

  const { tabs, safeActiveTab, tabBarActiveTab, isRailTool } =
    useWorkspaceTabs({
      summary,
      txnPhase: txn?.phase,
      viewedPhase,
      activeTab,
      baseTab,
    });
  const openVdrUpload = useOpenVdrUpload(id);
  const currentTabLabel =
    tabs.find((tab) => tab.id === tabBarActiveTab)?.label ?? "Previous Page";
  const legacyFallbackTab =
    baseTab && tabs.some((tab) => tab.id === baseTab)
      ? baseTab
      : viewedPhase
        ? (PHASE_TAB_MAP[viewedPhase] ?? "overview")
        : txn?.phase
          ? (PHASE_TAB_MAP[txn.phase as TransactionPhase] ?? "overview")
          : "overview";

  const activeRailTool = isRailTool
    ? (RAIL_TOOL_IDS as readonly string[]).includes(activeTab)
      ? (activeTab as RailToolId)
      : null
    : null;
  const isTimelineOpen = activeRailTool === "timeline";

  const handleTimelineToggle = () => {
    if (isTimelineOpen) {
      navigate(buildRailClosePath(id, safeActiveTab, searchParams), {
        replace: true,
      });
      return;
    }

    navigate(buildRailOpenPath(id, "timeline", safeActiveTab, searchParams), {
      replace: true,
    });
  };

  useEffect(() => {
    if (!isRemovedWorkspaceToolRoute) return;

    navigate(buildRailClosePath(id, legacyFallbackTab, searchParams), {
      replace: true,
    });
  }, [
    id,
    isRemovedWorkspaceToolRoute,
    legacyFallbackTab,
    navigate,
    searchParams,
  ]);

  if (!txnId) return <Navigate to="/ma/transactions" replace />;
  if (isLoading) return <Spinner size="lg" />;
  if (!txn)
    return (
      <div className="text-center py-20 text-text-muted">
        거래를 찾을 수 없습니다
      </div>
    );

  const canEdit = canWrite();
  const phaseForContent = viewedPhase ?? (txn.phase as TransactionPhase);
  const phaseLabel =
    PHASE_CONFIG.find((p) => p.phase === phaseForContent)?.label ??
    phaseForContent;
  const isCompletionPhase = phaseForContent === "POST_CLOSING";
  const showOverviewShortcut = true;
  const isVdrRoute = safeActiveTab === "vdr";
  const canUploadToVdr = canEdit || Boolean(isClient);
  const heroPhaseTabId = tabs.find((tab) => tab.id !== "overview")?.id;
  const contentTabs = tabs.filter((tab) => tab.id !== "overview");
  const contentTabActiveId = contentTabs.some(
    (tab) => tab.id === tabBarActiveTab,
  )
    ? tabBarActiveTab
    : "";
  return (
    <div className="space-y-6">
      {/* Hero */}
      <PageHero
        title={txn.name}
        subtitle={`${txn.code_name} | ${txn.target_company_name} | ${txn.client_name}`}
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        headerAside={
          <div
            data-testid="workspace-hero-actions"
            className="w-full lg:w-auto lg:justify-self-end"
          >
            <PhaseWorkspaceHeader
              txnId={id}
              txn={txn}
              canWrite={canEdit}
              isClient={isClient ?? false}
              surface="hero"
            />
          </div>
        }
        children={
          <div className="mt-1">
            <WorkspaceHeroShortcutRow
              showOverview={showOverviewShortcut}
              overviewActive={safeActiveTab === "overview"}
              phaseLabel={phaseLabel}
              phaseActive={safeActiveTab !== "overview" && !isVdrRoute}
              showVdrShortcut={isClient}
              vdrActive={isVdrRoute}
              onOverviewClick={() => handleTabChange("overview")}
              onPhaseClick={
                heroPhaseTabId
                  ? () => handleTabChange(heroPhaseTabId)
                  : undefined
              }
              onVdrClick={() => handleTabChange("vdr")}
              showUploadAction={canUploadToVdr && safeActiveTab !== "vdr"}
              onUploadClick={() =>
                openVdrUpload({
                  returnLabel: currentTabLabel,
                })
              }
            />
          </div>
        }
        compact
      />

      {/* Pipeline Flow */}
      <Card padding="md" data-onboarding="pipeline-flow">
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

      {/* Tabs + Timeline panel trigger */}
      <div className="min-w-0">
        <Card padding="none">
          <div
            className={cn(
              "flex items-center gap-3 px-5 pt-3",
              contentTabs.length === 0 && "justify-end",
            )}
            data-onboarding="workspace-tabs"
          >
            {contentTabs.length > 0 && (
              <div className="flex-1 min-w-0">
                <Tabs
                  tabs={contentTabs}
                  activeTab={contentTabActiveId}
                  onTabChange={handleTabChange}
                  variant="underline"
                />
              </div>
            )}
            <div
              className="shrink-0 flex items-center gap-2"
              data-testid="workspace-tabs-actions"
            >
              {isClient && (
                <button
                  type="button"
                  onClick={onboarding.restart}
                  className="p-1.5 rounded-md text-text-muted hover:text-text-default hover:bg-surface-secondary transition-colors"
                  title="가이드 다시보기"
                >
                  <HelpCircle className="w-4 h-4" />
                </button>
              )}
              <div
                id={WORKSPACE_TAB_HEADER_ACTION_PORTAL_ID}
                data-testid="workspace-tab-header-actions-slot"
                className="flex items-center gap-2"
              />
              <WorkspaceHeaderActionButton
                icon={CalendarDays}
                label="Timeline"
                onClick={handleTimelineToggle}
                aria-pressed={isTimelineOpen}
                active={isTimelineOpen}
              />
            </div>
          </div>

          <div
            className={
              safeActiveTab === "marketing-materials" ? undefined : "p-5"
            }
          >
            {/* ── Overview 탭 ─────────────────────────────── */}
            {safeActiveTab === "overview" && (
              <Suspense fallback={<Spinner size="lg" />}>
                {isCompletionPhase ? (
                  <TransactionCompletionOverview txn={txn} summary={summary} />
                ) : (
                  <TransactionOverviewTab txn={txn} />
                )}
              </Suspense>
            )}

            {/* ── Tab Components (lazy-loaded with Suspense) ── */}
            <Suspense fallback={<Spinner size="lg" />}>
              {safeActiveTab === "engagement" && (
                <EngagementTab txnId={id} canWrite={canEdit} />
              )}
              {safeActiveTab === "buyers" && (
                <BuyersTab
                  txnId={id}
                  canWrite={canEdit}
                  headerActionPortalId={WORKSPACE_TAB_HEADER_ACTION_PORTAL_ID}
                />
              )}
              {safeActiveTab === "vdr" && (
                <VdrTab
                  txnId={id}
                  readOnly={false}
                  showReviewTabs={!(isClient ?? false)}
                  showExtractionTools={!(isClient ?? false)}
                />
              )}
              {safeActiveTab === "rfi" && <RFIPanel txnId={id} />}
              {safeActiveTab === "ndas" && (
                <NdasTab txnId={id} canWrite={canEdit} />
              )}
              {safeActiveTab === "bids" && (
                <BidsTab txnId={id} canWrite={canEdit} />
              )}
              {safeActiveTab === "dd-checklist" && (
                <DDChecklistTab txnId={id} canWrite={canEdit} />
              )}
              {safeActiveTab === "contracts" && (
                <ContractsTab txnId={id} canWrite={canEdit} />
              )}
              {safeActiveTab === "closing" && (
                <ClosingTab txnId={id} canWrite={canEdit} />
              )}
              {safeActiveTab === "marketing-materials" && (
                <MarketingMaterialsTab
                  txnId={id}
                  canWrite={canEdit}
                  showSourcePreview={false}
                  surface="flat"
                />
              )}
              {safeActiveTab === "models" && (
                <ModelsTab
                  txnId={id}
                  canWrite={canEdit}
                  showSourcePreview={false}
                />
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
        </Card>
      </div>

      {/* Rail Tool SlidePanel */}
      <SlidePanel
        open={isTimelineOpen}
        onClose={() => {
          navigate(buildRailClosePath(id, safeActiveTab, searchParams), {
            replace: true,
          });
        }}
        title={isTimelineOpen ? RAIL_PANEL_TITLES.timeline : ""}
        width="xl"
      >
        <Suspense fallback={<Spinner size="lg" />}>
          {activeRailTool === "timeline" && <TimelineTab txnId={id} />}
        </Suspense>
      </SlidePanel>

      {/* CLIENT 온보딩 오버레이 */}
      {isClient && onboarding.isActive && onboarding.step && (
        <OnboardingOverlay
          step={onboarding.step}
          currentIndex={onboarding.currentStep}
          totalSteps={onboarding.totalSteps}
          onNext={onboarding.next}
          onPrev={onboarding.prev}
          onSkip={onboarding.skip}
        />
      )}
    </div>
  );
}
