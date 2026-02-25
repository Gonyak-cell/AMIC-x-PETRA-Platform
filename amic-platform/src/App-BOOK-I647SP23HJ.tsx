import React, { Suspense } from "react";
import { Routes, Route, Navigate, Outlet } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui";

const DashboardPage = React.lazy(() => import("@/pages/DashboardPage"));
const FddRoutes = React.lazy(() => import("@/modules/fdd/FddRoutes"));
const KiisRoutes = React.lazy(() => import("@/modules/kiis/KiisRoutes"));
const DocsRoutes = React.lazy(() => import("@/modules/docs/DocsRoutes"));
const MaRoutes = React.lazy(() => import("@/modules/ma/MaRoutes"));
const AdminRoutes = React.lazy(() => import("@/pages/admin/AdminRoutes"));
const SettingsRoutes = React.lazy(
  () => import("@/pages/settings/SettingsRoutes"),
);
const AnalyticsRoutes = React.lazy(
  () => import("@/pages/analytics/AnalyticsRoutes"),
);
const HelpRoutes = React.lazy(() => import("@/pages/help/HelpRoutes"));
const CalendarRoutes = React.lazy(
  () => import("@/pages/calendar/CalendarRoutes"),
);
const ExportsRoutes = React.lazy(
  () => import("@/pages/exports/ExportsRoutes"),
);

function ModuleFallback() {
  return <Skeleton className="h-96 w-full rounded-lg" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell>
              <Outlet />
            </AppShell>
          </ProtectedRoute>
        }
      >
        <Route
          index
          element={
            <Suspense fallback={<ModuleFallback />}>
              <DashboardPage />
            </Suspense>
          }
        />
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
          path="docs/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <DocsRoutes />
            </Suspense>
          }
        />
        <Route path="im/*" element={<Navigate to="/docs" replace />} />
        <Route
          path="ma/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <MaRoutes />
            </Suspense>
          }
        />
        <Route
          path="admin/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <AdminRoutes />
            </Suspense>
          }
        />
        <Route
          path="settings/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <SettingsRoutes />
            </Suspense>
          }
        />
        <Route
          path="analytics/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <AnalyticsRoutes />
            </Suspense>
          }
        />
        <Route
          path="help/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <HelpRoutes />
            </Suspense>
          }
        />
        <Route
          path="calendar/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <CalendarRoutes />
            </Suspense>
          }
        />
        <Route
          path="exports/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <ExportsRoutes />
            </Suspense>
          }
        />
        <Route
          path="*"
          element={
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <h1 className="text-4xl font-heading font-bold text-text-dark mb-2">404</h1>
              <p className="text-text-secondary mb-6">Page not found</p>
              <a href="/" className="text-amic hover:underline">Go to Dashboard</a>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
