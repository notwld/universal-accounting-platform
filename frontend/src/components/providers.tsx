"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { AuthBridge } from "@/features/auth/auth-bridge";
import { makeQueryClient } from "@/lib/query";

const clerkPk = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(makeQueryClient);
  const tree = (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  if (!clerkPk) return tree;
  return (
    <ClerkProvider
      publishableKey={clerkPk}
      signInUrl="/sign-in"
      signUpUrl="/sign-up"
      afterSignOutUrl="/"
    >
      <AuthBridge>{tree}</AuthBridge>
    </ClerkProvider>
  );
}
