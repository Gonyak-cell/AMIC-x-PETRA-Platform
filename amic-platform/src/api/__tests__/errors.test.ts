import { describe, expect, it } from "vitest";
import type { AxiosError } from "axios";
import { extractApiError } from "../errors";

function makeAxiosError(
  overrides: Partial<AxiosError<{ detail?: string | Array<{ msg: string }> } | string>>,
): AxiosError<{ detail?: string | Array<{ msg: string }> } | string> {
  return {
    name: "AxiosError",
    message: "Request failed",
    isAxiosError: true,
    toJSON: () => ({}),
    ...overrides,
  } as AxiosError<{ detail?: string | Array<{ msg: string }> } | string>;
}

describe("extractApiError", () => {
  it("returns detail string when present", () => {
    const err = makeAxiosError({
      response: {
        status: 400,
        statusText: "Bad Request",
        headers: {},
        config: {} as never,
        data: { detail: "Invalid payload" },
      },
    });

    expect(extractApiError(err, "Fallback")).toBe("Invalid payload");
  });

  it("returns joined validation messages", () => {
    const err = makeAxiosError({
      response: {
        status: 422,
        statusText: "Unprocessable Entity",
        headers: {},
        config: {} as never,
        data: { detail: [{ msg: "Field required" }, { msg: "Invalid email" }] },
      },
    });

    expect(extractApiError(err, "Fallback")).toBe(
      "Field required, Invalid email",
    );
  });

  it("appends HTTP status for 5xx responses without usable detail", () => {
    const err = makeAxiosError({
      response: {
        status: 500,
        statusText: "Internal Server Error",
        headers: {},
        config: {} as never,
        data: "Internal Server Error",
      },
    });

    expect(extractApiError(err, "거래 생성 중 오류가 발생했습니다.")).toBe(
      "거래 생성 중 오류가 발생했습니다. (HTTP 500)",
    );
  });
});
