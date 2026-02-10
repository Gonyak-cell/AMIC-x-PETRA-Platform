interface ScopeSelectorProps {
  scopeQoe: boolean;
  scopeNwc: boolean;
  scopeDebt: boolean;
  onScopeChange: (field: "scope_qoe" | "scope_nwc" | "scope_debt", value: boolean) => void;
}

const SCOPE_ITEMS = [
  {
    field: "scope_qoe" as const,
    label: "Quality of Earnings (QoE)",
    description: "비경상 항목 조정을 통한 EBITDA 분석",
  },
  {
    field: "scope_nwc" as const,
    label: "Net Working Capital (NWC)",
    description: "운전자본 추세 및 Target NWC 분석",
  },
  {
    field: "scope_debt" as const,
    label: "Net Debt",
    description: "순부채 및 부채성 항목 분류",
  },
];

export default function ScopeSelector({
  scopeQoe,
  scopeNwc,
  scopeDebt,
  onScopeChange,
}: ScopeSelectorProps) {
  const values: Record<string, boolean> = {
    scope_qoe: scopeQoe,
    scope_nwc: scopeNwc,
    scope_debt: scopeDebt,
  };

  return (
    <div className="space-y-4">
      {SCOPE_ITEMS.map((item) => (
        <label
          key={item.field}
          className="flex items-start gap-3 p-4 rounded-lg border border-gray-border hover:border-amic cursor-pointer transition-colors"
        >
          <input
            type="checkbox"
            checked={values[item.field]}
            onChange={(e) => onScopeChange(item.field, e.target.checked)}
            className="mt-0.5 rounded border-gray-border text-amic focus:ring-amic h-4 w-4"
          />
          <div>
            <div className="text-sm font-medium text-text-dark">{item.label}</div>
            <div className="text-xs text-text-secondary mt-0.5">{item.description}</div>
          </div>
        </label>
      ))}
    </div>
  );
}
