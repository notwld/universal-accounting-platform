"use client";

import {
  Banknote,
  BookOpen,
  ChevronDown,
  FileBarChart,
  Home,
  Package,
  ShoppingCart,
  Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/utils";

type NavLeaf = {
  href: string;
  label: string;
  icon: typeof Home;
  soon?: boolean;
};

type NavGroup = {
  label: string;
  icon: typeof Home;
  children: string[];
};

const nav: (NavLeaf | NavGroup)[] = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "#", label: "Items", icon: Package, soon: true },
  {
    label: "Sales",
    icon: Wallet,
    children: [
      "Customers",
      "Quotes",
      "Invoices",
      "Recurring Invoices",
      "Payments Received",
      "Credit Notes",
    ],
  },
  {
    label: "Purchases",
    icon: ShoppingCart,
    children: ["Vendors", "Bills", "Purchase Orders", "Payments Made"],
  },
  { href: "#", label: "Banking", icon: Banknote, soon: true },
  { href: "#", label: "Accountant", icon: BookOpen, soon: true },
  { href: "#", label: "Reports", icon: FileBarChart, soon: true },
];

function isGroup(item: NavLeaf | NavGroup): item is NavGroup {
  return "children" in item;
}

const itemBase =
  "flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left transition-colors duration-200";
const itemIdle = "text-foreground/80 hover:bg-black/[0.04]";
const groupOpen = "bg-black/[0.06] text-foreground font-medium";
const pageActive = "bg-[oklch(0.55_0.14_250)] font-medium text-white hover:bg-[oklch(0.5_0.14_250)]";

export function AppSidebar() {
  const pathname = usePathname();
  const [openKey, setOpenKey] = useState<string | null>("Sales");

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-[oklch(0.97_0.005_255)]">
      <nav className="flex flex-1 flex-col gap-0.5 p-2 text-sm">
        {nav.map((item) => {
          if (isGroup(item)) {
            const open = openKey === item.label;
            return (
              <div key={item.label} className="min-w-0">
                <button
                  type="button"
                  aria-expanded={open}
                  onClick={() => setOpenKey((k) => (k === item.label ? null : item.label))}
                  className={cn(itemBase, open ? groupOpen : itemIdle)}
                >
                  <item.icon className="size-4 shrink-0 opacity-80" />
                  <span className="flex-1">{item.label}</span>
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
                      {item.children.map((child) => (
                        <span
                          key={child}
                          className="block cursor-default rounded-md px-2 py-1.5 text-muted-foreground"
                          title="Coming soon"
                        >
                          {child}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          }

          const className = cn(
            itemBase,
            item.href === pathname ? pageActive : itemIdle
          );

          if (item.soon || item.href === "#") {
            return (
              <span key={item.label} className={className} title="Coming soon">
                <item.icon className="size-4 shrink-0 opacity-80" />
                {item.label}
              </span>
            );
          }

          return (
            <Link key={item.label} href={item.href} className={className}>
              <item.icon className="size-4 shrink-0 opacity-80" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
