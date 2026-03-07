import { useState, useEffect, useMemo, lazy, Suspense } from "react";
import { Users, Download, Building2, Sparkles } from "lucide-react";
import {
  useBuyers,
  useAddBuyer,
  useUpdateBuyer,
  useExportBuyerExcel,
  useTransaction,
} from "@/modules/ma/hooks/useTransactions";
import { useShortListOverview } from "@/modules/ma/hooks/useMarketingLogs";
import { useSICompanyByName } from "@/modules/ma/hooks/useSIMapping";
import type { CorporateDocsExtractedData } from "@/modules/ma/types/document_extraction";
import type {
  BuyerCandidate,
  BuyerCandidateCreate,
  BuyerTier,
  DealRole,
} from "@/modules/ma/types/buyer";
import {
  BUYER_TYPE_OPTIONS,
  BUYER_TIER_OPTIONS,
  DEAL_ROLE_OPTIONS,
} from "@/modules/ma/constants";
import BuyerTierBadge from "@/modules/ma/components/buyers/BuyerTierBadge";
import DealRoleBadge from "@/modules/ma/components/buyers/DealRoleBadge";
import ConsortiumPanel from "@/modules/ma/components/buyers/ConsortiumPanel";
import FunnelKPIBar from "@/modules/ma/components/buyers/FunnelKPIBar";
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
import { toast } from "sonner";

import {
  Badge,
  Button,
  Card,
  DataTable,
  EmptyState,
  InlineSelect,
  Input,
  Modal,
  Select,
  Tabs,
} from "@/components/ui";
import type { Column } from "@/components/ui";

interface BuyersTabProps {
  txnId: string;
  canWrite: boolean;
}

