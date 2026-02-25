import { useRef, useCallback } from "react";
import { gsap } from "@/lib/gsap";

/**
 * Adds a subtle 3D tilt effect to an element on mouse move.
 * Returns event handlers to attach to the element.
 */
export function useTilt(maxDeg = 2) {
  const ref = useRef<HTMLElement | null>(null);

  const onMouseMove = useCallback(
    (e: React.MouseEvent<HTMLElement>) => {
      const el = ref.current ?? e.currentTarget;
      ref.current = el;
      const rect = el.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width - 0.5; // -0.5 to 0.5
      const y = (e.clientY - rect.top) / rect.height - 0.5;

      gsap.to(el, {
        rotateY: x * maxDeg * 2,
        rotateX: -y * maxDeg * 2,
        duration: 0.3,
        ease: "power2.out",
        overwrite: true,
      });
    },
    [maxDeg],
  );

  const onMouseLeave = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const el = ref.current ?? e.currentTarget;
    gsap.to(el, {
      rotateY: 0,
      rotateX: 0,
      duration: 0.5,
      ease: "elastic.out(1, 0.5)",
      overwrite: true,
    });
  }, []);

  return { onMouseMove, onMouseLeave, style: { perspective: "600px" } as const };
}
