import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/cn";
import type { OnboardingStep } from "./steps";

interface Props {
  step: OnboardingStep;
  currentIndex: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
}

export function OnboardingOverlay({
  step,
  currentIndex,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
}: Props) {
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    const el = document.querySelector(step.targetSelector);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    const timer = setTimeout(
      () => setTargetRect(el.getBoundingClientRect()),
      300,
    );
    return () => clearTimeout(timer);
  }, [step.targetSelector]);

  if (!targetRect) return null;

  const isLast = currentIndex === totalSteps - 1;
  const isFirst = currentIndex === 0;
  const pad = 8;

  // Tooltip position based on placement
  const tooltipStyle: React.CSSProperties = { maxWidth: 340 };
  if (step.placement === "bottom") {
    tooltipStyle.top = targetRect.bottom + pad + 8;
    tooltipStyle.left = targetRect.left;
  } else {
    tooltipStyle.bottom = window.innerHeight - targetRect.top + pad + 8;
    tooltipStyle.left = targetRect.left;
  }

  return createPortal(
    <>
      {/* Overlay with spotlight hole */}
      <div className="fixed inset-0 z-[9998]" style={{ pointerEvents: "none" }}>
        <svg className="w-full h-full">
          <defs>
            <mask id="onboarding-mask">
              <rect width="100%" height="100%" fill="white" />
              <rect
                x={targetRect.left - pad}
                y={targetRect.top - pad}
                width={targetRect.width + pad * 2}
                height={targetRect.height + pad * 2}
                rx={8}
                fill="black"
              />
            </mask>
          </defs>
          <rect
            width="100%"
            height="100%"
            fill="rgba(0,0,0,0.5)"
            mask="url(#onboarding-mask)"
            style={{ pointerEvents: "auto" }}
            onClick={onSkip}
          />
        </svg>
      </div>
      {/* Tooltip */}
      <div
        className="fixed z-[9999] bg-white rounded-lg shadow-xl border border-gray-200 p-4 animate-in fade-in-0 zoom-in-95 duration-200"
        style={tooltipStyle}
      >
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400 font-medium">
            {currentIndex + 1} / {totalSteps}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={onSkip}
              className="text-xs text-gray-400 hover:text-gray-600"
            >
              건너뛰기
            </button>
            <button
              onClick={onSkip}
              className="text-xs text-gray-400 hover:text-gray-600"
              aria-label="닫기"
            >
              ✕
            </button>
          </div>
        </div>
        <h3 className="text-sm font-semibold text-gray-900">{step.title}</h3>
        <p className="text-sm text-gray-500 mt-1">{step.description}</p>
        <div className="flex justify-between mt-4">
          <button
            onClick={onPrev}
            disabled={isFirst}
            className={cn(
              "text-sm px-3 py-1.5 rounded-md",
              isFirst
                ? "text-gray-300 cursor-not-allowed"
                : "text-gray-500 hover:bg-gray-50",
            )}
          >
            이전
          </button>
          <button
            onClick={onNext}
            className="text-sm px-4 py-1.5 rounded-md bg-sky-500 text-white hover:bg-sky-600 font-medium"
          >
            {isLast ? "완료" : "다음"}
          </button>
        </div>
      </div>
    </>,
    document.body,
  );
}
