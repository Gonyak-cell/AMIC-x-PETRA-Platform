import { useState, useCallback, useEffect } from "react";
import type { OnboardingStep } from "./steps";

const STORAGE_PREFIX = "client-onboarding";

function getStorageKey(userId: string, txnId: string): string {
  return `${STORAGE_PREFIX}:${userId}:${txnId}:completed`;
}

export function useOnboarding(
  userId: string | undefined,
  txnId: string,
  steps: OnboardingStep[],
) {
  const [currentStep, setCurrentStep] = useState(-1);
  const [isCompleted, setIsCompleted] = useState(true); // default true to prevent flash
  const [activeSteps, setActiveSteps] = useState<OnboardingStep[]>([]);

  // Filter steps to only those with existing DOM targets
  // Retry multiple times to wait for lazy-loaded components
  useEffect(() => {
    let attempt = 0;
    const maxAttempts = 6;
    const interval = 500;

    const tryFilter = () => {
      const filtered = steps.filter(
        (s) => document.querySelector(s.targetSelector) !== null,
      );
      setActiveSteps(filtered);
      attempt++;
      if (filtered.length < steps.length && attempt < maxAttempts) {
        timerId = setTimeout(tryFilter, interval);
      }
    };

    let timerId = setTimeout(tryFilter, interval);
    return () => clearTimeout(timerId);
  }, [steps]);

  // Check completion state
  useEffect(() => {
    if (!userId || activeSteps.length === 0) return;
    const completed =
      localStorage.getItem(getStorageKey(userId, txnId)) === "true";
    setIsCompleted(completed);
    if (!completed) setCurrentStep(0);
  }, [userId, txnId, activeSteps.length]);

  const isActive = currentStep >= 0 && currentStep < activeSteps.length;
  const step = isActive ? activeSteps[currentStep] : null;

  const next = useCallback(() => {
    if (currentStep < activeSteps.length - 1) {
      setCurrentStep((s) => s + 1);
    } else {
      if (userId) localStorage.setItem(getStorageKey(userId, txnId), "true");
      setIsCompleted(true);
      setCurrentStep(-1);
    }
  }, [currentStep, activeSteps.length, userId, txnId]);

  const prev = useCallback(() => {
    if (currentStep > 0) setCurrentStep((s) => s - 1);
  }, [currentStep]);

  const skip = useCallback(() => {
    if (userId) localStorage.setItem(getStorageKey(userId, txnId), "true");
    setIsCompleted(true);
    setCurrentStep(-1);
  }, [userId, txnId]);

  const restart = useCallback(() => {
    setIsCompleted(false);
    setCurrentStep(0);
  }, []);

  return {
    isActive,
    isCompleted,
    currentStep,
    step,
    totalSteps: activeSteps.length,
    next,
    prev,
    skip,
    restart,
  };
}
