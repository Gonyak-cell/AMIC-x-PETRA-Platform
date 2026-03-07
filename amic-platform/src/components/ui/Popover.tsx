import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";

export interface PopoverProps {
  open: boolean;
  onClose: () => void;
  anchorRef: React.RefObject<HTMLElement | null>;
  children: ReactNode;
  className?: string;
  /** 앵커 기준 배치 방향 */
  placement?: "bottom-start" | "bottom-end" | "top-start" | "top-end";
}

export function Popover({
  open,
  onClose,
  anchorRef,
  children,
  className,
  placement = "bottom-start",
}: PopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState({ top: 0, left: 0 });

  const reposition = useCallback(() => {
    const anchor = anchorRef.current;
    const popover = popoverRef.current;
    if (!anchor || !popover) return;

    const rect = anchor.getBoundingClientRect();
    const popRect = popover.getBoundingClientRect();
    let top: number;
    let left: number;

    if (placement.startsWith("top")) {
      top = rect.top - popRect.height - 4;
    } else {
      top = rect.bottom + 4;
    }

    if (placement.endsWith("end")) {
      left = rect.right - popRect.width;
    } else {
      left = rect.left;
    }

    // 뷰포트 경계 보정
    if (left + popRect.width > window.innerWidth - 8) {
      left = window.innerWidth - popRect.width - 8;
    }
    if (left < 8) left = 8;
    if (top + popRect.height > window.innerHeight - 8) {
      top = rect.top - popRect.height - 4;
    }
    if (top < 8) top = 8;

    setPos({ top, left });
  }, [anchorRef, placement]);

  useEffect(() => {
    if (!open) return;
    reposition();
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    return () => {
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
  }, [open, reposition]);

  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      const popover = popoverRef.current;
      const anchor = anchorRef.current;
      if (
        popover &&
        !popover.contains(e.target as Node) &&
        anchor &&
        !anchor.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open, onClose, anchorRef]);

  if (!open) return null;

  return createPortal(
    <div
      ref={popoverRef}
      role="dialog"
      className={cn(
        "fixed z-50 bg-white rounded-dr shadow-dr-xl border border-gray-border",
        "animate-in fade-in-0 zoom-in-95 duration-150",
        className,
      )}
      style={{ top: pos.top, left: pos.left }}
    >
      {children}
    </div>,
    document.body,
  );
}
