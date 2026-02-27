import { Badge } from "@/components/ui/Badge";
import { CONTRACT_TYPE_OPTIONS } from "@/modules/ma/constants";
import type { Contract } from "@/modules/ma/types/contract";

interface ContractSelectorProps {
  contracts: Contract[];
  selectedContractId: string | null;
  onSelect: (contractId: string) => void;
  issueCountByContract?: Record<string, number>;
}

export function ContractSelector({ contracts, selectedContractId, onSelect, issueCountByContract }: ContractSelectorProps) {
  if (!contracts.length) return null;

  // 타입별로 그룹핑
  const byType = contracts.reduce<Record<string, Contract[]>>((acc, c) => {
    const key = c.contract_type;
    if (!acc[key]) acc[key] = [];
    acc[key].push(c);
    return acc;
  }, {});

  return (
    <div className="flex flex-wrap items-center gap-2">
      {Object.entries(byType).map(([type, typeContracts]) => {
        const label = CONTRACT_TYPE_OPTIONS.find((o) => o.value === type)?.label ?? type;
        const shortLabel = label.split("(")[0].trim() || label.split(" ")[0];
        const isSelected = typeContracts.some((c) => c.id === selectedContractId);

        if (typeContracts.length === 1) {
          const c = typeContracts[0];
          const issueCount = issueCountByContract?.[c.id] ?? 0;
          return (
            <button
              key={c.id}
              onClick={() => onSelect(c.id)}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                isSelected
                  ? "bg-primary-600 text-white shadow-sm"
                  : "bg-gray-100 text-text-secondary hover:bg-gray-200"
              }`}
            >
              {shortLabel}
              {issueCount > 0 && (
                <Badge variant={isSelected ? "neutral" : "warning"} className="ml-1 text-[10px]">
                  {issueCount}
                </Badge>
              )}
            </button>
          );
        }

        // 동일 타입 복수 계약
        return (
          <div key={type} className="relative">
            <select
              value={typeContracts.find((c) => c.id === selectedContractId)?.id ?? ""}
              onChange={(e) => { if (e.target.value) onSelect(e.target.value); }}
              className={`appearance-none rounded-full px-3 py-1.5 pr-6 text-xs font-medium transition-colors cursor-pointer ${
                isSelected
                  ? "bg-primary-600 text-white"
                  : "bg-gray-100 text-text-secondary hover:bg-gray-200"
              }`}
            >
              <option value="" disabled>{shortLabel} ({typeContracts.length})</option>
              {typeContracts.map((c) => (
                <option key={c.id} value={c.id}>{c.title}</option>
              ))}
            </select>
          </div>
        );
      })}
    </div>
  );
}
