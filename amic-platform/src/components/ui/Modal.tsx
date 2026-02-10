import { useEffect, useRef, useCallback } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";
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

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // 모달 열릴 때 포커스 저장 및 첫 번째 요소로 이동
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open) {
      // 현재 포커스된 요소 저장
      previousFocusRef.current = document.activeElement as HTMLElement;
      dialog.showModal();

      // 첫 번째 포커스 가능 요소로 이동 (닫기 버튼 제외하고 콘텐츠 내 첫 요소)
      requestAnimationFrame(() => {
        const firstFocusable = contentRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
        if (firstFocusable) {
          firstFocusable.focus();
        }
      });
    } else {
      dialog.close();
    }
  }, [open]);

  // 모달 닫힐 때 이전 포커스로 복귀
  const handleClose = useCallback(() => {
    onClose();
    // 이전에 포커스되어 있던 요소로 복귀
    requestAnimationFrame(() => {
      previousFocusRef.current?.focus();
    });
  }, [onClose]);

  // ESC 키로 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        handleClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, handleClose]);

  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      className={cn(
        "fixed inset-0 z-50 bg-transparent p-0 m-0 max-w-none max-h-none w-full h-full",
        "backdrop:bg-black/50"
      )}
      onClick={(e) => {
        if (e.target === dialogRef.current) handleClose();
      }}
      aria-labelledby="modal-title"
    >
      <div className="flex items-center justify-center min-h-screen p-4">
        <div
          ref={contentRef}
          className={cn(
            "bg-white rounded-lg shadow-xl w-full",
            sizeStyles[size]
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {/* 헤더 */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-border">
            <h2 id="modal-title" className="text-lg font-heading font-semibold text-text-dark">
              <span className="border-l-4 border-amic pl-3">{title}</span>
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
          <div className="px-5 py-4" role="document">{children}</div>

          {/* 푸터 */}
          {footer && (
            <div className="px-5 py-4 border-t border-gray-border bg-bg-cool rounded-b-lg flex justify-end gap-3">
              {footer}
            </div>
          )}
        </div>
      </div>
    </dialog>
  );
}
