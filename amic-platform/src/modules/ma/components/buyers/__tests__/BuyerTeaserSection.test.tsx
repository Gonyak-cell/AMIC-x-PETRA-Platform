import { QueryClientProvider } from "@tanstack/react-query";
import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { maApi } from "@/api/maClient";
import { createTestQueryClient } from "@/test/test-utils";

import BuyerTeaserSection from "../BuyerTeaserSection";

const mockUseMarketingMaterials = vi.fn();
const uploadMarketingMaterialMutateAsync = vi.fn();
const fileUploadZoneState = vi.hoisted(() => ({
  props: null as {
    entityType?: string;
    entityId?: string;
    uploadOnly?: boolean;
    customUpload?: ((files: File[]) => Promise<void> | void) | null;
  } | null,
}));

vi.mock("@/modules/ma/hooks/useMarketingMaterials", () => ({
  useMarketingMaterials: () => mockUseMarketingMaterials(),
  useUploadMarketingMaterial: () => ({
    mutateAsync: uploadMarketingMaterialMutateAsync,
    isPending: false,
  }),
}));

vi.mock("@/modules/ma/components/FileUploadZone", () => ({
  default: ({
    entityType,
    entityId,
    uploadOnly,
    customUpload,
    embeddedLabel,
    emptyTitle,
    emptyDescription,
    emptyHint,
    showUploadAction,
  }: {
      entityType?: string;
      entityId?: string;
      uploadOnly?: boolean;
      customUpload?: (files: File[]) => Promise<void> | void;
      embeddedLabel?: string;
      emptyTitle?: string;
      emptyDescription?: string;
    emptyHint?: string;
    showUploadAction?: boolean;
    }) => {
    fileUploadZoneState.props = {
      entityType,
      entityId,
      uploadOnly,
      customUpload: customUpload ?? null,
    };
    return (
      <div data-testid="file-upload-zone">
        <div>{embeddedLabel ?? "file-upload-zone"}</div>
        {emptyTitle ? <div>{emptyTitle}</div> : null}
        {emptyDescription ? <div>{emptyDescription}</div> : null}
        {emptyHint ? <div>{emptyHint}</div> : null}
        <div>{String(showUploadAction ?? true)}</div>
      </div>
    );
  },
}));

const toastSuccessSpy = vi
  .spyOn(toast, "success")
  .mockImplementation(() => "toast-success");
const toastErrorSpy = vi
  .spyOn(toast, "error")
  .mockImplementation(() => "toast-error");

