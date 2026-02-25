import { useRef } from "react";
import { cn } from "@/lib/cn";
import { gsap, useGSAP } from "@/lib/gsap";

export interface PageHeroProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  compact?: boolean;
  className?: string;
  backgroundImage?: string;
  backgroundOpacity?: number;
  backgroundPosition?: "top" | "center" | "bottom";
}

export function PageHero({
  title,
  subtitle,
  actions,
  children,
  compact = false,
  className,
  backgroundImage,
  backgroundOpacity = 0.2,
  backgroundPosition = "top",
}: PageHeroProps) {
  const containerRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const actionsRef = useRef<HTMLDivElement>(null);
  const childrenRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });

      if (titleRef.current) {
        tl.fromTo(
          titleRef.current,
          { y: 30, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.6 },
        );
      }

      if (subtitleRef.current) {
        tl.fromTo(
          subtitleRef.current,
          { y: 20, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.5 },
          "-=0.35",
        );
      }

      if (actionsRef.current) {
        tl.fromTo(
          actionsRef.current,
          { x: 20, opacity: 0 },
          { x: 0, opacity: 1, duration: 0.4 },
          "-=0.25",
        );
      }

      if (childrenRef.current?.children.length) {
        tl.fromTo(
          Array.from(childrenRef.current.children),
          { y: 25, opacity: 0 },
          { y: 0, opacity: 1, stagger: 0.06, duration: 0.5 },
          "-=0.2",
        );
      }
    },
    { scope: containerRef },
  );

  return (
    <section
      ref={containerRef}
      className={cn(
        "hero-gradient-radial text-white rounded-2xl relative overflow-hidden",
        compact ? "py-8 md:py-12" : "py-12 md:py-16",
        className,
      )}
    >
      {backgroundImage && (
        <img
          src={backgroundImage}
          alt=""
          className={cn(
            "absolute inset-0 w-full h-full object-cover pointer-events-none",
            backgroundPosition === "top" && "object-top",
            backgroundPosition === "center" && "object-center",
            backgroundPosition === "bottom" && "object-bottom",
          )}
          style={{ opacity: backgroundOpacity }}
        />
      )}
      <div className="relative z-10 px-6 md:px-10">
        {/* Title + Actions */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
          <div>
            <h1
              ref={titleRef}
              className="text-hero-title font-heading text-white mb-2"
              style={{ opacity: 0 }}
            >
              {title}
            </h1>
            {subtitle && (
              <p
                ref={subtitleRef}
                className="text-hero-subtitle text-white/80"
                style={{ opacity: 0 }}
              >
                {subtitle}
              </p>
            )}
          </div>
          {actions && (
            <div
              ref={actionsRef}
              className="flex flex-wrap items-center gap-3"
              style={{ opacity: 0 }}
            >
              {actions}
            </div>
          )}
        </div>

        {/* Optional Content (e.g., KPI cards) */}
        {children && <div ref={childrenRef}>{children}</div>}
      </div>
    </section>
  );
}
