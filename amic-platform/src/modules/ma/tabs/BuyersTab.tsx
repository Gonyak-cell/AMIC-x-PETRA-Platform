import { useState, useEffect, lazy, Suspense } from "react";
import { Users, UserPlus, Download, Building2, Sparkles } from "lucide-react";
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
  BuyerCandidateUpdate,
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
import ShortListOverview from "@/modules/ma/components/buyers/ShortListOverview";
import FIRecommendModal from "@/modules/ma/components/buyers/FIRecommendModal";
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

  const corporateInfo = ((): CorporateDocsExtractedData | null => {
    const v = txn?.corporate_info;
    if (
      typeof v === "object" &&
      v !== null &&
      ("corporate_registration_number" in v ||
        "business_registration_number" in v)
    ) {
      return v as CorporateDocsExtractedData;
    }
    return null;
  })();

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
          disabled={!canWrite}
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

  const allBuyers = buyers ?? [];
  const shortListBuyers = allBuyers.filter((b) => b.is_short_listed);

  return (
    <>
      <div className="space-y-4">
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
            {canWrite && (
              <Button
                icon={UserPlus}
                onClick={() => {
                  setBuyerForm({ company_name: "", buyer_type: "STRATEGIC" });
                  setShowBuyerModal(true);
                }}
                variant="ghost"
              >
                후보 추가
              </Button>
            )}
          </div>
        </div>

        {buyerSubTab === "long-list" && (
          <>
            <div className="mb-3 flex justify-end gap-2">
              <Button
                icon={Building2}
                onClick={() => setShowFIRecommendModal(true)}
                variant="secondary"
                size="sm"
              >
                FI 자동 추천
              </Button>
              <Button
                icon={Sparkles}
                onClick={() => setShowSIMappingModal(true)}
                variant="secondary"
                size="sm"
              >
                SI 자동 매핑
              </Button>
            </div>
            <Card title="Long List" headerBar padding="none">
              {!allBuyers.length ? (
                <EmptyState
                  icon={Users}
                  title="Long List 후보 없음"
                  description="잠재 매수자를 추가하세요."
                  actionLabel={canWrite ? "후보 추가" : undefined}
                  onAction={
                    canWrite ? () => setShowBuyerModal(true) : undefined
                  }
                />
              ) : (
                <DataTable
                  columns={buyerColumns}
                  data={allBuyers}
                  keyField="id"
                />
              )}
            </Card>
            {showSIMappingModal && (
              <Suspense
                fallback={
                  <p className="py-8 text-center text-sm text-slate-400">
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
            <ShortListOverview
              txnId={txnId}
              buyers={allBuyers}
              overviewData={shortListOverview ?? []}
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
