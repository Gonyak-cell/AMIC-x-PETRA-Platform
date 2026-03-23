import { Component, type ErrorInfo, type ReactNode } from "react";
import * as Sentry from "@sentry/react";
import { AlertTriangle } from "lucide-react";
import { Button, Card } from "@/components/ui";
import { isRecoverableChunkLoadError } from "@/lib/lazyWithRetry";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class MaErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[MA] Uncaught error:", error, info);
    Sentry.captureException(error, {
      extra: { componentStack: info.componentStack },
    });
  }

  render() {
    if (this.state.hasError) {
      const isChunkLoadError = isRecoverableChunkLoadError(this.state.error);
      const message = isChunkLoadError
        ? "새 배포가 반영되는 중일 수 있습니다. 페이지를 새로고침한 뒤 다시 시도해 주세요."
        : this.state.error?.message ||
          "M&A 모듈에서 예기치 않은 오류가 발생했습니다.";

      return (
        <Card className="max-w-lg mx-auto mt-12">
          <div
            role="alert"
            className="flex flex-col items-center py-8 text-center"
          >
            <AlertTriangle className="h-12 w-12 text-negative mb-4" />
            <h2 className="text-lg font-heading font-semibold text-text-dark mb-2">
              오류가 발생했습니다
            </h2>
            <p className="text-sm text-text-secondary mb-4">{message}</p>
            <Button
              variant="primary"
              onClick={() => {
                if (isChunkLoadError) {
                  window.location.reload();
                  return;
                }
                this.setState({ hasError: false, error: null });
              }}
            >
              {isChunkLoadError ? "새로고침" : "다시 시도"}
            </Button>
          </div>
        </Card>
      );
    }
    return this.props.children;
  }
}