function renderSection() {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <BuyerTeaserSection
        txnId="txn-1"
        canWrite
        buyer={{
          id: "buyer-1",
          transaction_id: "txn-1",
          company_name: "Test Buyer",
          contact_name: "Hong",
          contact_email: null,
          contact_phone: null,
          buyer_type: "STRATEGIC",
          status: "CONTACTED",
          tier: "TIER_1",
          deal_role: "SOLE_BUYER",
          is_short_listed: false,
          corp_code: null,
          ioi_value: null,
          ioi_date: null,
          loi_value: null,
          loi_date: null,
          final_offer_value: null,
          rejection_reason: null,
          notes: null,
          extra_data: null,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        }}
        onUploadedMaterial={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

describe("BuyerTeaserSection", () => {
  beforeEach(() => {
    mockUseMarketingMaterials.mockReset();
    uploadMarketingMaterialMutateAsync.mockReset();
    fileUploadZoneState.props = null;
    toastSuccessSpy.mockClear();
    toastErrorSpy.mockClear();
    vi.spyOn(maApi, "put").mockReset();
  });

  it("renders teaser versions and the latest distributed version", async () => {
    mockUseMarketingMaterials.mockReturnValue({
      data: [
        {
          id: "tm-1",
          transaction_id: "txn-1",
          doc_type: "TM",
          title: "Teaser v1",
          project_code: "T-001",
          status: "READY",
          error_message: null,
          source_mode: "UPLOADED",
          attachment_id: "att-1",
          parameters: null,
          file_path: null,
          file_name: "teaser-v1.pdf",
          file_size_bytes: 1024,
          quality_score: null,
          quality_status: null,
          quality_issues: null,
          slide_count: null,
          pipeline_metrics: null,
          distribution_eligible: true,
          distributed_to: [],
          distributed_at: null,
          created_by_email: "advisor@test.com",
          created_at: "2026-03-01T00:00:00Z",
          updated_at: "2026-03-01T00:00:00Z",
        },
        {
          id: "tm-2",
          transaction_id: "txn-1",
          doc_type: "TM",
          title: "Teaser v2",
          project_code: "T-002",
          status: "READY",
          error_message: null,
          source_mode: "UPLOADED",
          attachment_id: "att-2",
          parameters: null,
          file_path: null,
          file_name: "teaser-v2.pdf",
          file_size_bytes: 2048,
          quality_score: null,
          quality_status: null,
          quality_issues: null,
          slide_count: null,
          pipeline_metrics: null,
          distribution_eligible: true,
          distributed_to: ["Test Buyer"],
          distributed_at: "2026-03-20T00:00:00Z",
          created_by_email: "advisor@test.com",
          created_at: "2026-03-10T00:00:00Z",
          updated_at: "2026-03-20T00:00:00Z",
        },
      ],
    });

    renderSection();

    expect(
      await screen.findByRole("heading", { name: "Teaser" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Buyer 대상 Teaser 송부 관리")).toBeInTheDocument();
    expect(
      screen.getByText(
        "아래 버전 목록은 거래에 등록된 전역 Teaser 버전이며, 송부 상태는 현재 선택된 매수자 기준으로 표시됩니다.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("송부됨 v2")).toBeInTheDocument();
    expect(screen.getByText("2 version(s)")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getAllByText("v2").length).toBeGreaterThan(0);
    expect(screen.getByText("2026-03-20")).toBeInTheDocument();
    expect(screen.getByText("Teaser 업로드")).toBeInTheDocument();
    expect(fileUploadZoneState.props).toEqual({
      entityType: "MARKETING_MATERIAL",
      entityId: undefined,
      uploadOnly: true,
      customUpload: expect.any(Function),
    });
    expect(screen.queryByText(/\\u[a-f0-9]{4}/i)).not.toBeInTheDocument();
  });

  it("shows global teaser versions even when the current buyer is still unsent", async () => {
    mockUseMarketingMaterials.mockReturnValue({
      data: [
        {
          id: "tm-1",
          transaction_id: "txn-1",
          doc_type: "TM",
          title: "Shared teaser",
          project_code: "T-001",
          status: "READY",
          error_message: null,
          source_mode: "UPLOADED",
          attachment_id: "att-1",
          parameters: null,
          file_path: null,
          file_name: "shared-teaser.pdf",
          file_size_bytes: 1024,
          quality_score: null,
          quality_status: null,
          quality_issues: null,
          slide_count: null,
          pipeline_metrics: null,
          distribution_eligible: true,
          distributed_to: ["Other Buyer"],
          distributed_at: "2026-03-20T00:00:00Z",
          created_by_email: "advisor@test.com",
          created_at: "2026-03-10T00:00:00Z",
          updated_at: "2026-03-20T00:00:00Z",
        },
      ],
    });

    renderSection();

    expect(
      await screen.findByRole("heading", { name: "Teaser" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Test Buyer 대상 Teaser 송부 관리")).toBeInTheDocument();
    expect(screen.getByText("1 version(s)")).toBeInTheDocument();
    expect(screen.getAllByText("미송부")).toHaveLength(2);
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText("Shared teaser")).toBeInTheDocument();
  });

  it("moves teaser distribution to the selected version", async () => {
    const putSpy = vi.spyOn(maApi, "put").mockResolvedValue({
      data: {
        id: "tm-2",
      },
    } as never);

    mockUseMarketingMaterials.mockReturnValue({
      data: [
        {
          id: "tm-1",
          transaction_id: "txn-1",
          doc_type: "TM",
          title: "Teaser v1",
          project_code: null,
          status: "READY",
          error_message: null,
          source_mode: "UPLOADED",
          attachment_id: "att-1",
          parameters: null,
          file_path: null,
          file_name: "teaser-v1.pdf",
          file_size_bytes: 1024,
          quality_score: null,
          quality_status: null,
          quality_issues: null,
          slide_count: null,
          pipeline_metrics: null,
          distribution_eligible: true,
          distributed_to: ["Test Buyer"],
          distributed_at: "2026-03-15T00:00:00Z",
          created_by_email: "advisor@test.com",
          created_at: "2026-03-01T00:00:00Z",
          updated_at: "2026-03-15T00:00:00Z",
        },
        {
          id: "tm-2",
          transaction_id: "txn-1",
          doc_type: "TM",
          title: "Teaser v2",
          project_code: null,
          status: "READY",
          error_message: null,
          source_mode: "UPLOADED",
          attachment_id: "att-2",
          parameters: null,
          file_path: null,
          file_name: "teaser-v2.pdf",
          file_size_bytes: 2048,
          quality_score: null,
          quality_status: null,
          quality_issues: null,
          slide_count: null,
          pipeline_metrics: null,
          distribution_eligible: true,
          distributed_to: [],
          distributed_at: null,
          created_by_email: "advisor@test.com",
          created_at: "2026-03-10T00:00:00Z",
          updated_at: "2026-03-10T00:00:00Z",
        },
      ],
    });

    renderSection();

    const versionCell = await screen.findByText("v2");
    const row = versionCell.closest("tr");
    expect(row).not.toBeNull();

    const buttons = within(row as HTMLElement).getAllByRole("button");
    fireEvent.click(buttons[buttons.length - 1]);

    await waitFor(() => {
      expect(putSpy).toHaveBeenCalledTimes(2);
    });

    const payloads = putSpy.mock.calls.map(([url, body]) => ({ url, body }));
    expect(payloads).toEqual(
      expect.arrayContaining([
        {
          url: "/transactions/txn-1/marketing-materials/tm-1/distribute",
          body: expect.objectContaining({
            distributed_to: [],
          }),
        },
        {
          url: "/transactions/txn-1/marketing-materials/tm-2/distribute",
          body: expect.objectContaining({
            distributed_to: ["Test Buyer"],
            distributed_at: expect.any(String),
          }),
        },
      ]),
    );
    expect(toastSuccessSpy).toHaveBeenCalled();
  });

  it("renders only the upload zone when no teaser exists", async () => {
    mockUseMarketingMaterials.mockReturnValue({
      data: [],
    });

    renderSection();

    expect(
      await screen.findByRole("heading", { name: "Teaser" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Test Buyer 대상 Teaser 송부 관리"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("0 version(s)")).not.toBeInTheDocument();
    expect(screen.getByText("등록된 Teaser 없음")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Teaser 자료를 업로드하면 매수자별 송부 버전과 송부 여부를 여기서 관리할 수 있습니다.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Teaser PDF/PPTX 파일을 여기에 드롭하거나 클릭하여 추가하세요. PDF 업로드는 OCR 검토를 열고, 검토 확정 후 TM 자료로 연결할 수 있습니다.",
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByTestId("file-upload-zone")).getByText("false"),
    ).toBeInTheDocument();
    expect(fileUploadZoneState.props).toEqual({
      entityType: "MARKETING_MATERIAL",
      entityId: undefined,
      uploadOnly: true,
      customUpload: expect.any(Function),
    });
    expect(screen.queryByText(/\\u[a-f0-9]{4}/i)).not.toBeInTheDocument();
  });

  it("uploads teaser files through the uploaded marketing material endpoint", async () => {
    const onUploadedMaterial = vi.fn();
    uploadMarketingMaterialMutateAsync.mockResolvedValue({
      id: "tm-1",
      transaction_id: "txn-1",
      doc_type: "TM",
      title: "buyer teaser",
      project_code: null,
      status: "READY",
      error_message: null,
      source_mode: "UPLOADED",
      attachment_id: "att-1",
      parameters: null,
      file_path: null,
      file_name: "buyer-teaser.pdf",
      file_size_bytes: 1024,
      quality_score: null,
      quality_status: "SKIPPED",
      quality_issues: null,
      slide_count: null,
      pipeline_metrics: null,
      distribution_eligible: true,
      distributed_to: ["Test Buyer"],
      distributed_at: "2026-03-20T00:00:00Z",
      created_by_email: "advisor@test.com",
      created_at: "2026-03-10T00:00:00Z",
      updated_at: "2026-03-20T00:00:00Z",
    });
    mockUseMarketingMaterials.mockReturnValue({ data: [] });

    const queryClient = createTestQueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BuyerTeaserSection
          txnId="txn-1"
          canWrite
          buyer={{
            id: "buyer-1",
            transaction_id: "txn-1",
            company_name: "Test Buyer",
            contact_name: "Hong",
            contact_email: null,
            contact_phone: null,
            buyer_type: "STRATEGIC",
            status: "CONTACTED",
            tier: "TIER_1",
            deal_role: "SOLE_BUYER",
            is_short_listed: false,
            corp_code: null,
            ioi_value: null,
            ioi_date: null,
            loi_value: null,
            loi_date: null,
            final_offer_value: null,
            rejection_reason: null,
            notes: null,
            extra_data: null,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          }}
          onUploadedMaterial={onUploadedMaterial}
        />
      </QueryClientProvider>,
    );

    const file = new File(["pdf-content"], "buyer-teaser.pdf", {
      type: "application/pdf",
    });
    await fileUploadZoneState.props?.customUpload?.([file]);

    expect(uploadMarketingMaterialMutateAsync).toHaveBeenCalledWith({
      file,
      docType: "TM",
      title: "buyer-teaser",
      distributedTo: ["Test Buyer"],
      distributedAt: expect.any(String),
    });
    expect(onUploadedMaterial).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "tm-1",
        attachment_id: "att-1",
      }),
      file,
    );
  });
});
