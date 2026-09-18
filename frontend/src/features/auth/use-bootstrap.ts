"use client";

import { useAuth } from "@clerk/nextjs";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { bootstrapAuth } from "@/features/orgs/api";

export function useBootstrap() {
  const { isSignedIn, isLoaded } = useAuth();
  const once = useRef(false);

  const query = useQuery({
    queryKey: ["auth", "bootstrap"],
    enabled: isLoaded && !!isSignedIn,
    staleTime: Infinity,
    queryFn: async () => {
      await bootstrapAuth();
      return true;
    },
    retry: 1,
  });

  useEffect(() => {
    if (!isSignedIn) once.current = false;
  }, [isSignedIn]);

  return {
    ready: isLoaded && (!isSignedIn || query.isSuccess),
    error: query.error,
    isLoading: !isLoaded || (!!isSignedIn && query.isPending),
  };
}