export default function BuyersTab({ txnId, canWrite }: BuyersTabProps) {
  const { data: buyers } = useBuyers(txnId);
  const { data: txn } = useTransaction(txnId);
  const addBuyer = useAddBuyer(txnId);
  const updateBuyer = useUpdateBuyer(txnId);
  const exportExcel = useExportBuyerExcel(txnId);
  const { data: shortListOverview } = useShortListOverview(txnId);

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

  // Buyer modal state
  const [showBuyerModal, setShowBuyerModal] = useState(false);
  const [buyerForm, setBuyerForm] = useState<BuyerCandidateCreate>({
    company_name: "",
    buyer_type: "STRATEGIC",
  });

  const tierOptions = BUYER_TIER_OPTIONS.filter((o) => o.value !== "");

  const buyerColumns: Column<BuyerCandidate>[] = [
    {
      key: "is_short_listed" as keyof BuyerCandidate,
      header: <span className="sr-only">Short-List</span>,
      minWidth: "40px",
      render: (r) => (
        <input
          type="checkbox"
          checked={r.is_short_listed}
          disabled={!canWrite || updateBuyer.isPending}
          onChange={() =>
            updateBuyer.mutate({
              buyerId: r.id,
              body: {
                is_short_listed: !r.is_short_listed,
              },
            })
          }
          className="h-4 w-4 rounded border-border-default accent-accent"
          title={r.is_short_listed ? "Short-List 해제" : "Short-List 승격"}
        />
      ),
    },
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
            options={[{ value: "", label: "-" }, ...tierOptions]}
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
  ];

  const allBuyers = useMemo(() => buyers ?? [], [buyers]);
  const shortListBuyers = allBuyers.filter((b) => b.is_short_listed);

  // Client-side filtering for Long List
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
    if (longListFilters.search) {
      const q = longListFilters.search.toLowerCase();
      result = result.filter((b) => b.company_name.toLowerCase().includes(q));
    }
    return result;
  }, [allBuyers, longListFilters]);

  // Derive selected buyer and its stage summary for SlidePanel
  const selectedBuyer = useMemo(
    () => allBuyers.find((b) => b.id === selectedBuyerId) ?? null,
    [allBuyers, selectedBuyerId],
  );
  const selectedStageSummary = useMemo(
    () => (shortListOverview ?? []).find((s) => s.buyer_id === selectedBuyerId),
    [shortListOverview, selectedBuyerId],
  );

  return (
    <>
      <div className="space-y-4">
        {/* Funnel KPI Bar */}
        <FunnelKPIBar buyers={allBuyers} />

        <div className="flex items-center justify-between">
          <Tabs
            tabs={[
              {
                id: "long-list",
                label: "Long List",
                badge: allBuyers.length || undefined,
              },
              {
                id: "short-list",
                label: "Short List",
                badge: shortListBuyers.length || undefined,
              },
            ]}
            activeTab={buyerSubTab}
            onTabChange={(tab) =>
              setBuyerSubTab(tab as "long-list" | "short-list")
            }
            variant="pill"
            size="sm"
          />
          <div className="flex items-center gap-2">
            {buyerSubTab === "short-list" && (
              <ShortListViewToggle
                viewMode={shortListViewMode}
                onViewModeChange={setShortListViewMode}
              />
            )}
            {buyerSubTab === "long-list" && (
              <Button
                icon={Download}
                onClick={() => exportExcel.mutate()}
                variant="ghost"
                size="sm"
                loading={exportExcel.isPending}
              >
                Excel
              </Button>
            )}
          </div>
        </div>

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
            {shortListViewMode === "grid" && (
              <MarketingGridView
                buyers={shortListBuyers}
                overviewData={shortListOverview ?? []}
                onSelectBuyer={setSelectedBuyerId}
                canWrite={canWrite}
                txnId={txnId}
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
                  overviewData={shortListOverview ?? []}
                  onSelectBuyer={setSelectedBuyerId}
                  canWrite={canWrite}
                  txnId={txnId}
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
                  overviewData={shortListOverview ?? []}
                  onSelectBuyer={setSelectedBuyerId}
                  canWrite={canWrite}
                  txnId={txnId}
                />
              </Suspense>
            )}
            <ShortListMasterList
              buyers={shortListBuyers}
              overviewData={shortListOverview ?? []}
              selectedBuyerId={selectedBuyerId}
              onSelectBuyer={setSelectedBuyerId}
              totalBuyerCount={allBuyers.length}
            />
            <BuyerDetailPanel
              txnId={txnId}
              buyer={selectedBuyer}
              stageSummary={selectedStageSummary}
              onClose={() => setSelectedBuyerId(null)}
              canWrite={canWrite}
            />
            <ConsortiumPanel
              txnId={txnId}
              buyers={allBuyers}
              canWrite={canWrite}
            />
          </>
        )}

        <SIDetailPanel
          companyId={buyerDetailCompanyId}
          onClose={() => setBuyerDetailCompanyId(null)}
        />
      </div>

      {/* Buyer 추가 모달 */}
      <Modal
        open={showBuyerModal}
        onClose={() => setShowBuyerModal(false)}
        title="매수자 후보 추가"
      >
        <form
          onSubmit={(e) => {
            e.preventDefault();
            addBuyer.mutate(buyerForm, {
              onSuccess: () => {
                setShowBuyerModal(false);
                setBuyerForm({ company_name: "", buyer_type: "STRATEGIC" });
              },
            });
          }}
          className="space-y-4"
        >
          <Input
            label="회사명"
            required
            value={buyerForm.company_name}
            onChange={(e) =>
              setBuyerForm({ ...buyerForm, company_name: e.target.value })
            }
            placeholder="매수 후보 기업명"
          />
          <Select
            label="유형"
            options={BUYER_TYPE_OPTIONS.filter((o) => o.value !== "")}
            value={buyerForm.buyer_type}
            onChange={(e) =>
              setBuyerForm({
                ...buyerForm,
                buyer_type: e.target
                  .value as BuyerCandidateCreate["buyer_type"],
              })
            }
          />
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="담당자"
              value={buyerForm.contact_name ?? ""}
              onChange={(e) =>
                setBuyerForm({
                  ...buyerForm,
                  contact_name: e.target.value || undefined,
                })
              }
            />
            <Input
              label="이메일"
              type="email"
              value={buyerForm.contact_email ?? ""}
              onChange={(e) =>
                setBuyerForm({
                  ...buyerForm,
                  contact_email: e.target.value || undefined,
                })
              }
            />
          </div>
          <Input
            label="비고"
            value={buyerForm.notes ?? ""}
            onChange={(e) =>
              setBuyerForm({
                ...buyerForm,
                notes: e.target.value || undefined,
              })
            }
          />
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="ghost"
              type="button"
              onClick={() => setShowBuyerModal(false)}
            >
              취소
            </Button>
            <Button type="submit" loading={addBuyer.isPending}>
              추가
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
