import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, Lock, Clock } from "lucide-react";
import { toast } from "sonner";
import type { DocumentCategory } from "@/modules/docs/types/studio-categories";

interface Props {
  category: DocumentCategory;
}

export default function CategoryCard({ category }: Props) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  const availableCount = category.subTypes.filter(
    (s) => s.status === "available",
  ).length;

  return (
    <div className="rounded-xl border border-gray-border bg-white transition-shadow hover:shadow-md">
      {/* Header — always visible */}
      <button
        type="button"
        className="group/card flex w-full items-center gap-3 p-5 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-100 group-hover/card:bg-amic/10 transition-colors"
        >
          <category.icon className="h-5 w-5 text-text-secondary group-hover/card:text-amic transition-colors" />
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-base font-heading font-semibold text-text-dark">
            {category.label}
          </h3>
          <p className="text-xs text-text-secondary truncate">
            {category.labelKo} &middot; {availableCount}/{category.subTypes.length} available
          </p>
        </div>

        <ChevronDown
          className={`h-4 w-4 text-text-secondary transition-transform ${
            open ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* Sub-types — collapsible */}
      {open && (
        <div className="border-t border-gray-border px-5 pb-4 pt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
          {category.subTypes.map((sub) => {
            const isAvailable = sub.status === "available";
            const isComingSoon = sub.status === "coming_soon";

            return (
              <button
                key={sub.id}
                type="button"
                onClick={() => {
                  if (isAvailable && sub.createPath) {
                    navigate(sub.createPath);
                  } else if (sub.status === "requires_context") {
                    navigate("/ma/transactions");
                  } else {
                    toast.info("준비 중입니다", {
                      description: `${sub.labelKo}은(는) 곧 제공됩니다.`,
                    });
                  }
                }}
                className={`group flex items-center gap-3 rounded-lg border p-3 text-left transition-all ${
                  isAvailable
                    ? "border-gray-border hover:border-amic/40 hover:bg-amic/5 cursor-pointer"
                    : isComingSoon
                      ? "border-dashed border-gray-200 opacity-50 cursor-not-allowed"
                      : "border-dashed border-amber-200 cursor-pointer hover:bg-amber-50/50"
                }`}
              >
                <div
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gray-50 transition-colors group-hover:bg-amic/10"
                >
                  <sub.icon className="h-4 w-4 text-text-secondary transition-colors group-hover:text-amic" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-text-dark">
                      {sub.label}
                    </span>
                    {isComingSoon && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-500">
                        <Clock className="h-3 w-3" />
                        Coming Soon
                      </span>
                    )}
                    {sub.status === "requires_context" && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-caution-light px-2 py-0.5 text-[10px] font-medium text-amber-600">
                        <Lock className="h-3 w-3" />
                        거래 선택 필요
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-text-secondary truncate">
                    {sub.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
