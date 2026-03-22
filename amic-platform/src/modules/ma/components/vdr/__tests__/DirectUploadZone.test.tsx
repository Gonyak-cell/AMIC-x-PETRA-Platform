import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "@/test/mocks/server";
import { createTestQueryClient } from "@/test/test-utils";

import DirectUploadZone from "../DirectUploadZone";

function renderZone(onUploadComplete = vi.fn()) {
  const queryClient = createTestQueryClient();
  return {
    onUploadComplete,
    ...render(
      <QueryClientProvider client={queryClient}>
        <DirectUploadZone txnId="txn-1" onUploadComplete={onUploadComplete} />
      </QueryClientProvider>,
    ),
  };
}

beforeEach(() => {
  server.resetHandlers();
});

describe("DirectUploadZone", () => {
  it("uploads dropped files through the direct-upload endpoint", async () => {
    const onUploadComplete = vi.fn();

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

    renderZone(onUploadComplete);

    const dropTarget = screen.getByRole("button");
    const file = new File(["hello world"], "financial_report_2024.pdf", {
      type: "application/pdf",
    });

    fireEvent.dragOver(dropTarget, {
      dataTransfer: { files: [file], types: ["Files"] },
    });
    fireEvent.drop(dropTarget, {
      dataTransfer: { files: [file], types: ["Files"] },
    });

    await waitFor(() => {
      expect(onUploadComplete).toHaveBeenCalledWith(
        expect.objectContaining({
          total_uploaded: 1,
        }),
      );
    });
  });
});
