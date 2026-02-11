import { useState } from "react";
import {
  HeroSection,
  SectionDivider,
  PagePreviewCard,
  GalleryNav,
} from "@/components/gallery";
import type { GallerySection } from "@/components/gallery";
import {
  Card,
  KpiCard,
  Badge,
  Button,
  DataTable,
  Input,
  Select,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  Briefcase,
  Settings,
  BarChart3,
  Upload,
  FileText,
  GitBranch,
  TrendingUp,
  Wallet,
  CreditCard,
  AlertCircle,
  FileCheck,
  FolderTree,
  FileUp,
} from "lucide-react";

// Mock data types
interface MockDeal {
  id: string;
  name: string;
  type: string;
  client: string;
  target: string;
  currency: string;
  dealSize: string;
  status: string;
}

interface MockFile {
  id: string;
  fileName: string;
  size: string;
  uploadDate: string;
  processor: string;
  status: string;
}

interface MockAccount {
  id: string;
  code: string;
  name: string;
  category: string;
  mappingStatus: string;
}

interface MockAdjustment {
  id: string;
  item: string;
  category: string;
  amount: number;
  note: string;
}

interface MockNwcItem {
  id: string;
  item: string;
  fy2023: string;
  fy2024: string;
  fy2025: string;
  trend: string;
}

interface MockDebtItem {
  id: string;
  description: string;
  amount: string;
  classification: string;
  notes: string;
}

interface MockIssue {
  id: string;
  title: string;
  severity: string;
  category: string;
  owner: string;
  status: string;
  impact: string;
}

// Mock data
const mockDeals: MockDeal[] = [
  {
    id: "1",
    name: "프로젝트 알파",
    type: "Completion",
    client: "Petrabridge Partners",
    target: "Alpha Tech Co.",
    currency: "KRW",
    dealSize: "₩125.0B",
    status: "active",
  },
  {
    id: "2",
    name: "프로젝트 베타",
    type: "Locked Box",
    client: "Seoul Capital",
    target: "Beta Manufacturing",
    currency: "KRW",
    dealSize: "₩89.5B",
    status: "completed",
  },
  {
    id: "3",
    name: "프로젝트 감마",
    type: "Completion",
    client: "Korea Investment",
    target: "Gamma Industries",
    currency: "KRW",
    dealSize: "₩210.0B",
    status: "active",
  },
  {
    id: "4",
    name: "프로젝트 델타",
    type: "Locked Box",
    client: "Petrabridge Partners",
    target: "Delta Retail Group",
    currency: "KRW",
    dealSize: "₩45.2B",
    status: "review",
  },
  {
    id: "5",
    name: "프로젝트 엡실론",
    type: "Completion",
    client: "Busan Ventures",
    target: "Epsilon Logistics",
    currency: "KRW",
    dealSize: "₩67.8B",
    status: "active",
  },
];

const mockFiles: MockFile[] = [
  {
    id: "1",
    fileName: "Financial_Statements_2024.xlsx",
    size: "2.4 MB",
    uploadDate: "2026-02-10",
    processor: "Excel Parser",
    status: "parsed",
  },
  {
    id: "2",
    fileName: "Balance_Sheet_Q4.pdf",
    size: "1.8 MB",
    uploadDate: "2026-02-10",
    processor: "PDF Parser",
    status: "processing",
  },
  {
    id: "3",
    fileName: "Income_Statement_2023-2024.xlsx",
    size: "3.1 MB",
    uploadDate: "2026-02-09",
    processor: "Excel Parser",
    status: "parsed",
  },
  {
    id: "4",
    fileName: "Tax_Returns_2024.pdf",
    size: "5.2 MB",
    uploadDate: "2026-02-09",
    processor: "PDF Parser",
    status: "parsed",
  },
  {
    id: "5",
    fileName: "Audit_Report_2024.pdf",
    size: "4.7 MB",
    uploadDate: "2026-02-08",
    processor: "PDF Parser",
    status: "error",
  },
];

