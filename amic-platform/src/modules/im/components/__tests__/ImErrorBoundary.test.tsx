import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ImErrorBoundary } from "../ImErrorBoundary";

// Suppress console.error for error boundary tests
const originalError = console.error;
beforeAll(() => {
  console.error = vi.fn();
});
afterAll(() => {
  console.error = originalError;
});

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error("Test render error");
  return <div>Rendered successfully</div>;
}

describe("ImErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <ImErrorBoundary>
        <div>Hello</div>
      </ImErrorBoundary>,
    );
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("renders error UI when child throws", () => {
    render(
      <ImErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ImErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Test render error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try Again" })).toBeInTheDocument();
  });

  it("resets error state on Try Again click", async () => {
    const user = userEvent.setup();
    const { rerender } = render(
      <ImErrorBoundary>
        <ThrowingComponent shouldThrow />
      </ImErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();

    // Rerender with non-throwing component before clicking retry
    rerender(
      <ImErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ImErrorBoundary>,
    );

    await user.click(screen.getByRole("button", { name: "Try Again" }));
    expect(screen.getByText("Rendered successfully")).toBeInTheDocument();
  });
});
