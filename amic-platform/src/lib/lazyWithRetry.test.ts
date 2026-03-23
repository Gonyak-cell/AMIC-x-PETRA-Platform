import { describe, expect, it, vi, beforeEach } from "vitest";

import {
  isRecoverableChunkLoadError,
  loadModuleWithRetry,
} from "./lazyWithRetry";

const RETRY_KEY = "lazy-retry:dev:modules/ma/components/rfi/RFIPanel";

describe("lazyWithRetry", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("detects recoverable chunk load errors", () => {
    expect(
      isRecoverableChunkLoadError(
        new TypeError("Failed to fetch dynamically imported module"),
      ),
    ).toBe(true);
    expect(
      isRecoverableChunkLoadError(new Error("ChunkLoadError: Loading chunk 7 failed")),
    ).toBe(true);
    expect(
      isRecoverableChunkLoadError(new Error("Request failed with status code 500")),
    ).toBe(false);
  });

  it("reloads once on the first chunk load failure", async () => {
    const reload = vi.fn();

    void loadModuleWithRetry(
      async () => {
        throw new TypeError("Failed to fetch dynamically imported module");
      },
      "modules/ma/components/rfi/RFIPanel",
      reload,
    );

    await Promise.resolve();

    expect(reload).toHaveBeenCalledTimes(1);
    expect(window.sessionStorage.getItem(RETRY_KEY)).toBe("true");
  });

  it("throws after a repeated chunk load failure instead of reloading forever", async () => {
    const error = new TypeError("Failed to fetch dynamically imported module");
    const reload = vi.fn();
    window.sessionStorage.setItem(RETRY_KEY, "true");

    await expect(
      loadModuleWithRetry(
        async () => {
          throw error;
        },
        "modules/ma/components/rfi/RFIPanel",
        reload,
      ),
    ).rejects.toBe(error);

    expect(reload).not.toHaveBeenCalled();
    expect(window.sessionStorage.getItem(RETRY_KEY)).toBeNull();
  });

  it("clears the retry marker after a successful import", async () => {
    window.sessionStorage.setItem(RETRY_KEY, "true");

    const module = await loadModuleWithRetry(
      async () => ({
        default: () => null,
      }),
      "modules/ma/components/rfi/RFIPanel",
      vi.fn(),
    );

    expect(module.default).toBeTypeOf("function");
    expect(window.sessionStorage.getItem(RETRY_KEY)).toBeNull();
  });
});
