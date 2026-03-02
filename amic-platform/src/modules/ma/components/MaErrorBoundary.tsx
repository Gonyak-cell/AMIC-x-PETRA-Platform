import { Component, type ErrorInfo, type ReactNode } from "react";
import * as Sentry from "@sentry/react";
import { AlertTriangle } from "lucide-react";
import { Button, Card } from "@/components/ui";

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
            <p className="text-sm text-text-secondary mb-4">
              {this.state.error?.message ||
                "M&A 모듈에서 예기치 않은 오류가 발생했습니다."}
            </p>
            <Button
              variant="primary"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              다시 시도
            </Button>
          </div>
        </Card>
      );
    }
    return this.props.children;
  }
}
