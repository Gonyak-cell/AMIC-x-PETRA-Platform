import { FileText, BookOpen, BarChart2 } from "lucide-react";
import type { DocumentType } from "@/modules/docs/types/document";

interface DocumentTypeCardData {
  type: DocumentType;
  title: string;
  description: string;
  icon: typeof FileText;
  highlights: string[];
}

const DOCUMENT_TYPES: DocumentTypeCardData[] = [
  {
    type: "teaser",
    title: "Teaser Memorandum",
    description:
      "M&A 초기 단계에 잠재 투자자에게 배포하는 간결한 투자 개요 문서",
    icon: FileText,
    highlights: [
      "Executive Summary",
      "Market Opportunity",
      "Target Highlights",
      "Financial Summary",
    ],
  },
  {
    type: "im",
    title: "Information Memorandum",
    description:
      "상세한 기업, 재무, 시장 분석을 포함한 종합 투자 제안서",
    icon: BookOpen,
    highlights: [
      "Deal & Company Overview",
      "Market & Business Analysis",
      "Financial Analysis",
      "Valuation & Structure",
    ],
  },
  {
    type: "fdd",
    title: "Financial Due Diligence",
    description:
      "M&A 재무실사 보고서 — QoE · NWC · Net Debt 분석을 AI로 자동화",
    icon: BarChart2,
    highlights: [
      "Quality of Earnings",
      "Net Working Capital",
      "Net Debt",
      "Issue Log",
    ],
  },
];

interface DocumentTypePickerProps {
  selected: DocumentType | null;
  onSelect: (type: DocumentType) => void;
}

export function DocumentTypePicker({
  selected,
  onSelect,
}: DocumentTypePickerProps) {
  return (
    <div
      className="grid grid-cols-1 sm:grid-cols-3 gap-4"
      role="radiogroup"
      aria-label="문서 유형 선택"
    >
      {DOCUMENT_TYPES.map((dt) => {
        const isSelected = selected === dt.type;
        return (
          <button
            key={dt.type}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={`${dt.title} — ${dt.description}`}
            onClick={() => onSelect(dt.type)}
            className={`text-left p-5 rounded-xl border-2 transition-all ${
              isSelected
                ? "border-amic bg-amic/5 ring-1 ring-amic/20"
                : "border-gray-border bg-white hover:border-amic/40 hover:bg-bg-cool"
            }`}
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  isSelected ? "bg-amic text-white" : "bg-bg-cool text-text-secondary"
                }`}
              >
                <dt.icon className="h-5 w-5" />
              </div>
              <div>
                <h3
                  className={`text-base font-heading font-semibold ${
                    isSelected ? "text-amic" : "text-text-dark"
                  }`}
                >
                  {dt.title}
                </h3>
              </div>
            </div>
            <p className="text-sm text-text-secondary mb-3">{dt.description}</p>
            <div className="flex flex-wrap gap-1.5">
              {dt.highlights.map((h) => (
                <span
                  key={h}
                  className={`px-2 py-0.5 text-xs rounded ${
                    isSelected
                      ? "bg-amic/10 text-amic"
                      : "bg-bg-cool text-text-secondary"
                  }`}
                >
                  {h}
                </span>
              ))}
            </div>
          </button>
        );
      })}
    </div>
  );
}
