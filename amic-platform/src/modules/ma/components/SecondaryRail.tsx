import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ShieldAlert,
  CheckSquare,
  ClipboardCheck,
  CalendarDays,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  RAIL_TOOL_IDS,
  RAIL_TOOL_PHASE_RULES,
  type RailToolId,
} from "@/modules/ma/constants";
import type { TransactionPhase } from "@/modules/ma/types/transaction";
import {
  buildRailOpenPath,
  buildRailClosePath,
} from "@/modules/ma/pages/workspace/railRouteHelpers";

// ── 아이콘 매핑 ──────────────────────────────────────
const RAIL_ICONS: Record<RailToolId, LucideIcon> = {
  risks: ShieldAlert,
  compliance: CheckSquare,
  "notes-approvals": ClipboardCheck,
  timeline: CalendarDays,
  "ai-quality": Sparkles,
};

const RAIL_LABELS: Record<RailToolId, string> = {
  risks: "리스크",
  compliance: "컴플라이언스",
  "notes-approvals": "노트/승인",
  timeline: "타임라인",
  "ai-quality": "AI 품질",
};

// ── Props ──────────────────────────────────────────
interface SecondaryRailProps {
  txnId: string;
  txnPhase: TransactionPhase | undefined;
  activeRailTool: RailToolId | null;
  /** rail tool 닫기 시 복귀할 primary tab */
  baseTab: string;
}

// ── Component ──────────────────────────────────────
export default function SecondaryRail({
  txnId,
  txnPhase,
  activeRailTool,
  baseTab,
}: SecondaryRailProps) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const handleRailClick = (toolId: RailToolId) => {
    if (activeRailTool === toolId) {
      // 이미 활성화된 아이콘 클릭 → 닫기 (baseTab으로 복귀)
      navigate(buildRailClosePath(txnId, baseTab, searchParams), {
        replace: true,
      });
    } else {
      // 새 rail tool 열기 — 현재 baseTab을 쿼리에 보존
      navigate(buildRailOpenPath(txnId, toolId, baseTab, searchParams), {
        replace: true,
      });
    }
  };

  // phase별 노출 여부 결정
  const visibleTools = (RAIL_TOOL_IDS as readonly RailToolId[]).filter(
    (toolId) => {
      if (!txnPhase) return false;
      const allowedPhases = RAIL_TOOL_PHASE_RULES[toolId];
      return allowedPhases.length === 0 || allowedPhases.includes(txnPhase);
    },
  );

  if (visibleTools.length === 0) return null;

  return (
    <div className="flex flex-col items-center gap-1 w-10 py-2">
      {visibleTools.map((toolId) => {
        const Icon = RAIL_ICONS[toolId];
        const isActive = activeRailTool === toolId;
        return (
          <button
            key={toolId}
            title={RAIL_LABELS[toolId]}
            onClick={() => handleRailClick(toolId)}
            className={[
              "flex items-center justify-center w-8 h-8 rounded-lg transition-colors",
              isActive
                ? "bg-accent text-white"
                : "text-text-secondary hover:bg-bg-cool hover:text-text-dark",
            ].join(" ")}
          >
            <Icon size={16} />
          </button>
        );
      })}
    </div>
  );
}
