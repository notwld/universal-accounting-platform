"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AppHeader } from "@/features/shell/app-header";
import { AppSidebar } from "@/features/shell/app-sidebar";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [navOpen, setNavOpen] = useState(false);

  useEffect(() => {
    setNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen]);

  return (
    <div className="flex h-svh flex-col overflow-hidden bg-background">
      <AppHeader navOpen={navOpen} onNavToggle={() => setNavOpen((o) => !o)} />
      <div className="relative flex min-h-0 flex-1">
        <button
          type="button"
          aria-label="Close menu"
          tabIndex={navOpen ? 0 : -1}
          className={cn(
            "fixed inset-0 z-30 bg-black/40 transition-opacity duration-300 lg:hidden",
            navOpen ? "opacity-100" : "pointer-events-none opacity-0"
          )}
          onClick={() => setNavOpen(false)}
        />
        <AppSidebar open={navOpen} onNavigate={() => setNavOpen(false)} />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  );
}
