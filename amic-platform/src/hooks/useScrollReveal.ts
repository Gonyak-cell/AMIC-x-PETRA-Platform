import type { RefObject } from "react";
import { gsap, ScrollTrigger, useGSAP } from "@/lib/gsap";

interface ScrollRevealOptions {
  /** Stagger delay between children (default: 0.08) */
  stagger?: number;
  /** Y offset to animate from (default: 30) */
  y?: number;
  /** Animation duration (default: 0.6) */
  duration?: number;
  /** ScrollTrigger start position (default: "top 85%") */
  start?: string;
}

/**
 * Reveals child elements with a staggered fade-in-up when scrolled into view.
 */
export function useScrollReveal(
  ref: RefObject<HTMLElement | null>,
  options?: ScrollRevealOptions,
  deps?: unknown[],
) {
  useGSAP(
    () => {
      const el = ref.current;
      if (!el || !el.children.length) return;

      gsap.fromTo(
        Array.from(el.children),
        {
          y: options?.y ?? 30,
          opacity: 0,
        },
        {
          y: 0,
          opacity: 1,
          stagger: options?.stagger ?? 0.08,
          duration: options?.duration ?? 0.6,
          ease: "power2.out",
          scrollTrigger: {
            trigger: el,
            start: options?.start ?? "top 85%",
            toggleActions: "play none none none",
          },
        },
      );

      return () => {
        ScrollTrigger.getAll()
          .filter((t) => t.trigger === el)
          .forEach((t) => t.kill());
      };
    },
    { scope: ref, ...(deps ? { dependencies: deps } : {}) },
  );
}
