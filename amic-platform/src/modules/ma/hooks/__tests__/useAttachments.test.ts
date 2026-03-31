import { describe, expect, it } from "vitest";

import {
  buildAttachmentUploadErrorMessage,
  shouldRetryAttachmentUpload,
} from "../useAttachments";

describe("useAttachments helpers", () => {
  it("retries transient dev proxy failures", () => {
    const err = {
      response: {
        status: 500,
        data: "Error: connect ECONNREFUSED 127.0.0.1:8003",
      },
    };

    expect(shouldRetryAttachmentUpload(err, true)).toBe(true);
    expect(shouldRetryAttachmentUpload(err, false)).toBe(false);
  });

  it("does not retry normal validation failures", () => {
    const err = {
      response: {
        status: 400,
        data: {
          detail: "허용하지 않는 파일 형식입니다.",
        },
      },
    };

    expect(shouldRetryAttachmentUpload(err, true)).toBe(false);
  });

  it("shows a backend hint for dev proxy connection failures", () => {
    const err = {
      response: {
        status: 500,
        data: "Error: connect ECONNREFUSED 127.0.0.1:8003",
      },
    };

    expect(
      buildAttachmentUploadErrorMessage(
        err,
        true,
        "http://127.0.0.1:8003",
      ),
    ).toContain("개발 MA 백엔드");
  });

  it("keeps backend detail for normal API failures", () => {
    const err = {
      response: {
        status: 400,
        data: {
          detail: "허용하지 않는 파일 형식입니다.",
        },
      },
    };

    expect(buildAttachmentUploadErrorMessage(err, true)).toBe(
      "허용하지 않는 파일 형식입니다.",
    );
  });
});
