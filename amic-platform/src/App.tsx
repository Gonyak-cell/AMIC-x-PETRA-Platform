import React, { Suspense } from "react";
import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import AppShell from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui";

const FddRoutes = React.lazy(() => import("@/modules/fdd/FddRoutes"));
const KiisRoutes = React.lazy(() => import("@/modules/kiis/KiisRoutes"));
const ImRoutes = React.lazy(() => import("@/modules/im/ImRoutes"));

function ModuleFallback() {
  return <Skeleton className="h-96 w-full rounded-lg" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <AppShell>
            <Outlet />
          </AppShell>
        }
      >
        <Route index element={<Navigate to="/fdd/deals" replace />} />
        <Route
          path="fdd/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <FddRoutes />
            </Suspense>
          }
        />
        <Route
          path="kiis/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <KiisRoutes />
            </Suspense>
          }
        />
        <Route
          path="im/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <ImRoutes />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}
