import { useMemo } from "react";
import { ChevronRight, FileText } from "lucide-react";
import {
  BUYER_TYPE_OPTIONS,
  DEAL_ROLE_LABELS,
  FUNNEL_NDA_AND_AFTER,
} from "@/modules/ma/constants";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { NDA } from "@/modules/ma/types/nda";
import BuyerCompanyLogo from "@/modules/ma/components/buyers/BuyerCompanyLogo";
import { getBuyerLogoUrl } from "@/modules/ma/utils/buyerLogo";
import { Badge, Card, DataTable, EmptyState } from "@/components/ui";
import type { Column } from "@/components/ui";

type TierKey = "TIER_1" | "TIER_2" | "TIER_3";

interface BuyerNdaStageBoardProps {
  buyers: BuyerCandidate[];
  ndaByBuyerId: Map<string, NDA>;
  onSelectBuyer: (buyerId: string) => void;
}

function resolveNdaStatus(buyer: BuyerCandidate, nda?: NDA) {
  if (nda?.status === "SIGNED" || FUNNEL_NDA_AND_AFTER.has(buyer.status)) {
    return { label: "SIGNED", variant: "success" as const };
  }
  if (nda?.status === "SENT") {
    return { label: "SENT", variant: "warning" as const };
  }
  if (nda?.status) {
    return { label: nda.status, variant: "neutral" as const };
  }
  return { label: "UPLOAD", variant: "neutral" as const };
}

function getTierTitle(tier: TierKey): string {
  return {
    TIER_1: "Tier 1",
    TIER_2: "Tier 2",
    TIER_3: "Tier 3",
  }[tier];
}

export default function BuyerNdaStageBoard({
  buyers,
  ndaByBuyerId,
  onSelectBuyer,
}: BuyerNdaStageBoardProps) {
  const columns = useMemo((): Column<BuyerCandidate>[] => {
    return [
      {
        key: "company_name",
        header: "Long List",
        minWidth: "240px",
        render: (buyer) => (
          <div className="flex items-center gap-3">
            <BuyerCompanyLogo
              logoUrl={getBuyerLogoUrl(buyer.extra_data)}
              name={buyer.company_name}
              size="sm"
            />
            <div className="min-w-0">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onSelectBuyer(buyer.id);
                }}
                className="truncate text-left font-medium text-text-dark hover:text-accent hover:underline"
              >
                {buyer.company_name}
              </button>
              <p className="mt-1 truncate text-xs text-text-muted">
                {buyer.contact_name ?? "담당자 미등록"}
              </p>
            </div>
          </div>
        ),
      },
      {
        key: "buyer_type",
        header: "유형",
        minWidth: "160px",
        render: (buyer) => (
          <Badge variant="neutral">
            {BUYER_TYPE_OPTIONS.find((option) => option.value === buyer.buyer_type)
              ?.label ?? buyer.buyer_type}
          </Badge>
        ),
      },
      {
        key: "deal_role",
        header: "역할",
        minWidth: "140px",
        render: (buyer) => (
          <span className="text-sm text-text-secondary">
            {buyer.deal_role
              ? DEAL_ROLE_LABELS[buyer.deal_role] ?? buyer.deal_role
              : "-"}
          </span>
        ),
      },
      {
        key: "nda_status",
        header: "NDA",
        align: "right",
        width: "140px",
        render: (buyer) => {
          const status = resolveNdaStatus(buyer, ndaByBuyerId.get(buyer.id));

          return (
            <div className="flex items-center justify-end gap-2">
              <Badge variant={status.variant}>{status.label}</Badge>
              <ChevronRight className="h-4 w-4 text-text-muted" />
            </div>
          );
        },
      },
    ];
  }, [ndaByBuyerId, onSelectBuyer]);

  const tierSections = useMemo(
    () =>
      (["TIER_1", "TIER_2", "TIER_3"] as TierKey[]).map((tier) => ({
        tier,
        title: getTierTitle(tier),
        buyers: buyers.filter((buyer) => buyer.tier === tier),
      })),
    [buyers],
  );

  if (buyers.length === 0) {
    return (
      <Card padding="none">
        <EmptyState
          icon={FileText}
          title="NDA 대상이 없습니다"
          description="Long List에서 Tier 1-3 후보를 지정하면 NDA 체결 단계가 열립니다."
        />
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card className="border-accent/20 bg-accent/5" padding="sm">
        <div className="flex flex-col gap-2 px-1 py-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-heading text-base font-semibold text-amic">
              NDA 체결
            </h3>
            <p className="mt-1 text-sm text-text-secondary">
              Tier 1-3 후보를 클릭해 NDA 버전 업로드, 버전 확인, 날인을 진행하세요.
            </p>
          </div>
          <Badge variant="info">{buyers.length}개 후보</Badge>
        </div>
      </Card>

      {tierSections.map((section) => (
        <Card
          key={section.tier}
          title={section.title}
          headerBar
          padding="none"
          actions={<Badge variant="neutral">{section.buyers.length}</Badge>}
        >
          <DataTable
            columns={columns}
            data={section.buyers}
            keyField="id"
            emptyMessage={`${section.title} 대상이 없습니다.`}
            onRowClick={(buyer) => onSelectBuyer(buyer.id)}
          />
        </Card>
      ))}
    </div>
  );
}
