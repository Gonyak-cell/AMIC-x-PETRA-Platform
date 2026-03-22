import {
  useState,
  useEffect,
  useMemo,
  useDeferredValue,
  lazy,
  Suspense,
} from "react";
import { createPortal } from "react-dom";
import {
  Users,
  Download,
  Building2,
  Sparkles,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import {
  useBuyers,
  useUpdateBuyer,
  useExportBuyerExcel,
  useTransaction,
} from "@/modules/ma/hooks/useTransactions";
import { useShortListOverview } from "@/modules/ma/hooks/useBuyerMarketing";
import { useSICompanyByName } from "@/modules/ma/hooks/useSIMapping";
import type { CorporateDocsExtractedData } from "@/modules/ma/types/document_extraction";
import type {
  BuyerCandidate,
  BuyerTier,
  DealRole,
} from "@/modules/ma/types/buyer";
import {
  BUYER_TYPE_OPTIONS,
  BUYER_TIER_OPTIONS,
  DEAL_ROLE_OPTIONS,
  isShortListed,
  buildStageMap,
} from "@/modules/ma/constants";
import type { BuyerStageSummary } from "@/modules/ma/types/marketing_log";
import type { KpiFilter } from "@/modules/ma/components/buyers/ShortListOverview";
import BuyerTierBadge from "@/modules/ma/components/buyers/BuyerTierBadge";
import DealRoleBadge from "@/modules/ma/components/buyers/DealRoleBadge";
import FunnelNav from "@/modules/ma/components/buyers/FunnelNav";
import ShortListSummaryBar from "@/modules/ma/components/buyers/ShortListSummaryBar";
import LongListFilters from "@/modules/ma/components/buyers/LongListFilters";
import type { LongListFilterState } from "@/modules/ma/components/buyers/LongListFilters";
import ShortListMasterList from "@/modules/ma/components/buyers/ShortListMasterList";
import BuyerDetailPanel from "@/modules/ma/components/buyers/BuyerDetailPanel";
import FIRecommendModal from "@/modules/ma/components/buyers/FIRecommendModal";
import ShortListViewToggle from "@/modules/ma/components/buyers/ShortListViewToggle";
import type { ShortListViewMode } from "@/modules/ma/components/buyers/ShortListViewToggle";
import MarketingGridView from "@/modules/ma/components/buyers/MarketingGridView";
const MarketingTimelineView = lazy(
  () => import("@/modules/ma/components/buyers/MarketingTimelineView"),
);
const MarketingKanbanView = lazy(
  () => import("@/modules/ma/components/buyers/MarketingKanbanView"),
);
const SIMappingPanel = lazy(
  () => import("@/modules/ma/components/si-mapping/SIMappingPanel"),
);
import SIDetailPanel from "@/modules/ma/components/si-mapping/SIDetailPanel";
import WorkspaceHeaderActionButton from "@/modules/ma/pages/workspace/WorkspaceHeaderActionButton";
import { toast } from "sonner";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  InlineSelect,
  Spinner,
} from "@/components/ui";
import type { Column } from "@/components/ui";

interface BuyersTabProps {
  txnId: string;
  canWrite: boolean;
  headerActionPortalId?: string;
}

