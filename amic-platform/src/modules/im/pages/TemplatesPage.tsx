import { useNavigate, useSearchParams } from "react-router-dom";
import { FileText, Briefcase, BarChart3, Layers, Settings2 } from "lucide-react";
import { Button, Card, PageHero } from "@/components/ui";
import type { IMStyle, SectionId } from "@/modules/im/types/document";
import { SECTION_LABEL_MAP } from "@/modules/im/types/document";
import heroImg from "@/assets/images/heroes/hero-arch-purple.jpg";

interface TemplateInfo {
  style: IMStyle;
  name: string;
  description: string;
  icon: typeof FileText;
  sections: SectionId[] | null;
}

/** Backend preset sections — must match im_document.py TITAN_SECTIONS / COVENANT_SECTIONS / FULL_SECTIONS */
const TEMPLATES: TemplateInfo[] = [
  {
    style: "TITAN",
    name: "Titan",
    description: "Concise investment summary focused on key highlights, financials overview, and deal rationale.",
    icon: Briefcase,
    sections: ["cover", "disclaimer", "toc_divider", "executive_summary", "company_overview", "financial_analysis", "contact"],
  },
  {
    style: "COVENANT",
    name: "Covenant",
    description: "Enhanced financial analysis with detailed covenant compliance, debt structure, and risk assessment.",
    icon: BarChart3,
    sections: [
      "cover", "disclaimer", "toc_divider", "deal_overview", "executive_summary",
      "company_overview", "market_overview", "financial_analysis", "valuation",
      "transaction_structure", "contact",
    ],
  },
  {
    style: "FULL",
    name: "Full",
    description: "Comprehensive IM covering all sections including market analysis, management, and projections.",
    icon: Layers,
    sections: [
      "cover", "disclaimer", "toc_divider", "deal_overview", "executive_summary",
      "investment_highlights", "company_overview", "business_model", "market_overview",
      "business_overview", "value_creation", "growth_strategy", "financial_analysis",
      "valuation", "management_team", "shareholder_structure", "transaction_structure",
      "appendix", "contact",
    ],
  },
  {
    style: "CUSTOM",
    name: "Custom",
    description: "Build your own IM by selecting specific sections tailored to your needs.",
    icon: Settings2,
    sections: null,
  },
];

export default function TemplatesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const selectedStyle = searchParams.get("style");

  return (
    <div className="space-y-6">
      <PageHero
        title="IM Templates"
        subtitle="Choose a template style for your Investment Memorandum"
        backgroundImage={heroImg}
        backgroundOpacity={0.18}
        compact
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {TEMPLATES.map((template) => (
          <Card key={template.style} className="flex flex-col">
            <div className="flex items-start gap-4 p-6">
              <div className="w-12 h-12 rounded-lg bg-amic/10 flex items-center justify-center flex-shrink-0">
                <template.icon className="h-6 w-6 text-amic" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-heading font-semibold text-text-dark">
                  {template.name}
                </h3>
                <p className="mt-1 text-sm text-text-secondary">
                  {template.description}
                </p>

                {/* Sections list */}
                <div className="mt-4">
                  <h4 className="text-xs font-medium text-text-secondary uppercase tracking-wider mb-2">
                    Sections
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {template.sections ? (
                      template.sections.map((sectionId) => (
                        <span
                          key={sectionId}
                          className="px-2 py-0.5 text-xs rounded bg-bg-cool text-text-secondary"
                        >
                          {SECTION_LABEL_MAP[sectionId] ?? sectionId}
                        </span>
                      ))
                    ) : (
                      <span className="px-2 py-0.5 text-xs rounded bg-bg-cool text-text-secondary italic">
                        User-selected sections
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
            <div className="px-6 pb-6 pt-2 mt-auto">
              <Button
                variant={selectedStyle === template.style ? "accent" : "primary"}
                className="w-full"
                onClick={() => navigate(`/im/new?style=${template.style}`)}
              >
                Use {template.name}
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
