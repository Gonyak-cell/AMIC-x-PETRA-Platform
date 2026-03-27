import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import BuyerNdaExecutionPanel from "../BuyerNdaExecutionPanel";
import type { BuyerCandidate } from "@/modules/ma/types/buyer";
import type { NDA } from "@/modules/ma/types/nda";

const updateNdaMutateAsync = vi.fn();
const deleteMarkupMutate = vi.fn();

vi.mock("@/modules/ma/hooks/useNdas", () => ({
  useCreateNda: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateNda: () => ({
    mutateAsync: updateNdaMutateAsync,
    isPending: false,
  }),
}));

vi.mock("@/modules/ma/hooks/useNdaMarkups", () => ({
  useNdaMarkups: () => ({
    data: {
      items: [
        {
          id: "markup-1",
          nda_id: "nda-1",
          version_label: "v1",
          version_number: 1,
          version_date: "2026-03-28",
          source_party: null,
          markup_type: null,
          file_name: "nda-v1.pdf",
          file_size_bytes: 1024,
          changes_summary: "signed-ready",
          key_changes: null,
          redline_issues_count: null,
          base_version_id: null,
          created_by_email: "advisor@test.com",
          created_at: "2026-03-28T00:00:00Z",
          updated_at: "2026-03-28T00:00:00Z",
          has_file: true,
          has_redline: false,
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    },
    isLoading: false,
    isError: false,
  }),
  useDeleteNdaMarkup: () => ({
    mutate: deleteMarkupMutate,
  }),
  getNdaMarkupDownloadUrl: () => "#",
}));

const buyer: BuyerCandidate = {
  id: "buyer-1",
  transaction_id: "txn-1",
  company_name: "ATU파트너스",
  contact_name: "홍길동",
  contact_email: null,
  contact_phone: null,
  buyer_type: "FINANCIAL_SPONSOR",
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
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-01T00:00:00Z",
};

const nda: NDA = {
  id: "nda-1",
  transaction_id: "txn-1",
  party_type: "BUYER",
  buyer_candidate_id: "buyer-1",
  nda_type: "MUTUAL",
  status: "DRAFT",
  sent_at: null,
  signed_at: null,
  expires_at: null,
  document_url: null,
  counterparty_name: "ATU파트너스",
  jurisdiction: null,
  confidentiality_period_months: null,
  notes: null,
  created_at: "2026-03-01T00:00:00Z",
  updated_at: "2026-03-01T00:00:00Z",
};

describe("BuyerNdaExecutionPanel", () => {
  beforeEach(() => {
    updateNdaMutateAsync.mockReset();
    deleteMarkupMutate.mockReset();
    updateNdaMutateAsync.mockResolvedValue({
      ...nda,
      status: "SIGNED",
      signed_at: "2026-03-28",
      updated_at: "2026-03-28T10:00:00Z",
    });
  });

  it("syncs NDA signing into buyer and NDA caches before closing", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false, gcTime: Infinity, staleTime: Infinity },
        mutations: { retry: false },
      },
    });

    queryClient.setQueryData(["ma", "transactions", "txn-1", "buyers"], [buyer]);
    queryClient.setQueryData(
      ["ma", "transactions", "txn-1", "ndas", { partyType: "BUYER" }],
      [nda],
    );
    queryClient.setQueryData(
      [
        "ma",
        "transactions",
        "txn-1",
        "ndas",
        { buyerId: "buyer-1", partyType: "BUYER" },
      ],
      [nda],
    );

    render(
      <QueryClientProvider client={queryClient}>
        <BuyerNdaExecutionPanel
          open
          onClose={onClose}
          txnId="txn-1"
          buyer={buyer}
          nda={nda}
          canWrite
        />
      </QueryClientProvider>,
    );

    await user.click(await screen.findByRole("button", { name: "날인" }));

    await waitFor(() => {
      expect(updateNdaMutateAsync).toHaveBeenCalledWith({
        ndaId: "nda-1",
        body: expect.objectContaining({
          status: "SIGNED",
          signed_at: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/),
        }),
      });
    });

    await waitFor(() => {
      expect(onClose).toHaveBeenCalled();
    });

    expect(
      queryClient.getQueryData<BuyerCandidate[]>([
        "ma",
        "transactions",
        "txn-1",
        "buyers",
      ]),
    ).toEqual([
      expect.objectContaining({
        id: "buyer-1",
        status: "NDA_SIGNED",
        updated_at: "2026-03-28T10:00:00Z",
      }),
    ]);

    expect(
      queryClient.getQueryData<NDA[]>([
        "ma",
        "transactions",
        "txn-1",
        "ndas",
        { partyType: "BUYER" },
      ]),
    ).toEqual([
      expect.objectContaining({
        id: "nda-1",
        status: "SIGNED",
        signed_at: "2026-03-28",
      }),
    ]);
  });
});