const mockAccounts: MockAccount[] = [
  { id: "1", code: "4000", name: "Revenue", category: "Income", mappingStatus: "mapped" },
  { id: "2", code: "5000", name: "Cost of Goods Sold", category: "COGS", mappingStatus: "mapped" },
  { id: "3", code: "6100", name: "Sales & Marketing", category: "OpEx", mappingStatus: "mapped" },
  { id: "4", code: "6200", name: "General & Administrative", category: "OpEx", mappingStatus: "unmapped" },
  { id: "5", code: "7000", name: "Depreciation & Amortization", category: "D&A", mappingStatus: "mapped" },
  { id: "6", code: "8000", name: "Interest Expense", category: "Finance", mappingStatus: "unmapped" },
];

const mockAdjustments: MockAdjustment[] = [
  {
    id: "1",
    item: "Non-recurring legal fees",
    category: "One-time",
    amount: 850000000,
    note: "Settlement costs",
  },
  {
    id: "2",
    item: "Stock-based compensation",
    category: "Non-cash",
    amount: 1200000000,
    note: "Employee equity grants",
  },
  {
    id: "3",
    item: "Related party transactions",
    category: "Normalization",
    amount: -450000000,
    note: "Above-market rent",
  },
  {
    id: "4",
    item: "Restructuring costs",
    category: "One-time",
    amount: 320000000,
    note: "Facility closure",
  },
  {
    id: "5",
    item: "Gain on asset sale",
    category: "Non-recurring",
    amount: -220000000,
    note: "Property disposal",
  },
];

const mockNwcItems: MockNwcItem[] = [
  { id: "1", item: "Accounts Receivable", fy2023: "₩5.2B", fy2024: "₩5.8B", fy2025: "₩6.1B", trend: "up" },
  { id: "2", item: "Inventory", fy2023: "₩3.1B", fy2024: "₩3.4B", fy2025: "₩3.6B", trend: "up" },
  { id: "3", item: "Accounts Payable", fy2023: "₩2.8B", fy2024: "₩3.0B", fy2025: "₩3.2B", trend: "up" },
  { id: "4", item: "Accrued Expenses", fy2023: "₩1.2B", fy2024: "₩1.3B", fy2025: "₩1.4B", trend: "up" },
  { id: "5", item: "Net Working Capital", fy2023: "₩7.5B", fy2024: "₩8.1B", fy2025: "₩8.3B", trend: "stable" },
];

const mockDebtItems: MockDebtItem[] = [
  { id: "1", description: "Senior Term Loan", amount: "₩18.0B", classification: "Debt", notes: "Matures 2028" },
  { id: "2", description: "Revolving Credit Facility", amount: "₩7.0B", classification: "Debt", notes: "Undrawn capacity" },
  { id: "3", description: "Cash & Bank Balances", amount: "₩6.5B", classification: "Cash", notes: "Operating accounts" },
  { id: "4", description: "Short-term Investments", amount: "₩2.0B", classification: "Cash-like", notes: "Money market funds" },
  { id: "5", description: "Finance Lease Obligations", amount: "₩1.8B", classification: "Debt-like", notes: "Equipment leases" },
  { id: "6", description: "Deferred Revenue", amount: "₩0.7B", classification: "Debt-like", notes: "Customer prepayments" },
];

const mockIssues: MockIssue[] = [
  {
    id: "1",
    title: "Revenue recognition policy mismatch",
    severity: "high",
    category: "Accounting",
    owner: "J. Kim",
    status: "open",
    impact: "₩1.2B",
  },
  {
    id: "2",
    title: "Missing inventory reconciliation",
    severity: "medium",
    category: "Working Capital",
    owner: "S. Lee",
    status: "in-progress",
    impact: "₩0.5B",
  },
  {
    id: "3",
    title: "Contingent liability disclosure",
    severity: "high",
    category: "Legal",
    owner: "M. Park",
    status: "open",
    impact: "₩2.8B",
  },
  {
    id: "4",
    title: "Lease classification review needed",
    severity: "low",
    category: "Accounting",
    owner: "J. Kim",
    status: "resolved",
    impact: "₩0.3B",
  },
  {
    id: "5",
    title: "Related party transaction documentation",
    severity: "medium",
    category: "Compliance",
    owner: "H. Choi",
    status: "in-progress",
    impact: "₩0.8B",
  },
];

