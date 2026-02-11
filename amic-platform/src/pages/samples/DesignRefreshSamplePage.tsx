/**
 * Design Refresh Sample Page
 * dealroom.net-inspired UI 리프레시 프리뷰 — before/after 비교
 * Route: /samples/design-refresh
 */

import { useState } from "react";
import {
  SectionDivider,
  PagePreviewCard,
  GalleryNav,
} from "@/components/gallery";
import type { GallerySection } from "@/components/gallery";
import { Card, Button, Input } from "@/components/ui";
import {
  Briefcase,
  Bell,
  FileText,
  AlertTriangle,
  Plus,
  Search,
  Star,
  ArrowRight,
  TrendingUp,
  Palette,
  Layers,
  Type,
  MousePointerClick,
  LayoutDashboard,
  LogIn,
  Sparkles,
  Square,
  RectangleHorizontal,
} from "lucide-react";

/* ── Gallery Sections ── */
const sections: GallerySection[] = [
  { id: "hero", label: "Dark Hero", icon: Sparkles },
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "cards", label: "Cards", icon: Layers },
  { id: "buttons", label: "Buttons", icon: MousePointerClick },
  { id: "typography", label: "Typography", icon: Type },
  { id: "glass", label: "Glass UI", icon: Square },
  { id: "shadows", label: "Shadows", icon: RectangleHorizontal },
  { id: "login", label: "Login", icon: LogIn },
];

