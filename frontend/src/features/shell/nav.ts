import type { LucideIcon } from "lucide-react";
import {
  Banknote,
  BookOpen,
  FileBarChart,
  Home,
  Landmark,
  Package,
  Settings,
  ShoppingCart,
  Wallet,
} from "lucide-react";

export type NavChild = {
  label: string;
  href: string;
};

export type NavLeaf = {
  kind: "leaf";
  label: string;
  href: string;
  icon: LucideIcon;
};

export type NavGroup = {
  kind: "group";
  label: string;
  icon: LucideIcon;
  children: NavChild[];
};

export type NavItem = NavLeaf | NavGroup;

function slug(...parts: string[]) {
  return "/" + parts.join("/");
}

/** Single source for sidebar + placeholder routes. */
export const NAV: NavItem[] = [
  { kind: "leaf", href: "/dashboard", label: "Home", icon: Home },
  {
    kind: "group",
    label: "Items",
    icon: Package,
    children: [
      { label: "Items", href: slug("items") },
      {
        label: "Warehouses",
        href: slug("items", "warehouses"),
      },
      {
        label: "Stock Balances",
        href: slug("items", "stock-balances"),
      },
      {
        label: "Stock Adjustments",
        href: slug("items", "stock-adjustments"),
      },
      {
        label: "Stock Transfers",
        href: slug("items", "stock-transfers"),
      },
    ],
  },
  {
    kind: "group",
    label: "Banking",
    icon: Banknote,
    children: [
      {
        label: "Cash Accounts",
        href: slug("banking", "cash-accounts"),
      },
      {
        label: "Statement Import",
        href: slug("banking", "statement-import"),
      },
      {
        label: "Bank Lines",
        href: slug("banking", "bank-lines"),
      },
      {
        label: "Reconciliations",
        href: slug("banking", "reconciliations"),
      },
      {
        label: "Bank Rules",
        href: slug("banking", "bank-rules"),
      },
      {
        label: "Bank Feeds",
        href: slug("banking", "bank-feeds"),
      },
    ],
  },
  {
    kind: "group",
    label: "Sales",
    icon: Wallet,
    children: [
      {
        label: "Customers",
        href: slug("sales", "customers"),
      },
      { label: "Quotes", href: slug("sales", "quotes") },
      {
        label: "Invoices",
        href: slug("sales", "invoices"),
      },
      {
        label: "Recurring Schedules",
        href: slug("sales", "recurring"),
      },
      {
        label: "Customer Payments",
        href: slug("sales", "customer-payments"),
      },
      {
        label: "Credit Notes",
        href: slug("sales", "credit-notes"),
      },
      { label: "Refunds", href: slug("sales", "refunds") },
      {
        label: "Reminder Rules",
        href: slug("sales", "reminder-rules"),
      },
    ],
  },
  {
    kind: "group",
    label: "Purchases",
    icon: ShoppingCart,
    children: [
      {
        label: "Vendors",
        href: slug("purchases", "vendors"),
      },
      {
        label: "Purchase Orders",
        href: slug("purchases", "purchase-orders"),
      },
      { label: "Bills", href: slug("purchases", "bills") },
      {
        label: "Expenses",
        href: slug("purchases", "expenses"),
      },
      {
        label: "Vendor Payments",
        href: slug("purchases", "vendor-payments"),
      },
      {
        label: "Vendor Credits",
        href: slug("purchases", "vendor-credits"),
      },
      {
        label: "Vendor Refunds",
        href: slug("purchases", "vendor-refunds"),
      },
      {
        label: "Payment Runs",
        href: slug("purchases", "payment-runs"),
      },
    ],
  },
  {
    kind: "group",
    label: "Accountant",
    icon: BookOpen,
    children: [
      {
        label: "Chart of Accounts",
        href: slug("accountant", "chart-of-accounts"),
      },
      {
        label: "Journals",
        href: slug("accountant", "journals"),
      },
      {
        label: "Periods",
        href: slug("accountant", "periods"),
      },
      {
        label: "Adjustments",
        href: slug("accountant", "adjustments"),
      },
      {
        label: "FX Revaluation",
        href: slug("accountant", "fx-revaluation"),
      },
      {
        label: "Cutover",
        href: slug("accountant", "cutover"),
      },
      {
        label: "Reporting Tags",
        href: slug("accountant", "tags"),
      },
      {
        label: "Exceptions",
        href: slug("accountant", "exceptions"),
      },
    ],
  },
  {
    kind: "group",
    label: "Assets",
    icon: Landmark,
    children: [
      {
        label: "Fixed Assets",
        href: slug("assets", "fixed-assets"),
      },
      {
        label: "Asset Register",
        href: slug("assets", "asset-register"),
      },
    ],
  },
  {
    kind: "group",
    label: "Reports",
    icon: FileBarChart,
    children: [
      {
        label: "Trial Balance",
        href: slug("reports", "trial-balance"),
      },
      {
        label: "General Ledger",
        href: slug("reports", "general-ledger"),
      },
      {
        label: "Profit and Loss",
        href: slug("reports", "profit-and-loss"),
      },
      {
        label: "Balance Sheet",
        href: slug("reports", "balance-sheet"),
      },
      {
        label: "Cash Flow",
        href: slug("reports", "cash-flow"),
      },
      {
        label: "Tax Summary",
        href: slug("reports", "tax-summary"),
      },
      {
        label: "Equity Movement",
        href: slug("reports", "equity-movement"),
      },
      {
        label: "AR Aging",
        href: slug("reports", "ar-aging"),
      },
      {
        label: "AP Aging",
        href: slug("reports", "ap-aging"),
      },
      {
        label: "Inventory Valuation",
        href: slug("reports", "inventory-valuation"),
      },
      {
        label: "Data Export",
        href: slug("reports", "export"),
      },
    ],
  },
  {
    kind: "group",
    label: "Settings",
    icon: Settings,
    children: [
      {
        label: "Finance Settings",
        href: slug("settings", "finance"),
      },
      {
        label: "Tax Rates",
        href: slug("settings", "tax-rates"),
      },
      {
        label: "Country Packs",
        href: slug("settings", "country-packs"),
      },
      {
        label: "Payment Terms",
        href: slug("settings", "payment-terms"),
      },
      {
        label: "Exchange Rates",
        href: slug("settings", "exchange-rates"),
      },
      { label: "Roles", href: slug("settings", "roles") },
      { label: "Grants", href: slug("settings", "grants") },
      {
        label: "Webhooks",
        href: slug("settings", "webhooks"),
      },
      {
        label: "Saved Filters",
        href: slug("settings", "saved-filters"),
      },
    ],
  },
];

const byHref = new Map<string, { label: string; group: string }>();
for (const item of NAV) {
  if (item.kind === "group") {
    for (const child of item.children) {
      byHref.set(child.href, { label: child.label, group: item.label });
    }
  }
}

export function resolveModulePage(pathname: string) {
  return byHref.get(pathname) ?? null;
}

export function isModulePathActive(pathname: string, href: string) {
  return pathname === href;
}
