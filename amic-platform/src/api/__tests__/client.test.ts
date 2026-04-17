/**
 * API Client Interceptor 회귀 테스트
 *
 * client.ts의 401 auto-refresh, force-logout, 에러 전파 로직을 검증한다.
 * 이 테스트가 통과하면 코드 수정 후 인증 관련 회귀 오류가 방지된다.
 */
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import {
  createApiClient,
  getAuthApiForPath,
  resolveAuthApiBasePath,
  shouldSkipAuthBootstrapPath,
} from "@/api/client";
import { AUTH_LOGOUT_EVENT } from "@/lib/auth-events";

const testClient = createApiClient("/api/fdd");

describe("API Client — 401 Auto-Refresh", () => {
  it("401 응답 시 자동으로 refresh 후 재시도한다", async () => {
    let callCount = 0;
    server.use(
      http.get("*/api/fdd/test-endpoint", () => {
        callCount++;
        if (callCount === 1) {
          return new HttpResponse(null, { status: 401 });
        }
        return HttpResponse.json({ ok: true });
      }),
      http.post("*/api/fdd/auth/refresh", () => {
        return HttpResponse.json({ message: "refreshed" });
      }),
    );

    const { data } = await testClient.get("/test-endpoint");
    expect(data).toEqual({ ok: true });
    expect(callCount).toBe(2);
  });

  it("refresh도 401이면 force-logout 이벤트를 발행한다", async () => {
    const logoutSpy = vi.fn();
    window.addEventListener(AUTH_LOGOUT_EVENT, logoutSpy);

    server.use(
      http.get("*/api/fdd/test-endpoint", () => {
        return new HttpResponse(null, { status: 401 });
      }),
      http.post("*/api/fdd/auth/refresh", () => {
        return new HttpResponse(null, { status: 401 });
      }),
    );

    await expect(testClient.get("/test-endpoint")).rejects.toThrow();
    expect(logoutSpy).toHaveBeenCalledTimes(1);

    window.removeEventListener(AUTH_LOGOUT_EVENT, logoutSpy);
  });

  it("/auth/login 401은 retry하지 않는다", async () => {
    let refreshCalled = false;
    server.use(
      http.post("*/api/fdd/auth/login", () => {
        return HttpResponse.json(
          { detail: "Invalid credentials" },
          { status: 401 },
        );
      }),
      http.post("*/api/fdd/auth/refresh", () => {
        refreshCalled = true;
        return HttpResponse.json({ message: "refreshed" });
      }),
    );

    await expect(
      testClient.post("/auth/login", { email: "x", password: "y" }),
    ).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(refreshCalled).toBe(false);
  });

  it("/auth/me 401은 retry하지 않는다", async () => {
    let refreshCalled = false;
    server.use(
      http.get("*/api/fdd/auth/me", () => {
        return new HttpResponse(null, { status: 401 });
      }),
      http.post("*/api/fdd/auth/refresh", () => {
        refreshCalled = true;
        return HttpResponse.json({ message: "refreshed" });
      }),
    );

    await expect(testClient.get("/auth/me")).rejects.toMatchObject({
      response: { status: 401 },
    });
    expect(refreshCalled).toBe(false);
  });
});

describe("API Client — 500 Server Error", () => {
  it("500 에러는 retry 없이 그대로 전파한다", async () => {
    let callCount = 0;
    server.use(
      http.get("*/api/fdd/test-endpoint", () => {
        callCount++;
        return HttpResponse.json(
          { detail: "Internal server error" },
          { status: 500 },
        );
      }),
    );

    await expect(testClient.get("/test-endpoint")).rejects.toMatchObject({
      response: { status: 500 },
    });
    expect(callCount).toBe(1);
  });

  it("403 에러는 retry 없이 전파한다", async () => {
    server.use(
      http.get("*/api/fdd/test-endpoint", () => {
        return HttpResponse.json({ detail: "Forbidden" }, { status: 403 });
      }),
    );

    await expect(testClient.get("/test-endpoint")).rejects.toMatchObject({
      response: { status: 403 },
    });
  });
});

describe("API Client — 기본 설정", () => {
  it("timeout이 30초로 설정되어 있다", () => {
    expect(testClient.defaults.timeout).toBe(30_000);
  });

  it("withCredentials가 true이다 (쿠키 전송)", () => {
    expect(testClient.defaults.withCredentials).toBe(true);
  });

  it("Content-Type이 application/json이다", () => {
    expect(String(testClient.defaults.headers["Content-Type"])).toContain(
      "application/json",
    );
  });
});

describe("API Client route-aware auth selection", () => {
  it("resolves MA auth for MA and shared routes", () => {
    expect(resolveAuthApiBasePath("/ma/transactions")).toBe("/api/ma");
    expect(resolveAuthApiBasePath("/login")).toBe("/api/ma");
    expect(resolveAuthApiBasePath("/")).toBe("/api/ma");
  });

  it("resolves dedicated module auth bases", () => {
    expect(resolveAuthApiBasePath("/fdd/deals")).toBe("/api/fdd");
    expect(resolveAuthApiBasePath("/kiis/dashboard")).toBe("/api/kiis");
    expect(resolveAuthApiBasePath("/im/documents")).toBe("/api/im");
  });

  it("skips auth bootstrap only on anonymous-friendly routes", () => {
    expect(shouldSkipAuthBootstrapPath("/login")).toBe(true);
    expect(shouldSkipAuthBootstrapPath("/invite/accept")).toBe(true);
    expect(shouldSkipAuthBootstrapPath("/ma/transactions")).toBe(false);
  });

  it("returns auth clients with route-matched base URLs", () => {
    expect(getAuthApiForPath("/ma/transactions").defaults.baseURL).toBe(
      "/api/ma",
    );
    expect(getAuthApiForPath("/fdd/deals").defaults.baseURL).toBe("/api/fdd");
  });
});
