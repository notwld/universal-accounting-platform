export const queryKeys = {
  org: (orgId: string) => [orgId] as const,
  orgs: () => ["organizations"] as const,
  items: (orgId: string) => ["finance", orgId, "items"] as const,
  warehouses: (orgId: string) => ["finance", orgId, "warehouses"] as const,
  stockBalances: (orgId: string) => ["finance", orgId, "stock-balances"] as const,
  accounts: (orgId: string) => ["finance", orgId, "accounts"] as const,
};
