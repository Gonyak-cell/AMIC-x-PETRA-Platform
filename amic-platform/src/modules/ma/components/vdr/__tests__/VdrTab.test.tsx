import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";

import {
  AuthContext,
  type AuthContextValue,
} from "@/components/auth/AuthContext";
import { mockUser } from "@/test/mocks/data";
import { server } from "@/test/mocks/server";
import { createTestQueryClient } from "@/test/test-utils";

import VdrTab from "../VdrTab";

const defaultAuth: AuthContextValue = {
  user: mockUser,
  isAuthenticated: true,
  isLoading: false,
  setAuthState: vi.fn(),
};

const initializedSummary = {
  total_folders: 2,
  total_documents: 5,
  total_size_bytes: 1024000,
  initialized: true,
};

const mockFolders = [
  {
    id: "folder-1",
    transaction_id: "txn-1",
    name: "Financial",
    category: "FINANCIAL",
    parent_id: null,
    children: [],
    document_count: 3,
    is_required: true,
    order_index: 0,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

function renderTab(
  txnId = "txn-1",
  options?: {
    entryPath?: string;
    entrySearch?: string;
    entryState?: unknown;
    readOnly?: boolean;
    showReviewTabs?: boolean;
    showExtractionTools?: boolean;
  },
) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter
        initialEntries={[
          {
            pathname: options?.entryPath ?? "/ma/transactions/txn-1/vdr",
            search: options?.entrySearch,
            state: options?.entryState,
          },
        ]}
      >
        <AuthContext.Provider value={defaultAuth}>
          <VdrTab
            txnId={txnId}
            readOnly={options?.readOnly}
            showReviewTabs={options?.showReviewTabs}
            showExtractionTools={options?.showExtractionTools}
          />
        </AuthContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function installDefaultHandlers() {
  server.use(
    http.get("*/api/ma/transactions/:txnId/vdr/summary", () =>
      HttpResponse.json(initializedSummary),
    ),
    http.get("*/api/ma/transactions/:txnId/vdr/folders", () =>
      HttpResponse.json(mockFolders),
    ),
    http.get("*/api/ma/transactions/:txnId/extractions", () =>
      HttpResponse.json({ items: [], total: 0 }),
    ),
    http.get("*/api/ma/transactions/:txnId/vdr/routing-queue", () =>
      HttpResponse.json({
        summary: {
          total_documents: 1,
          returned_documents: 0,
          open_documents: 0,
          reviewed_documents: 0,
          auto_routed_documents: 1,
          by_effective_workstream: { FDD: 1 },
        },
        items: [],
      }),
    ),
  );
}

beforeEach(() => {
  server.resetHandlers();
});

describe("VdrTab", () => {
  it("shows a loading state while the summary request is pending", () => {
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () => {
        return new Promise(() => {});
      }),
    );

    renderTab();
    expect(screen.getByText("Loading VDR...")).toBeInTheDocument();
  });

  it("renders the documents, routing, and access tabs", async () => {
    installDefaultHandlers();
    renderTab();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Documents" })).toBeVisible();
    });

    expect(screen.getByRole("button", { name: "Routing" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Access" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Quick Upload" })).toBeVisible();
  });

  it("renders a client upload view without internal review tabs", async () => {
    installDefaultHandlers();
    renderTab("txn-1", {
      showReviewTabs: false,
      showExtractionTools: false,
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Documents" })).toBeVisible();
    });

    expect(
      screen.queryByRole("button", { name: "Routing" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Access" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Quick Upload" }),
    ).toBeVisible();
  });

  it("shows root folders in both the tree and the document list", async () => {
    installDefaultHandlers();
    renderTab();

    await waitFor(() => {
      expect(screen.getAllByText("Financial").length).toBeGreaterThanOrEqual(2);
    });
  });

  it("renders the routing triage panel when the routing tab is selected", async () => {
    installDefaultHandlers();
    renderTab();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Routing" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Routing" }));

    await waitFor(() => {
      expect(screen.getByText("Routing Triage Queue")).toBeInTheDocument();
    });
    expect(
      await screen.findByText("No documents match the current filter."),
    ).toBeInTheDocument();
  });

  it("shows a repair action when VDR initialization is incomplete", async () => {
    let initialized = false;
    server.use(
      http.get("*/api/ma/transactions/:txnId/vdr/summary", () =>
        HttpResponse.json({
          ...initializedSummary,
          total_folders: initialized ? 12 : 1,
          initialized,
        }),
      ),
      http.get("*/api/ma/transactions/:txnId/vdr/folders", () =>
        HttpResponse.json(initialized ? mockFolders : []),
      ),
      http.post("*/api/ma/transactions/:txnId/vdr/init", () => {
        initialized = true;
        return HttpResponse.json(mockFolders);
      }),
      http.get("*/api/ma/transactions/:txnId/extractions", () =>
        HttpResponse.json({ items: [], total: 0 }),
      ),
      http.get("*/api/ma/transactions/:txnId/vdr/routing-queue", () =>
        HttpResponse.json({
          summary: {
            total_documents: 0,
            returned_documents: 0,
            open_documents: 0,
            reviewed_documents: 0,
            auto_routed_documents: 0,
            by_effective_workstream: {},
          },
          items: [],
        }),
      ),
    );

    renderTab();

    expect(
      await screen.findByText("VDR setup is incomplete."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Quick Upload" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Repair VDR" }));

    await waitFor(() => {
      expect(
        screen.queryByText("VDR setup is incomplete."),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Quick Upload" })).toBeVisible();
  });

  it("opens the upload dropzone and return action when entered from another page", async () => {
    installDefaultHandlers();

    const { container } = renderTab("txn-1", {
      entryPath: "/ma/transactions/txn-1/vdr",
      entrySearch: "?upload=1",
      entryState: {
        vdrUploadEntry: {
          returnTo: "/ma/transactions/txn-1/buyers",
          returnLabel: "Buyers",
        },
      },
    });

    expect(await screen.findByText("Upload to VDR")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Back to Buyers" }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(container.querySelector("input[type='file']")).not.toBeNull();
    });
  });

  it("keeps the quick upload dropzone open after a drag-and-drop upload completes", async () => {
    installDefaultHandlers();
    server.use(
      http.post("*/api/ma/transactions/:txnId/vdr/uploads", async () =>
        HttpResponse.json(
          {
            results: [],
            pending_review_count: 0,
            total_uploaded: 1,
            failed_files: [],
          },
          { status: 201 },
        ),
      ),
    );

    const { container } = renderTab();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Quick Upload" })).toBeVisible();
    });

    fireEvent.click(screen.getByRole("button", { name: "Quick Upload" }));

    const fileInput = await waitFor(() => {
      const input = container.querySelector("input[type='file']");
      expect(input).not.toBeNull();
      return input as HTMLInputElement;
    });
    const dropTarget = fileInput.closest("[role='button']");
    expect(dropTarget).not.toBeNull();

    const file = new File(["hello world"], "teaser.pdf", {
      type: "application/pdf",
    });

    fireEvent.dragOver(dropTarget as HTMLElement, {
      dataTransfer: { files: [file], types: ["Files"] },
    });
    fireEvent.drop(dropTarget as HTMLElement, {
      dataTransfer: { files: [file], types: ["Files"] },
    });

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    expect(container.querySelector("input[type='file']")).not.toBeNull();
  });
});
