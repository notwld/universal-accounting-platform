"use client";

import { useAuth, UserButton } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { buttonVariants } from "@/components/ui/button";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useBootstrap } from "@/features/auth/use-bootstrap";
import { createOrganization, listOrganizations } from "@/features/orgs/api";
import { queryKeys } from "@/lib/api/keys";
import { useOrg } from "@/stores/org";

export function HomeGate() {
  const { isSignedIn, isLoaded } = useAuth();
  const router = useRouter();
  const { orgId, setOrg } = useOrg();
  const { ready, isLoading, error } = useBootstrap();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);

  const orgs = useQuery({
    queryKey: queryKeys.orgs(),
    enabled: ready && !!isSignedIn,
    queryFn: listOrganizations,
  });

  useEffect(() => {
    if (!ready || !isSignedIn || !orgs.data || !orgId) return;
    const match = orgs.data.find((o) => o.id === orgId);
    if (match) {
      setOrg({ id: match.id, name: match.name });
      router.replace("/dashboard");
      return;
    }
    setOrg(null);
  }, [ready, isSignedIn, orgs.data, orgId, router, setOrg]);

  const create = useMutation({
    mutationFn: createOrganization,
    onSuccess: async (org) => {
      setOrg({ id: org.id, name: org.name });
      await qc.invalidateQueries({ queryKey: queryKeys.orgs() });
      router.push("/dashboard");
    },
  });

  if (!isLoaded || isLoading || (isSignedIn && orgs.isPending)) {
    return (
      <main className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
        Loading…
      </main>
    );
  }

  if (!isSignedIn) {
    return (
      <main className="flex flex-1 items-center justify-center gap-3">
        <Link href="/sign-in" className={buttonVariants()}>
          Sign in
        </Link>
        <Link href="/sign-up" className={buttonVariants({ variant: "outline" })}>
          Create account
        </Link>
      </main>
    );
  }

  if (error || orgs.error) {
    return (
      <main className="flex flex-1 flex-col items-center justify-center gap-3 px-4">
        <p className="text-sm text-destructive" role="alert">
          Could not load your account. Try signing in again.
        </p>
        <Link href="/sign-in" className={buttonVariants({ variant: "outline" })}>
          Sign in
        </Link>
      </main>
    );
  }

  const items = orgs.data ?? [];

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-12">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">UAP</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Choose an organization
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            We&apos;ll remember your choice for next time. Switch anytime from the header.
          </p>
        </div>
        <UserButton />
      </div>

      {items.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>Create your first organization</CardTitle>
            <CardDescription>
              Organizations keep books, banking, and reports separate for each business.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              className="grid gap-3"
              onSubmit={(e) => {
                e.preventDefault();
                if (!name.trim()) return;
                create.mutate(name.trim());
              }}
            >
              <div className="grid gap-2">
                <Label htmlFor="org-name">Organization name</Label>
                <Input
                  id="org-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Acme Trading"
                  autoFocus
                  className="h-10"
                />
              </div>
              <Button type="submit" className="h-10 w-fit" disabled={create.isPending}>
                {create.isPending ? "Creating…" : "Create organization"}
              </Button>
              {create.error && (
                <p className="text-sm text-destructive" role="alert">
                  Could not create organization.
                </p>
              )}
            </form>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            {items.map((org) => (
              <button
                key={org.id}
                type="button"
                onClick={() => {
                  setOrg({ id: org.id, name: org.name });
                  router.push("/dashboard");
                }}
                className="rounded-xl border bg-card p-5 text-left shadow-sm transition hover:border-foreground/20 hover:shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
              >
                <div className="flex items-start gap-3">
                  <span className="flex size-10 items-center justify-center rounded-lg bg-muted">
                    <Building2 className="size-5 text-muted-foreground" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{org.name}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {org.finance_role_slug
                        ? org.finance_role_slug.replaceAll("_", " ")
                        : "Member"}
                      {org.finance_setup_complete ? "" : " · Setup needed"}
                    </span>
                  </span>
                </div>
              </button>
            ))}
          </div>

          {creating ? (
            <Card>
              <CardHeader>
                <CardTitle>New organization</CardTitle>
              </CardHeader>
              <CardContent>
                <form
                  className="flex flex-col gap-3 sm:flex-row sm:items-end"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (!name.trim()) return;
                    create.mutate(name.trim());
                  }}
                >
                  <div className="grid flex-1 gap-2">
                    <Label htmlFor="new-org">Name</Label>
                    <Input
                      id="new-org"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="h-10"
                      autoFocus
                    />
                  </div>
                  <Button type="submit" className="h-10" disabled={create.isPending}>
                    Create
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    className="h-10"
                    onClick={() => setCreating(false)}
                  >
                    Cancel
                  </Button>
                </form>
              </CardContent>
            </Card>
          ) : (
            <Button
              type="button"
              variant="outline"
              className="h-10 w-fit"
              onClick={() => setCreating(true)}
            >
              <Plus />
              New organization
            </Button>
          )}
        </>
      )}
    </main>
  );
}
