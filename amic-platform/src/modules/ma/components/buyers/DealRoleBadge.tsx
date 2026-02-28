import type { DealRole } from "@/modules/ma/types/buyer";
import { DEAL_ROLE_LABELS } from "@/modules/ma/constants";

const ROLE_STYLES: Record<string, string> = {
  SOLE_BUYER: "bg-gray-100 text-gray-600",
  CONSORTIUM_LEAD: "bg-purple-50 text-purple-700",
  CO_INVESTOR: "bg-indigo-50 text-indigo-700",
  FINANCING_PROVIDER: "bg-cyan-50 text-cyan-700",
};

interface DealRoleBadgeProps {
  role: DealRole | null;
}

export default function DealRoleBadge({ role }: DealRoleBadgeProps) {
  if (!role) {
    return <span className="text-xs text-text-muted italic">미지정</span>;
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${ROLE_STYLES[role] ?? "bg-gray-100 text-gray-500"}`}
    >
      {DEAL_ROLE_LABELS[role] ?? role}
    </span>
  );
}