const sections: GallerySection[] = [
  { id: "deal-list", label: "Deal List", icon: Briefcase },
  { id: "deal-wizard", label: "Deal Setup Wizard", icon: Settings },
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "deal-setup", label: "Deal Setup", icon: Settings },
  { id: "vdr", label: "VDR", icon: FolderTree },
  { id: "uploads", label: "Uploads", icon: FileUp },
  { id: "definitions", label: "Definitions", icon: FileText },
  { id: "mapping", label: "Mapping", icon: GitBranch },
  { id: "qoe-bridge", label: "QoE Bridge", icon: TrendingUp },
  { id: "nwc", label: "Net Working Capital", icon: Wallet },
  { id: "net-debt", label: "Net Debt", icon: CreditCard },
  { id: "issues", label: "Issues", icon: AlertCircle },
  { id: "report", label: "Report", icon: FileCheck },
];

export default function GallerySamplePage() {
  const [activeSection, setActiveSection] = useState<string>("deal-list");

  // Column definitions
  const dealColumns: Column<MockDeal>[] = [
    {
      key: "name",
      label: "Deal Name",
      sortable: true,
      render: (deal) => <span className="font-semibold">{deal.name}</span>,
    },
    { key: "type", label: "Type", sortable: true },
    { key: "client", label: "Client", sortable: true },
    { key: "target", label: "Target", sortable: true },
    { key: "currency", label: "Currency", sortable: true },
    {
      key: "dealSize",
      label: "Deal Size",
      sortable: true,
      render: (deal) => <span className="font-mono">{deal.dealSize}</span>,
    },
    {
      key: "status",
      label: "Status",
      render: (deal) => {
        const variant =
          deal.status === "active"
            ? "success"
            : deal.status === "completed"
              ? "info"
              : "warning";
        return <Badge variant={variant}>{deal.status}</Badge>;
      },
    },
  ];

  const fileColumns: Column<MockFile>[] = [
    { key: "fileName", label: "File Name", sortable: true },
    { key: "size", label: "Size", sortable: true },
    { key: "uploadDate", label: "Upload Date", sortable: true },
    { key: "processor", label: "Processor" },
    {
      key: "status",
      label: "Status",
      render: (file) => {
        const variant =
          file.status === "parsed"
            ? "success"
            : file.status === "processing"
              ? "warning"
              : "error";
        return <Badge variant={variant}>{file.status}</Badge>;
      },
    },
  ];

  const accountColumns: Column<MockAccount>[] = [
    {
      key: "code",
      label: "Account Code",
      sortable: true,
      render: (acc) => <span className="font-mono">{acc.code}</span>,
    },
    { key: "name", label: "Account Name", sortable: true },
    {
      key: "category",
      label: "Category",
      render: (acc) => <Badge variant="info">{acc.category}</Badge>,
    },
    {
      key: "mappingStatus",
      label: "Mapping Status",
      render: (acc) => {
        const variant = acc.mappingStatus === "mapped" ? "success" : "warning";
        return <Badge variant={variant}>{acc.mappingStatus}</Badge>;
      },
    },
  ];

  const adjustmentColumns: Column<MockAdjustment>[] = [
    { key: "item", label: "Item", sortable: true },
    {
      key: "category",
      label: "Category",
      render: (adj) => <Badge variant="neutral">{adj.category}</Badge>,
    },
    {
      key: "amount",
      label: "Amount",
      sortable: true,
      render: (adj) => {
        const formatted = `₩${(adj.amount / 1000000000).toFixed(1)}B`;
        const color = adj.amount > 0 ? "text-text-success" : "text-text-error";
        return <span className={cn("font-mono", color)}>{formatted}</span>;
      },
    },
    { key: "note", label: "Note" },
  ];

  const nwcColumns: Column<MockNwcItem>[] = [
    { key: "item", label: "Item", sortable: true },
    {
      key: "fy2023",
      label: "FY2023",
      render: (item) => <span className="font-mono">{item.fy2023}</span>,
    },
    {
      key: "fy2024",
      label: "FY2024",
      render: (item) => <span className="font-mono">{item.fy2024}</span>,
    },
    {
      key: "fy2025",
      label: "FY2025",
      render: (item) => <span className="font-mono">{item.fy2025}</span>,
    },
    {
      key: "trend",
      label: "Trend",
      render: (item) => {
        const variant = item.trend === "up" ? "success" : "info";
        return <Badge variant={variant}>{item.trend}</Badge>;
      },
    },
  ];

  const debtColumns: Column<MockDebtItem>[] = [
    { key: "description", label: "Description", sortable: true },
    {
      key: "amount",
      label: "Amount",
      sortable: true,
      render: (item) => <span className="font-mono">{item.amount}</span>,
    },
    {
      key: "classification",
      label: "Classification",
      render: (item) => {
        const variant =
          item.classification === "Debt"
            ? "error"
            : item.classification === "Cash"
              ? "success"
              : "warning";
        return <Badge variant={variant}>{item.classification}</Badge>;
      },
    },
    { key: "notes", label: "Notes" },
  ];

  const issueColumns: Column<MockIssue>[] = [
    { key: "title", label: "Issue", sortable: true },
    {
      key: "severity",
      label: "Severity",
      render: (issue) => {
        const variant =
          issue.severity === "high"
            ? "error"
            : issue.severity === "medium"
              ? "warning"
              : "info";
        return <Badge variant={variant}>{issue.severity}</Badge>;
      },
    },
    { key: "category", label: "Category" },
    { key: "owner", label: "Owner" },
    {
      key: "status",
      label: "Status",
      render: (issue) => {
        const variant =
          issue.status === "resolved"
            ? "success"
            : issue.status === "in-progress"
              ? "warning"
              : "neutral";
        return <Badge variant={variant}>{issue.status}</Badge>;
      },
    },
    {
      key: "impact",
      label: "Impact",
      render: (issue) => <span className="font-mono">{issue.impact}</span>,
    },
  ];

  return (
    <div className="bg-bg-cool min-h-screen">
      <HeroSection
        title="Auto FDD Gallery"
        subtitle="Financial Due Diligence module pages"
        backgroundUrl="https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=1920&h=600&fit=crop"
      />

      <div className="container mx-auto px-6 py-12">
        <div className="flex gap-8">
          <GalleryNav
            sections={sections}
            activeSection={activeSection}
            onSectionChange={setActiveSection}
          />

          <div className="flex-1 space-y-16">
            {/* 1. Deal List */}
            <section id="deal-list">
              <SectionDivider
                title="Deal List"
                description="Browse and manage all FDD deals"
                icon={Briefcase}
              />
              <PagePreviewCard route="/fdd/deals">
                <DataTable
                  data={mockDeals}
                  columns={dealColumns}
                  keyField="id"
                  uppercaseHeaders
                  striped
                />
              </PagePreviewCard>
            </section>

            {/* 2. Deal Setup Wizard */}
            <section id="deal-wizard">
              <SectionDivider
                title="Deal Setup Wizard"
                description="Step-by-step deal creation"
                icon={Settings}
              />
              <PagePreviewCard route="/fdd/deals/new">
                <div className="space-y-8">
                  {/* Step indicator */}
                  <div className="flex items-center justify-center gap-4">
                    <div className="flex flex-col items-center">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-600 text-white font-semibold">
                        1
                      </div>
                      <span className="mt-2 text-sm font-medium text-primary-600">
                        Company Info
                      </span>
                    </div>
                    <div className="h-0.5 w-24 bg-border-strong" />
                    <div className="flex flex-col items-center">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-bg-weak text-text-subtle font-semibold">
                        2
                      </div>
                      <span className="mt-2 text-sm text-text-subtle">
                        Deal Parameters
                      </span>
                    </div>
                    <div className="h-0.5 w-24 bg-border-strong" />
                    <div className="flex flex-col items-center">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-bg-weak text-text-subtle font-semibold">
                        3
                      </div>
                      <span className="mt-2 text-sm text-text-subtle">
                        Review
                      </span>
                    </div>
                  </div>

                  {/* Mock form */}
                  <Card variant="forest-lift" className="p-6">
                    <div className="space-y-4">
                      <Input label="Company Name" placeholder="Enter target company name" />
                      <Select
                        label="Deal Type"
                        value=""
                        onChange={() => {}}
                        options={[
                          { value: "completion", label: "Completion" },
                          { value: "locked-box", label: "Locked Box" },
                        ]}
                      />
                      <Select
                        label="Currency"
                        value=""
                        onChange={() => {}}
                        options={[
                          { value: "KRW", label: "KRW" },
                          { value: "USD", label: "USD" },
                        ]}
                      />
                      <div className="flex gap-3 pt-4">
                        <Button variant="primary">Start Deal</Button>
                        <Button variant="secondary">Cancel</Button>
                      </div>
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 3. Overview */}
            <section id="overview">
              <SectionDivider
                title="Overview"
                description="High-level deal progress and status"
                icon={BarChart3}
              />
              <PagePreviewCard route="/fdd/deals/:id">
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KpiCard
                      title="Deal Status"
                      value="Active"
                      variant="default"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Completion"
                      value="75%"
                      variant="positive"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Open Issues"
                      value="3"
                      variant="caution"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Days Remaining"
                      value="45"
                      variant="default"
                      hoverLift
                      generous
                    />
                  </div>

                  <Card variant="forest-lift" className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Phase Progress</h3>
                    <div className="space-y-3">
                      {[
                        { name: "Setup", progress: 100, color: "bg-primary-600" },
                        { name: "Upload", progress: 100, color: "bg-primary-600" },
                        { name: "Mapping", progress: 80, color: "bg-accent-600" },
                        { name: "Analysis", progress: 40, color: "bg-warning-500" },
                        { name: "Report", progress: 0, color: "bg-border-strong" },
                      ].map((phase) => (
                        <div key={phase.name}>
                          <div className="flex justify-between text-sm mb-1">
                            <span className="font-medium">{phase.name}</span>
                            <span className="text-text-subtle">{phase.progress}%</span>
                          </div>
                          <div className="h-2 bg-bg-weak rounded-full overflow-hidden">
                            <div
                              className={cn("h-full transition-all", phase.color)}
                              style={{ width: `${phase.progress}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 4. Deal Setup */}
            <section id="deal-setup">
              <SectionDivider
                title="Deal Setup"
                description="Configure deal parameters and settings"
                icon={Settings}
              />
              <PagePreviewCard route="/fdd/deals/:id/setup">
                <Card variant="forest-lift" className="p-6">
                  <div className="space-y-4">
                    <Input label="Deal Name" value="프로젝트 알파" readOnly />
                    <Select
                      label="Deal Type"
                      value="completion"
                      onChange={() => {}}
                      options={[
                        { value: "completion", label: "Completion" },
                        { value: "locked-box", label: "Locked Box" },
                      ]}
                    />
                    <Input label="Client Name" value="Petrabridge Partners" readOnly />
                    <Input label="Target Company" value="Alpha Tech Co." readOnly />
                    <Select
                      label="Base Currency"
                      value="KRW"
                      onChange={() => {}}
                      options={[
                        { value: "KRW", label: "KRW" },
                        { value: "USD", label: "USD" },
                      ]}
                    />
                    <Input
                      label="Reference Date"
                      type="date"
                      value="2026-02-11"
                      readOnly
                    />
                    <div className="flex gap-3 pt-4">
                      <Button variant="primary">Save Changes</Button>
                      <Button variant="secondary">Cancel</Button>
                    </div>
                  </div>
                </Card>
              </PagePreviewCard>
            </section>

            {/* 5. VDR */}
            <section id="vdr">
              <SectionDivider
                title="Virtual Data Room"
                description="Organize and manage deal documents"
                icon={FolderTree}
              />
              <PagePreviewCard route="/fdd/deals/:id/vdr">
                <div className="space-y-6">
                  <Card variant="forest-lift" className="p-6">
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-weak hover:bg-bg-subtle transition-colors cursor-pointer">
                        <FolderTree className="h-5 w-5 text-accent-600" />
                        <div className="flex-1">
                          <div className="font-medium">Financial Statements</div>
                          <div className="text-sm text-text-subtle">12 files</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-weak hover:bg-bg-subtle transition-colors cursor-pointer">
                        <FolderTree className="h-5 w-5 text-accent-600" />
                        <div className="flex-1">
                          <div className="font-medium">Contracts</div>
                          <div className="text-sm text-text-subtle">8 files</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-weak hover:bg-bg-subtle transition-colors cursor-pointer">
                        <FolderTree className="h-5 w-5 text-accent-600" />
                        <div className="flex-1">
                          <div className="font-medium">Tax Documents</div>
                          <div className="text-sm text-text-subtle">5 files</div>
                        </div>
                      </div>
                    </div>
                  </Card>

                  <Card
                    variant="forest-lift"
                    className="p-12 border-2 border-dashed border-border-strong"
                  >
                    <div className="flex flex-col items-center gap-4 text-center">
                      <Upload className="h-12 w-12 text-text-subtle" />
                      <div>
                        <div className="font-medium text-lg">
                          Drag and drop files here
                        </div>
                        <div className="text-sm text-text-subtle mt-1">
                          or click to browse
                        </div>
                      </div>
                      <Button variant="secondary">Select Files</Button>
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 6. Uploads */}
            <section id="uploads">
              <SectionDivider
                title="Uploads"
                description="Track document upload and parsing status"
                icon={FileUp}
              />
              <PagePreviewCard route="/fdd/deals/:id/uploads">
                <div className="space-y-4">
                  <DataTable
                    data={mockFiles}
                    columns={fileColumns}
                    keyField="id"
                    uppercaseHeaders
                    striped
                  />
                  <Card variant="forest-lift" className="p-4">
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <div className="flex justify-between text-sm mb-1">
                          <span className="font-medium">
                            Balance_Sheet_Q4.pdf
                          </span>
                          <span className="text-text-subtle">Processing... 67%</span>
                        </div>
                        <div className="h-2 bg-bg-weak rounded-full overflow-hidden">
                          <div
                            className="h-full bg-accent-600 transition-all"
                            style={{ width: "67%" }}
                          />
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 7. Definitions */}
            <section id="definitions">
              <SectionDivider
                title="Definitions"
                description="Define and categorize financial accounts"
                icon={FileText}
              />
              <PagePreviewCard route="/fdd/deals/:id/definitions">
                <DataTable
                  data={mockAccounts}
                  columns={accountColumns}
                  keyField="id"
                  uppercaseHeaders
                  striped
                />
              </PagePreviewCard>
            </section>

            {/* 8. Mapping */}
            <section id="mapping">
              <SectionDivider
                title="Mapping"
                description="Map source accounts to target definitions"
                icon={GitBranch}
              />
              <PagePreviewCard route="/fdd/deals/:id/mapping">
                <div className="space-y-6">
                  <Card variant="forest-lift" className="p-6">
                    <div className="grid grid-cols-2 gap-8">
                      <div>
                        <h4 className="font-semibold mb-3 text-sm uppercase text-text-subtle">
                          Source Accounts
                        </h4>
                        <div className="space-y-2">
                          {["매출", "매출원가", "판매비", "관리비"].map((item, i) => (
                            <div
                              key={i}
                              className="p-3 rounded-lg bg-bg-weak border border-border-strong"
                            >
                              {item}
                            </div>
                          ))}
                        </div>
                      </div>
                      <div>
                        <h4 className="font-semibold mb-3 text-sm uppercase text-text-subtle">
                          Target Accounts
                        </h4>
                        <div className="space-y-2">
                          {["Revenue", "COGS", "S&M Expense", "G&A Expense"].map(
                            (item, i) => (
                              <div
                                key={i}
                                className="p-3 rounded-lg bg-accent-50 border border-accent-200"
                              >
                                {item}
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>

                  <div className="grid grid-cols-3 gap-4">
                    <KpiCard
                      title="Total Accounts"
                      value="15"
                      variant="default"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Mapped"
                      value="12"
                      variant="positive"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Unmapped"
                      value="3"
                      variant="caution"
                      hoverLift
                      generous
                    />
                  </div>
                </div>
              </PagePreviewCard>
            </section>

            {/* 9. QoE Bridge */}
            <section id="qoe-bridge">
              <SectionDivider
                title="Quality of Earnings Bridge"
                description="Reconcile reported to adjusted EBITDA"
                icon={TrendingUp}
              />
              <PagePreviewCard route="/fdd/deals/:id/qoe">
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KpiCard
                      title="Reported EBITDA"
                      value="₩12.5B"
                      variant="default"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Adjusted EBITDA"
                      value="₩14.2B"
                      variant="positive"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Net Adjustments"
                      value="+₩1.7B"
                      variant="positive"
                      hoverLift
                      generous
                    />
                  </div>

                  <Card variant="forest-lift" className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Adjustments</h3>
                    <DataTable
                      data={mockAdjustments}
                      columns={adjustmentColumns}
                      keyField="id"
                      uppercaseHeaders
                      striped
                    />
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 10. NWC */}
            <section id="nwc">
              <SectionDivider
                title="Net Working Capital"
                description="Analyze working capital trends and normalization"
                icon={Wallet}
              />
              <PagePreviewCard route="/fdd/deals/:id/nwc">
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <KpiCard
                      title="Average NWC"
                      value="₩8.3B"
                      variant="default"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="NWC Target"
                      value="₩7.5B"
                      variant="positive"
                      hoverLift
                      generous
                    />
                  </div>

                  <Card variant="forest-lift" className="p-6">
                    <h3 className="text-lg font-semibold mb-4">NWC Components</h3>
                    <DataTable
                      data={mockNwcItems}
                      columns={nwcColumns}
                      keyField="id"
                      uppercaseHeaders
                      striped
                    />
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 11. Net Debt */}
            <section id="net-debt">
              <SectionDivider
                title="Net Debt"
                description="Calculate enterprise value bridge"
                icon={CreditCard}
              />
              <PagePreviewCard route="/fdd/deals/:id/netdebt">
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KpiCard
                      title="Total Debt"
                      value="₩25.0B"
                      variant="negative"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Cash & Equiv"
                      value="₩8.5B"
                      variant="positive"
                      hoverLift
                      generous
                    />
                    <KpiCard
                      title="Net Debt"
                      value="₩16.5B"
                      variant="default"
                      hoverLift
                      generous
                    />
                  </div>

                  <Card variant="forest-lift" className="p-6">
                    <h3 className="text-lg font-semibold mb-4">Debt Schedule</h3>
                    <DataTable
                      data={mockDebtItems}
                      columns={debtColumns}
                      keyField="id"
                      uppercaseHeaders
                      striped
                    />
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* 12. Issues */}
            <section id="issues">
              <SectionDivider
                title="Issues"
                description="Track and manage due diligence findings"
                icon={AlertCircle}
              />
              <PagePreviewCard route="/fdd/deals/:id/issues">
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm">
                      All
                    </Button>
                    <Button variant="secondary" size="sm">
                      High
                    </Button>
                    <Button variant="secondary" size="sm">
                      Medium
                    </Button>
                    <Button variant="secondary" size="sm">
                      Low
                    </Button>
                  </div>

                  <DataTable
                    data={mockIssues}
                    columns={issueColumns}
                    keyField="id"
                    uppercaseHeaders
                    striped
                  />
                </div>
              </PagePreviewCard>
            </section>

            {/* 13. Report */}
            <section id="report">
              <SectionDivider
                title="Report"
                description="Generate and export final FDD report"
                icon={FileCheck}
              />
              <PagePreviewCard route="/fdd/deals/:id/report">
                <Card variant="forest-lift" className="p-6">
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-bold">
                        Financial Due Diligence Report
                      </h2>
                      <p className="text-text-subtle mt-1">
                        Project Alpha - Draft
                      </p>
                    </div>

                    <div className="space-y-3">
                      <h3 className="font-semibold text-sm uppercase text-text-subtle">
                        Included Sections
                      </h3>
                      {[
                        "Executive Summary",
                        "Quality of Earnings Analysis",
                        "Net Working Capital Analysis",
                        "Net Debt Analysis",
                        "Key Issues and Findings",
                      ].map((section, i) => (
                        <label key={i} className="flex items-center gap-3 cursor-pointer">
                          <input
                            type="checkbox"
                            checked
                            readOnly
                            className="h-4 w-4 rounded border-border-strong text-primary-600"
                          />
                          <span>{section}</span>
                        </label>
                      ))}
                    </div>

                    <div className="flex gap-3 pt-4">
                      <Button variant="primary">Generate Report</Button>
                      <Button variant="secondary">Download PDF</Button>
                    </div>
                  </div>
                </Card>
              </PagePreviewCard>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
