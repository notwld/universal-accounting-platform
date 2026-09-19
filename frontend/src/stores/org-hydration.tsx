"use client";

import { useEffect } from "react";
import { useOrg } from "@/stores/org";

/** Rehydrate persisted org after mount so SSR HTML matches the first client paint. */
export function OrgStoreHydration() {
  useEffect(() => {
    void useOrg.persist.rehydrate();
  }, []);
  return null;
}
