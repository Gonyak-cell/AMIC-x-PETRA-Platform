import React, { Suspense } from "react";
import { Routes, Route, Outlet } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui";

const DashboardPage = React.lazy(() => import("@/pages/DashboardPage"));
const FddRoutes = React.lazy(() => import("@/modules/fdd/FddRoutes"));
const KiisRoutes = React.lazy(() => import("@/modules/kiis/KiisRoutes"));
const ImRoutes = React.lazy(() => import("@/modules/im/ImRoutes"));
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
const PortalSamplePage = React.lazy(
  () => import("@/pages/samples/PortalSamplePage"),
);
const NewsSamplePage = React.lazy(
  () => import("@/pages/samples/NewsSamplePage"),
);
const DesignRefreshSamplePage = React.lazy(
  () => import("@/pages/samples/DesignRefreshSamplePage"),
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
          path="im/*"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <ImRoutes />
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
          path="samples/portal"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <PortalSamplePage />
            </Suspense>
          }
        />
        <Route
          path="samples/news"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <NewsSamplePage />
            </Suspense>
          }
        />
        <Route
          path="samples/design-refresh"
          element={
            <Suspense fallback={<ModuleFallback />}>
              <DesignRefreshSamplePage />
            </Suspense>
          }
        />
      </Route>
    </Routes>
  );
}
