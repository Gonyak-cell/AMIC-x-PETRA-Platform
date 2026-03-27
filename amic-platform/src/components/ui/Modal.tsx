import { useEffect, useRef, useCallback, useId, type DragEvent as ReactDragEvent } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
import { gsap } from "@/lib/gsap";
import { Button } from "./Button";

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg";
}

const sizeStyles = {
  sm: "max-w-md",
  md: "max-w-lg",
  lg: "max-w-2xl",
};

// 포커스 가능한 요소 선택자
const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

function hasDraggedFiles(dataTransfer?: DataTransfer | null) {
  if (!dataTransfer) {
    return false;
  }
  const types = Array.from(dataTransfer.types ?? []);
  return types.includes("Files") || dataTransfer.files.length > 0;
}

function isHandledFileDropTarget(target: EventTarget | null) {
  return target instanceof Element && target.closest("[data-file-dropzone='true']") !== null;
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
}: ModalProps) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const isClosingRef = useRef(false);

  // 모달 열릴 때 포커스 저장 및 첫 번째 요소로 이동
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      isClosingRef.current = false;
      // 현재 포커스된 요소 저장
      previousFocusRef.current = document.activeElement as HTMLElement;
      dialog.showModal();

      // GSAP 진입 애니메이션
      const tl = gsap.timeline();
      tl.fromTo(
        backdropRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.3, ease: "power2.out" },
      );
      tl.fromTo(
        contentRef.current,
        { scale: 0.95, opacity: 0, y: 16 },
        { scale: 1, opacity: 1, y: 0, duration: 0.35, ease: "power3.out" },
        "-=0.15",
      );

      // 첫 번째 포커스 가능 요소로 이동
      requestAnimationFrame(() => {
        const firstFocusable =
          contentRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
        if (firstFocusable) {
          firstFocusable.focus();
        }
      });
    } else if (!isClosingRef.current) {
      dialog.close();
    }
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const allowNativeFileDrag = (event: globalThis.DragEvent) => {
      if (!hasDraggedFiles(event.dataTransfer)) {
        return;
      }
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "copy";
      }
    };

    const preventNativeFileDrop = (event: globalThis.DragEvent) => {
      if (!hasDraggedFiles(event.dataTransfer)) {
        return;
      }
      if (isHandledFileDropTarget(event.target)) {
        return;
      }
      event.preventDefault();
    };

    const targets: Pick<
      Window,
      "addEventListener" | "removeEventListener"
    >[] = [window, document];

    for (const target of targets) {
      target.addEventListener("dragenter", allowNativeFileDrag, true);
      target.addEventListener("dragover", allowNativeFileDrag, true);
      target.addEventListener("drop", preventNativeFileDrop, true);
    }

    return () => {
      for (const target of targets) {
        target.removeEventListener("dragenter", allowNativeFileDrag, true);
        target.removeEventListener("dragover", allowNativeFileDrag, true);
        target.removeEventListener("drop", preventNativeFileDrop, true);
      }
    };
  }, [open]);

  // 모달 닫힐 때 퇴장 애니메이션 → 이전 포커스로 복귀
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

    tl.to(contentRef.current, {
      scale: 0.95,
      opacity: 0,
      y: 12,
      duration: 0.25,
      ease: "power2.in",
    });
    tl.to(
      backdropRef.current,
      { opacity: 0, duration: 0.2, ease: "power2.in" },
      "-=0.15",
    );
  }, [onClose]);

  const allowFileDropWithinModal = useCallback(
    (event: ReactDragEvent<HTMLElement>) => {
      if (!hasDraggedFiles(event.dataTransfer)) {
        return;
      }
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    },
    [],
  );

  const preventUnhandledFileDrop = useCallback(
    (event: ReactDragEvent<HTMLElement>) => {
      if (!hasDraggedFiles(event.dataTransfer)) {
        return;
      }
      if (isHandledFileDropTarget(event.target)) {
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
      onDragEnterCapture={allowFileDropWithinModal}
      onDragOverCapture={allowFileDropWithinModal}
      onDropCapture={preventUnhandledFileDrop}
      aria-labelledby={titleId}
    >
      {/* Animated backdrop */}
      <div
        ref={backdropRef}
        className="fixed inset-0 bg-amic-900/70 backdrop-blur-sm"
        style={{ opacity: 0 }}
      />

      <div className="relative flex items-center justify-center min-h-screen p-4">
        <div
          ref={contentRef}
          className={cn(
            "relative bg-white rounded-dr shadow-dr-xl w-full",
            sizeStyles[size],
          )}
          style={{ opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-border">
            <h2
              id={titleId}
              className="text-lg font-heading font-semibold text-text-dark"
            >
              <span className="border-l-4 border-accent pl-3">{title}</span>
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClose}
              className="p-1.5"
              aria-label="Close modal"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* 콘텐츠 */}
          <div className="px-5 py-4">{children}</div>

          {/* 푸터 */}
          {footer && (
            <div className="px-5 py-4 border-t border-gray-border bg-bg-cool rounded-b-dr flex justify-end gap-3">
              {footer}
            </div>
          )}
        </div>
      </div>
    </dialog>
  );
}
