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
  toast.error(message);
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

async function enableMocking() {
  if (!import.meta.env.DEV || import.meta.env.VITE_DISABLE_MSW === "true") {
    return;
  }
  try {
    const { worker } = await import("./test/mocks/browser");
    await worker.start({
      onUnhandledRequest: "bypass",
      quiet: false,
    });
    console.log("[MSW] Mocking enabled successfully");
  } catch (err) {
    console.warn("[MSW] Failed to start:", err);
  }
}

enableMocking().then(() => {
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
});
