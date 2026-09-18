"use client";

import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { NAV, type NavGroup } from "@/features/shell/nav";
import { cn } from "@/lib/utils";

const itemBase =
  "flex min-h-11 w-full items-center gap-2 rounded-md px-2.5 py-2 text-left transition-colors duration-200 lg:min-h-0";
const itemIdle = "text-foreground/80 hover:bg-black/[0.04]";
const groupOpen = "bg-black/[0.06] text-foreground font-medium";
const pageActive =
  "bg-[oklch(0.55_0.14_250)] font-medium text-white hover:bg-[oklch(0.5_0.14_250)]";

function groupForPath(pathname: string): string | null {
  for (const item of NAV) {
    if (item.kind === "group" && item.children.some((c) => c.href === pathname)) {
      return item.label;
    }
  }
  return null;
}

export function AppSidebar({
  open,
  onNavigate,
}: {
  open: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const [openKey, setOpenKey] = useState<string | null>(() => groupForPath(pathname) ?? "Sales");

  useEffect(() => {
    const g = groupForPath(pathname);
    if (g) setOpenKey(g);
  }, [pathname]);

  return (
    <aside
      className={cn(
        "flex w-56 shrink-0 flex-col border-r bg-[oklch(0.97_0.005_255)] transition-transform duration-300 ease-out",
        "fixed top-12 bottom-0 left-0 z-40 lg:static lg:top-auto lg:z-auto",
        open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}
    >
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2 text-sm">
        {NAV.map((item) => {
          if (item.kind === "group") {
            return (
              <NavGroupBlock
                key={item.label}
                item={item}
                open={openKey === item.label}
                pathname={pathname}
                onToggle={() =>
                  setOpenKey((k) => (k === item.label ? null : item.label))
                }
                onNavigate={onNavigate}
              />
            );
          }

          const active = pathname === item.href;
          return (
            <Link
              key={item.label}
              href={item.href}
              className={cn(itemBase, active ? pageActive : itemIdle)}
              onClick={onNavigate}
            >
              <item.icon className="size-4 shrink-0 opacity-80" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

function NavGroupBlock({
  item,
  open,
  pathname,
  onToggle,
  onNavigate,
}: {
  item: NavGroup;
  open: boolean;
  pathname: string;
  onToggle: () => void;
  onNavigate?: () => void;
}) {
  return (
    <div className="min-w-0">
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className={cn(itemBase, open ? groupOpen : itemIdle)}
      >
        <item.icon className="size-4 shrink-0 opacity-80" />
        <span className="flex-1 truncate">{item.label}</span>
        <ChevronDown
          className={cn(
            "size-3.5 shrink-0 opacity-60 transition-transform duration-300 ease-out",
            open ? "rotate-0" : "-rotate-90"
          )}
        />
      </button>
      <div
        className={cn(
          "grid transition-[grid-template-rows] duration-300 ease-out",
          open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        )}
      >
        <div className="overflow-hidden">
          <div
            className={cn(
              "mb-1 ml-4 border-l border-black/10 pl-2 transition-opacity duration-300",
              open ? "opacity-100" : "opacity-0"
            )}
          >
            {item.children.map((child) => {
              const active = pathname === child.href;
              return (
                <Link
                  key={child.href}
                  href={child.href}
                  onClick={onNavigate}
                  className={cn(
                    "block min-h-10 truncate rounded-md px-2 py-2 transition-colors duration-200 lg:min-h-0 lg:py-1.5",
                    active
                      ? "bg-[oklch(0.55_0.14_250)] font-medium text-white"
                      : "text-muted-foreground hover:bg-black/[0.04] hover:text-foreground"
                  )}
                >
                  {child.label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
