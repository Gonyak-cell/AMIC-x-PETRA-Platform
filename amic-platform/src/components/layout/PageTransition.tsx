import { useRef, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { gsap, useGSAP } from "@/lib/gsap";

interface PageTransitionProps {
  children: ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const location = useLocation();
  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const el = containerRef.current;
      if (!el) return;

      gsap.fromTo(
        el,
        { opacity: 0, y: 14 },
        { opacity: 1, y: 0, duration: 0.4, ease: "power2.out" },
      );
    },
    { dependencies: [location.pathname], scope: containerRef },
  );

  return (
    <div ref={containerRef} key={location.pathname}>
      {children}
    </div>
  );
}
