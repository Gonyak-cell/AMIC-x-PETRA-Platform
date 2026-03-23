import React, { Suspense } from "react";
import { Routes, Route, Outlet, Navigate } from "react-router-dom";
import LoginPage from "@/pages/LoginPage";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import AppShell from "@/components/layout/AppShell";
import { Skeleton } from "@/components/ui";
import { PlatformSettingsProvider } from "@/contexts/PlatformSettingsContext";
import { useAuth } from "@/hooks/useAuth";
import { lazyWithRetry } from "@/lib/lazyWithRetry";

/** CLIENT 역할의 사내 전용 라우트 접근을 차단한다. */
function InternalOnlyRoute({ children }: { children: React.ReactNode }) {
  const { isClient } = useAuth();
  if (isClient) return <Navigate to="/ma/transactions" replace />;
  return <>{children}</>;
}

function AdminOnlyRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "ADMIN") return <Navigate to="/" replace />;
  return <>{children}</>;
}

const DashboardPage = lazyWithRetry(
  () => import("@/pages/DashboardPage"),
  "pages/DashboardPage",
);
const FddRoutes = lazyWithRetry(
  () => import("@/modules/fdd/FddRoutes"),
  "modules/fdd/FddRoutes",
);
const KiisRoutes = lazyWithRetry(
  () => import("@/modules/kiis/KiisRoutes"),
  "modules/kiis/KiisRoutes",
);
const ImRoutes = lazyWithRetry(
  () => import("@/modules/im/ImRoutes"),
  "modules/im/ImRoutes",
);
const MaRoutes = lazyWithRetry(
  () => import("@/modules/ma/MaRoutes"),
  "modules/ma/MaRoutes",
);
const AdminRoutes = lazyWithRetry(
  () => import("@/pages/admin/AdminRoutes"),
  "pages/admin/AdminRoutes",
);
const SettingsRoutes = lazyWithRetry(
  () => import("@/pages/settings/SettingsRoutes"),
  "pages/settings/SettingsRoutes",
);
const AnalyticsRoutes = lazyWithRetry(
  () => import("@/pages/analytics/AnalyticsRoutes"),
  "pages/analytics/AnalyticsRoutes",
);
const HelpRoutes = lazyWithRetry(
  () => import("@/pages/help/HelpRoutes"),
  "pages/help/HelpRoutes",
);
const CalendarRoutes = lazyWithRetry(
  () => import("@/pages/calendar/CalendarRoutes"),
  "pages/calendar/CalendarRoutes",
);
const ExportsRoutes = lazyWithRetry(
  () => import("@/pages/exports/ExportsRoutes"),
  "pages/exports/ExportsRoutes",
);
const DocsRoutes = lazyWithRetry(
  () => import("@/modules/docs/DocsRoutes"),
  "modules/docs/DocsRoutes",
);
const TeamPage = lazyWithRetry(
  () => import("@/pages/team/TeamPage"),
  "pages/team/TeamPage",
);
const InviteAcceptPage = lazyWithRetry(
  () => import("@/pages/invite/InviteAcceptPage"),
  "pages/invite/InviteAcceptPage",
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
              <AdminOnlyRoute>
                <Suspense fallback={<ModuleFallback />}>
                  <AnalyticsRoutes />
                </Suspense>
              </AdminOnlyRoute>
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
            <Suspense fallback={<ModuleFallback />}>
              <CalendarRoutes />
            </Suspense>
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
          element={<Navigate to="/ma/transactions" replace />}
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
            <Suspense fallback={<ModuleFallback />}>
              <TeamPage />
            </Suspense>
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
