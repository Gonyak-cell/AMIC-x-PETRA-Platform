import React, { Suspense } from "react";
import { Routes, Route, Outlet, Navigate } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui";
import { PlatformSettingsProvider } from "@/contexts/PlatformSettingsContext";
import { useAuth } from "@/hooks/useAuth";

/** CLIENT 역할의 사내 전용 라우트 접근을 차단한다. */
function InternalOnlyRoute({ children }: { children: React.ReactNode }) {
  const { isClient } = useAuth();
  if (isClient) return <Navigate to="/ma/transactions" replace />;
  return <>{children}</>;
}

const DashboardPage = React.lazy(() => import("@/pages/DashboardPage"));
const FddRoutes = React.lazy(() => import("@/modules/fdd/FddRoutes"));
const KiisRoutes = React.lazy(() => import("@/modules/kiis/KiisRoutes"));
const ImRoutes = React.lazy(() => import("@/modules/im/ImRoutes"));
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
const ExportsRoutes = React.lazy(() => import("@/pages/exports/ExportsRoutes"));
const DocsRoutes = React.lazy(() => import("@/modules/docs/DocsRoutes"));
const VdrRoutes = React.lazy(() => import("@/modules/vdr/VdrRoutes"));
const TeamPage = React.lazy(() => import("@/pages/team/TeamPage"));
const InviteAcceptPage = React.lazy(
  () => import("@/pages/invite/InviteAcceptPage"),
);

function ModuleFallback() {
  return <Skeleton className="h-96 w-full rounded-lg" />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/invite/accept"
        element={
          <Suspense fallback={<ModuleFallback />}>
            <InviteAcceptPage />
          </Suspense>
        }
      />
      <Route
        element={
          <ProtectedRoute>
            <PlatformSettingsProvider>
              <AppShell>
                <Outlet />
              </AppShell>
            </PlatformSettingsProvider>
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
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <FddRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="kiis/*"
          element={
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <KiisRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="im/*"
          element={
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <ImRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
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
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <AdminRoutes />
              </Suspense>
            </InternalOnlyRoute>
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
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <AnalyticsRoutes />
              </Suspense>
            </InternalOnlyRoute>
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
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <CalendarRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="exports/*"
          element={
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <ExportsRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="vdr/*"
          element={
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <VdrRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="docs/*"
          element={
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <DocsRoutes />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="team/*"
          element={
            <InternalOnlyRoute>
              <Suspense fallback={<ModuleFallback />}>
                <TeamPage />
              </Suspense>
            </InternalOnlyRoute>
          }
        />
        <Route
          path="*"
          element={
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <h1 className="text-4xl font-heading font-bold text-text-dark mb-2">
                404
              </h1>
              <p className="text-text-secondary mb-6">Page not found</p>
              <a href="/" className="text-amic hover:underline">
                Go to Dashboard
              </a>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
