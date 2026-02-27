import { DataTable, Badge } from "@/components/ui";
import type { Column } from "@/components/ui";
import type { GPResearchItem } from "@/modules/kiis/types/gpResearch";
import { LICENSE_SHORT_LABELS } from "@/modules/kiis/types/gpResearch";
import type { LicenseType } from "@/modules/kiis/types/gpResearch";
import { Building2 } from "lucide-react";

interface GPMasterListProps {
  data: GPResearchItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  isLoading?: boolean;
}

const LICENSE_BADGE_VARIANT: Record<
  LicenseType,
  "info" | "success" | "warning"
> = {
  pef: "info",
  vc: "success",
  nta: "warning",
};

const columns: Column<GPResearchItem>[] = [
  {
    key: "name",
    header: "운용사",
    width: "240px",
    render: (row) => (
      <div className="flex items-center gap-2.5">
        <div className="h-8 w-8 rounded-full bg-amic-50 flex items-center justify-center shrink-0">
          <Building2 className="h-4 w-4 text-amic" />
        </div>
        <div className="min-w-0">
          <p className="font-medium text-text-dark truncate text-sm">
            {row.name}
          </p>
          {row.nameEn && (
            <p className="text-[11px] text-text-secondary truncate">
              {row.nameEn}
            </p>
          )}
        </div>
      </div>
    ),
  },
  {
    key: "established",
    header: "설립",
    align: "center",
    width: "90px",
    render: (row) => (
      <span className="text-xs text-text-secondary">{row.established}</span>
    ),
  },
  {
    key: "licenses",
    header: "라이선스",
    width: "140px",
    render: (row) => (
      <div className="flex gap-1 flex-wrap">
        {row.licenses.map((l) => (
          <Badge key={l} variant={LICENSE_BADGE_VARIANT[l]} pill>
            {LICENSE_SHORT_LABELS[l]}
          </Badge>
        ))}
      </div>
    ),
  },
  {
    key: "cumAum",
    header: "누적 AUM",
    align: "right",
    width: "120px",
    mono: true,
    render: (row) => {
      if (row.cumAum >= 10000) {
        return `${(row.cumAum / 10000).toFixed(1)}조`;
      }
      return `${row.cumAum.toLocaleString()}억`;
    },
  },
  {
    key: "activeFundCount",
    header: "활성 펀드",
    align: "center",
    width: "80px",
    render: (row) => (
      <span className="font-medium tabular-nums">{row.activeFundCount}</span>
    ),
  },
  {
    key: "keyPerson",
    header: "대표 인력",
    width: "100px",
    render: (row) => (
      <span className="text-sm text-text-body">{row.keyPerson}</span>
    ),
  },
];

export function GPMasterList({ data, onSelect, isLoading }: GPMasterListProps) {
  return (
    <DataTable<GPResearchItem>
      columns={columns}
      data={data}
      keyField="id"
      onRowClick={(row) => onSelect(row.id)}
      loading={isLoading}
      striped
      emptyMessage="조건에 맞는 GP가 없습니다."
    />
  );
}
