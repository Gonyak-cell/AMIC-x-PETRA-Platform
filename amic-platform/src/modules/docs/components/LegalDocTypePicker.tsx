import { Scale, Users, Building2, TrendingUp, Handshake } from "lucide-react";
import type { LegalDocType } from "@/modules/docs/types/legal_document";
import { LEGAL_DOC_META } from "@/modules/docs/types/legal_document";
import { cn } from "@/lib/cn";

const ICONS: Record<LegalDocType, React.ComponentType<{ className?: string }>> = {
  SPA: Scale,
  SHA: Users,
  BTA: Building2,
  SSA: TrendingUp,
  MOU: Handshake,
};

interface LegalDocTypePickerProps {
  value: LegalDocType | null;
  onChange: (type: LegalDocType) => void;
}

export default function LegalDocTypePicker({ value, onChange }: LegalDocTypePickerProps) {
  const types: LegalDocType[] = ["SPA", "SHA", "BTA", "SSA"];

  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2"
      role="radiogroup"
      aria-label="법률 문서 유형 선택"
    >
      {types.map((type) => {
        const meta = LEGAL_DOC_META[type];
        const Icon = ICONS[type];
        const selected = value === type;

        return (
          <button
            key={type}
            type="button"
            role="radio"
            aria-checked={selected}
            aria-label={`${meta.labelKo} (${type}) — ${meta.description}`}
            onClick={() => onChange(type)}
            className={cn(
              "flex flex-col gap-4 rounded-xl border-2 p-6 text-left transition-all",
              selected
                ? "border-amic bg-amic/5 ring-1 ring-amic/20 shadow-dr-sm"
                : "border-gray-border bg-white hover:border-amic/40 hover:bg-bg-cool hover:shadow-dr-sm",
            )}
          >
            {/* 헤더 */}
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                  selected ? "bg-amic text-white" : "bg-bg-cool text-text-secondary",
                )}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <h3
                  className={cn(
                    "text-base font-heading font-semibold",
                    selected ? "text-amic" : "text-text-dark",
                  )}
                >
                  {meta.labelKo}
                </h3>
                <p className="truncate text-xs text-text-secondary">
                  {type} &middot; {meta.label}
                </p>
              </div>
            </div>

            {/* 설명 */}
            <p className="text-sm leading-relaxed text-text-secondary">{meta.description}</p>

            {/* 하이라이트 배지 */}
            <div className="flex flex-wrap gap-1.5">
              {meta.highlights.map((h) => (
                <span
                  key={h}
                  className={cn(
                    "rounded px-2 py-0.5 text-xs font-medium",
                    selected ? "bg-amic/10 text-amic" : "bg-bg-cool text-text-secondary",
                  )}
                >
                  {h}
                </span>
              ))}
            </div>
          </button>
        );
      })}
    </div>
  );
}
