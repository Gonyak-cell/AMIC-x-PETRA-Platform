import { useState } from "react";
import {
  HeroSection,
  SectionDivider,
  PagePreviewCard,
  GalleryNav,
} from "@/components/gallery";
import type { GallerySection } from "@/components/gallery";
import { Card, KpiCard, Badge, Button, DataTable, Input, Select } from "@/components/ui";
import type { Column } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  LayoutDashboard,
  LogIn,
  Users,
  Activity,
  User,
  Webhook,
  BarChart3,
  HelpCircle,
  Calendar,
  Download,
  Search,
  Plus,
  FileText,
  TrendingUp,
  AlertCircle,
  Save,
} from "lucide-react";

// Mock data for DataTables
const mockUsers = [
  {
    id: "1",
    name: "Sarah Kim",
    email: "sarah.kim@petrabridge.com",
    role: "Admin",
    status: "Active",
    lastLogin: "2026-02-11 09:45",
  },
  {
    id: "2",
    name: "Michael Chen",
    email: "michael.chen@petrabridge.com",
    role: "Analyst",
    status: "Active",
    lastLogin: "2026-02-11 08:30",
  },
  {
    id: "3",
    name: "Jessica Park",
    email: "jessica.park@petrabridge.com",
    role: "Manager",
    status: "Active",
    lastLogin: "2026-02-10 16:20",
  },
  {
    id: "4",
    name: "David Lee",
    email: "david.lee@petrabridge.com",
    role: "Analyst",
    status: "Inactive",
    lastLogin: "2026-02-08 14:15",
  },
  {
    id: "5",
    name: "Emily Choi",
    email: "emily.choi@petrabridge.com",
    role: "Viewer",
    status: "Active",
    lastLogin: "2026-02-11 10:00",
  },
];

const mockWebhooks = [
  {
    id: "1",
    url: "https://api.example.com/webhooks/deals",
    events: "deal.created, deal.updated",
    status: "Active",
    created: "2025-12-15",
  },
  {
    id: "2",
    url: "https://slack.com/webhooks/notifications",
    events: "notification.sent",
    status: "Active",
    created: "2026-01-08",
  },
  {
    id: "3",
    url: "https://api.internal.com/sync/documents",
    events: "document.generated",
    status: "Inactive",
    created: "2025-11-22",
  },
  {
    id: "4",
    url: "https://analytics.petrabridge.com/events",
    events: "*.all",
    status: "Active",
    created: "2026-01-20",
  },
];

const mockExports = [
  {
    id: "1",
    fileName: "Q4_2025_FDD_Analysis.xlsx",
    module: "FDD",
    format: "Excel",
    size: "2.4 MB",
    date: "2026-02-10 14:30",
    status: "Completed",
  },
  {
    id: "2",
    fileName: "Portfolio_Holdings_Jan2026.csv",
    module: "KIIS",
    format: "CSV",
    size: "856 KB",
    date: "2026-02-09 11:15",
    status: "Completed",
  },
  {
    id: "3",
    fileName: "IM_Documents_Batch_008.zip",
    module: "IM",
    format: "ZIP",
    size: "12.8 MB",
    date: "2026-02-08 16:45",
    status: "Completed",
  },
  {
    id: "4",
    fileName: "Activity_Log_Feb2026.pdf",
    module: "Portal",
    format: "PDF",
    size: "1.2 MB",
    date: "2026-02-11 09:00",
    status: "Processing",
  },
  {
    id: "5",
    fileName: "All_Modules_Backup.zip",
    module: "All",
    format: "ZIP",
    size: "48.5 MB",
    date: "2026-02-07 22:30",
    status: "Completed",
  },
];

const mockActivityLog = [
  {
    id: "1",
    user: "SK",
    action: "Created new deal analysis for TechCorp Inc.",
    timestamp: "2 minutes ago",
    color: "bg-amic",
  },
  {
    id: "2",
    user: "MC",
    action: "Updated portfolio holdings - added 3 new entities",
    timestamp: "15 minutes ago",
    color: "bg-amic-400",
  },
  {
    id: "3",
    user: "JP",
    action: "Generated IM document for Project Alpha",
    timestamp: "1 hour ago",
    color: "bg-accent",
  },
  {
    id: "4",
    user: "EС",
    action: "Exported Q4 2025 FDD analysis report",
    timestamp: "2 hours ago",
    color: "bg-amic-300",
  },
  {
    id: "5",
    user: "DL",
    action: "Added 2 companies to watchlist",
    timestamp: "3 hours ago",
    color: "bg-amic-500",
  },
];

