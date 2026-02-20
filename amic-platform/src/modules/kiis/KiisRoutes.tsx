import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import DashboardPage from "./pages/DashboardPage";

const CompanyListPage = lazy(() => import("./pages/CompanyListPage"));
const CompanyDetailPage = lazy(() => import("./pages/CompanyDetailPage"));
const GPListPage = lazy(() => import("./pages/GPListPage"));
const GPDetailPage = lazy(() => import("./pages/GPDetailPage"));
const FundListPage = lazy(() => import("./pages/FundListPage"));
const FundDetailPage = lazy(() => import("./pages/FundDetailPage"));
const ReitListPage = lazy(() => import("./pages/ReitListPage"));
const ReitDetailPage = lazy(() => import("./pages/ReitDetailPage"));
const NewsListPage = lazy(() => import("./pages/NewsListPage"));
const NewsDetailPage = lazy(() => import("./pages/NewsDetailPage"));
const DealSourcingPage = lazy(() => import("./pages/DealSourcingPage"));
const SanctionListPage = lazy(() => import("./pages/SanctionListPage"));
const WatchlistPage = lazy(() => import("./pages/WatchlistPage"));
const PortfolioPage = lazy(() => import("./pages/PortfolioPage"));
const ManagerListPage = lazy(() => import("./pages/ManagerListPage"));
const ManagerProfilePage = lazy(() => import("./pages/ManagerProfilePage"));
const EntityResolutionPage = lazy(() => import("./pages/EntityResolutionPage"));
const DisclosurePage = lazy(() => import("./pages/DisclosurePage"));

export default function KiisRoutes() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route index element={<DashboardPage />} />
        <Route path="companies" element={<CompanyListPage />} />
        <Route path="companies/:corpCode" element={<CompanyDetailPage />} />
        <Route path="funds" element={<GPListPage />} />
        <Route path="funds/all" element={<FundListPage />} />
        <Route path="funds/gp/:companyCode" element={<GPDetailPage />} />
        <Route path="funds/:fundCode" element={<FundDetailPage />} />
        <Route path="reits" element={<ReitListPage />} />
        <Route path="reits/:reitsCode" element={<ReitDetailPage />} />
        <Route path="news" element={<NewsListPage />} />
        <Route path="news/:articleId" element={<NewsDetailPage />} />
        <Route path="deals" element={<DealSourcingPage />} />
        <Route path="sanctions" element={<SanctionListPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="managers" element={<ManagerListPage />} />
        <Route path="managers/:managerName" element={<ManagerProfilePage />} />
        <Route path="entities" element={<EntityResolutionPage />} />
        <Route path="disclosures" element={<DisclosurePage />} />
        <Route path="watchlist" element={<WatchlistPage />} />
        <Route path="*" element={<Navigate to="/kiis" replace />} />
      </Routes>
    </Suspense>
  );
}
