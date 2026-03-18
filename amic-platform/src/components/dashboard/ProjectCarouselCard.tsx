/** MY PROJECTS — 캐러셀 프로젝트 카드 (Figma 카드형 위젯 기반) */

import { Badge } from "@/components/ui";
import { PHASE_CONFIG } from "@/modules/ma/constants";
import { TRANSACTION_STATUS_VARIANT } from "@/modules/ma/constants/status-variants";
import { TRANSACTION_STATUS_OPTIONS } from "@/modules/ma/constants/transaction";
import type { Transaction } from "@/modules/ma/types/transaction";

const PHASE_LABEL: Record<string, string> = {};
for (const p of PHASE_CONFIG) {
  PHASE_LABEL[p.phase] = p.label;
}

const STATUS_LABEL: Record<string, string> = {};
for (const o of TRANSACTION_STATUS_OPTIONS) {
  if (o.value) STATUS_LABEL[o.value] = o.label;
}

interface ProjectCarouselCardProps {
  transaction: Transaction;
  onClick: () => void;
}

export default function ProjectCarouselCard({
  transaction: txn,
  onClick,
}: ProjectCarouselCardProps) {
  const phaseLabel = PHASE_LABEL[txn.phase] ?? txn.phase;
  const statusLabel = STATUS_LABEL[txn.status] ?? txn.status;
  const statusVariant = TRANSACTION_STATUS_VARIANT[txn.status] ?? "neutral";

  return (
    <button
      type="button"
      onClick={onClick}
      className="relative w-full overflow-hidden rounded-2xl cursor-pointer transition-all duration-300 hover:scale-[1.01] active:scale-[0.99] text-left"
      style={{
        background:
          "radial-gradient(ellipse at 75% 50%, rgba(26,140,82,0.6) 0%, transparent 60%), radial-gradient(ellipse at 20% 70%, rgba(15,107,62,0.4) 0%, transparent 50%), radial-gradient(ellipse at 0% 0%, rgba(0,0,0,0.3) 0%, transparent 35%), linear-gradient(150deg, #0d5a33 0%, #128850 35%, #1a8c52 65%, #0F6B3E 100%)",
        boxShadow:
          "0px 16px 32px rgba(0,0,0,0.15), 0px 4px 8px rgba(0,0,0,0.08)",
      }}
    >
      {/* Glassmorphism overlay */}
      <div
        className="absolute inset-0 rounded-2xl border border-white/30 pointer-events-none"
        style={{
          background:
            "linear-gradient(135deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.02) 40%, rgba(255,255,255,0.06) 100%)",
          boxShadow:
            "inset 0 1px 1px rgba(255,255,255,0.4), inset 0 -1px 1px rgba(255,255,255,0.06)",
        }}
      />
      {/* Glass top highlight */}
      <div
        className="absolute left-0 top-0 w-full pointer-events-none z-10"
        style={{
          height: "2px",
          background:
            "linear-gradient(90deg, transparent 5%, rgba(255,255,255,0.6) 50%, transparent 95%)",
        }}
      />
      {/* Glass left edge */}
      <div
        className="absolute left-0 top-0 h-full pointer-events-none z-10"
        style={{
          width: "1px",
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.08) 100%)",
        }}
      />

      {/* Content */}
      <div className="relative z-10 p-6">
        {/* Top: badge only */}
        <div className="flex items-center justify-end mb-6">
          <Badge variant={statusVariant} className="text-[10px]">
            {statusLabel}
          </Badge>
        </div>

        {/* Middle: project identity */}
        <div className="mb-4">
          <div className="font-bold text-white text-xl leading-tight truncate">
            {txn.name}
          </div>
          <p className="text-sm text-white/60 truncate mt-1">
            {txn.target_company_name}
          </p>
        </div>

        {/* Bottom: phase */}
        <div className="flex items-center gap-2 pt-3 border-t border-white/10">
          <span className="text-xs text-white/50">Phase</span>
          <span className="text-sm font-medium text-white">{phaseLabel}</span>
        </div>
      </div>
    </button>
  );
}
