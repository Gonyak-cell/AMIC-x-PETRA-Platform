import { useState } from "react";
import {
  HeroSection,
  SectionDivider,
  PagePreviewCard,
  GalleryNav,
  type GallerySection,
} from "@/components/gallery";
import { Card, KpiCard, Badge, Button, DataTable, Input } from "@/components/ui";
import type { Column } from "@/components/ui";
import {
  LayoutDashboard,
  Building2,
  TrendingUp,
  Landmark,
  Newspaper,
  Handshake,
  ShieldAlert,
  PieChart,
  Users,
  UserCircle,
  Link2,
  FileSearch,
  Eye,
  Bell,
  Search,
  BarChart3,
  DollarSign,
  Activity,
  Globe,
  AlertTriangle,
  Star,
  Calendar,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Mock data interfaces                                               */
/* ------------------------------------------------------------------ */

interface MockCompany {
  id: string;
  name: string;
  code: string;
  sector: string;
  marketCap: string;
  change: string;
}

interface MockFund {
  id: string;
  name: string;
  type: string;
  aum: string;
  returns: string;
  manager: string;
}

interface MockReit {
  id: string;
  name: string;
  assetType: string;
  totalAssets: string;
  divYield: string;
  status: string;
}

interface MockNews {
  id: string;
  title: string;
  source: string;
  date: string;
  sentiment: "Positive" | "Negative" | "Neutral";
}

interface MockDeal {
  id: string;
  name: string;
  company: string;
  stage: string;
  value: string;
  date: string;
}

interface MockSanction {
  id: string;
  entity: string;
  country: string;
  program: string;
  matchScore: string;
  status: string;
}

interface MockManager {
  id: string;
  name: string;
  firm: string;
  fundsManaged: number;
  totalAum: string;
  rating: string;
}

interface MockEntity {
  id: string;
  sourceName: string;
  candidateMatch: string;
  score: string;
  status: string;
}

interface MockDisclosure {
  id: string;
  title: string;
  company: string;
  type: string;
  filedDate: string;
  status: string;
}

interface MockWatchlistItem {
  id: string;
  name: string;
  type: string;
  lastPrice: string;
  change: string;
  alert: string;
}

/* ------------------------------------------------------------------ */
/*  Mock data                                                          */
/* ------------------------------------------------------------------ */

const mockCompanies: MockCompany[] = [
  { id: "1", name: "삼성전자", code: "005930", sector: "IT", marketCap: "₩412.5T", change: "+1.2%" },
  { id: "2", name: "SK하이닉스", code: "000660", sector: "Semiconductors", marketCap: "₩128.3T", change: "+2.8%" },
  { id: "3", name: "LG에너지솔루션", code: "373220", sector: "Battery", marketCap: "₩95.1T", change: "-0.5%" },
  { id: "4", name: "현대자동차", code: "005380", sector: "Automotive", marketCap: "₩52.7T", change: "+0.3%" },
];

const mockFunds: MockFund[] = [
  { id: "1", name: "Korea Growth Fund I", type: "Equity", aum: "₩2.5T", returns: "+14.2%", manager: "Kim J.H." },
  { id: "2", name: "Asia Pacific Balanced", type: "Balanced", aum: "₩1.8T", returns: "+8.7%", manager: "Park S.Y." },
  { id: "3", name: "Tech Innovation Fund", type: "Sector", aum: "₩950B", returns: "+22.1%", manager: "Lee M.K." },
];

const mockReits: MockReit[] = [
  { id: "1", name: "SK리츠", assetType: "Office", totalAssets: "₩3.2T", divYield: "5.8%", status: "Active" },
  { id: "2", name: "롯데리츠", assetType: "Retail", totalAssets: "₩2.1T", divYield: "6.2%", status: "Active" },
  { id: "3", name: "NH올원리츠", assetType: "Diversified", totalAssets: "₩1.5T", divYield: "5.1%", status: "Active" },
];

const mockNews: MockNews[] = [
  { id: "1", title: "Samsung Electronics Reports Record Q4 Revenue", source: "Bloomberg", date: "2026-02-10", sentiment: "Positive" },
  { id: "2", title: "Korea CPI Slows to 2.1% in January", source: "Reuters", date: "2026-02-09", sentiment: "Neutral" },
  { id: "3", title: "SK Hynix Faces Supply Chain Disruption Concerns", source: "Nikkei", date: "2026-02-08", sentiment: "Negative" },
  { id: "4", title: "Hyundai Motor Expands EV Production in Georgia", source: "CNBC", date: "2026-02-07", sentiment: "Positive" },
];

const mockDeals: MockDeal[] = [
  { id: "1", name: "Project Alpha", company: "삼성SDI", stage: "Due Diligence", value: "₩500B", date: "2026-02-05" },
  { id: "2", name: "Project Beta", company: "카카오엔터", stage: "Negotiation", value: "₩120B", date: "2026-01-28" },
  { id: "3", name: "Project Gamma", company: "쿠팡", stage: "Screening", value: "₩800B", date: "2026-02-01" },
  { id: "4", name: "Project Delta", company: "네이버클라우드", stage: "Closed", value: "₩250B", date: "2025-12-15" },
];

const mockSanctions: MockSanction[] = [
  { id: "1", entity: "Sunrise Trading Co.", country: "North Korea", program: "UN Sanctions", matchScore: "95%", status: "Confirmed" },
  { id: "2", entity: "Pacific Holdings Ltd.", country: "Iran", program: "OFAC SDN", matchScore: "78%", status: "Review" },
  { id: "3", entity: "East Wind Corp.", country: "Russia", program: "EU Sanctions", matchScore: "62%", status: "Cleared" },
];

const mockManagers: MockManager[] = [
  { id: "1", name: "Kim Jin-Hwan", firm: "AMIC Partners", fundsManaged: 4, totalAum: "₩5.2T", rating: "A+" },
  { id: "2", name: "Park Su-Yeon", firm: "Hana Asset", fundsManaged: 3, totalAum: "₩3.8T", rating: "A" },
  { id: "3", name: "Lee Min-Kyu", firm: "KB Investment", fundsManaged: 5, totalAum: "₩7.1T", rating: "A+" },
];

const mockEntities: MockEntity[] = [
  { id: "1", sourceName: "Samsung Elec.", candidateMatch: "삼성전자 (005930)", score: "98%", status: "Confirmed" },
  { id: "2", sourceName: "Hyundai Motor Co", candidateMatch: "현대자동차 (005380)", score: "95%", status: "Confirmed" },
  { id: "3", sourceName: "SK Hynics", candidateMatch: "SK하이닉스 (000660)", score: "87%", status: "Review" },
  { id: "4", sourceName: "LG Energy Sol.", candidateMatch: "LG에너지솔루션 (373220)", score: "91%", status: "Confirmed" },
];

const mockDisclosures: MockDisclosure[] = [
  { id: "1", title: "Annual Report 2025", company: "삼성전자", type: "Annual", filedDate: "2026-01-30", status: "Filed" },
  { id: "2", title: "Quarterly Earnings Q4", company: "SK하이닉스", type: "Quarterly", filedDate: "2026-01-25", status: "Filed" },
  { id: "3", title: "Material Event Notice", company: "카카오", type: "Event", filedDate: "2026-02-03", status: "Pending" },
];

const mockWatchlist: MockWatchlistItem[] = [
  { id: "1", name: "삼성전자", type: "Stock", lastPrice: "₩78,200", change: "+1.2%", alert: "Price > ₩80,000" },
  { id: "2", name: "SK하이닉스", type: "Stock", lastPrice: "₩195,500", change: "+2.8%", alert: "Volume spike" },
  { id: "3", name: "Korea Growth Fund I", type: "Fund", lastPrice: "₩12,450", change: "+0.5%", alert: "NAV change > 3%" },
  { id: "4", name: "SK리츠", type: "REIT", lastPrice: "₩4,850", change: "-0.3%", alert: "Dividend date" },
];

/* ------------------------------------------------------------------ */
/*  Gallery sections                                                   */
/* ------------------------------------------------------------------ */

const sections: GallerySection[] = [
  { id: "dashboard", label: "Dashboard", path: "/kiis" },
  { id: "company-list", label: "Company List", path: "/kiis/companies" },
  { id: "company-detail", label: "Company Detail", path: "/kiis/companies/:code" },
  { id: "fund-list", label: "Fund List", path: "/kiis/funds" },
  { id: "fund-detail", label: "Fund Detail", path: "/kiis/funds/:id" },
  { id: "reit-list", label: "REIT List", path: "/kiis/reits" },
  { id: "reit-detail", label: "REIT Detail", path: "/kiis/reits/:id" },
  { id: "news-list", label: "News List", path: "/kiis/news" },
  { id: "news-detail", label: "News Detail", path: "/kiis/news/:id" },
  { id: "deal-sourcing", label: "Deal Sourcing", path: "/kiis/deals" },
  { id: "sanctions", label: "Sanctions", path: "/kiis/sanctions" },
  { id: "portfolio", label: "Portfolio", path: "/kiis/portfolio" },
  { id: "managers", label: "Managers", path: "/kiis/managers" },
  { id: "manager-profile", label: "Manager Profile", path: "/kiis/managers/:name" },
  { id: "entity-resolution", label: "Entity Resolution", path: "/kiis/entities" },
  { id: "disclosures", label: "Disclosures", path: "/kiis/disclosures" },
  { id: "watchlist", label: "Watchlist", path: "/kiis/watchlist" },
];

/* ------------------------------------------------------------------ */
/*  Column definitions                                                 */
/* ------------------------------------------------------------------ */

const companyColumns: Column<MockCompany>[] = [
  { key: "name", header: "Company", render: (r) => <span className="font-semibold">{r.name}</span> },
  { key: "code", header: "Code", mono: true },
  { key: "sector", header: "Sector" },
  { key: "marketCap", header: "Market Cap", align: "right", mono: true },
  {
    key: "change",
    header: "Change",
    align: "right",
    render: (r) => (
      <span className={r.change.startsWith("+") ? "text-positive font-medium" : "text-negative font-medium"}>
        {r.change}
      </span>
    ),
  },
];

const fundColumns: Column<MockFund>[] = [
  { key: "name", header: "Fund Name", render: (r) => <span className="font-semibold">{r.name}</span> },
  { key: "type", header: "Type", render: (r) => <Badge variant="info">{r.type}</Badge> },
  { key: "aum", header: "AUM", align: "right", mono: true },
  {
    key: "returns",
    header: "Returns (1Y)",
    align: "right",
    render: (r) => <span className="text-positive font-medium">{r.returns}</span>,
  },
  { key: "manager", header: "Manager" },
];

const reitColumns: Column<MockReit>[] = [
  { key: "name", header: "REIT Name", render: (r) => <span className="font-semibold">{r.name}</span> },
  { key: "assetType", header: "Asset Type" },
  { key: "totalAssets", header: "Total Assets", align: "right", mono: true },
  { key: "divYield", header: "Div. Yield", align: "right", mono: true },
  {
    key: "status",
    header: "Status",
    render: (r) => <Badge variant={r.status === "Active" ? "success" : "neutral"}>{r.status}</Badge>,
  },
];

const newsColumns: Column<MockNews>[] = [
  { key: "title", header: "Headline", render: (r) => <span className="font-medium">{r.title}</span> },
  { key: "source", header: "Source" },
  { key: "date", header: "Date", mono: true },
  {
    key: "sentiment",
    header: "Sentiment",
    render: (r) => (
      <Badge
        variant={r.sentiment === "Positive" ? "success" : r.sentiment === "Negative" ? "error" : "neutral"}
      >
        {r.sentiment}
      </Badge>
    ),
  },
];

const dealColumns: Column<MockDeal>[] = [
  { key: "name", header: "Deal Name", render: (r) => <span className="font-semibold">{r.name}</span> },
  { key: "company", header: "Company" },
  {
    key: "stage",
    header: "Stage",
    render: (r) => (
      <Badge
        variant={
          r.stage === "Closed"
            ? "success"
            : r.stage === "Due Diligence"
              ? "info"
              : r.stage === "Negotiation"
                ? "warning"
                : "neutral"
        }
      >
        {r.stage}
      </Badge>
    ),
  },
  { key: "value", header: "Value", align: "right", mono: true },
  { key: "date", header: "Date", mono: true },
];

const sanctionColumns: Column<MockSanction>[] = [
  { key: "entity", header: "Entity", render: (r) => <span className="font-semibold">{r.entity}</span> },
  { key: "country", header: "Country" },
  { key: "program", header: "Program" },
  { key: "matchScore", header: "Match", align: "center", mono: true },
  {
    key: "status",
    header: "Status",
    render: (r) => (
      <Badge variant={r.status === "Confirmed" ? "error" : r.status === "Review" ? "warning" : "success"}>
        {r.status}
      </Badge>
    ),
  },
];

const managerColumns: Column<MockManager>[] = [
  { key: "name", header: "Name", render: (r) => <span className="font-semibold">{r.name}</span> },
  { key: "firm", header: "Firm" },
  { key: "fundsManaged", header: "Funds", align: "center" },
  { key: "totalAum", header: "Total AUM", align: "right", mono: true },
  {
    key: "rating",
    header: "Rating",
    render: (r) => <Badge variant={r.rating === "A+" ? "success" : "info"}>{r.rating}</Badge>,
  },
];

const entityColumns: Column<MockEntity>[] = [
  { key: "sourceName", header: "Source Name", render: (r) => <span className="font-medium">{r.sourceName}</span> },
  { key: "candidateMatch", header: "Candidate Match" },
  { key: "score", header: "Score", align: "center", mono: true },
  {
    key: "status",
    header: "Status",
    render: (r) => (
      <Badge variant={r.status === "Confirmed" ? "success" : "warning"}>{r.status}</Badge>
    ),
  },
];

const disclosureColumns: Column<MockDisclosure>[] = [
  { key: "title", header: "Title", render: (r) => <span className="font-semibold">{r.title}</span> },
  { key: "company", header: "Company" },
  {
    key: "type",
    header: "Type",
    render: (r) => <Badge variant={r.type === "Annual" ? "info" : r.type === "Quarterly" ? "success" : "warning"}>{r.type}</Badge>,
  },
  { key: "filedDate", header: "Filed Date", mono: true },
  {
    key: "status",
    header: "Status",
    render: (r) => <Badge variant={r.status === "Filed" ? "success" : "warning"}>{r.status}</Badge>,
  },
];

const watchlistColumns: Column<MockWatchlistItem>[] = [
  { key: "name", header: "Name", render: (r) => <span className="font-semibold">{r.name}</span> },
  {
    key: "type",
    header: "Type",
    render: (r) => <Badge variant={r.type === "Stock" ? "info" : r.type === "Fund" ? "success" : "neutral"}>{r.type}</Badge>,
  },
  { key: "lastPrice", header: "Last Price", align: "right", mono: true },
  {
    key: "change",
    header: "Change",
    align: "right",
    render: (r) => (
      <span className={r.change.startsWith("+") ? "text-positive font-medium" : "text-negative font-medium"}>
        {r.change}
      </span>
    ),
  },
  { key: "alert", header: "Alert Rule" },
];

/* ------------------------------------------------------------------ */
/*  Page component                                                     */
/* ------------------------------------------------------------------ */

export default function GallerySamplePage() {
  const [activeSection, setActiveSection] = useState<string>("dashboard");

  return (
    <div className="bg-bg-cool min-h-screen">
      <HeroSection
        title="KIIS Module Gallery"
        subtitle="Korea Investment Intelligence System — 17 pages"
        backgroundUrl="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1600&q=80"
      />

      <div className="container mx-auto px-6 py-12">
        <div className="flex gap-8">
          <GalleryNav
            sections={sections}
            activeSection={activeSection}
            onSectionChange={setActiveSection}
          />

          <div className="flex-1 min-w-0 space-y-16">
            {/* ============================================================ */}
            {/* Section 1: Dashboard                                         */}
            {/* ============================================================ */}
            <section id="dashboard">
              <SectionDivider
                label="Dashboard"
                anchor="dashboard"
                route="/kiis"
                icon={LayoutDashboard}
                description="Market overview with KPIs, news, and watchlist summary"
              />
              <PagePreviewCard title="Dashboard" path="/kiis" tags={["Overview", "KPI"]}>
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KpiCard title="KOSPI" value="2,687.45" icon={BarChart3} trend="up" trendValue="+0.82%" variant="positive" hoverLift generous />
                    <KpiCard title="KOSDAQ" value="842.31" icon={TrendingUp} trend="down" trendValue="-0.35%" variant="negative" hoverLift generous />
                    <KpiCard title="Tracked Companies" value="1,284" icon={Building2} variant="default" hoverLift generous />
                    <KpiCard title="Active Alerts" value="12" icon={Bell} variant="caution" hoverLift generous />
                  </div>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-3">Recent News</h3>
                    <div className="space-y-3">
                      {mockNews.slice(0, 3).map((n) => (
                        <div key={n.id} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
                          <div>
                            <p className="text-sm font-medium">{n.title}</p>
                            <p className="text-xs text-text-secondary">{n.source} &middot; {n.date}</p>
                          </div>
                          <Badge variant={n.sentiment === "Positive" ? "success" : n.sentiment === "Negative" ? "error" : "neutral"}>
                            {n.sentiment}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </Card>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-3">Watchlist Summary</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {mockWatchlist.slice(0, 4).map((w) => (
                        <div key={w.id} className="p-3 bg-bg-cool rounded-lg text-center">
                          <p className="text-xs text-text-secondary">{w.name}</p>
                          <p className="font-mono font-semibold mt-1">{w.lastPrice}</p>
                          <p className={`text-xs mt-0.5 ${w.change.startsWith("+") ? "text-positive" : "text-negative"}`}>
                            {w.change}
                          </p>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 2: Company List                                      */}
            {/* ============================================================ */}
            <section id="company-list">
              <SectionDivider
                label="Company List"
                anchor="company-list"
                route="/kiis/companies"
                icon={Building2}
                description="Browse and search Korean listed companies"
              />
              <PagePreviewCard title="Company List" path="/kiis/companies" tags={["Search", "Table"]}>
                <div className="space-y-4">
                  <Input placeholder="Search companies by name or code..." />
                  <DataTable data={mockCompanies} columns={companyColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 3: Company Detail                                    */}
            {/* ============================================================ */}
            <section id="company-detail">
              <SectionDivider
                label="Company Detail"
                anchor="company-detail"
                route="/kiis/companies/:code"
                icon={Building2}
                description="Company profile with financial KPIs and chart"
              />
              <PagePreviewCard title="Company Detail" path="/kiis/companies/:code" tags={["Profile", "Financials"]}>
                <div className="space-y-6">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h2 className="text-2xl font-bold">삼성전자</h2>
                    <Badge variant="info">005930</Badge>
                    <Badge variant="success">IT</Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KpiCard title="Market Cap" value="₩412.5T" icon={DollarSign} variant="default" hoverLift generous />
                    <KpiCard title="Revenue (TTM)" value="₩302.2T" icon={BarChart3} trend="up" trendValue="+8.5%" variant="positive" hoverLift generous />
                    <KpiCard title="P/E Ratio" value="14.2x" icon={Activity} variant="default" hoverLift generous />
                  </div>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-4">Price Chart (6M)</h3>
                    <div className="h-40 bg-gradient-to-r from-amic-50 to-accent-50 rounded-lg flex items-center justify-center">
                      <span className="text-sm text-text-secondary">Chart placeholder — Recharts integration</span>
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 4: Fund List                                         */}
            {/* ============================================================ */}
            <section id="fund-list">
              <SectionDivider
                label="Fund List"
                anchor="fund-list"
                route="/kiis/funds"
                icon={PieChart}
                description="Browse investment funds with AUM and type"
              />
              <PagePreviewCard title="Fund List" path="/kiis/funds" tags={["Funds", "Table"]}>
                <DataTable data={mockFunds} columns={fundColumns} keyField="id" uppercaseHeaders striped />
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 5: Fund Detail                                       */}
            {/* ============================================================ */}
            <section id="fund-detail">
              <SectionDivider
                label="Fund Detail"
                anchor="fund-detail"
                route="/kiis/funds/:id"
                icon={PieChart}
                description="Fund profile with performance KPIs"
              />
              <PagePreviewCard title="Fund Detail" path="/kiis/funds/:id" tags={["Profile", "Performance"]}>
                <div className="space-y-6">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h2 className="text-2xl font-bold">Korea Growth Fund I</h2>
                    <Badge variant="info">Equity</Badge>
                    <Badge variant="success">Active</Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <KpiCard title="AUM" value="₩2.5T" icon={DollarSign} variant="default" hoverLift generous />
                    <KpiCard title="1Y Return" value="+14.2%" icon={TrendingUp} trend="up" trendValue="vs. KOSPI +8.1%" variant="positive" hoverLift generous />
                    <KpiCard title="Sharpe Ratio" value="1.32" icon={Activity} variant="positive" hoverLift generous />
                    <KpiCard title="Inception" value="2019-03" icon={Calendar} variant="default" hoverLift generous />
                  </div>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-4">NAV Performance</h3>
                    <div className="h-36 bg-gradient-to-r from-amic-50 to-accent-50 rounded-lg flex items-center justify-center">
                      <span className="text-sm text-text-secondary">Performance chart placeholder</span>
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 6: REIT List                                         */}
            {/* ============================================================ */}
            <section id="reit-list">
              <SectionDivider
                label="REIT List"
                anchor="reit-list"
                route="/kiis/reits"
                icon={Landmark}
                description="Browse REITs with asset types and yields"
              />
              <PagePreviewCard title="REIT List" path="/kiis/reits" tags={["REITs", "Table"]}>
                <DataTable data={mockReits} columns={reitColumns} keyField="id" uppercaseHeaders striped />
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 7: REIT Detail                                       */}
            {/* ============================================================ */}
            <section id="reit-detail">
              <SectionDivider
                label="REIT Detail"
                anchor="reit-detail"
                route="/kiis/reits/:id"
                icon={Landmark}
                description="REIT profile with asset composition"
              />
              <PagePreviewCard title="REIT Detail" path="/kiis/reits/:id" tags={["Profile", "Assets"]}>
                <div className="space-y-6">
                  <div className="flex items-center gap-3 flex-wrap">
                    <h2 className="text-2xl font-bold">SK리츠</h2>
                    <Badge variant="info">Office</Badge>
                    <Badge variant="success">Active</Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KpiCard title="Total Assets" value="₩3.2T" icon={Landmark} variant="default" hoverLift generous />
                    <KpiCard title="Dividend Yield" value="5.8%" icon={DollarSign} trend="up" trendValue="+0.3%p YoY" variant="positive" hoverLift generous />
                    <KpiCard title="Occupancy" value="96.2%" icon={Building2} variant="positive" hoverLift generous />
                  </div>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-4">Asset Composition</h3>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { label: "Seoul Office", pct: "62%" },
                        { label: "Logistics", pct: "23%" },
                        { label: "Data Center", pct: "15%" },
                      ].map((a) => (
                        <div key={a.label} className="p-3 bg-bg-cool rounded-lg text-center">
                          <p className="text-xs text-text-secondary">{a.label}</p>
                          <p className="font-mono text-lg font-semibold mt-1">{a.pct}</p>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 8: News List                                         */}
            {/* ============================================================ */}
            <section id="news-list">
              <SectionDivider
                label="News List"
                anchor="news-list"
                route="/kiis/news"
                icon={Newspaper}
                description="Market news with sentiment analysis"
              />
              <PagePreviewCard title="News List" path="/kiis/news" tags={["News", "Sentiment"]}>
                <div className="space-y-4">
                  <div className="flex gap-2 flex-wrap">
                    <Button variant="accent" size="sm">All</Button>
                    <Button variant="secondary" size="sm">Positive</Button>
                    <Button variant="secondary" size="sm">Neutral</Button>
                    <Button variant="secondary" size="sm">Negative</Button>
                  </div>
                  <DataTable data={mockNews} columns={newsColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 9: News Detail                                       */}
            {/* ============================================================ */}
            <section id="news-detail">
              <SectionDivider
                label="News Detail"
                anchor="news-detail"
                route="/kiis/news/:id"
                icon={Newspaper}
                description="Full article with related company links"
              />
              <PagePreviewCard title="News Detail" path="/kiis/news/:id" tags={["Article", "Analysis"]}>
                <div className="space-y-6">
                  <div>
                    <h2 className="text-2xl font-bold mb-2">Samsung Electronics Reports Record Q4 Revenue</h2>
                    <div className="flex items-center gap-3 text-sm text-text-secondary">
                      <span>Bloomberg</span>
                      <span>&middot;</span>
                      <span>2026-02-10</span>
                      <Badge variant="success">Positive</Badge>
                    </div>
                  </div>

                  <Card variant="forest-lift">
                    <div className="space-y-3">
                      <div className="h-3 bg-gray-200 rounded w-full" />
                      <div className="h-3 bg-gray-200 rounded w-5/6" />
                      <div className="h-3 bg-gray-200 rounded w-4/5" />
                      <div className="h-3 bg-gray-200 rounded w-full" />
                      <div className="h-3 bg-gray-200 rounded w-3/4" />
                    </div>
                  </Card>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-3">Related Companies</h3>
                    <div className="flex flex-wrap gap-2">
                      {["삼성전자 (005930)", "삼성SDI (006400)", "삼성전기 (009150)"].map((c) => (
                        <div key={c} className="px-3 py-2 bg-bg-cool rounded-lg text-sm font-medium flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-amic" />
                          {c}
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 10: Deal Sourcing                                    */}
            {/* ============================================================ */}
            <section id="deal-sourcing">
              <SectionDivider
                label="Deal Sourcing"
                anchor="deal-sourcing"
                route="/kiis/deals"
                icon={Handshake}
                description="Deal pipeline with stage tracking"
              />
              <PagePreviewCard title="Deal Sourcing" path="/kiis/deals" tags={["Pipeline", "Deals"]}>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <KpiCard title="Active Deals" value="8" icon={Handshake} variant="default" hoverLift generous />
                    <KpiCard title="Pipeline Value" value="₩2.4T" icon={DollarSign} trend="up" trendValue="+15%" variant="positive" hoverLift generous />
                    <KpiCard title="Closed (YTD)" value="3" icon={TrendingUp} variant="positive" hoverLift generous />
                    <KpiCard title="Avg. Deal Size" value="₩310B" icon={BarChart3} variant="default" hoverLift generous />
                  </div>
                  <DataTable data={mockDeals} columns={dealColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 11: Sanctions                                        */}
            {/* ============================================================ */}
            <section id="sanctions">
              <SectionDivider
                label="Sanctions"
                anchor="sanctions"
                route="/kiis/sanctions"
                icon={ShieldAlert}
                description="Sanctions screening and compliance checks"
              />
              <PagePreviewCard title="Sanctions" path="/kiis/sanctions" tags={["Compliance", "Screening"]}>
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <Input placeholder="Search entity name..." />
                    </div>
                    <Button variant="primary" size="md">
                      <Search className="w-4 h-4 mr-1" />
                      Screen
                    </Button>
                  </div>
                  <DataTable data={mockSanctions} columns={sanctionColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 12: Portfolio                                        */}
            {/* ============================================================ */}
            <section id="portfolio">
              <SectionDivider
                label="Portfolio"
                anchor="portfolio"
                route="/kiis/portfolio"
                icon={PieChart}
                description="Portfolio KPIs and allocation overview"
              />
              <PagePreviewCard title="Portfolio" path="/kiis/portfolio" tags={["Portfolio", "Allocation"]}>
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <KpiCard title="Total NAV" value="₩15.8T" icon={DollarSign} variant="default" hoverLift generous />
                    <KpiCard title="YTD Return" value="+9.4%" icon={TrendingUp} trend="up" trendValue="vs. BM +6.2%" variant="positive" hoverLift generous />
                    <KpiCard title="Holdings" value="142" icon={PieChart} variant="default" hoverLift generous />
                    <KpiCard title="Risk Score" value="Medium" icon={AlertTriangle} variant="caution" hoverLift generous />
                  </div>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-4">Allocation Summary</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {[
                        { label: "Equities", pct: "45%", color: "bg-amic" },
                        { label: "Fixed Income", pct: "25%", color: "bg-accent" },
                        { label: "Alternatives", pct: "20%", color: "bg-caution" },
                        { label: "Cash", pct: "10%", color: "bg-gray-400" },
                      ].map((a) => (
                        <div key={a.label} className="p-3 bg-bg-cool rounded-lg">
                          <div className="flex items-center gap-2 mb-1">
                            <div className={`w-3 h-3 rounded-full ${a.color}`} />
                            <span className="text-xs text-text-secondary">{a.label}</span>
                          </div>
                          <p className="font-mono text-lg font-semibold">{a.pct}</p>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 13: Managers                                         */}
            {/* ============================================================ */}
            <section id="managers">
              <SectionDivider
                label="Managers"
                anchor="managers"
                route="/kiis/managers"
                icon={Users}
                description="Fund manager list with performance filters"
              />
              <PagePreviewCard title="Managers" path="/kiis/managers" tags={["Managers", "Filter"]}>
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <Input placeholder="Search managers..." />
                    </div>
                    <Button variant="secondary" size="md">
                      <Star className="w-4 h-4 mr-1" />
                      Top Rated
                    </Button>
                  </div>
                  <DataTable data={mockManagers} columns={managerColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 14: Manager Profile                                  */}
            {/* ============================================================ */}
            <section id="manager-profile">
              <SectionDivider
                label="Manager Profile"
                anchor="manager-profile"
                route="/kiis/managers/:name"
                icon={UserCircle}
                description="Manager info with managed fund details"
              />
              <PagePreviewCard title="Manager Profile" path="/kiis/managers/:name" tags={["Profile", "Funds"]}>
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-amic-100 flex items-center justify-center">
                      <UserCircle className="w-10 h-10 text-amic" />
                    </div>
                    <div>
                      <h2 className="text-2xl font-bold">Kim Jin-Hwan</h2>
                      <p className="text-text-secondary">AMIC Partners &middot; Managing Director</p>
                    </div>
                    <Badge variant="success">A+</Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <KpiCard title="Funds Managed" value="4" icon={PieChart} variant="default" hoverLift generous />
                    <KpiCard title="Total AUM" value="₩5.2T" icon={DollarSign} variant="default" hoverLift generous />
                    <KpiCard title="Avg. Return (3Y)" value="+12.8%" icon={TrendingUp} trend="up" trendValue="Top 10%" variant="positive" hoverLift generous />
                  </div>

                  <Card variant="forest-lift" hoverEffect>
                    <h3 className="text-lg font-semibold mb-3">Managed Funds</h3>
                    <div className="space-y-2">
                      {[
                        { name: "Korea Growth Fund I", aum: "₩2.5T", ret: "+14.2%" },
                        { name: "Korea Value Fund II", aum: "₩1.5T", ret: "+9.8%" },
                        { name: "Korea Small Cap Fund", aum: "₩800B", ret: "+18.3%" },
                        { name: "ESG Leaders Fund", aum: "₩400B", ret: "+11.1%" },
                      ].map((f) => (
                        <div key={f.name} className="flex items-center justify-between py-2 border-b border-gray-200 last:border-0">
                          <span className="font-medium">{f.name}</span>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="text-text-secondary font-mono">{f.aum}</span>
                            <span className="text-positive font-medium">{f.ret}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Card>
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 15: Entity Resolution                                */}
            {/* ============================================================ */}
            <section id="entity-resolution">
              <SectionDivider
                label="Entity Resolution"
                anchor="entity-resolution"
                route="/kiis/entities"
                icon={Link2}
                description="Entity matching with confidence scores"
              />
              <PagePreviewCard title="Entity Resolution" path="/kiis/entities" tags={["Matching", "NLP"]}>
                <div className="space-y-4">
                  <Card variant="accent-left">
                    <div className="flex items-center gap-3">
                      <Globe className="w-5 h-5 text-amic" />
                      <div>
                        <p className="font-semibold">Entity Resolution Engine</p>
                        <p className="text-sm text-text-secondary">Matching external entity names to canonical Korean corporate records</p>
                      </div>
                    </div>
                  </Card>
                  <DataTable data={mockEntities} columns={entityColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 16: Disclosures                                      */}
            {/* ============================================================ */}
            <section id="disclosures">
              <SectionDivider
                label="Disclosures"
                anchor="disclosures"
                route="/kiis/disclosures"
                icon={FileSearch}
                description="DART disclosure filings with date filters"
              />
              <PagePreviewCard title="Disclosures" path="/kiis/disclosures" tags={["Disclosure", "DART"]}>
                <div className="space-y-4">
                  <div className="flex gap-3 flex-wrap">
                    <Input placeholder="Search disclosures..." className="flex-1 min-w-[200px]" />
                    <Input type="date" defaultValue="2026-01-01" className="w-40" />
                    <Input type="date" defaultValue="2026-02-11" className="w-40" />
                    <Button variant="primary" size="md">
                      <Search className="w-4 h-4 mr-1" />
                      Filter
                    </Button>
                  </div>
                  <DataTable data={mockDisclosures} columns={disclosureColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>

            {/* ============================================================ */}
            {/* Section 17: Watchlist                                        */}
            {/* ============================================================ */}
            <section id="watchlist">
              <SectionDivider
                label="Watchlist"
                anchor="watchlist"
                route="/kiis/watchlist"
                icon={Eye}
                description="Personal watchlist with alert configuration"
              />
              <PagePreviewCard title="Watchlist" path="/kiis/watchlist" tags={["Watchlist", "Alerts"]}>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex gap-2">
                      <Button variant="accent" size="sm">All</Button>
                      <Button variant="secondary" size="sm">Stocks</Button>
                      <Button variant="secondary" size="sm">Funds</Button>
                      <Button variant="secondary" size="sm">REITs</Button>
                    </div>
                    <Button variant="primary" size="sm">
                      <Bell className="w-4 h-4 mr-1" />
                      Alert Settings
                    </Button>
                  </div>
                  <DataTable data={mockWatchlist} columns={watchlistColumns} keyField="id" uppercaseHeaders striped />
                </div>
              </PagePreviewCard>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
