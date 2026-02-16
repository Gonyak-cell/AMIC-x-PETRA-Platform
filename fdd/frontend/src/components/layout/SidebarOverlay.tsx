import { cn } from "@/lib/cn";

export interface SidebarOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SidebarOverlay({ isOpen, onClose }: SidebarOverlayProps) {
  return (
    <div
      className={cn(
        "fixed inset-0 z-40 bg-black/50 transition-opacity duration-300",
        isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
      )}
      onClick={onClose}
      aria-hidden="true"
    />
  );
}
