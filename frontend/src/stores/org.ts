import { create } from "zustand";

export const useOrg = create<{
  orgId: string | null;
  setOrgId: (orgId: string | null) => void;
}>((set) => ({
  orgId: null,
  setOrgId: (orgId) => set({ orgId }),
}));
