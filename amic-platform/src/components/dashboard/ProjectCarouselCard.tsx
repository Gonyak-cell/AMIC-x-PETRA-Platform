/** MY PROJECTS — 캐러셀 프로젝트 카드 (Figma 카드형 위젯 기반) */

import { Briefcase } from "lucide-react";
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
      className="relative w-full overflow-hidden rounded-2xl cursor-pointer transition-transform duration-200 hover:scale-[1.01] active:scale-[0.99] text-left"
      style={{
        background: "linear-gradient(180deg, #1C8F57 0%, #27A96A 100%)",
        boxShadow:
          "0px 16px 24px rgba(0,0,0,0.06), 0px 2px 6px rgba(0,0,0,0.04), 0px 0px 1px rgba(0,0,0,0.04)",
      }}
    >
      {/* Decorative overlay — from Figma card pattern */}
      <div
        className="absolute -right-8 -bottom-8 w-48 h-48 rounded-full pointer-events-none"
        style={{ background: "rgba(255,255,255,0.08)" }}
      />
      <div
        className="absolute -right-4 -bottom-16 w-32 h-32 rounded-full pointer-events-none"
        style={{ background: "rgba(255,255,255,0.06)" }}
      />

      {/* Content */}
      <div className="relative z-10 p-6">
        {/* Top: brand + badge */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur-sm flex items-center justify-center">
              <Briefcase className="w-5 h-5 text-white" />
            </div>
            <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">
              AMIC Deal
            </span>
          </div>
          <Badge variant={statusVariant} className="text-[10px]">
            {statusLabel}
          </Badge>
        </div>

        {/* Middle: project identity */}
        <div className="mb-4">
          <div className="font-bold text-white text-xl leading-tight truncate">
            {txn.code_name}
          </div>
          <p className="text-sm text-white/60 truncate mt-1">
            {txn.target_company_name || txn.name}
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
