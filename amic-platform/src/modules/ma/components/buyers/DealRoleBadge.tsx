import { Badge } from "@/components/ui";
import type { DealRole } from "@/modules/ma/types/buyer";
import { DEAL_ROLE_LABELS } from "@/modules/ma/constants";

const ROLE_STYLES: Record<string, string> = {
  SOLE_BUYER: "bg-gray-100 text-gray-600",
  CONSORTIUM_LEAD: "bg-accent-light text-amic-400",
  CO_INVESTOR: "bg-amic-50 text-amic-400",
  FINANCING_PROVIDER: "bg-amic-100 text-amic-500",
};

interface DealRoleBadgeProps {
  role: DealRole | null;
}

export default function DealRoleBadge({ role }: DealRoleBadgeProps) {
  if (!role) {
    return <span className="text-xs text-text-muted italic">미지정</span>;
  }

  return (
    <Badge pill className={ROLE_STYLES[role] ?? "bg-gray-100 text-gray-500"}>
      {DEAL_ROLE_LABELS[role] ?? role}
    </Badge>
  );
}
