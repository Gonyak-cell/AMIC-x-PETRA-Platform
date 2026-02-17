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

function handleGlobalError(error: Error) {
  const message = error.message || "요청 처리 중 오류가 발생했습니다";
  // DEBUG: API 에러 시 요청 URL 포함하여 표시
  const axiosErr = error as { config?: { method?: string; url?: string; baseURL?: string } };
  const url = axiosErr.config?.url;
  const base = axiosErr.config?.baseURL;
  const method = axiosErr.config?.method?.toUpperCase();
  if (url) {
    const fullPath = base ? `${base}${url}` : url;
    console.error(`[API Error] ${method} ${fullPath}:`, message);
    toast.error(`${message}\n${method} ${fullPath}`);
  } else {
    toast.error(message);
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: handleGlobalError,
  }),
  mutationCache: new MutationCache({
    onError: handleGlobalError,
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
                    fontFamily: "'Pretendard', 'Inter', sans-serif",
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
