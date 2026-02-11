import { useState, useEffect } from "react";
import { cn } from "@/lib/cn";

export interface GallerySection {
  id: string;
  /** Display name — accepts either `label` or `title` */
  label?: string;
  title?: string;
  description?: string;
  path?: string;
  icon?: unknown;
}

export interface GalleryNavProps {
  sections: GallerySection[];
  activeSection?: string;
  onSectionChange?: (id: string) => void;
  className?: string;
}

export function GalleryNav({ sections, activeSection, onSectionChange, className }: GalleryNavProps) {
  const [observedId, setObservedId] = useState<string>(sections[0]?.id ?? "");
  const activeId = activeSection ?? observedId;

  useEffect(() => {
    if (activeSection !== undefined) return; // controlled mode — skip observer

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setObservedId(entry.target.id);
          }
        }
      },
      { rootMargin: "-20% 0px -70% 0px" }
    );

    for (const section of sections) {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
    }

    return () => observer.disconnect();
  }, [sections, activeSection]);

  return (
    <nav
      className={cn(
        "hidden lg:block w-48 shrink-0 sticky top-24 self-start max-h-[calc(100vh-8rem)] overflow-y-auto",
        className
      )}
    >
      <p className="label-uppercase text-text-muted mb-3">Sections</p>
      <ul className="space-y-1">
        {sections.map((section) => (
          <li key={section.id}>
            <a
              href={`#${section.id}`}
              onClick={() => onSectionChange?.(section.id)}
              className={cn(
                "block text-sm py-1.5 px-3 rounded-md transition-colors duration-200",
                activeId === section.id
                  ? "bg-amic-50 text-amic font-medium border-accent-left"
                  : "text-text-secondary hover:text-text-body hover:bg-bg-cool"
              )}
            >
              {section.label ?? section.title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
