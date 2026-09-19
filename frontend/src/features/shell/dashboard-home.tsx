"use client";

import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { buttonVariants } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useBootstrap } from "@/features/auth/use-bootstrap";
import { useOrg } from "@/stores/org";

export function DashboardHome() {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();
  const orgId = useOrg((s) => s.orgId);
  const orgName = useOrg((s) => s.orgName);
  const { ready, isLoading } = useBootstrap();

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn) {
      router.replace("/sign-in");
      return;
    }
    if (ready && !orgId) router.replace("/");
  }, [isLoaded, isSignedIn, ready, orgId, router]);

  if (!isLoaded || isLoading || !isSignedIn || !orgId) {
    return <Spinner className="h-full min-h-40" />;
  }

  return (
    <div className="mx-auto flex h-full w-full max-w-[1600px] flex-col gap-4 overflow-auto p-4 sm:gap-6 sm:p-6">
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">Dashboard</p>
        <h1 className="text-balance text-xl font-semibold tracking-tight sm:text-2xl">
          {orgName}
        </h1>
      </div>

      <div className="grid gap-3 sm:gap-4 md:grid-cols-2">
        <section className="rounded-xl border bg-card p-4 transition-shadow duration-200 hover:shadow-sm sm:p-5">
          <h2 className="text-sm font-medium">Total Receivables</h2>
          <p className="mt-3 font-mono text-2xl font-semibold tabular-nums text-muted-foreground">
            —
          </p>
          <p className="mt-2 text-xs text-muted-foreground text-pretty">
            Live balances connect when sales screens ship.
          </p>
        </section>
        <section className="rounded-xl border bg-card p-4 transition-shadow duration-200 hover:shadow-sm sm:p-5">
          <h2 className="text-sm font-medium">Total Payables</h2>
          <p className="mt-3 font-mono text-2xl font-semibold tabular-nums text-muted-foreground">
            —
          </p>
          <p className="mt-2 text-xs text-muted-foreground text-pretty">
            Live balances connect when purchase screens ship.
          </p>
        </section>
      </div>

      <section className="rounded-xl border bg-card p-4 transition-shadow duration-200 hover:shadow-sm sm:p-5">
        <h2 className="text-sm font-medium">Cash flow</h2>
        <p className="mt-3 text-sm text-muted-foreground text-pretty">
          Charts stay empty until report APIs are wired. Organization{" "}
          <span className="font-medium text-foreground">{orgName}</span> is active
          for every request.
        </p>
        <Link
          href="/"
          className={`${buttonVariants({ variant: "outline" })} mt-4 h-11 min-h-11 sm:h-9 sm:min-h-0`}
        >
          Switch organization
        </Link>
      </section>
    </div>
  );
}
