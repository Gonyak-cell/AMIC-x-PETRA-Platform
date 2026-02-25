import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { Spinner } from "@/components/ui";

const VdrOverviewPage = lazy(() => import("./pages/VdrOverviewPage"));

export default function VdrRoutes() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route index element={<VdrOverviewPage />} />
      </Routes>
    </Suspense>
  );
}
