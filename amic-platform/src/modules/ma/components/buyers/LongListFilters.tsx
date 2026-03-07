import { Search } from "lucide-react";
import { Select, Input } from "@/components/ui";
import {
  BUYER_TYPE_OPTIONS,
  BUYER_TIER_OPTIONS,
  BUYER_STATUS_OPTIONS,
} from "@/modules/ma/constants";

export interface LongListFilterState {
  type: string | null;
  tier: string | null;
  status: string | null;
  search: string;
}

interface LongListFiltersProps {
  filters: LongListFilterState;
  onChange: (filters: LongListFilterState) => void;
}

export default function LongListFilters({
  filters,
  onChange,
}: LongListFiltersProps) {
  const handleSelect =
    (field: "type" | "tier" | "status") =>
    (e: React.ChangeEvent<HTMLSelectElement>) => {
      const value = e.target.value;
      onChange({ ...filters, [field]: value === "" ? null : value });
    };

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({ ...filters, search: e.target.value });
  };

  return (
    <div className="flex items-center gap-3 font-body">
      <div className="w-40">
        <Select
          options={BUYER_TYPE_OPTIONS}
          value={filters.type ?? ""}
          onChange={handleSelect("type")}
        />
      </div>

      <div className="w-32">
        <Select
          options={BUYER_TIER_OPTIONS}
          value={filters.tier ?? ""}
          onChange={handleSelect("tier")}
        />
      </div>

      <div className="w-36">
        <Select
          options={BUYER_STATUS_OPTIONS}
          value={filters.status ?? ""}
          onChange={handleSelect("status")}
        />
      </div>

      <div className="relative w-48">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary pointer-events-none" />
        <Input
          value={filters.search}
          onChange={handleSearch}
          placeholder="회사명 검색..."
          className="pl-9"
        />
      </div>
    </div>
  );
}

export type { LongListFilterState as LongListFilterStateType };