export default function DesignRefreshSamplePage() {
  const [activeSection, setActiveSection] = useState("hero");

  return (
    <div className="bg-bg-cool min-h-screen">
      {/* Custom Dark Hero (dealroom.net style) — not using HeroSection component */}
      <div className="hero-gradient-radial -mx-4 md:-mx-6 -mt-4 md:-mt-6 px-4 md:px-6 pt-16 pb-20 mb-12">
        <div className="max-w-screen-2xl mx-auto">
          <div className="stagger">
            <p className="label-uppercase text-accent/80 mb-4 tracking-[0.2em]">
              Design System Preview
            </p>
            <h1 className="text-hero-title font-heading text-white max-w-3xl">
              dealroom.net-Inspired
              <br />
              <span className="text-accent">UI Refresh</span>
            </h1>
            <p className="text-hero-subtitle text-white/60 mt-6 max-w-2xl">
              AMIC x PETRA Platform의 시각적 품질을 끌어올리는 디자인 리프레시
              프리뷰입니다. 다크 Hero, Glass UI, 깊이감 있는 쉐도우, 세련된 호버
              효과를 확인하세요.
            </p>
            <div className="flex gap-3 mt-8">
              <Button variant="accent" size="lg">
                <Palette className="w-4 h-4 mr-2" />
                View Components
              </Button>
              <Button
                variant="secondary"
                size="lg"
                className="border-white/20 text-white hover:bg-white/10 hover:border-white/30"
              >
                Full Plan
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-screen-2xl mx-auto px-6 pb-12 flex gap-8">
        <GalleryNav
          sections={sections}
          activeSection={activeSection}
          onSectionChange={setActiveSection}
        />

        <div className="flex-1 space-y-16">
          {/* ── 1. Dark Hero Section ── */}
          <section id="hero">
            <SectionDivider
              icon={Sparkles}
              label="Dark Hero Section"
              description="dealroom.net 스타일의 다크 그라디언트 Hero — 페이지 상단 앵커"
            />
            <PagePreviewCard>
              <div className="space-y-6">
                {/* Compact Hero variant */}
                <div className="hero-gradient-radial rounded-dr-lg p-8 md:p-12">
                  <div className="stagger">
                    <p className="label-uppercase text-accent/70 mb-2">
                      Compact Hero
                    </p>
                    <h2 className="text-2xl md:text-3xl font-heading font-bold text-white">
                      Cross-Module Analytics
                    </h2>
                    <p className="text-sm text-white/50 mt-2">
                      FDD, KIIS, IM 모듈의 통합 성과를 한눈에 확인
                    </p>
                  </div>

                  {/* Glass KPI Cards */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-8 stagger">
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Briefcase className="h-4 w-4 text-white/50" />
                        <span className="text-xs text-white/50">
                          Active Deals
                        </span>
                      </div>
                      <div className="font-mono text-2xl font-semibold text-white tabular-nums">
                        12
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        <TrendingUp className="h-3 w-3 text-accent" />
                        <span className="text-xs text-accent">+3</span>
                      </div>
                    </div>
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Bell className="h-4 w-4 text-white/50" />
                        <span className="text-xs text-white/50">Alerts</span>
                      </div>
                      <div className="font-mono text-2xl font-semibold text-white tabular-nums">
                        5
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        <TrendingUp className="h-3 w-3 text-caution" />
                        <span className="text-xs text-caution">+2</span>
                      </div>
                    </div>
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-white/50" />
                        <span className="text-xs text-white/50">IM Docs</span>
                      </div>
                      <div className="font-mono text-2xl font-semibold text-white tabular-nums">
                        3
                      </div>
                    </div>
                    <div className="glass-card p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4 text-white/50" />
                        <span className="text-xs text-white/50">Drafts</span>
                      </div>
                      <div className="font-mono text-2xl font-semibold text-white tabular-nums">
                        8
                      </div>
                    </div>
                  </div>
                </div>

                {/* Hero with radial glow */}
                <div className="hero-gradient rounded-dr-lg p-8 md:p-12 relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-accent/5 rounded-full blur-3xl" />
                  <div className="relative">
                    <h2 className="text-hero-title font-heading text-white">
                      Scale Your M&A
                      <br />
                      <span className="text-accent">With Precision</span>
                    </h2>
                    <p className="text-hero-subtitle text-white/60 mt-4 max-w-lg">
                      End-to-end due diligence, investment intelligence, and
                      document generation in one unified platform.
                    </p>
                    <div className="flex gap-3 mt-8">
                      <Button variant="accent" size="lg">
                        Get Started
                      </Button>
                      <Button
                        variant="ghost"
                        size="lg"
                        className="text-white/70 hover:text-white hover:bg-white/10"
                      >
                        Learn More
                        <ArrowRight className="w-4 h-4 ml-2" />
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 2. Dashboard Preview ── */}
          <section id="dashboard">
            <SectionDivider
              icon={LayoutDashboard}
              label="Dashboard (Refreshed)"
              description="다크 Hero + Glass KPI 카드가 적용된 새 대시보드 프리뷰"
              route="/"
            />
            <PagePreviewCard>
              <div className="space-y-6">
                {/* Dashboard Hero */}
                <div className="hero-gradient-radial rounded-dr-lg p-6 md:p-10">
                  <div className="mb-8">
                    <h2 className="text-2xl md:text-3xl font-heading font-bold text-white">
                      Welcome, Sarah Kim
                    </h2>
                    <p className="text-sm text-white/50 mt-1">
                      2026년 2월 11일 화요일
                    </p>
                  </div>

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 stagger">
                    <div className="glass-card p-4 hover-glow cursor-pointer">
                      <div className="flex items-center gap-2 mb-2">
                        <Briefcase className="h-4 w-4 text-accent" />
                        <span className="text-xs text-white/60">
                          Active FDD Deals
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-white tabular-nums">
                        12
                      </div>
                      <div className="flex items-center gap-1 mt-2">
                        <TrendingUp className="h-3 w-3 text-accent" />
                        <span className="text-xs text-accent font-medium">
                          +3
                        </span>
                      </div>
                    </div>
                    <div className="glass-card p-4 hover-glow cursor-pointer">
                      <div className="flex items-center gap-2 mb-2">
                        <Bell className="h-4 w-4 text-caution" />
                        <span className="text-xs text-white/60">
                          Watchlist Alerts
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-white tabular-nums">
                        5
                      </div>
                      <div className="flex items-center gap-1 mt-2">
                        <TrendingUp className="h-3 w-3 text-caution" />
                        <span className="text-xs text-caution font-medium">
                          +2
                        </span>
                      </div>
                    </div>
                    <div className="glass-card p-4 hover-glow cursor-pointer">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-white/50" />
                        <span className="text-xs text-white/60">
                          IM In Progress
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-white tabular-nums">
                        3
                      </div>
                    </div>
                    <div className="glass-card p-4 hover-glow cursor-pointer">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4 text-negative" />
                        <span className="text-xs text-white/60">
                          Draft Deals
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-white tabular-nums">
                        8
                      </div>
                    </div>
                  </div>
                </div>

                {/* Quick Actions (upgraded) */}
                <div>
                  <h3 className="label-uppercase mb-3">Quick Actions</h3>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                      {
                        label: "New Deal",
                        desc: "Start a new FDD deal",
                        icon: Plus,
                        bg: "bg-amic-100",
                        iconColor: "text-amic",
                      },
                      {
                        label: "New IM",
                        desc: "Generate Investment Memo",
                        icon: FileText,
                        bg: "bg-accent-light",
                        iconColor: "text-accent",
                      },
                      {
                        label: "Search Company",
                        desc: "Look up information",
                        icon: Search,
                        bg: "bg-amic-200",
                        iconColor: "text-amic-400",
                      },
                      {
                        label: "Watchlist",
                        desc: "View alerts",
                        icon: Star,
                        bg: "bg-accent/10",
                        iconColor: "text-accent",
                      },
                    ].map((action) => (
                      <div
                        key={action.label}
                        className="bg-white rounded-dr border border-gray-border shadow-dr-sm hover-glow-green cursor-pointer p-4 group"
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className={`w-10 h-10 rounded-lg ${action.bg} flex items-center justify-center`}
                          >
                            <action.icon
                              className={`w-5 h-5 ${action.iconColor}`}
                            />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-text-dark group-hover:text-amic transition-colors flex items-center gap-1">
                              {action.label}
                              <ArrowRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>
                            <p className="text-xs text-text-secondary mt-0.5">
                              {action.desc}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Module Status (slim) */}
                <div className="flex items-center gap-6 bg-white rounded-dr border border-gray-border shadow-dr-sm px-5 py-3">
                  <span className="label-uppercase text-text-muted text-[10px]">
                    Module Status
                  </span>
                  {["Auto FDD", "KIIS", "IM Generator"].map((mod) => (
                    <div key={mod} className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-positive" />
                      <span className="text-sm text-text-dark">{mod}</span>
                      <span className="text-xs text-text-muted">Connected</span>
                    </div>
                  ))}
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 3. Card Variants ── */}
          <section id="cards">
            <SectionDivider
              icon={Layers}
              label="Card Variants"
              description="기존 vs 업그레이드된 카드 비교 — rounded-dr, shadow-dr-*, hover-glow"
            />
            <PagePreviewCard>
              <div className="space-y-8">
                {/* Before: existing cards */}
                <div>
                  <h3 className="label-uppercase mb-3 text-text-muted">
                    Before (Current)
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <Card variant="default">
                      <p className="text-sm text-text-secondary">
                        Default card — rounded-corporate (6px), shadow-card
                      </p>
                    </Card>
                    <Card variant="forest-lift">
                      <p className="text-sm text-text-secondary">
                        Forest-lift — hover-lift, shadow-forest-card
                      </p>
                    </Card>
                    <Card variant="elevated">
                      <p className="text-sm text-text-secondary">
                        Elevated — shadow-elevated
                      </p>
                    </Card>
                  </div>
                </div>

                {/* After: upgraded cards */}
                <div>
                  <h3 className="label-uppercase mb-3 text-accent">
                    After (Refreshed)
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-white rounded-dr border border-gray-border shadow-dr-sm p-5">
                      <p className="text-sm text-text-secondary">
                        Default — rounded-dr (12px), shadow-dr-sm
                      </p>
                    </div>
                    <div className="bg-white rounded-dr border border-gray-border shadow-dr-sm hover-glow cursor-pointer p-5">
                      <p className="text-sm text-text-secondary">
                        Hover Glow — hover-glow effect with shadow-dr-lg
                      </p>
                    </div>
                    <div className="bg-white rounded-dr border border-gray-border shadow-dr-md p-5">
                      <p className="text-sm text-text-secondary">
                        Elevated — shadow-dr-md (deeper teal tint)
                      </p>
                    </div>
                  </div>
                </div>

                {/* KPI Card comparison */}
                <div>
                  <h3 className="label-uppercase mb-3 text-accent">
                    KPI Cards (Refreshed)
                  </h3>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-white rounded-dr border border-positive/30 bg-bg-light-green/30 shadow-dr-sm hover-glow cursor-pointer p-5 transition-all duration-300">
                      <div className="flex items-center gap-2 mb-2">
                        <Briefcase className="h-4 w-4 text-text-secondary" />
                        <span className="text-kpi-label text-text-secondary">
                          Active Deals
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-text-dark tabular-nums">
                        12
                      </div>
                    </div>
                    <div className="bg-white rounded-dr border border-gray-border shadow-dr-sm hover-glow cursor-pointer p-5 transition-all duration-300">
                      <div className="flex items-center gap-2 mb-2">
                        <Bell className="h-4 w-4 text-text-secondary" />
                        <span className="text-kpi-label text-text-secondary">
                          Alerts
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-text-dark tabular-nums">
                        5
                      </div>
                    </div>
                    <div className="bg-white rounded-dr border border-caution/30 bg-amber-50/30 shadow-dr-sm hover-glow cursor-pointer p-5 transition-all duration-300">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4 text-text-secondary" />
                        <span className="text-kpi-label text-text-secondary">
                          IM In Progress
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-text-dark tabular-nums">
                        3
                      </div>
                    </div>
                    <div className="bg-white rounded-dr border border-negative/30 bg-red-50/30 shadow-dr-sm hover-glow cursor-pointer p-5 transition-all duration-300">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="h-4 w-4 text-text-secondary" />
                        <span className="text-kpi-label text-text-secondary">
                          Draft Deals
                        </span>
                      </div>
                      <div className="font-mono text-kpi-value text-text-dark tabular-nums">
                        8
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 4. Button Variants ── */}
          <section id="buttons">
            <SectionDivider
              icon={MousePointerClick}
              label="Button Variants"
              description="rounded-dr-sm, glow 호버, active:scale 클릭 피드백"
            />
            <PagePreviewCard>
              <div className="space-y-8">
                {/* Before */}
                <div>
                  <h3 className="label-uppercase mb-4 text-text-muted">
                    Before (Current)
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    <Button variant="primary">Primary</Button>
                    <Button variant="secondary">Secondary</Button>
                    <Button variant="accent">Accent</Button>
                    <Button variant="ghost">Ghost</Button>
                    <Button variant="danger">Danger</Button>
                  </div>
                </div>

                {/* After */}
                <div>
                  <h3 className="label-uppercase mb-4 text-accent">
                    After (Refreshed)
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-amic text-white hover:bg-amic-700 focus:ring-amic-600 shadow-dr-sm hover:shadow-dr-md active:scale-[0.98] px-4 py-2 text-sm">
                      Primary
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-white text-amic border border-amic/20 hover:border-amic/40 hover:bg-amic-50 focus:ring-amic-600 active:scale-[0.98] px-4 py-2 text-sm">
                      Secondary
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-accent text-white hover:bg-accent-hover focus:ring-accent shadow-dr-sm hover:shadow-glow-green active:scale-[0.98] px-4 py-2 text-sm">
                      Accent (Glow)
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 focus:outline-none bg-transparent text-text-secondary hover:bg-bg-cool hover:text-text-body active:scale-[0.98] px-4 py-2 text-sm">
                      Ghost
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 bg-negative text-white hover:bg-red-700 focus:ring-negative shadow-dr-sm hover:shadow-dr-md active:scale-[0.98] px-4 py-2 text-sm">
                      Danger
                    </button>
                  </div>
                </div>

                {/* Large buttons */}
                <div>
                  <h3 className="label-uppercase mb-4 text-accent">
                    Large Size (Refreshed)
                  </h3>
                  <div className="flex flex-wrap gap-3">
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 bg-amic text-white hover:bg-amic-700 shadow-dr-sm hover:shadow-dr-md active:scale-[0.98] px-6 py-3 text-base">
                      <Plus className="w-4 h-4" />
                      New Deal
                    </button>
                    <button className="inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 bg-accent text-white hover:bg-accent-hover shadow-dr-sm hover:shadow-glow-green active:scale-[0.98] px-6 py-3 text-base">
                      <FileText className="w-4 h-4" />
                      Generate IM
                    </button>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 5. Typography ── */}
          <section id="typography">
            <SectionDivider
              icon={Type}
              label="Typography Scale"
              description="hero-title, page-title, 기존 사이즈 비교"
            />
            <PagePreviewCard>
              <div className="space-y-8">
                <div className="space-y-4">
                  <div>
                    <span className="text-xs text-text-muted font-mono">
                      hero-title (2.5rem / 800 / -0.03em)
                    </span>
                    <h2 className="text-hero-title font-heading text-text-dark">
                      Scale Your M&A Process
                    </h2>
                  </div>
                  <div className="section-divider-line" />
                  <div>
                    <span className="text-xs text-text-muted font-mono">
                      page-title (1.75rem / 700 / -0.02em) — upgraded from 1.5rem
                    </span>
                    <h2 className="text-page-title font-heading text-text-dark">
                      Cross-Module Analytics
                    </h2>
                  </div>
                  <div className="section-divider-line" />
                  <div>
                    <span className="text-xs text-text-muted font-mono">
                      hero-subtitle (1.125rem / 400)
                    </span>
                    <p className="text-hero-subtitle text-text-secondary">
                      Comprehensive financial due diligence and investment
                      intelligence platform for M&A advisory.
                    </p>
                  </div>
                  <div className="section-divider-line" />
                  <div>
                    <span className="text-xs text-text-muted font-mono">
                      kpi-value (1.6875rem / 600) — IBM Plex Mono
                    </span>
                    <p className="font-mono text-kpi-value text-text-dark tabular-nums">
                      ₩ 1,234,567,890
                    </p>
                  </div>
                </div>

                {/* Dark background typography */}
                <div className="hero-gradient-radial rounded-dr-lg p-8">
                  <div className="space-y-4">
                    <div>
                      <span className="text-xs text-white/30 font-mono">
                        On dark background
                      </span>
                      <h2 className="text-hero-title font-heading text-white">
                        White on Dark
                      </h2>
                      <p className="text-hero-subtitle text-white/60 mt-2">
                        Subtitle text at 60% opacity for comfortable reading on
                        dark backgrounds.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 6. Glass UI ── */}
          <section id="glass">
            <SectionDivider
              icon={Square}
              label="Glass UI Components"
              description="다크 배경 위 glass-morphism 카드, 인풋, 뱃지"
            />
            <PagePreviewCard>
              <div className="hero-gradient-radial rounded-dr-lg p-8 md:p-12 space-y-8">
                {/* Glass Cards */}
                <div>
                  <h3 className="label-uppercase text-white/40 mb-4">
                    Glass Cards
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="glass-card p-5 hover-glow cursor-pointer">
                      <h4 className="font-heading font-semibold text-white mb-2">
                        Auto FDD
                      </h4>
                      <p className="text-sm text-white/50">
                        Financial Due Diligence automation with AI-powered
                        analysis
                      </p>
                      <div className="flex items-center gap-1 mt-4 text-accent text-sm font-medium">
                        Open Module
                        <ArrowRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                    <div className="glass-card p-5 hover-glow cursor-pointer">
                      <h4 className="font-heading font-semibold text-white mb-2">
                        KIIS
                      </h4>
                      <p className="text-sm text-white/50">
                        Korea Investment Intelligence System for portfolio
                        monitoring
                      </p>
                      <div className="flex items-center gap-1 mt-4 text-accent text-sm font-medium">
                        Open Module
                        <ArrowRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                    <div className="glass-card p-5 hover-glow cursor-pointer">
                      <h4 className="font-heading font-semibold text-white mb-2">
                        IM Generator
                      </h4>
                      <p className="text-sm text-white/50">
                        Investment Memorandum generation and template management
                      </p>
                      <div className="flex items-center gap-1 mt-4 text-accent text-sm font-medium">
                        Open Module
                        <ArrowRight className="h-3.5 w-3.5" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Glass Form Elements */}
                <div>
                  <h3 className="label-uppercase text-white/40 mb-4">
                    Glass Form Elements
                  </h3>
                  <div className="max-w-md space-y-4">
                    <div>
                      <label className="text-xs text-white/50 mb-1.5 block">
                        Search
                      </label>
                      <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
                        <input
                          type="text"
                          placeholder="Search across modules..."
                          className="w-full bg-white/[0.06] border border-white/[0.08] rounded-dr-sm px-3 py-2 pl-10 text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent/30 backdrop-blur-sm"
                        />
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <button className="rounded-dr-sm bg-accent text-white px-4 py-2 text-sm font-medium hover:bg-accent-hover shadow-dr-sm hover:shadow-glow-green transition-all active:scale-[0.98]">
                        Search
                      </button>
                      <button className="rounded-dr-sm bg-white/[0.06] border border-white/[0.08] text-white/70 px-4 py-2 text-sm font-medium hover:bg-white/[0.10] hover:text-white transition-all active:scale-[0.98]">
                        Clear
                      </button>
                    </div>
                  </div>
                </div>

                {/* Glass Badges */}
                <div>
                  <h3 className="label-uppercase text-white/40 mb-4">
                    Glass Badges
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-accent/20 text-accent border border-accent/10">
                      Connected
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-caution/20 text-caution border border-caution/10">
                      Pending
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-negative/20 text-red-300 border border-negative/10">
                      Error
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-white/10 text-white/70 border border-white/10">
                      Neutral
                    </span>
                  </div>
                </div>
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 7. Shadow System ── */}
          <section id="shadows">
            <SectionDivider
              icon={RectangleHorizontal}
              label="Shadow System"
              description="AMIC 틸 기반 쉐도우 + 그린 글로우"
            />
            <PagePreviewCard>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                {[
                  { name: "dr-sm", cls: "shadow-dr-sm" },
                  { name: "dr-md", cls: "shadow-dr-md" },
                  { name: "dr-lg", cls: "shadow-dr-lg" },
                  { name: "dr-xl", cls: "shadow-dr-xl" },
                  { name: "glow-green", cls: "shadow-glow-green" },
                  { name: "glow-teal", cls: "shadow-glow-teal" },
                ].map((shadow) => (
                  <div
                    key={shadow.name}
                    className={`bg-white rounded-dr p-6 border border-gray-border ${shadow.cls}`}
                  >
                    <p className="text-sm font-mono text-text-secondary">
                      shadow-{shadow.name}
                    </p>
                  </div>
                ))}
              </div>
            </PagePreviewCard>
          </section>

          {/* ── 8. Login Page Preview ── */}
          <section id="login">
            <SectionDivider
              icon={LogIn}
              label="Login Page (Refreshed)"
              description="다크 오버레이 + 브랜딩 텍스트 + 글로우 버튼"
              route="/login"
            />
            <PagePreviewCard>
              <div className="grid md:grid-cols-2 gap-0 -m-6 rounded-dr overflow-hidden">
                {/* Left: Dark branded panel */}
                <div className="hero-gradient-radial p-12 flex flex-col justify-center min-h-[480px] relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-48 h-48 bg-accent/5 rounded-full blur-3xl" />
                  <div className="absolute bottom-0 left-0 w-64 h-64 bg-amic-400/5 rounded-full blur-3xl" />
                  <div className="relative">
                    <div className="flex items-start gap-3 mb-8">
                      <span className="text-white font-serif font-bold text-[28px] tracking-[0.2em] leading-none mt-0.5">
                        AMIC
                      </span>
                      <span className="text-white/25 text-2xl font-extralight leading-none">
                        &amp;
                      </span>
                      <div className="text-accent font-heading font-bold leading-[1.15]">
                        <div className="text-lg tracking-[0.1em]">
                          PETRABRIDGE
                        </div>
                        <div className="text-lg tracking-[0.1em]">
                          PARTNERS
                        </div>
                      </div>
                    </div>
                    <h2 className="text-2xl font-heading font-bold text-white mb-3">
                      M&A Advisory Platform
                    </h2>
                    <p className="text-white/50 text-sm leading-relaxed max-w-sm">
                      End-to-end due diligence, investment intelligence, and
                      document generation — all in one unified platform.
                    </p>
                    <div className="mt-8 flex items-center gap-4 text-white/30 text-xs">
                      <span className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        Auto FDD
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        KIIS
                      </span>
                      <span className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent" />
                        IM Generator
                      </span>
                    </div>
                  </div>
                </div>

                {/* Right: Login form */}
                <div className="p-12 flex items-center justify-center bg-white">
                  <div className="w-full max-w-sm space-y-6">
                    <div>
                      <h2 className="text-2xl font-heading font-bold text-text-dark mb-2">
                        Welcome
                      </h2>
                      <p className="text-text-secondary">
                        Sign in to continue
                      </p>
                    </div>
                    <div className="space-y-4">
                      <Input
                        label="Email"
                        type="email"
                        placeholder="user@petrabridge.com"
                      />
                      <Input
                        label="Password"
                        type="password"
                        placeholder="Enter your password"
                      />
                      <button className="w-full inline-flex items-center justify-center gap-2 rounded-dr-sm font-medium transition-all duration-200 bg-accent text-white hover:bg-accent-hover shadow-dr-sm hover:shadow-glow-green active:scale-[0.98] px-5 py-2.5 text-base">
                        <LogIn className="w-4 h-4" />
                        Sign In
                      </button>
                    </div>
                    <p className="text-center text-footnote text-text-muted">
                      AMIC x PETRA Platform v2.0
                    </p>
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
