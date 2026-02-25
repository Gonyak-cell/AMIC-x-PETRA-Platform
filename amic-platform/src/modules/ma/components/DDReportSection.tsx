import { useState } from "react";
import { FileText, Gavel, Calculator, ArrowLeft, ArrowRight } from "lucide-react";
import LDDReportsTab from "@/modules/docs/components/LDDReportsTab";
import FDDReportsTab from "@/modules/ma/components/FDDReportsTab";

interface DDReportSectionProps {
  txnId: string;
}

type DDReportView = "overview" | "ldd" | "fdd";

const DD_REPORTS = [
  {
    key: "fdd" as const,
    title: "FDD (재무실사)",
    description: "재무 실사 보고서 생성 및 관리",
    icon: FileText,
    available: true,
  },
  {
    key: "ldd" as const,
    title: "LDD (법률실사)",
    description: "DDRL 체크리스트 기반 법률실사보고서 생성",
    icon: Gavel,
    available: true,
  },
  {
    key: "tdd" as const,
    title: "TDD (세무실사)",
    description: "세무 실사 보고서 생성 및 관리",
    icon: Calculator,
    available: false,
  },
] as const;

export default function DDReportSection({ txnId }: DDReportSectionProps) {
  const [view, setView] = useState<DDReportView>("overview");

  if (view === "ldd" || view === "fdd") {
    return (
      <div className="space-y-4">
        <button
          type="button"
          onClick={() => setView("overview")}
          className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-accent-primary transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          DD 리포트 목록
        </button>
        {view === "ldd" && <LDDReportsTab txnId={txnId} />}
        {view === "fdd" && <FDDReportsTab txnId={txnId} />}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {DD_REPORTS.map((report) => (
        <div
          key={report.key}
          className={`rounded-xl border p-5 flex flex-col gap-3 transition-all ${
            report.available
              ? "border-border hover:border-accent-primary hover:shadow-md cursor-pointer"
              : "border-border/60 opacity-60"
          }`}
          onClick={report.available ? () => setView(report.key as DDReportView) : undefined}
          role={report.available ? "button" : undefined}
          tabIndex={report.available ? 0 : undefined}
          onKeyDown={
            report.available
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setView(report.key as DDReportView);
                  }
                }
              : undefined
          }
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <report.icon className="h-5 w-5 text-accent-primary" />
              <h4 className="text-sm font-semibold text-text-primary">{report.title}</h4>
            </div>
            {!report.available && (
              <span className="text-[10px] font-medium uppercase tracking-wider text-text-tertiary bg-white-alt px-2 py-0.5 rounded-full">
                Coming Soon
              </span>
            )}
            {report.available && (
              <ArrowRight className="h-4 w-4 text-text-tertiary" />
            )}
          </div>
          <p className="text-xs text-text-secondary leading-relaxed">{report.description}</p>
        </div>
      ))}
    </div>
  );
}
