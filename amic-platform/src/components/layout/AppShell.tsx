import {
  createContext,
  useContext,
  useState,
  useEffect,
  lazy,
  Suspense,
  type ReactNode,
} from "react";
import { cn } from "@/lib/cn";
import { Sidebar } from "./Sidebar";
import { MobileMenuButton } from "./MobileMenuButton";
import amicMainWhiteUrl from "@/assets/logos/AMIC_Main_White.svg";
import { SidebarOverlay } from "./SidebarOverlay";
import { PageTransition } from "./PageTransition";
import { DesktopHeader } from "@/components/DesktopHeader";
import { NotificationBell } from "@/components/notifications/NotificationBell";

const CommandPalette = lazy(() => import("@/components/search/CommandPalette"));

export interface AppShellContextValue {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  isMobile: boolean;
}

const AppShellContext = createContext<AppShellContextValue | null>(null);

export function useAppShell() {
  const context = useContext(AppShellContext);
  if (!context) throw new Error("useAppShell must be used within AppShell");
  return context;
}

export interface AppShellProps {
  children: ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // 768px breakpoint detection
  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(e.matches);
      if (!e.matches) setSidebarOpen(false); // Close drawer on desktop
    };

    handleChange(mediaQuery);
    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  // ESC key to close sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && sidebarOpen) setSidebarOpen(false);
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  // Cmd/Ctrl+K to open command palette (excludes input/textarea/contentEditable)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        (e.metaKey || e.ctrlKey) &&
        e.key === "k" &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement) &&
        !(e.target instanceof HTMLElement && e.target.isContentEditable)
      ) {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Lock body scroll when mobile sidebar is open
  useEffect(() => {
    if (isMobile && sidebarOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isMobile, sidebarOpen]);

  return (
    <AppShellContext.Provider value={{ sidebarOpen, setSidebarOpen, isMobile }}>
      {/* Skip Navigation */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100]
                   focus:bg-amic focus:text-white focus:px-4 focus:py-2 focus:rounded-lg
                   focus:outline-none focus:ring-2 focus:ring-accent"
      >
        Skip to main content
      </a>

      <div className="flex min-h-screen overflow-x-hidden">
        {/* Desktop Sidebar */}
        <div className="hidden md:block">
          <Sidebar />
        </div>

        {/* Mobile Sidebar (Drawer) */}
        {isMobile && (
          <>
            <SidebarOverlay
              isOpen={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
            />
            <div
              id="mobile-sidebar"
              className={cn(
                "fixed inset-y-0 left-0 z-50 transform transition-transform duration-300",
                sidebarOpen ? "translate-x-0" : "-translate-x-full",
              )}
            >
              <Sidebar onNavItemClick={() => setSidebarOpen(false)} />
            </div>
          </>
        )}

        {/* Main Content */}
        <main
          id="main-content"
          className="flex-1 min-w-0 bg-bg-cool"
          {...(isMobile && sidebarOpen ? { inert: true } : {})}
        >
          {/* Mobile Header */}
          {isMobile && (
            <div className="sticky top-0 z-40 flex items-center gap-4 bg-amic backdrop-blur-md px-4 py-3">
              <MobileMenuButton
                isOpen={sidebarOpen}
                onClick={() => setSidebarOpen(!sidebarOpen)}
              />
              <div className="flex items-center gap-2">
                <img src={amicMainWhiteUrl} alt="AMIC" className="h-5 w-auto" />
                <span className="text-white/40 text-xs font-display">x</span>
                <span className="text-accent font-display font-bold text-[10px] tracking-[0.08em]">
                  PETRA
                </span>
              </div>
              <div className="ml-auto text-white">
                <NotificationBell />
              </div>
            </div>
          )}
          {/* Desktop Header */}
          {!isMobile && (
            <DesktopHeader onSearchClick={() => setCommandPaletteOpen(true)} />
          )}
          <div className="max-w-7xl mx-auto px-4 py-4 md:px-8 md:py-6">
            <PageTransition>{children}</PageTransition>
          </div>
        </main>
      </div>

      {/* Command Palette (Global Search) */}
      {commandPaletteOpen && (
        <Suspense fallback={null}>
          <CommandPalette
            open={commandPaletteOpen}
            onClose={() => setCommandPaletteOpen(false)}
          />
        </Suspense>
      )}
    </AppShellContext.Provider>
  );
}
