import { useState } from "react";
import {
  HeroSection,
  SectionDivider,
  PagePreviewCard,
  GalleryNav,
  type GallerySection,
} from "@/components/gallery";
import {
  Card,
  KpiCard,
  Badge,
  Button,
  DataTable,
  Input,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  FileText,
  TrendingUp,
  Clock,
  AlertTriangle,
  Eye,
  Download,
  RefreshCw,
  Zap,
  FileOutput,
  Building2,
  CheckCircle2,
  Check,
} from "lucide-react";

interface MockDocument {
  id: string;
  projectName: string;
  companyName: string;
  corpCode: string;
  imStyle: "TITAN" | "FULL" | "COMPACT";
  status: "COMPLETED" | "GENERATING" | "PENDING" | "FAILED";
  progress: number;
  fileSize: string;
}

const mockDocuments: MockDocument[] = [
  {
    id: "1",
    projectName: "Samsung Electronics Q4 2025",
    companyName: "삼성전자",
    corpCode: "005930",
    imStyle: "TITAN",
    status: "COMPLETED",
    progress: 100,
    fileSize: "2.0 MB",
  },
  {
    id: "2",
    projectName: "SK Hynix Investment Memo",
    companyName: "SK하이닉스",
    corpCode: "000660",
    imStyle: "FULL",
    status: "GENERATING",
    progress: 67,
    fileSize: "-",
  },
  {
    id: "3",
    projectName: "LG Energy Solutions Brief",
    companyName: "LG에너지솔루션",
    corpCode: "373220",
    imStyle: "COMPACT",
    status: "COMPLETED",
    progress: 100,
    fileSize: "1.2 MB",
  },
  {
    id: "4",
    projectName: "Kakao Strategic Analysis",
    companyName: "카카오",
    corpCode: "035720",
    imStyle: "FULL",
    status: "PENDING",
    progress: 0,
    fileSize: "-",
  },
  {
    id: "5",
    projectName: "Naver Market Review",
    companyName: "네이버",
    corpCode: "035420",
    imStyle: "TITAN",
    status: "FAILED",
    progress: 45,
    fileSize: "-",
  },
  {
    id: "6",
    projectName: "Hyundai Motor Due Diligence",
    companyName: "현대자동차",
    corpCode: "005380",
    imStyle: "FULL",
    status: "COMPLETED",
    progress: 100,
    fileSize: "1.8 MB",
  },
];

const sections: GallerySection[] = [
  {
    id: "document-list",
    title: "Document List",
    description: "Browse and manage investment memorandums",
    path: "/im",
  },
  {
    id: "create-document",
    title: "Create Document",
    description: "Generate new IM with AI-powered analysis",
    path: "/im/new",
  },
  {
    id: "document-detail",
    title: "Document Detail",
    description: "View and download completed documents",
    path: "/im/documents/:id",
  },
  {
    id: "templates",
    title: "Templates",
    description: "Choose from available IM templates",
    path: "/im/templates",
  },
];

