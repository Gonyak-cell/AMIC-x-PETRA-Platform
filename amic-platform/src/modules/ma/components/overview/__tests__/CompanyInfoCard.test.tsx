import { describe, expect, it, beforeEach } from "vitest";
import { http, HttpResponse } from "msw";

import CompanyInfoCard from "@/modules/ma/components/overview/CompanyInfoCard";
import type { Transaction } from "@/modules/ma/types/transaction";
import { server } from "@/test/mocks/server";
import {
  renderWithProviders,
  screen,
  userEvent,
  waitFor,
} from "@/test/test-utils";

const baseTxn: Transaction = {
  id: "txn-1",
  code_name: "SE26-TST-01",
  name: "Project Guided",
  deal_type: "SE",
  side: "SELL",
  phase: "ENGAGEMENT",
  status: "DRAFT",
  target_company_name: "Target Co",
  target_corp_code: null,
  client_name: "Client Co",
  estimated_deal_value: null,
  currency: "KRW",
  deal_structure: null,
  investment_type: null,
  industry: null,
  lead_advisor_email: "lead@amic.kr",
  deal_captain_email: null,
  target_close_date: null,
  sale_process: null,
  control_transfer: null,
  target_stake: null,
  new_share_ratio: null,
  old_share_ratio: null,
  valuation_basis: null,
  cross_border: null,
  target_buyer_types: null,
  exclusivity: null,
  exclusivity_deadline: null,
  fdd_deal_id: null,
  im_document_id: null,
  notes: null,
  corporate_info: null,
  financial_summary: null,
  is_deleted: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("CompanyInfoCard", () => {
  beforeEach(() => {
    server.resetHandlers();
  });

  it("keeps next-step disabled until required manual fields are saved", async () => {
    const user = userEvent.setup();
    const patchBodies: Array<Record<string, unknown>> = [];
    let patchedTxn = { ...baseTxn };

    server.use(
      http.get("*/api/ma/transactions/:txnId/extractions", () =>
        HttpResponse.json({ items: [], total: 0 }),
      ),
      http.patch("*/api/ma/transactions/:txnId", async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        patchBodies.push(body);
        patchedTxn = {
          ...patchedTxn,
          corporate_info: (body.corporate_info ?? null) as Record<
            string,
            unknown
          > | null,
          updated_at: "2026-02-01T00:00:00Z",
        };
        return HttpResponse.json(patchedTxn);
      }),
    );

    renderWithProviders(<CompanyInfoCard txn={baseTxn} canWrite />, {
      initialEntries: ["/ma/transactions/txn-1?setup=company-info"],
    });

    const nextButton = screen.getByRole("button", { name: "다음 단계" });
    expect(nextButton).toBeDisabled();

    await user.type(screen.getByLabelText("대표이사"), "홍길동");
    await user.type(
      screen.getByLabelText("사업자등록번호"),
      "123-45-67890",
    );
    await user.type(
      screen.getByLabelText("법인등록번호"),
      "110111-1234567",
    );

    await user.click(screen.getByRole("button", { name: "회사 정보 저장" }));

    await waitFor(() => {
      expect(patchBodies).toHaveLength(1);
    });

    expect(patchBodies[0]).toMatchObject({
      corporate_info: {
        company_name: "Target Co",
        representative_name: "홍길동",
        business_registration_number: "123-45-67890",
        corporate_registration_number: "110111-1234567",
      },
    });

    await waitFor(() => {
      expect(nextButton).toBeEnabled();
    });
  });
});
