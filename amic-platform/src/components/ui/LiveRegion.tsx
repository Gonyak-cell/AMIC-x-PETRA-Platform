import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

interface LiveRegionContextValue {
  announce: (message: string, assertive?: boolean) => void;
}

const LiveRegionContext = createContext<LiveRegionContextValue | null>(null);

export interface LiveRegionProviderProps {
  children: ReactNode;
}

/**
 * LiveRegion Provider - 스크린 리더를 위한 동적 알림
 *
 * @example
 * // 사용법
 * const { announce } = useLiveAnnounce();
 * announce("Adjustment approved successfully");
 * announce("Error: Failed to save", true); // assertive
 */
export function LiveRegionProvider({ children }: LiveRegionProviderProps) {
  const [politeMessage, setPoliteMessage] = useState("");
  const [assertiveMessage, setAssertiveMessage] = useState("");

  const announce = useCallback((message: string, assertive = false) => {
    if (assertive) {
      // Clear then set to trigger re-announcement
      setAssertiveMessage("");
      setTimeout(() => setAssertiveMessage(message), 100);
    } else {
      setPoliteMessage("");
      setTimeout(() => setPoliteMessage(message), 100);
    }
  }, []);

  return (
    <LiveRegionContext.Provider value={{ announce }}>
      {children}
      {/* Polite region - waits for user to finish current task */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {politeMessage}
      </div>
      {/* Assertive region - interrupts immediately */}
      <div
        aria-live="assertive"
        aria-atomic="true"
        className="sr-only"
      >
        {assertiveMessage}
      </div>
    </LiveRegionContext.Provider>
  );
}

/**
 * Hook to announce messages to screen readers
 *
 * @example
 * const { announce } = useLiveAnnounce();
 * announce("Data saved successfully"); // polite
 * announce("Error: Connection lost", true); // assertive (immediate)
 */
export function useLiveAnnounce() {
  const context = useContext(LiveRegionContext);
  if (!context) {
    // Fallback if not wrapped in provider - no-op
    return {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      announce: (_message: string, _assertive?: boolean) => {
        // No-op when provider is missing
      },
    };
  }
  return context;
}