const mockGlossaryItems = [
  {
    term: "Financial Due Diligence (FDD)",
    definition:
      "Comprehensive review of a company's financial statements, operations, and market position to assess investment viability.",
  },
  {
    term: "Korea Information Investment System (KIIS)",
    definition:
      "Portfolio monitoring and company information management system for Korean equity investments.",
  },
  {
    term: "Information Memorandum (IM)",
    definition:
      "Detailed document describing investment opportunity, including company background, financials, and deal structure.",
  },
  {
    term: "Watchlist",
    definition:
      "Collection of companies or deals monitored for potential investment opportunities or risk alerts.",
  },
];

const sections: GallerySection[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "login", label: "Login", icon: LogIn },
  { id: "users", label: "User Management", icon: Users },
  { id: "activity", label: "Activity Log", icon: Activity },
  { id: "profile", label: "Profile", icon: User },
  { id: "webhooks", label: "Webhooks", icon: Webhook },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "help", label: "Help Center", icon: HelpCircle },
  { id: "calendar", label: "Calendar", icon: Calendar },
  { id: "exports", label: "Exports", icon: Download },
];

export default function PortalSamplePage() {
  const [activeSection, setActiveSection] = useState("dashboard");

  // Column definitions for DataTables
  const userColumns: Column<(typeof mockUsers)[0]>[] = [
    {
      key: "name",
      header: "Name",
      render: (user) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-amic-100 flex items-center justify-center text-sm font-medium text-amic">
            {user.name
              .split(" ")
              .map((n) => n[0])
              .join("")}
          </div>
          <span className="font-medium">{user.name}</span>
        </div>
      ),
    },
    { key: "email", header: "Email" },
    {
      key: "role",
      header: "Role",
      render: (user) => (
        <Badge
          variant={
            user.role === "Admin"
              ? "error"
              : user.role === "Manager"
                ? "warning"
                : "info"
          }
        >
          {user.role}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (user) => (
        <Badge variant={user.status === "Active" ? "success" : "neutral"}>
          {user.status}
        </Badge>
      ),
    },
    { key: "lastLogin", header: "Last Login" },
  ];

  const webhookColumns: Column<(typeof mockWebhooks)[0]>[] = [
    {
      key: "url",
      header: "URL",
      render: (webhook) => (
        <span className="text-sm font-mono text-text-secondary">{webhook.url}</span>
      ),
    },
    {
      key: "events",
      header: "Events",
      render: (webhook) => (
        <span className="text-sm text-text-tertiary">{webhook.events}</span>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (webhook) => (
        <Badge variant={webhook.status === "Active" ? "success" : "neutral"}>
          {webhook.status}
        </Badge>
      ),
    },
    { key: "created", header: "Created" },
  ];

  const exportColumns: Column<(typeof mockExports)[0]>[] = [
    {
      key: "fileName",
      header: "File Name",
      render: (exp) => (
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-text-tertiary" />
          <span className="font-medium">{exp.fileName}</span>
        </div>
      ),
    },
    {
      key: "module",
      header: "Module",
      render: (exp) => (
        <Badge
          variant={
            exp.module === "FDD"
              ? "info"
              : exp.module === "KIIS"
                ? "success"
                : exp.module === "IM"
                  ? "warning"
                  : "neutral"
          }
        >
          {exp.module}
        </Badge>
      ),
    },
    { key: "format", header: "Format" },
    { key: "size", header: "Size" },
    { key: "date", header: "Date" },
    {
      key: "status",
      header: "Status",
      render: (exp) => (
        <Badge variant={exp.status === "Completed" ? "success" : "warning"}>
          {exp.status}
        </Badge>
      ),
    },
  ];

  return (
    <div className="bg-bg-cool min-h-screen">
      <HeroSection
        title="Portal Pages Gallery"
        subtitle="Comprehensive showcase of all 10 portal-level pages with corporate design system and interactive components"
        backgroundUrl="https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1920&h=600&fit=crop"
      />

      <div className="max-w-screen-2xl mx-auto px-6 py-12 flex gap-8">
        <GalleryNav
          sections={sections}
          activeSection={activeSection}
          onSectionChange={setActiveSection}
        />

        <div className="flex-1 space-y-16">
          {/* 1. Dashboard */}
          <section id="dashboard">
            <SectionDivider
              icon={LayoutDashboard}
              label="Dashboard"
              description="Unified overview with KPIs and quick actions"
              route="/"
            />
            <PagePreviewCard>
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <KpiCard
                    label="Active Deals"
                    value="12"
                    trend="up" trendValue="+3"
                    variant="positive"
                    hoverLift generous
                  />
                  <KpiCard
                    label="Watchlist Alerts"
                    value="5"
                    trend="up" trendValue="+2"
                    variant="caution"
                    hoverLift generous
                  />
                  <KpiCard
                    label="IM In Progress"
                    value="3"
                    variant="default"
                    hoverLift generous
                  />
                  <KpiCard
                    label="Draft Deals"
                    value="8"
                    trend="down" trendValue="-1"
                    variant="negative"
                    hoverLift generous
                  />
                </div>

                <div>
                  <h3 className="label-uppercase mb-4">Quick Actions</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <Card variant="forest-lift" className="p-4 cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-amic-100 flex items-center justify-center">
                          <Plus className="w-5 h-5 text-amic" />
                        </div>
                        <div>
                          <div className="font-medium">New Analysis</div>
                          <div className="text-xs text-text-tertiary">Start FDD</div>
                        </div>
                      </div>
                    </Card>
                    <Card variant="forest-lift" className="p-4 cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-amic-50 flex items-center justify-center">
                          <FileText className="w-5 h-5 text-accent" />
                        </div>
                        <div>
                          <div className="font-medium">Generate IM</div>
                          <div className="text-xs text-text-tertiary">Create document</div>
                        </div>
                      </div>
                    </Card>
                    <Card variant="forest-lift" className="p-4 cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-amic-200 flex items-center justify-center">
                          <TrendingUp className="w-5 h-5 text-amic-400" />
                        </div>
                        <div>
                          <div className="font-medium">View Portfolio</div>
                          <div className="text-xs text-text-tertiary">KIIS overview</div>
                        </div>
                      </div>
                    </Card>
                    <Card variant="forest-lift" className="p-4 cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
                          <Search className="w-5 h-5 text-accent" />
                        </div>
                        <div>
                          <div className="font-medium">Global Search</div>
                          <div className="text-xs text-text-tertiary">Find anything</div>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 2. Login */}
          <section id="login">
            <SectionDivider
              icon={LogIn}
              label="Login"
              description="Authentication page with modern two-panel layout"
              route="/login"
            />
            <PagePreviewCard>
              <div className="grid md:grid-cols-2 gap-0 -m-6 rounded-xl overflow-hidden">
                <div className="bg-gradient-to-br from-amic to-amic-800 p-12 flex items-center justify-center min-h-[400px]">
                  <div className="text-white text-center">
                    <div className="text-4xl font-bold mb-4">
                      AMIC × PETRA
                    </div>
                    <div className="text-white/70 text-lg">
                      Investment Platform
                    </div>
                  </div>
                </div>
                <div className="p-12 flex items-center justify-center bg-white dark:bg-bg-primary">
                  <div className="w-full max-w-sm space-y-6">
                    <div>
                      <h2 className="text-2xl font-bold text-text-primary mb-2">
                        Welcome Back
                      </h2>
                      <p className="text-text-secondary">
                        Sign in to your account to continue
                      </p>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <label className="label-uppercase mb-2 block">
                          Email
                        </label>
                        <Input
                          type="email"
                          placeholder="you@petrabridge.com"
                        />
                      </div>
                      <div>
                        <label className="label-uppercase mb-2 block">
                          Password
                        </label>
                        <Input type="password" placeholder="********" />
                      </div>
                      <Button variant="primary" className="w-full">
                        Sign In
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 3. User Management */}
          <section id="users">
            <SectionDivider
              icon={Users}
              label="User Management"
              description="Admin interface for managing platform users"
              route="/admin/users"
            />
            <PagePreviewCard>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="label-uppercase">All Users</h3>
                  <Button variant="primary" size="sm">
                    <Plus className="w-4 h-4 mr-2" />
                    Add User
                  </Button>
                </div>
                <DataTable
                  data={mockUsers}
                  columns={userColumns}
                  keyField="id"
                  uppercaseHeaders
                />
              </div>
            </PagePreviewCard>
          </section>

          {/* 4. Activity Log */}
          <section id="activity">
            <SectionDivider
              icon={Activity}
              label="Activity Log"
              description="Timeline of all platform actions and events"
              route="/admin/activity"
            />
            <PagePreviewCard>
              <div className="space-y-4">
                <h3 className="label-uppercase">Recent Activity</h3>
                <div className="relative">
                  {/* Timeline vertical line */}
                  <div className="absolute left-4 top-0 bottom-0 w-px bg-border-primary" />

                  <div className="space-y-6">
                    {mockActivityLog.map((activity) => (
                      <div key={activity.id} className="relative pl-12">
                        {/* Timeline dot */}
                        <div
                          className={cn(
                            "absolute left-0 w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold",
                            activity.color
                          )}
                        >
                          {activity.user}
                        </div>
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-text-primary font-medium">
                              {activity.action}
                            </p>
                            <p className="text-sm text-text-tertiary mt-1">
                              {activity.timestamp}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 5. Profile */}
          <section id="profile">
            <SectionDivider
              icon={User}
              label="Profile"
              description="User profile and account settings"
              route="/settings/profile"
            />
            <PagePreviewCard>
              <div className="max-w-2xl space-y-6">
                <div className="flex items-center gap-6">
                  <div className="w-20 h-20 rounded-full bg-gradient-to-br from-amic to-amic-700 flex items-center justify-center text-white text-2xl font-bold">
                    SK
                  </div>
                  <div>
                    <h3 className="text-xl font-bold text-text-primary">
                      Sarah Kim
                    </h3>
                    <Badge variant="error">Admin</Badge>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="label-uppercase mb-2 block">
                      Display Name
                    </label>
                    <Input defaultValue="Sarah Kim" />
                  </div>
                  <div>
                    <label className="label-uppercase mb-2 block">
                      Email Address
                    </label>
                    <Input
                      type="email"
                      defaultValue="sarah.kim@petrabridge.com"
                    />
                  </div>
                  <div>
                    <label className="label-uppercase mb-2 block">
                      Current Role
                    </label>
                    <div className="flex items-center gap-2 p-3 bg-bg-secondary rounded-lg">
                      <Badge variant="error">Admin</Badge>
                      <span className="text-sm text-text-secondary">
                        Full platform access
                      </span>
                    </div>
                  </div>
                  <div className="flex gap-3 pt-4">
                    <Button variant="primary">
                      <Save className="w-4 h-4 mr-2" />
                      Save Changes
                    </Button>
                    <Button variant="secondary">Cancel</Button>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 6. Webhooks */}
          <section id="webhooks">
            <SectionDivider
              icon={Webhook}
              label="Webhooks"
              description="Manage external integrations and webhooks"
              route="/settings/webhooks"
            />
            <PagePreviewCard>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="label-uppercase">Configured Webhooks</h3>
                  <Button variant="primary" size="sm">
                    <Plus className="w-4 h-4 mr-2" />
                    Add Webhook
                  </Button>
                </div>
                <DataTable
                  data={mockWebhooks}
                  columns={webhookColumns}
                  keyField="id"
                  uppercaseHeaders
                />
              </div>
            </PagePreviewCard>
          </section>

          {/* 7. Analytics */}
          <section id="analytics">
            <SectionDivider
              icon={BarChart3}
              label="Analytics"
              description="Cross-module KPIs and performance metrics"
              route="/analytics"
            />
            <PagePreviewCard>
              <div className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <KpiCard
                    label="Total Analyses"
                    value="156"
                    trend="up" trendValue="+12"
                    variant="positive"
                    hoverLift generous
                  />
                  <KpiCard
                    label="Success Rate"
                    value="94.2%"
                    trend="up" trendValue="+2.3%"
                    variant="positive"
                    hoverLift generous
                  />
                  <KpiCard
                    label="Avg Processing Time"
                    value="2.3h"
                    trend="down" trendValue="-0.5h"
                    variant="positive"
                    hoverLift generous
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  <Card variant="forest-lift">
                    <div className="p-6">
                      <h4 className="label-uppercase mb-4">
                        Analyses by Module
                      </h4>
                      <div className="h-64 bg-bg-secondary rounded-lg flex items-center justify-center text-text-tertiary">
                        <div className="text-center">
                          <BarChart3 className="w-12 h-12 mx-auto mb-2 opacity-50" />
                          <p>Chart Placeholder</p>
                        </div>
                      </div>
                    </div>
                  </Card>
                  <Card variant="forest-lift">
                    <div className="p-6">
                      <h4 className="label-uppercase mb-4">
                        Performance Trends
                      </h4>
                      <div className="h-64 bg-bg-secondary rounded-lg flex items-center justify-center text-text-tertiary">
                        <div className="text-center">
                          <TrendingUp className="w-12 h-12 mx-auto mb-2 opacity-50" />
                          <p>Chart Placeholder</p>
                        </div>
                      </div>
                    </div>
                  </Card>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 8. Help Center */}
          <section id="help">
            <SectionDivider
              icon={HelpCircle}
              label="Help Center"
              description="Documentation, glossary, and keyboard shortcuts"
              route="/help"
            />
            <PagePreviewCard>
              <div className="space-y-6">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-tertiary" />
                  <Input
                    placeholder="Search help articles, glossary terms..."
                    className="pl-10"
                  />
                </div>

                <div className="flex gap-2">
                  <Button variant="primary" size="sm">
                    Glossary
                  </Button>
                  <Button variant="secondary" size="sm">
                    Shortcuts
                  </Button>
                  <Button variant="secondary" size="sm">
                    Release Notes
                  </Button>
                </div>

                <div className="space-y-4">
                  <h3 className="label-uppercase">Glossary</h3>
                  <div className="space-y-3">
                    {mockGlossaryItems.map((item) => (
                      <Card key={item.term} variant="forest-lift">
                        <div className="p-4">
                          <h4 className="font-semibold text-text-primary mb-2">
                            {item.term}
                          </h4>
                          <p className="text-sm text-text-secondary">
                            {item.definition}
                          </p>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 9. Calendar */}
          <section id="calendar">
            <SectionDivider
              icon={Calendar}
              label="Calendar"
              description="Timeline view of deals, milestones, and events"
              route="/calendar"
            />
            <PagePreviewCard>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-text-primary">
                    February 2026
                  </h3>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm">
                      Today
                    </Button>
                    <Select value="month" options={[{ value: "month", label: "Month" }, { value: "week", label: "Week" }, { value: "day", label: "Day" }]} />
                  </div>
                </div>

                {/* Calendar grid */}
                <div className="border border-border-primary rounded-lg overflow-hidden">
                  {/* Day headers */}
                  <div className="grid grid-cols-7 bg-bg-secondary">
                    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(
                      (day) => (
                        <div
                          key={day}
                          className="p-3 text-center text-sm font-medium text-text-secondary border-r border-border-primary last:border-r-0"
                        >
                          {day}
                        </div>
                      )
                    )}
                  </div>

                  {/* Calendar days (5 weeks) */}
                  <div className="grid grid-cols-7">
                    {Array.from({ length: 35 }).map((_, i) => {
                      const dayNum = i - 1; // Start from day 0 for offset
                      const day = dayNum > 0 && dayNum <= 28 ? dayNum : null;
                      const hasEvent =
                        day && [5, 12, 18, 25].includes(day);
                      const hasMultipleEvents = day === 12;

                      return (
                        <div
                          key={i}
                          className={cn(
                            "min-h-[80px] p-2 border-r border-b border-border-primary last:border-r-0",
                            !day && "bg-bg-secondary/50"
                          )}
                        >
                          {day && (
                            <>
                              <div className="text-sm font-medium text-text-primary mb-1">
                                {day}
                              </div>
                              {hasEvent && (
                                <div className="space-y-1">
                                  <div className="w-2 h-2 rounded-full bg-amic" />
                                  {hasMultipleEvents && (
                                    <div className="w-2 h-2 rounded-full bg-accent" />
                                  )}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amic" />
                    <span className="text-text-secondary">FDD Deadline</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-accent" />
                    <span className="text-text-secondary">IM Due Date</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-amic-300" />
                    <span className="text-text-secondary">Meeting</span>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* 10. Exports */}
          <section id="exports">
            <SectionDivider
              icon={Download}
              label="Exports"
              description="Unified export history and batch download management"
              route="/exports"
            />
            <PagePreviewCard>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="label-uppercase">Export History</h3>
                  <div className="flex gap-2">
                    <Button variant="secondary" size="sm">
                      <Download className="w-4 h-4 mr-2" />
                      Batch Export
                    </Button>
                    <Button variant="primary" size="sm">
                      <Plus className="w-4 h-4 mr-2" />
                      New Export
                    </Button>
                  </div>
                </div>
                <DataTable
                  data={mockExports}
                  columns={exportColumns}
                  keyField="id"
                  uppercaseHeaders
                />

                <div className="flex items-center justify-between pt-4 border-t border-border-primary">
                  <div className="flex items-center gap-2 text-sm text-text-secondary">
                    <AlertCircle className="w-4 h-4" />
                    <span>
                      Exports are retained for 30 days before auto-deletion
                    </span>
                  </div>
                  <div className="text-sm text-text-tertiary">
                    Total storage: 65.7 MB
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>
        </div>
      </div>
    </div>
  );
}
