import type { TeamMember } from "@/types/collaboration";

interface TeamAvatarsProps {
  members: TeamMember[];
  max?: number;
  size?: "sm" | "md";
}

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const COLORS = [
  "bg-blue-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-violet-500",
  "bg-cyan-500",
];

function hashColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = id.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

const SIZE_CLASSES = {
  sm: "w-7 h-7 text-[10px]",
  md: "w-8 h-8 text-xs",
};

export function TeamAvatars({ members, max = 3, size = "sm" }: TeamAvatarsProps) {
  if (members.length === 0) return null;

  const visible = members.slice(0, max);
  const overflow = members.length - max;

  return (
    <div className="flex -space-x-2" aria-label={`Team: ${members.map((m) => m.display_name).join(", ")}`}>
      {visible.map((member) => (
        <div
          key={member.user_id}
          className={`${SIZE_CLASSES[size]} ${hashColor(member.user_id)} rounded-full flex items-center justify-center text-white font-medium ring-2 ring-white`}
          title={`${member.display_name} (${member.role})`}
        >
          {getInitials(member.display_name)}
        </div>
      ))}
      {overflow > 0 && (
        <div
          className={`${SIZE_CLASSES[size]} bg-gray-400 rounded-full flex items-center justify-center text-white font-medium ring-2 ring-white`}
          title={`${overflow} more member${overflow > 1 ? "s" : ""}`}
        >
          +{overflow}
        </div>
      )}
    </div>
  );
}
