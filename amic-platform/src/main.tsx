import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { Toaster, toast } from "sonner";
import { initSentry } from "@/lib/sentry";
import { SentryErrorBoundary } from "@/components/SentryErrorBoundary";
import AuthProvider from "./components/auth/AuthProvider";
import { LiveRegionProvider } from "./components/ui";
import App from "./App";
import "./index.css";

initSentry();

const DEV_LOCAL_AUTH_ENABLED =
  (import.meta.env.VITE_DEV_LOCAL_AUTH ?? "").trim() === "true";

type ApiErrorShape = Error & {
  config?: { method?: string; url?: string; baseURL?: string };
  response?: { status?: number };
};

function getRequestInfo(error: Error) {
  const axiosErr = error as ApiErrorShape;
  const url = axiosErr.config?.url;
  const base = axiosErr.config?.baseURL;
  const method = axiosErr.config?.method?.toUpperCase();
  const status = axiosErr.response?.status;
  const fullPath = url ? (base ? `${base}${url}` : url) : undefined;
  return { url, method, status, fullPath };
}

function shouldSuppressDevModuleQueryError(error: Error) {
  if (!DEV_LOCAL_AUTH_ENABLED) return false;
  if (typeof window === "undefined") return false;
  if (
    !window.location.pathname.startsWith("/ma") &&
    !window.location.pathname.startsWith("/analytics")
  ) {
    return false;
  }

  const { method, status, fullPath } = getRequestInfo(error);
  if (method !== "GET") return false;
  if (!fullPath) return false;
  if (![401, 403, 404, 405].includes(status ?? 0)) return false;

  return ["/api/fdd", "/api/kiis", "/api/im"].some((prefix) =>
    fullPath.startsWith(prefix),
  );
}

function handleGlobalError(error: Error) {
  const message = error.message || "요청 처리 중 오류가 발생했습니다";
  const { url, method, fullPath } = getRequestInfo(error);
  if (url) {
    console.error(`[API Error] ${method} ${fullPath}:`, message);
  }
  toast.error(message);
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      if (shouldSuppressDevModuleQueryError(error)) {
        const { method, status, fullPath } = getRequestInfo(error);
        console.warn(
          `[Suppressed dev query error] ${method} ${fullPath} -> ${status}`,
        );
        return;
      }
      handleGlobalError(error);
    },
  }),
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      if (!mutation.options.onError) {
        handleGlobalError(error);
      }
    },
  }),
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

// 기존 MSW 서비스 워커가 남아있을 수 있으므로 해제
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    for (const reg of registrations) {
      if (reg.active?.scriptURL.includes("mockServiceWorker")) {
        reg.unregister();
        console.log("[MSW] Stale service worker unregistered");
      }
    }
  });
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SentryErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <LiveRegionProvider>
              <App />
              <Toaster
                position="top-right"
                toastOptions={{
                  className: "font-body",
                  style: {
                    fontFamily: "'Pretendard Variable', 'Pretendard', sans-serif",
                  },
                }}
                richColors
                closeButton
              />
            </LiveRegionProvider>
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </SentryErrorBoundary>
  </StrictMode>,
);
