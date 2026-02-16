import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ChevronDown, BarChart3, Briefcase, FileText, Layers } from "lucide-react";
import { cn } from "@/lib/cn";

interface ModuleConfig {
  id: string;
  label: string;
  icon: React.ElementType;
  path: string;
}

const MODULES: ModuleConfig[] = [
  { id: "fdd", label: "Auto FDD", icon: Briefcase, path: "/fdd/deals" },
  { id: "kiis", label: "KIIS", icon: BarChart3, path: "/kiis" },
  { id: "im", label: "IM Generator", icon: FileText, path: "/im" },
];

function getCurrentModule(pathname: string): ModuleConfig | null {
  if (pathname.startsWith("/kiis")) return MODULES[1];
  if (pathname.startsWith("/im")) return MODULES[2];
  if (pathname.startsWith("/fdd")) return MODULES[0];
  // Portal-level routes (/, /admin, /settings) have no active module
  return null;
}

export function ModuleSwitcher() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = getCurrentModule(pathname);

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Close on Escape
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, []);

  return (
    <div ref={ref} className="relative px-3 py-3">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.08] hover:bg-white/[0.12] transition-colors text-white text-sm border border-white/5"
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {current ? (
          <>
            <current.icon className="h-4 w-4 flex-shrink-0" />
            <span className="flex-1 text-left font-medium">{current.label}</span>
          </>
        ) : (
          <>
            <Layers className="h-4 w-4 flex-shrink-0" />
            <span className="flex-1 text-left font-medium text-white/70">Select Module</span>
          </>
        )}
        <ChevronDown
          className={cn(
            "h-4 w-4 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open && (
        <div
          className="absolute left-3 right-3 top-full mt-1 bg-amic-800 border border-white/10 rounded-dr shadow-dr-lg z-50 overflow-hidden"
          role="listbox"
          aria-label="Select module"
        >
          {MODULES.map((mod) => (
            <button
              key={mod.id}
              role="option"
              aria-selected={current?.id === mod.id}
              onClick={() => {
                navigate(mod.path);
                setOpen(false);
              }}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2.5 text-sm transition-colors",
                current?.id === mod.id
                  ? "bg-white/15 text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white",
              )}
            >
              <mod.icon className="h-4 w-4 flex-shrink-0" />
              <span>{mod.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
