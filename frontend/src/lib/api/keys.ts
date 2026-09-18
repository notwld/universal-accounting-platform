export const queryKeys = {
  org: (orgId: string) => [orgId] as const,
  orgs: () => ["organizations"] as const,
};
