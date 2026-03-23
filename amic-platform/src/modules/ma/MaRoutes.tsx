import { Suspense } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Spinner } from "@/components/ui";
import { lazyWithRetry } from "@/lib/lazyWithRetry";
import { MaErrorBoundary } from "./components/MaErrorBoundary";

const TransactionListPage = lazyWithRetry(
  () => import("./pages/TransactionListPage"),
  "modules/ma/pages/TransactionListPage",
);
const DealSetupWizardPage = lazyWithRetry(
  () => import("./pages/DealSetupWizardPage"),
  "modules/ma/pages/DealSetupWizardPage",
);
const TransactionWorkspacePage = lazyWithRetry(
  () => import("./pages/TransactionWorkspacePage"),
  "modules/ma/pages/TransactionWorkspacePage",
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
