import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";

const GPResearchPage = lazy(() => import("./pages/GPResearchPage"));
const FundListPage = lazy(() => import("./pages/FundListPage"));
const FundDetailPage = lazy(() => import("./pages/FundDetailPage"));
const ReitListPage = lazy(() => import("./pages/ReitListPage"));
const ReitDetailPage = lazy(() => import("./pages/ReitDetailPage"));
const CompanyListPage = lazy(() => import("./pages/CompanyListPage"));
const CompanyDetailPage = lazy(() => import("./pages/CompanyDetailPage"));

export default function KiisRoutes() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route index element={<Navigate to="/kiis/gp" replace />} />
        <Route path="gp" element={<GPResearchPage />} />
        <Route path="funds" element={<FundListPage />} />
        <Route path="funds/:fundCode" element={<FundDetailPage />} />
        <Route path="reits" element={<ReitListPage />} />
        <Route path="reits/:reitsCode" element={<ReitDetailPage />} />
        <Route path="companies" element={<CompanyListPage />} />
        <Route path="companies/:corpCode" element={<CompanyDetailPage />} />
        <Route path="*" element={<Navigate to="/kiis/gp" replace />} />
      </Routes>
    </Suspense>
  );
}
