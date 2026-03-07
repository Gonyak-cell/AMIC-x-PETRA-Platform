import { lazy, Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import { MaErrorBoundary } from "./components/MaErrorBoundary";

const TransactionListPage = lazy(() => import("./pages/TransactionListPage"));
const DealSetupWizardPage = lazy(() => import("./pages/DealSetupWizardPage"));
const TransactionWorkspacePage = lazy(
  () => import("./pages/TransactionWorkspacePage"),
);

export default function MaRoutes() {
  return (
    <MaErrorBoundary>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route path="transactions" element={<TransactionListPage />} />
          <Route path="transactions/new" element={<DealSetupWizardPage />} />
          <Route
            path="transactions/:txnId/*"
            element={<TransactionWorkspacePage />}
          />
          <Route index element={<Navigate to="transactions" replace />} />
        </Routes>
      </Suspense>
    </MaErrorBoundary>
  );
}
