import type { ComponentType } from "react";
import { Upload } from "lucide-react";
import { cn } from "@/lib/cn";

interface WorkspaceHeroShortcutRowProps {
  showOverview: boolean;
  overviewActive: boolean;
  phaseLabel: string;
  phaseActive: boolean;
  showVdrShortcut?: boolean;
  vdrActive?: boolean;
  onOverviewClick: () => void;
  onPhaseClick?: () => void;
  onVdrClick?: () => void;
  showUploadAction: boolean;
  onUploadClick: () => void;
}

interface HeroShortcutButtonProps {
  label: string;
  active?: boolean;
  accent?: boolean;
  icon?: ComponentType<{ className?: string }>;
  onClick?: () => void;
  disabled?: boolean;
}

function HeroShortcutButton({
  label,
  active = false,
  accent = false,
  icon: Icon,
  onClick,
  disabled = false,
}: HeroShortcutButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex items-center gap-2 rounded-dr-sm border px-4 py-2 text-sm font-semibold transition-all duration-200",
        "backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-white/25 focus:ring-offset-0",
        "disabled:cursor-not-allowed disabled:opacity-55",
        accent
          ? cn(
              "border-accent bg-accent text-white hover:bg-accent-hover",
              active && "shadow-[0_14px_28px_rgba(52,199,89,0.22)]",
            )
          : active
            ? "border-accent/35 bg-accent/18 text-white"
            : "border-white/16 bg-white/[0.08] text-white/88 hover:bg-white/[0.12] hover:text-white",
      )}
    >
      {Icon && <Icon className="h-4 w-4" />}
      <span>{label}</span>
    </button>
  );
}

export default function WorkspaceHeroShortcutRow({
  showOverview,
  overviewActive,
  phaseLabel,
  phaseActive,
  showVdrShortcut = false,
  vdrActive = false,
  onOverviewClick,
  onPhaseClick,
  onVdrClick,
  showUploadAction,
  onUploadClick,
}: WorkspaceHeroShortcutRowProps) {
  return (
    <div
      data-testid="workspace-hero-shortcuts"
      className="flex flex-wrap items-center gap-3"
    >
      {showOverview && (
        <HeroShortcutButton
          label="Overview"
          active={overviewActive}
          accent
          onClick={onOverviewClick}
        />
      )}
      <HeroShortcutButton
        label={phaseLabel}
        active={phaseActive}
        onClick={onPhaseClick}
        disabled={!onPhaseClick}
      />
      {showVdrShortcut && (
        <HeroShortcutButton
          label="VDR"
          active={vdrActive}
          onClick={onVdrClick}
          disabled={!onVdrClick}
        />
      )}
      {showUploadAction && (
        <HeroShortcutButton
          label="Upload to VDR"
          icon={Upload}
          onClick={onUploadClick}
        />
      )}
    </div>
  );
}
