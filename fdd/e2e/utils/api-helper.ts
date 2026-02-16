/**
 * API helper for direct backend calls in E2E tests.
 * Bypasses the UI for test data setup and teardown.
 */

import type { APIRequestContext } from "@playwright/test";

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000/api/v1";

export interface ApiHelper {
  login(email: string, password: string): Promise<string>;
  createDeal(token: string, deal: DealCreatePayload): Promise<DealResponse>;
  deleteDeal(token: string, dealId: string): Promise<void>;
  uploadFile(
    token: string,
    dealId: string,
    filePath: string,
  ): Promise<UploadResponse>;
  confirmType(
    token: string,
    dealId: string,
    uploadId: string,
    confirmedType: string,
  ): Promise<void>;
  ingest(
    token: string,
    dealId: string,
    uploadId: string,
  ): Promise<void>;
}

export interface DealCreatePayload {
  name: string;
  deal_type: "COMPLETION_ACCOUNTS" | "LOCKED_BOX";
  base_currency?: string;
  reference_date: string;
  period_start: string;
  period_end: string;
}

export interface DealResponse {
  id: string;
  name: string;
  deal_type: string;
  status: string;
}

export interface UploadResponse {
  id: string;
  original_filename: string;
  detected_type: string | null;
  status: string;
}

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export function createApiHelper(request: APIRequestContext): ApiHelper {
  return {
    async login(email: string, password: string): Promise<string> {
      const res = await request.post(`${API_BASE}/auth/login`, {
        data: { email, password },
      });
      if (!res.ok()) {
        throw new Error(`Login failed: ${res.status()}`);
      }
      const body = await res.json();
      return body.access_token;
    },

    async createDeal(
      token: string,
      deal: DealCreatePayload,
    ): Promise<DealResponse> {
      const res = await request.post(`${API_BASE}/deals`, {
        headers: authHeader(token),
        data: deal,
      });
      if (!res.ok()) {
        throw new Error(`Create deal failed: ${res.status()}`);
      }
      return res.json();
    },

    async deleteDeal(token: string, dealId: string): Promise<void> {
      await request.delete(`${API_BASE}/deals/${dealId}`, {
        headers: authHeader(token),
      });
    },

    async uploadFile(
      token: string,
      dealId: string,
      filePath: string,
    ): Promise<UploadResponse> {
      const res = await request.post(
        `${API_BASE}/deals/${dealId}/uploads`,
        {
          headers: authHeader(token),
          multipart: {
            file: {
              name: filePath.split(/[\\/]/).pop()!,
              mimeType:
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
              buffer: require("fs").readFileSync(filePath),
            },
          },
        },
      );
      if (!res.ok()) {
        throw new Error(`Upload failed: ${res.status()}`);
      }
      return res.json();
    },

    async confirmType(
      token: string,
      dealId: string,
      uploadId: string,
      confirmedType: string,
    ): Promise<void> {
      const res = await request.put(
        `${API_BASE}/deals/${dealId}/uploads/${uploadId}/confirm-type`,
        {
          headers: authHeader(token),
          data: { confirmed_type: confirmedType },
        },
      );
      if (!res.ok()) {
        throw new Error(`Confirm type failed: ${res.status()}`);
      }
    },

    async ingest(
      token: string,
      dealId: string,
      uploadId: string,
    ): Promise<void> {
      const res = await request.post(
        `${API_BASE}/deals/${dealId}/uploads/${uploadId}/ingest`,
        {
          headers: authHeader(token),
        },
      );
      if (!res.ok()) {
        throw new Error(`Ingest failed: ${res.status()}`);
      }
    },
  };
}
