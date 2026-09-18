import { create } from "zustand";
import { persist } from "zustand/middleware";

type OrgState = {
  orgId: string | null;
  orgName: string | null;
  setOrg: (org: { id: string; name: string } | null) => void;
};

export const useOrg = create<OrgState>()(
  persist(
    (set) => ({
      orgId: null,
      orgName: null,
      setOrg: (org) =>
        set(org ? { orgId: org.id, orgName: org.name } : { orgId: null, orgName: null }),
    }),
    { name: "uap-org" }
  )
);
