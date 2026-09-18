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
  /** Backend route hint for future CRUD screens */
  api: string;
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
      { label: "Items", href: slug("items"), api: "GET/POST /finance/items" },
      {
        label: "Warehouses",
        href: slug("items", "warehouses"),
        api: "GET/POST /finance/warehouses",
      },
      {
        label: "Stock Balances",
        href: slug("items", "stock-balances"),
        api: "GET /finance/stock/balances",
      },
      {
        label: "Stock Adjustments",
        href: slug("items", "stock-adjustments"),
        api: "POST /finance/stock/adjust",
      },
      {
        label: "Stock Transfers",
        href: slug("items", "stock-transfers"),
        api: "POST /finance/stock/transfer",
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
        api: "GET/POST /finance/accounts",
      },
      {
        label: "Statement Import",
        href: slug("banking", "statement-import"),
        api: "POST /finance/bank-statements",
      },
      {
        label: "Bank Lines",
        href: slug("banking", "bank-lines"),
        api: "GET /finance/bank-lines",
      },
      {
        label: "Reconciliations",
        href: slug("banking", "reconciliations"),
        api: "POST /finance/bank-reconciliations",
      },
      {
        label: "Bank Rules",
        href: slug("banking", "bank-rules"),
        api: "GET/POST /finance/bank-rules",
      },
      {
        label: "Bank Feeds",
        href: slug("banking", "bank-feeds"),
        api: "GET/POST /finance/bank-feeds",
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
        api: "GET/POST /finance/contacts (is_customer)",
      },
      { label: "Quotes", href: slug("sales", "quotes"), api: "GET/POST /finance/quotes" },
      {
        label: "Invoices",
        href: slug("sales", "invoices"),
        api: "GET/POST /finance/invoices",
      },
      {
        label: "Recurring Schedules",
        href: slug("sales", "recurring"),
        api: "GET/POST /finance/recurring",
      },
      {
        label: "Customer Payments",
        href: slug("sales", "customer-payments"),
        api: "POST /finance/payments",
      },
      {
        label: "Credit Notes",
        href: slug("sales", "credit-notes"),
        api: "POST /finance/credit-notes",
      },
      { label: "Refunds", href: slug("sales", "refunds"), api: "POST /finance/refunds" },
      {
        label: "Reminder Rules",
        href: slug("sales", "reminder-rules"),
        api: "GET/POST /finance/reminder-rules",
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
        api: "GET/POST /finance/contacts (is_vendor)",
      },
      {
        label: "Purchase Orders",
        href: slug("purchases", "purchase-orders"),
        api: "GET/POST /finance/purchase-orders",
      },
      { label: "Bills", href: slug("purchases", "bills"), api: "GET/POST /finance/bills" },
      {
        label: "Expenses",
        href: slug("purchases", "expenses"),
        api: "POST /finance/expenses",
      },
      {
        label: "Vendor Payments",
        href: slug("purchases", "vendor-payments"),
        api: "POST /finance/vendor-payments",
      },
      {
        label: "Vendor Credits",
        href: slug("purchases", "vendor-credits"),
        api: "POST /finance/vendor-credits",
      },
      {
        label: "Vendor Refunds",
        href: slug("purchases", "vendor-refunds"),
        api: "POST /finance/vendor-refunds",
      },
      {
        label: "Payment Runs",
        href: slug("purchases", "payment-runs"),
        api: "POST /finance/payment-runs",
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
        api: "GET/POST /finance/accounts",
      },
      {
        label: "Journals",
        href: slug("accountant", "journals"),
        api: "GET/POST /finance/journals",
      },
      {
        label: "Periods",
        href: slug("accountant", "periods"),
        api: "GET/POST /finance/periods",
      },
      {
        label: "Adjustments",
        href: slug("accountant", "adjustments"),
        api: "POST /finance/adjustments",
      },
      {
        label: "FX Revaluation",
        href: slug("accountant", "fx-revaluation"),
        api: "POST /finance/fx/revalue",
      },
      {
        label: "Cutover",
        href: slug("accountant", "cutover"),
        api: "POST /finance/cutover",
      },
      {
        label: "Reporting Tags",
        href: slug("accountant", "tags"),
        api: "GET/POST /finance/tags",
      },
      {
        label: "Exceptions",
        href: slug("accountant", "exceptions"),
        api: "GET /finance/exceptions",
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
        api: "GET/POST /finance/assets",
      },
      {
        label: "Asset Register",
        href: slug("assets", "asset-register"),
        api: "GET /finance/reports/asset-register",
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
        api: "GET /finance/reports/trial-balance",
      },
      {
        label: "General Ledger",
        href: slug("reports", "general-ledger"),
        api: "GET /finance/reports/general-ledger",
      },
      {
        label: "Profit and Loss",
        href: slug("reports", "profit-and-loss"),
        api: "GET /finance/reports/profit-loss",
      },
      {
        label: "Balance Sheet",
        href: slug("reports", "balance-sheet"),
        api: "GET /finance/reports/balance-sheet",
      },
      {
        label: "Cash Flow",
        href: slug("reports", "cash-flow"),
        api: "GET /finance/reports/cash-flow",
      },
      {
        label: "Tax Summary",
        href: slug("reports", "tax-summary"),
        api: "GET /finance/reports/tax-summary",
      },
      {
        label: "Equity Movement",
        href: slug("reports", "equity-movement"),
        api: "GET /finance/reports/equity-movement",
      },
      {
        label: "AR Aging",
        href: slug("reports", "ar-aging"),
        api: "GET /finance/reports/ar-aging",
      },
      {
        label: "AP Aging",
        href: slug("reports", "ap-aging"),
        api: "GET /finance/reports/ap-aging",
      },
      {
        label: "Inventory Valuation",
        href: slug("reports", "inventory-valuation"),
        api: "GET /finance/reports/inventory-valuation",
      },
      {
        label: "Data Export",
        href: slug("reports", "export"),
        api: "GET /finance/export",
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
        api: "GET/PUT /finance/settings",
      },
      {
        label: "Tax Rates",
        href: slug("settings", "tax-rates"),
        api: "GET/POST /finance/tax-rates",
      },
      {
        label: "Country Packs",
        href: slug("settings", "country-packs"),
        api: "GET /finance/country-packs",
      },
      {
        label: "Payment Terms",
        href: slug("settings", "payment-terms"),
        api: "GET/POST /finance/payment-terms",
      },
      {
        label: "Exchange Rates",
        href: slug("settings", "exchange-rates"),
        api: "GET/POST /finance/exchange-rates",
      },
      { label: "Roles", href: slug("settings", "roles"), api: "GET/POST /finance/roles" },
      { label: "Grants", href: slug("settings", "grants"), api: "GET/POST /finance/grants" },
      {
        label: "Webhooks",
        href: slug("settings", "webhooks"),
        api: "GET/POST /finance/webhooks",
      },
      {
        label: "Saved Filters",
        href: slug("settings", "saved-filters"),
        api: "GET/POST /finance/saved-filters",
      },
    ],
  },
];

const byHref = new Map<string, { label: string; group: string; api: string }>();
for (const item of NAV) {
  if (item.kind === "group") {
    for (const child of item.children) {
      byHref.set(child.href, { label: child.label, group: item.label, api: child.api });
    }
  }
}

export function resolveModulePage(pathname: string) {
  return byHref.get(pathname) ?? null;
}

export function isModulePathActive(pathname: string, href: string) {
  return pathname === href;
}