export default function BuyersTab({
  txnId,
  canWrite,
  headerActionPortalId,
}: BuyersTabProps) {
  const {
    data: buyers,
    isLoading: isBuyersLoading,
    isError: isBuyersError,
    refetch: refetchBuyers,
  } = useBuyers(txnId);
  const { data: txn } = useTransaction(txnId);
  const updateBuyer = useUpdateBuyer(txnId);
  const exportExcel = useExportBuyerExcel(txnId);
  const {
    data: shortListOverview,
    isError: isOverviewError,
    refetch: refetchOverview,
  } = useShortListOverview(txnId);

  const corporateInfo = useMemo((): CorporateDocsExtractedData | null => {
    const v = txn?.corporate_info;
    if (
      typeof v === "object" &&
      v !== null &&
      ("corporate_registration_number" in v ||
        "business_registration_number" in v)
    ) {
      return v as unknown as CorporateDocsExtractedData;
    }
    return null;
  }, [txn?.corporate_info]);

  const [buyerSubTab, setBuyerSubTab] = useState<"long-list" | "short-list">(
    "long-list",
  );
  const [showSIMappingModal, setShowSIMappingModal] = useState(false);
  const [showFIRecommendModal, setShowFIRecommendModal] = useState(false);
  const [buyerDetailCompanyId, setBuyerDetailCompanyId] = useState<
    string | null
  >(null);
  const [buyerDetailSearchName, setBuyerDetailSearchName] = useState<
    string | null
  >(null);
  const { data: searchedSICompany, isFetched: siNameFetched } =
    useSICompanyByName(buyerDetailSearchName);

  // Short List detail panel state
  const [selectedBuyerId, setSelectedBuyerId] = useState<string | null>(null);
  const [shortListViewMode, setShortListViewMode] =
    useState<ShortListViewMode>("grid");
  const [activeFilter, setActiveFilter] = useState<KpiFilter>("all");
  const [masterListOpen, setMasterListOpen] = useState(false);
  const [headerActionPortalTarget, setHeaderActionPortalTarget] =
    useState<HTMLElement | null>(null);

  // Long List filter state
  const [longListFilters, setLongListFilters] = useState<LongListFilterState>({
    type: null,
    tier: null,
    status: null,
    search: "",
  });

  useEffect(() => {
    if (!buyerDetailSearchName || !siNameFetched) return;
    if (searchedSICompany?.id) {
      setBuyerDetailCompanyId(searchedSICompany.id);
    } else {
      toast.info("SI 데이터베이스에 등록되지 않은 기업입니다.");
    }
    setBuyerDetailSearchName(null);
  }, [searchedSICompany, buyerDetailSearchName, siNameFetched]);

  useEffect(() => {
    if (!headerActionPortalId || typeof document === "undefined") {
      setHeaderActionPortalTarget(null);
      return;
    }

    setHeaderActionPortalTarget(
      document.getElementById(headerActionPortalId),
    );
  }, [headerActionPortalId]);

  const buyerColumns: Column<BuyerCandidate>[] = useMemo(
    () => [
      {
        key: "company_name",
        header: "회사명",
        minWidth: "160px",
        render: (r) => {
          const siId = (r.extra_data as Record<string, unknown> | null)
            ?.si_company_id as string | undefined;

          return (
            <div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  if (siId) {
                    setBuyerDetailCompanyId(siId);
                  } else {
                    setBuyerDetailSearchName(r.company_name);
                  }
                }}
                className="text-left font-medium hover:text-accent hover:underline"
              >
                {r.company_name}
              </button>
              {r.contact_name && (
                <span className="block text-xs text-text-muted">
                  {r.contact_name}
                </span>
              )}
            </div>
          );
        },
      },
      {
        key: "tier",
        header: "Tier",
        minWidth: "100px",
        render: (r) =>
          canWrite ? (
            <InlineSelect
              options={[
                { value: "", label: "-" },
                ...BUYER_TIER_OPTIONS.filter((o) => o.value !== ""),
              ]}
              value={r.tier ?? ""}
              onChange={(val) =>
                updateBuyer.mutate({
                  buyerId: r.id,
                  body: {
                    tier: (val || undefined) as BuyerTier | undefined,
                  },
                })
              }
            />
          ) : (
            <BuyerTierBadge tier={r.tier} />
          ),
      },
      {
        key: "deal_role",
        header: "역할",
        minWidth: "120px",
        render: (r) => {
          const roleOptions = DEAL_ROLE_OPTIONS.filter((o) => o.value !== "");
          return canWrite ? (
            <InlineSelect
              options={[{ value: "", label: "-" }, ...roleOptions]}
              value={r.deal_role ?? ""}
              onChange={(val) =>
                updateBuyer.mutate({
                  buyerId: r.id,
                  body: {
                    deal_role: (val || undefined) as DealRole | undefined,
                  },
                })
              }
            />
          ) : (
            <DealRoleBadge role={r.deal_role} />
          );
        },
      },
      {
        key: "buyer_type",
        header: "유형",
        minWidth: "100px",
        render: (r) => (
          <Badge variant="neutral">
            {BUYER_TYPE_OPTIONS.find((o) => o.value === r.buyer_type)?.label ??
              r.buyer_type}
          </Badge>
        ),
      },
    ],
    [canWrite, updateBuyer],
  );

  const allBuyers = useMemo(() => buyers ?? [], [buyers]);
  const realShortList = useMemo(
    () => allBuyers.filter(isShortListed),
    [allBuyers],
  );

  // ── Dev-only mock data for Short List preview (동적 import) ──
  const [devMockBuyers, setDevMockBuyers] = useState<BuyerCandidate[]>([]);
  const [devMockOverview, setDevMockOverview] = useState<BuyerStageSummary[]>(
    [],
  );

  useEffect(() => {
    if (!import.meta.env.DEV) return;
    import("@/modules/ma/constants/devMockBuyers").then((mod) => {
      setDevMockBuyers(mod.createDevMockBuyers(txnId));
      setDevMockOverview(mod.createDevMockOverview());
    });
  }, [txnId]);

  const shortListBuyers =
    realShortList.length > 0 ? realShortList : devMockBuyers;
  const overviewMerged = useMemo(
    () => [
      ...(shortListOverview ?? []),
      ...(realShortList.length > 0 ? [] : devMockOverview),
    ],
    [shortListOverview, realShortList.length, devMockOverview],
  );

  const stageMap = useMemo(
    () => buildStageMap(overviewMerged),
    [overviewMerged],
  );

  // Client-side filtering for Long List
  const deferredSearch = useDeferredValue(longListFilters.search);
  const filteredBuyers = useMemo(() => {
    let result = allBuyers;
    if (longListFilters.type) {
      result = result.filter((b) => b.buyer_type === longListFilters.type);
    }
    if (longListFilters.tier) {
      result = result.filter((b) => b.tier === longListFilters.tier);
    }
    if (longListFilters.status) {
      result = result.filter((b) => b.status === longListFilters.status);
    }
    if (deferredSearch) {
      const q = deferredSearch.toLowerCase();
      result = result.filter((b) => b.company_name.toLowerCase().includes(q));
    }
    return result;
  }, [
    allBuyers,
    longListFilters.type,
    longListFilters.tier,
    longListFilters.status,
    deferredSearch,
  ]);

  // Derive selected buyer and its stage summary for SlidePanel
  const selectedBuyer = useMemo(
    () => allBuyers.find((b) => b.id === selectedBuyerId) ?? null,
    [allBuyers, selectedBuyerId],
  );
  const selectedStageSummary = useMemo(
    () => (shortListOverview ?? []).find((s) => s.buyer_id === selectedBuyerId),
    [shortListOverview, selectedBuyerId],
  );
  const showShortListToolbar = !isBuyersLoading && buyerSubTab === "short-list";
  const showHeaderExcelAction = !isBuyersLoading && buyerSubTab === "long-list";

  return (
    <>
      {headerActionPortalTarget &&
        showHeaderExcelAction &&
        createPortal(
          <WorkspaceHeaderActionButton
            icon={Download}
            label="Excel"
            onClick={() => exportExcel.mutate()}
            loading={exportExcel.isPending}
          />,
          headerActionPortalTarget,
        )}
      <div className="space-y-4">
        {/* Funnel Navigation (탭 + 퍼널 통합) */}
        <FunnelNav
          buyers={allBuyers}
          activeStep={buyerSubTab}
          onStepChange={setBuyerSubTab}
        />

        {/* 인라인 KPI 바 + 액션 버튼 */}
        {showShortListToolbar && (
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setMasterListOpen(!masterListOpen)}
                className="p-1.5 rounded-lg text-gray-500 hover:text-text-dark hover:bg-gray-100 transition-colors"
                aria-expanded={masterListOpen}
                aria-label="마스터 리스트 토글"
              >
                {masterListOpen ? (
                  <PanelLeftClose className="h-4 w-4" />
                ) : (
                  <PanelLeftOpen className="h-4 w-4" />
                )}
              </button>
              <ShortListSummaryBar
                buyers={shortListBuyers}
                overviewData={overviewMerged}
                stageMap={stageMap}
                activeFilter={activeFilter}
                onFilterChange={setActiveFilter}
              />
            </div>
            <div className="flex items-center gap-2 flex-shrink-0 ml-auto">
              <ShortListViewToggle
                viewMode={shortListViewMode}
                onViewModeChange={setShortListViewMode}
              />
            </div>
          </div>
        )}

        {isBuyersLoading && (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        )}

        {(isBuyersError || isOverviewError) && (
          <div
            role="alert"
            className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-4 py-3"
          >
            <p className="text-sm text-red-700">
              {isBuyersError
                ? "매수자 목록을 불러오는 중 오류가 발생했습니다."
                : "Short List 개요 데이터를 불러오는 중 오류가 발생했습니다."}
            </p>
            <button
              type="button"
              className="text-sm font-medium text-red-700 underline hover:text-red-900"
              onClick={() =>
                isBuyersError ? refetchBuyers() : refetchOverview()
              }
            >
              재시도
            </button>
          </div>
        )}

        {buyerSubTab === "long-list" && (
          <>
            <Card title="Long List" headerBar padding="none">
              {!allBuyers.length ? (
                <>
                  <EmptyState
                    icon={Users}
                    title="Long List 후보 없음"
                    description="AI 자동 매핑으로 후보를 추가하세요."
                  />
                  {canWrite && (
                    <div className="flex justify-center gap-3 pb-6">
                      <Button
                        icon={Building2}
                        onClick={() => setShowFIRecommendModal(true)}
                        variant="primary"
                        size="sm"
                      >
                        FI 자동 추천
                      </Button>
                      <Button
                        icon={Sparkles}
                        onClick={() => setShowSIMappingModal(true)}
                        variant="primary"
                        size="sm"
                      >
                        SI 자동 매핑
                      </Button>
                    </div>
                  )}
                </>
              ) : (
                <>
                  {canWrite && (
                    <div className="flex items-center justify-between border-b border-border-default px-4 py-2">
                      <LongListFilters
                        filters={longListFilters}
                        onChange={setLongListFilters}
                      />
                      <div className="flex gap-2">
                        <Button
                          icon={Building2}
                          onClick={() => setShowFIRecommendModal(true)}
                          variant="primary"
                          size="sm"
                        >
                          FI 자동 추천
                        </Button>
                        <Button
                          icon={Sparkles}
                          onClick={() => setShowSIMappingModal(true)}
                          variant="primary"
                          size="sm"
                        >
                          SI 자동 매핑
                        </Button>
                      </div>
                    </div>
                  )}
                  {!canWrite && (
                    <div className="border-b border-border-default px-4 py-2">
                      <LongListFilters
                        filters={longListFilters}
                        onChange={setLongListFilters}
                      />
                    </div>
                  )}
                  <DataTable
                    columns={buyerColumns}
                    data={filteredBuyers}
                    keyField="id"
                  />
                </>
              )}
            </Card>
            {showSIMappingModal && (
              <Suspense
                fallback={
                  <p className="py-8 text-center text-sm text-text-muted">
                    로딩 중...
                  </p>
                }
              >
                <SIMappingPanel
                  txnId={txnId}
                  onClose={() => setShowSIMappingModal(false)}
                  corporateInfo={corporateInfo}
                />
              </Suspense>
            )}
            {showFIRecommendModal && (
              <FIRecommendModal
                open
                onClose={() => setShowFIRecommendModal(false)}
                txnId={txnId}
                existingCompanyNames={allBuyers.map((b) => b.company_name)}
              />
            )}
          </>
        )}

        {buyerSubTab === "short-list" && (
          <>
            <div className="flex gap-4">
              {shortListBuyers.length > 0 && (
                <div
                  className={
                    masterListOpen
                      ? "w-[280px] flex-shrink-0 transition-all duration-200"
                      : "w-0 overflow-hidden flex-shrink-0 transition-all duration-200"
                  }
                >
                  <ShortListMasterList
                    buyers={shortListBuyers}
                    stageMap={stageMap}
                    selectedBuyerId={selectedBuyerId}
                    onSelectBuyer={setSelectedBuyerId}
                    totalBuyerCount={allBuyers.length}
                  />
                </div>
              )}

              <div className="flex-1 min-w-0">
                {shortListViewMode === "grid" && (
                  <MarketingGridView
                    buyers={shortListBuyers}
                    stageMap={stageMap}
                    onSelectBuyer={setSelectedBuyerId}
                  />
                )}
                {shortListViewMode === "kanban" && (
                  <Suspense
                    fallback={
                      <p className="py-8 text-center text-sm text-text-muted">
                        로딩 중...
                      </p>
                    }
                  >
                    <MarketingKanbanView
                      buyers={shortListBuyers}
                      stageMap={stageMap}
                      onSelectBuyer={setSelectedBuyerId}
                    />
                  </Suspense>
                )}
                {shortListViewMode === "timeline" && (
                  <Suspense
                    fallback={
                      <p className="py-8 text-center text-sm text-text-muted">
                        로딩 중...
                      </p>
                    }
                  >
                    <MarketingTimelineView
                      buyers={shortListBuyers}
                      stageMap={stageMap}
                      onSelectBuyer={setSelectedBuyerId}
                      canWrite={canWrite}
                      txnId={txnId}
                    />
                  </Suspense>
                )}
              </div>
            </div>

            <BuyerDetailPanel
              txnId={txnId}
              buyer={selectedBuyer}
              stageSummary={selectedStageSummary}
              onClose={() => setSelectedBuyerId(null)}
              canWrite={canWrite}
              onToggleDrop={(buyerId, isCurrentlyDropped) =>
                updateBuyer.mutate(
                  {
                    buyerId,
                    body: {
                      // Drop 복구 시 IDENTIFIED로 초기화 — Short List 멤버십은 tier/flag 기반이므로 유지됨
                      status: isCurrentlyDropped ? "IDENTIFIED" : "BID_DROPPED",
                    },
                  },
                  {
                    onSuccess: () => {
                      toast.success(
                        isCurrentlyDropped
                          ? "복구되었습니다"
                          : "Drop 되었습니다",
                      );
                    },
                    onError: () => {
                      toast.error("상태 변경에 실패했습니다");
                    },
                  },
                )
              }
            />
          </>
        )}

        <SIDetailPanel
          companyId={buyerDetailCompanyId}
          onClose={() => setBuyerDetailCompanyId(null)}
        />
      </div>
    </>
  );
}
