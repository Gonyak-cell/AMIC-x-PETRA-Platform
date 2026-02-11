import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./mocks/server";

// MSW lifecycle
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
  localStorage.clear();
});
afterAll(() => server.close());

// Mock HTMLDialogElement methods (jsdom doesn't implement them)
HTMLDialogElement.prototype.showModal =
  HTMLDialogElement.prototype.showModal ||
  function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
HTMLDialogElement.prototype.close =
  HTMLDialogElement.prototype.close ||
  function (this: HTMLDialogElement) {
    this.removeAttribute("open");
  };

// Mock window.matchMedia (Tailwind responsive)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
