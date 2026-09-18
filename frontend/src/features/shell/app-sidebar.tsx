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

const nav = [
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
  { href: "#", label: "Purchases", icon: ShoppingCart, soon: true },
  { href: "#", label: "Banking", icon: Banknote, soon: true },
  { href: "#", label: "Accountant", icon: BookOpen, soon: true },
  { href: "#", label: "Reports", icon: FileBarChart, soon: true },
];

export function AppSidebar() {
  const pathname = usePathname();
  const [salesOpen, setSalesOpen] = useState(true);

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r bg-[oklch(0.97_0.005_255)]">
      <nav className="flex flex-1 flex-col gap-0.5 p-2 text-sm">
        {nav.map((item) => {
          if ("children" in item && item.children) {
            return (
              <div key={item.label}>
                <button
                  type="button"
                  onClick={() => setSalesOpen((v) => !v)}
                  className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-foreground/80 hover:bg-black/5"
                >
                  <item.icon className="size-4 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  <ChevronDown
                    className={cn("size-3.5 transition", salesOpen ? "rotate-0" : "-rotate-90")}
                  />
                </button>
                {salesOpen && (
                  <div className="mb-1 ml-4 border-l pl-2">
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
                )}
              </div>
            );
          }

          const active = item.href === pathname;
          const className = cn(
            "flex items-center gap-2 rounded-md px-2.5 py-2",
            active
              ? "bg-[oklch(0.45_0.14_250)] text-white"
              : "text-foreground/80 hover:bg-black/5",
            item.soon && !active && "opacity-70"
          );

          if (item.soon || item.href === "#") {
            return (
              <span key={item.label} className={className} title="Coming soon">
                <item.icon className="size-4 shrink-0" />
                {item.label}
              </span>
            );
          }

          return (
            <Link key={item.label} href={item.href!} className={className}>
              <item.icon className="size-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