export default function GallerySamplePage() {
  const [activeSection, setActiveSection] = useState<string>("document-list");
  const [filterStatus, setFilterStatus] = useState<string>("All");
  const [selectedStyle, setSelectedStyle] = useState<string>("TITAN");

  const documentColumns: Column<MockDocument>[] = [
    {
      key: "projectName",
      header: "Project Name",
      render: (doc) => <span className="font-semibold">{doc.projectName}</span>,
    },
    {
      key: "companyName",
      header: "Company Name",
      render: (doc) => doc.companyName,
    },
    {
      key: "corpCode",
      header: "Corp Code",
      render: (doc) => (
        <span className="font-mono text-sm">{doc.corpCode}</span>
      ),
    },
    {
      key: "imStyle",
      header: "IM Style",
      render: (doc) => (
        <Badge
          variant={
            doc.imStyle === "TITAN"
              ? "info"
              : doc.imStyle === "FULL"
                ? "success"
                : "neutral"
          }
        >
          {doc.imStyle}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (doc) => (
        <Badge
          variant={
            doc.status === "COMPLETED"
              ? "success"
              : doc.status === "GENERATING"
                ? "info"
                : doc.status === "PENDING"
                  ? "warning"
                  : "error"
          }
        >
          {doc.status}
        </Badge>
      ),
    },
    {
      key: "progress",
      header: "Progress",
      render: (doc) => (
        <div className="flex items-center gap-2 min-w-[120px]">
          <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                doc.status === "COMPLETED"
                  ? "bg-green-500"
                  : doc.status === "GENERATING"
                    ? "bg-blue-500"
                    : doc.status === "FAILED"
                      ? "bg-red-500"
                      : "bg-gray-300"
              )}
              style={{ width: `${doc.progress}%` }}
            />
          </div>
          <span className="text-xs text-gray-600 dark:text-gray-400 min-w-[35px]">
            {doc.progress}%
          </span>
        </div>
      ),
    },
    {
      key: "fileSize",
      header: "File Size",
      render: (doc) => doc.fileSize,
    },
  ];

  return (
    <div className="bg-bg-cool min-h-screen">
      <HeroSection
        title="IM Generator Gallery"
        subtitle="Investment Memorandum generation and management"
        backgroundUrl="https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1920&h=600&fit=crop"
      />

      <div className="container mx-auto px-6 py-12">
        <div className="flex gap-8">
          <GalleryNav
            sections={sections}
            activeSection={activeSection}
            onSectionChange={setActiveSection}
          />

          <div className="flex-1 space-y-16">
            {/* Section 1: Document List */}
            <section id="document-list">
              <SectionDivider
                title="Document List"
                description="Browse and manage investment memorandums"
              />

              <PagePreviewCard
                title="Document Management"
                path="/im"
                variant="forest-lift"
              >
                <div className="space-y-6">
                  {/* KPI Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KpiCard
                      title="Total Projects"
                      value="15"
                      icon={FileText}
                      variant="default"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Completed"
                      value="8"
                      icon={CheckCircle2}
                      variant="positive"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="In Progress"
                      value="5"
                      icon={Clock}
                      variant="caution"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Failed"
                      value="2"
                      icon={AlertTriangle}
                      variant="negative"
                      hoverLift
                      generous
                    />
                  </div>

                  {/* Filter Buttons */}
                  <div className="flex flex-wrap gap-2">
                    {["All", "Completed", "Generating", "Pending", "Failed"].map(
                      (status) => (
                        <Button
                          key={status}
                          variant={
                            filterStatus === status ? "accent" : "secondary"
                          }
                          size="sm"
                          onClick={() => setFilterStatus(status)}
                        >
                          {status}
                        </Button>
                      )
                    )}
                  </div>

                  {/* Data Table */}
                  <DataTable
                    data={mockDocuments}
                    columns={documentColumns}
                    keyField="id"
                    uppercaseHeaders
                    striped
                  />
                </div>
              </PagePreviewCard>
            </section>

            {/* Section 2: Create Document */}
            <section id="create-document">
              <SectionDivider
                title="Create Document"
                description="Generate new IM with AI-powered analysis"
              />

              <PagePreviewCard
                title="New IM Generation"
                path="/im/new"
                variant="forest-lift"
              >
                <div className="space-y-8">
                  <Card variant="forest-lift" hoverEffect>
                    <div className="space-y-6">
                      {/* Step 1: Company Selection */}
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-accent-500 text-white flex items-center justify-center font-semibold">
                            1
                          </div>
                          <h3 className="text-lg font-semibold">
                            Company Selection
                          </h3>
                        </div>
                        <div className="pl-10 space-y-3">
                          <Input
                            placeholder="Enter corporation code (e.g., 005930)"
                            className="font-mono"
                          />
                          <div className="p-3 bg-amic-50 rounded-lg border border-amic-200">
                            <div className="flex items-center gap-2">
                              <Building2 className="w-4 h-4 text-amic" />
                              <span className="font-medium">
                                삼성전자 (Samsung Electronics Co., Ltd.)
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Step 2: IM Style */}
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-accent-500 text-white flex items-center justify-center font-semibold">
                            2
                          </div>
                          <h3 className="text-lg font-semibold">IM Style</h3>
                        </div>
                        <div className="pl-10 grid grid-cols-1 md:grid-cols-3 gap-4">
                          {[
                            {
                              id: "TITAN",
                              title: "TITAN",
                              desc: "Comprehensive analysis with AI-driven insights",
                            },
                            {
                              id: "FULL",
                              title: "FULL",
                              desc: "Complete IM with all standard sections",
                            },
                            {
                              id: "COMPACT",
                              title: "COMPACT",
                              desc: "Concise summary for quick reviews",
                            },
                          ].map((style) => (
                            <button
                              key={style.id}
                              onClick={() => setSelectedStyle(style.id)}
                              className={cn(
                                "p-4 rounded-lg border-2 text-left transition-all",
                                selectedStyle === style.id
                                  ? "border-accent-500 bg-accent-50 dark:bg-accent-900/20"
                                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
                              )}
                            >
                              <div className="font-semibold mb-1">
                                {style.title}
                              </div>
                              <div className="text-sm text-gray-600 dark:text-gray-400">
                                {style.desc}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Step 3: Section Selection */}
                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <div className="w-8 h-8 rounded-full bg-accent-500 text-white flex items-center justify-center font-semibold">
                            3
                          </div>
                          <h3 className="text-lg font-semibold">
                            Section Selection
                          </h3>
                        </div>
                        <div className="pl-10 space-y-2">
                          {[
                            { label: "Executive Summary", checked: true },
                            { label: "Company Overview", checked: true },
                            { label: "Financial Analysis", checked: true },
                            { label: "Valuation", checked: true },
                            { label: "Market Analysis", checked: false },
                            { label: "Risk Factors", checked: false },
                          ].map((section) => (
                            <label
                              key={section.label}
                              className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                            >
                              <div
                                className={cn(
                                  "w-5 h-5 rounded border-2 flex items-center justify-center",
                                  section.checked
                                    ? "bg-accent-500 border-accent-500"
                                    : "border-gray-300 dark:border-gray-600"
                                )}
                              >
                                {section.checked && (
                                  <Check className="w-3 h-3 text-white" />
                                )}
                              </div>
                              <span className="font-medium">
                                {section.label}
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Generate Button */}
                      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                        <Button variant="accent" size="lg" className="w-full">
                          <Zap className="w-5 h-5 mr-2" />
                          Generate Investment Memorandum
                        </Button>
                      </div>
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* Section 3: Document Detail */}
            <section id="document-detail">
              <SectionDivider
                title="Document Detail"
                description="View and download completed documents"
              />

              <PagePreviewCard
                title="Document Viewer"
                path="/im/documents/:id"
                variant="forest-lift"
              >
                <div className="space-y-6">
                  {/* Header */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <h2 className="text-2xl font-bold">Samsung IM</h2>
                    <Badge variant="info">TITAN</Badge>
                    <Badge variant="success">COMPLETED</Badge>
                  </div>

                  {/* KPI Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KpiCard
                      title="Generation Time"
                      value="2m 34s"
                      icon={Clock}
                      variant="default"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Sections"
                      value="4"
                      icon={FileText}
                      variant="positive"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="File Size"
                      value="2.0 MB"
                      icon={TrendingUp}
                      variant="default"
                      hoverLift
                      generous
                    />
                  </div>

                  {/* Progress Card */}
                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-4">
                      Generation Progress
                    </h3>
                    <div className="space-y-3">
                      {[
                        { label: "Overview", progress: 100 },
                        { label: "Financials", progress: 100 },
                        { label: "Valuation", progress: 100 },
                        { label: "Appendix", progress: 100 },
                      ].map((section) => (
                        <div key={section.label}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium">
                              {section.label}
                            </span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              {section.progress}%
                            </span>
                          </div>
                          <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500 rounded-full transition-all"
                              style={{ width: `${section.progress}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>

                  {/* Preview Card */}
                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-4">
                      Document Preview
                    </h3>
                    <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-8 space-y-4">
                      <h1 className="text-3xl font-bold text-center mb-8">
                        Investment Memorandum - 삼성전자
                      </h1>
                      <div className="space-y-3">
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-4/5" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                      </div>
                      <div className="pt-6 space-y-3">
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-4/5" />
                        <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                      </div>
                    </div>
                  </Card>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-3">
                    <Button variant="primary" size="lg">
                      <Eye className="w-5 h-5 mr-2" />
                      Preview
                    </Button>
                    <Button variant="accent" size="lg">
                      <Download className="w-5 h-5 mr-2" />
                      Download
                    </Button>
                    <Button variant="secondary" size="lg">
                      <RefreshCw className="w-5 h-5 mr-2" />
                      Regenerate
                    </Button>
                  </div>
                </div>
              </PagePreviewCard>
            </section>

            {/* Section 4: Templates */}
            <section id="templates">
              <SectionDivider
                title="Templates"
                description="Choose from available IM templates"
              />

              <PagePreviewCard
                title="Template Library"
                path="/im/templates"
                variant="forest-lift"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    {
                      icon: <Zap className="w-8 h-8" />,
                      title: "TITAN",
                      description:
                        "Comprehensive analysis with AI-driven insights",
                      badge: "Premium",
                      badgeVariant: "info" as const,
                      sections: 6,
                    },
                    {
                      icon: <FileText className="w-8 h-8" />,
                      title: "FULL",
                      description:
                        "Complete IM with all standard sections",
                      badge: "Standard",
                      badgeVariant: "success" as const,
                      sections: 5,
                    },
                    {
                      icon: <FileOutput className="w-8 h-8" />,
                      title: "COMPACT",
                      description: "Concise summary for quick reviews",
                      badge: "Basic",
                      badgeVariant: "neutral" as const,
                      sections: 3,
                    },
                  ].map((template) => (
                    <Card
                      key={template.title}
                      variant="forest-lift"
                      hoverEffect
                    >
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <div className="p-3 bg-amic-50 rounded-lg text-amic">
                            {template.icon}
                          </div>
                          <Badge variant={template.badgeVariant}>
                            {template.badge}
                          </Badge>
                        </div>

                        <div>
                          <h3 className="text-xl font-bold mb-2">
                            {template.title}
                          </h3>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {template.description}
                          </p>
                        </div>

                        <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                          <div className="flex items-center justify-between text-sm mb-4">
                            <span className="text-gray-600 dark:text-gray-400">
                              Sections
                            </span>
                            <span className="font-semibold">
                              {template.sections}
                            </span>
                          </div>

                          <Button variant="primary" size="md" className="w-full">
                            Use Template
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </PagePreviewCard>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
