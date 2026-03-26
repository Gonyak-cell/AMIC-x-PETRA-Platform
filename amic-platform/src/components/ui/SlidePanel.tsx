import { useEffect, useRef, useCallback, useId, type DragEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";
import { Button } from "./Button";

export interface SlidePanelProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  width?: "md" | "lg" | "xl";
  children: React.ReactNode;
  headerActions?: React.ReactNode;
}

const widthStyles = {
  md: "max-w-[480px]",
  lg: "max-w-[640px]",
  xl: "max-w-[50vw]",
};

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

function hasDraggedFiles(event: DragEvent<HTMLElement>) {
  const types = Array.from(event.dataTransfer.types ?? []);
  return types.includes("Files") || event.dataTransfer.files.length > 0;
}

export function SlidePanel({
  open,
  onClose,
  title,
  subtitle,
  width = "xl",
  children,
  headerActions,
}: SlidePanelProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const isClosingRef = useRef(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      isClosingRef.current = false;
      previousFocusRef.current = document.activeElement as HTMLElement;
      dialog.showModal();

      const tl = gsap.timeline();
      tl.fromTo(
        backdropRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.3, ease: "power2.out" },
      );
      tl.fromTo(
        panelRef.current,
        { x: "100%" },
        { x: 0, duration: 0.4, ease: "power3.out" },
        "-=0.15",
      );

      requestAnimationFrame(() => {
        const firstFocusable =
          panelRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
        if (firstFocusable) firstFocusable.focus();
      });
    } else if (!isClosingRef.current) {
      dialog.close();
    }
  }, [open]);

  const handleClose = useCallback(() => {
    if (isClosingRef.current) return;
    isClosingRef.current = true;

    const tl = gsap.timeline({
      onComplete: () => {
        dialogRef.current?.close();
        onClose();
        requestAnimationFrame(() => {
          previousFocusRef.current?.focus();
        });
      },
    });

    tl.to(panelRef.current, {
      x: "100%",
      duration: 0.3,
      ease: "power2.in",
    });
    tl.to(
      backdropRef.current,
      { opacity: 0, duration: 0.2, ease: "power2.in" },
      "-=0.15",
    );
  }, [onClose]);

  const allowFileDropWithinPanel = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (!hasDraggedFiles(event)) {
        return;
      }
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    },
    [],
  );

  const preventUnhandledFileDrop = useCallback(
    (event: DragEvent<HTMLElement>) => {
      if (!hasDraggedFiles(event)) {
        return;
      }
      event.preventDefault();
    },
    [],
  );

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      className={cn(
        "fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full",
        "backdrop:bg-transparent",
      )}
      onCancel={(e) => {
        e.preventDefault();
        handleClose();
      }}
      onClick={(e) => {
        if (e.target === dialogRef.current) handleClose();
      }}
      onDragEnterCapture={allowFileDropWithinPanel}
      onDragOverCapture={allowFileDropWithinPanel}
      onDropCapture={preventUnhandledFileDrop}
      aria-labelledby={titleId}
    >
      {/* Backdrop */}
      <div
        ref={backdropRef}
        className="fixed inset-0 bg-amic-900/70 backdrop-blur-sm"
        style={{ opacity: 0 }}
        onClick={handleClose}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={cn(
          "fixed top-0 right-0 h-full w-full bg-white shadow-dr-xl flex flex-col",
          widthStyles[width],
        )}
        style={{ transform: "translateX(100%)" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-border shrink-0">
          <div className="min-w-0">
            <h2
              id={titleId}
              className="text-lg font-heading font-semibold text-text-dark truncate"
            >
              <span className="border-l-4 border-accent pl-3">{title}</span>
            </h2>
            {subtitle && (
              <p className="text-sm text-text-secondary mt-0.5 pl-[19px]">
                {subtitle}
              </p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {headerActions}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className="p-1.5"
              aria-label="Close panel"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </dialog>
  );
}
