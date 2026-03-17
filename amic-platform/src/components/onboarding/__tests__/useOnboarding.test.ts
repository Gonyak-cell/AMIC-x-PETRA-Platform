import { renderHook, act } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { useOnboarding } from "../useOnboarding";
import type { OnboardingStep } from "../steps";

const TEST_STEPS: OnboardingStep[] = [
  {
    id: "step-a",
    targetSelector: "[data-onboarding='a']",
    title: "A",
    description: "Desc A",
    placement: "bottom",
  },
  {
    id: "step-b",
    targetSelector: "[data-onboarding='b']",
    title: "B",
    description: "Desc B",
    placement: "top",
  },
  {
    id: "step-c",
    targetSelector: "[data-onboarding='c']",
    title: "C",
    description: "Desc C",
    placement: "bottom",
  },
];

function addOnboardingTargets(ids: string[]) {
  ids.forEach((id) => {
    const el = document.createElement("div");
    el.setAttribute("data-onboarding", id);
    document.body.appendChild(el);
  });
}

function clearOnboardingTargets() {
  document.querySelectorAll("[data-onboarding]").forEach((el) => el.remove());
}

describe("useOnboarding", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
    addOnboardingTargets(["a", "b", "c"]);
  });

  afterEach(() => {
    vi.useRealTimers();
    clearOnboardingTargets();
  });

  it("localStorage 비어 있음 → step 0 시작", () => {
    const { result } = renderHook(() =>
      useOnboarding("user-1", "txn-1", TEST_STEPS),
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    expect(result.current.isActive).toBe(true);
    expect(result.current.currentStep).toBe(0);
    expect(result.current.step?.id).toBe("step-a");
  });

  it("next 마지막까지 → 완료 key 저장", () => {
    const { result } = renderHook(() =>
      useOnboarding("user-1", "txn-1", TEST_STEPS),
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    // a → b
    act(() => {
      result.current.next();
    });
    // b → c
    act(() => {
      result.current.next();
    });
    // c → complete
    act(() => {
      result.current.next();
    });

    expect(result.current.isCompleted).toBe(true);
    expect(result.current.isActive).toBe(false);
    expect(
      localStorage.getItem("client-onboarding:user-1:txn-1:completed"),
    ).toBe("true");
  });

  it("skip → 완료 key 저장", () => {
    const { result } = renderHook(() =>
      useOnboarding("user-1", "txn-1", TEST_STEPS),
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    act(() => {
      result.current.skip();
    });

    expect(result.current.isCompleted).toBe(true);
    expect(result.current.isActive).toBe(false);
    expect(
      localStorage.getItem("client-onboarding:user-1:txn-1:completed"),
    ).toBe("true");
  });

  it("restart → 다시 step 0", () => {
    localStorage.setItem("client-onboarding:user-1:txn-1:completed", "true");

    const { result } = renderHook(() =>
      useOnboarding("user-1", "txn-1", TEST_STEPS),
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    // 완료 상태로 시작
    expect(result.current.isActive).toBe(false);

    act(() => {
      result.current.restart();
    });

    expect(result.current.currentStep).toBe(0);
    expect(result.current.isActive).toBe(true);
  });

  it("txnId가 다르면 다른 key", () => {
    // txn-1 완료 처리
    localStorage.setItem("client-onboarding:user-1:txn-1:completed", "true");

    // txn-2로 훅 렌더링
    const { result } = renderHook(() =>
      useOnboarding("user-1", "txn-2", TEST_STEPS),
    );

    act(() => {
      vi.advanceTimersByTime(600);
    });

    // txn-2는 완료되지 않았으므로 자동 시작
    expect(result.current.isCompleted).toBe(false);
    expect(result.current.isActive).toBe(true);
    expect(result.current.currentStep).toBe(0);
  });
});
