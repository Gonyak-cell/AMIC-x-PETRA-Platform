import { Menu, X } from "lucide-react";
import { cn } from "@/lib/cn";

export interface MobileMenuButtonProps {
  isOpen: boolean;
  onClick: () => void;
  className?: string;
}

export function MobileMenuButton({ isOpen, onClick, className }: MobileMenuButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "p-2 rounded-lg text-white hover:bg-white/10 transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-white/50",
        className
      )}
      aria-expanded={isOpen}
      aria-controls="mobile-sidebar"
      aria-label={isOpen ? "Close navigation menu" : "Open navigation menu"}
    >
      {isOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
    </button>
  );
}
