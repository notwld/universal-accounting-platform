"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect } from "react";
import { setAuthTokenGetter } from "@/lib/api/token";
import { useOrg } from "@/stores/org";

export function AuthBridge({ children }: { children: React.ReactNode }) {
  const { getToken, isSignedIn } = useAuth();
  const setOrg = useOrg((s) => s.setOrg);

  useEffect(() => {
    setAuthTokenGetter(async () => (await getToken()) ?? null);
    return () => setAuthTokenGetter(null);
  }, [getToken]);

  useEffect(() => {
    if (isSignedIn === false) setOrg(null);
  }, [isSignedIn, setOrg]);

  return children;
}
