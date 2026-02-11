import { Routes, Route, Navigate } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import CompanyListPage from "./pages/CompanyListPage";
import CompanyDetailPage from "./pages/CompanyDetailPage";
import FundListPage from "./pages/FundListPage";
import FundDetailPage from "./pages/FundDetailPage";
import ReitListPage from "./pages/ReitListPage";
import ReitDetailPage from "./pages/ReitDetailPage";
import NewsListPage from "./pages/NewsListPage";
import NewsDetailPage from "./pages/NewsDetailPage";
import DealSourcingPage from "./pages/DealSourcingPage";
import SanctionListPage from "./pages/SanctionListPage";
import WatchlistPage from "./pages/WatchlistPage";
import PortfolioPage from "./pages/PortfolioPage";
import ManagerListPage from "./pages/ManagerListPage";
import ManagerProfilePage from "./pages/ManagerProfilePage";
import EntityResolutionPage from "./pages/EntityResolutionPage";
import DisclosurePage from "./pages/DisclosurePage";
import GallerySamplePage from "./pages/GallerySamplePage";

export default function KiisRoutes() {
  return (
    <Routes>
      <Route index element={<DashboardPage />} />
      <Route path="companies" element={<CompanyListPage />} />
      <Route path="companies/:corpCode" element={<CompanyDetailPage />} />
      <Route path="funds" element={<FundListPage />} />
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
      <Route path="gallery" element={<GallerySamplePage />} />
      <Route path="*" element={<Navigate to="/kiis" replace />} />
    </Routes>
  );
}
