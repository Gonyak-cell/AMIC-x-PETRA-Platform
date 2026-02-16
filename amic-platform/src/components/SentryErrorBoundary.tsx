import * as Sentry from "@sentry/react";
import { AlertTriangle } from "lucide-react";
import { Button, Card } from "@/components/ui";

function FallbackUI({
  error,
  resetError,
}: {
  error: unknown;
  resetError: () => void;
}) {
  const message = import.meta.env.PROD
    ? "예상치 못한 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    : error instanceof Error ? error.message : "An unexpected error occurred.";

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface p-4">
      <Card className="max-w-lg w-full">
        <div className="flex flex-col items-center py-8 text-center">
          <AlertTriangle className="h-12 w-12 text-negative mb-4" />
          <h1 className="text-lg font-heading font-semibold text-text-dark mb-2">
            Something went wrong
          </h1>
          <p className="text-sm text-text-secondary mb-4">{message}</p>
          <div className="flex gap-3">
            <Button variant="primary" onClick={resetError}>
              Try Again
            </Button>
            <Button
              variant="secondary"
              onClick={() => (window.location.href = "/")}
            >
              Go to Dashboard
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

export function SentryErrorBoundary({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Sentry.ErrorBoundary
      fallback={({ error, resetError }) => (
        <FallbackUI error={error} resetError={resetError} />
      )}
    >
      {children}
    </Sentry.ErrorBoundary>
  );
}
