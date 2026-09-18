"use client";

import { useAuth, UserButton } from "@clerk/nextjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Building2, Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { buttonVariants } from "@/components/ui/button";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
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

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace("/sign-in");
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || !isSignedIn || isLoading || orgs.isPending) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <Spinner className="min-h-40" />
      </main>
    );
  }

  if (error || orgs.error) {
    return (
      <main className="relative flex min-h-svh flex-1 flex-col items-center justify-center gap-3 px-4">
        <div className="absolute top-4 right-4">
          <UserButton />
        </div>
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
    <main className="relative flex min-h-svh flex-1 flex-col bg-muted/30">
      <div className="absolute top-4 right-4 z-10">
        <UserButton />
      </div>

      <div className="flex flex-1 flex-col items-center justify-center px-4 py-16">
        <div className="grid w-full max-w-2xl grid-cols-2 gap-4 sm:grid-cols-3">
          {items.map((org) => (
            <button
              key={org.id}
              type="button"
              onClick={() => {
                setOrg({ id: org.id, name: org.name });
                router.push("/dashboard");
              }}
              className="group aspect-square rounded-2xl border bg-card p-5 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-foreground/20 hover:shadow-md focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <div className="flex h-full flex-col">
                <span className="flex size-12 items-center justify-center rounded-xl bg-muted transition group-hover:bg-muted/80">
                  <Building2 className="size-6 text-muted-foreground" />
                </span>
                <span className="mt-auto min-w-0">
                  <span className="block truncate text-base font-medium">{org.name}</span>
                  <span className="mt-1 block truncate text-xs text-muted-foreground capitalize">
                    {org.finance_role_slug
                      ? org.finance_role_slug.replaceAll("_", " ")
                      : "Member"}
                    {org.finance_setup_complete ? "" : " · Setup needed"}
                  </span>
                </span>
              </div>
            </button>
          ))}

          {creating ? (
            <div className="col-span-2 aspect-auto rounded-2xl border bg-card p-5 shadow-sm sm:col-span-1 sm:aspect-square sm:min-h-[11rem]">
              <form
                className="flex h-full flex-col gap-3"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!name.trim()) return;
                  create.mutate(name.trim());
                }}
              >
                <div className="grid gap-2">
                  <Label htmlFor="new-org">Name</Label>
                  <Input
                    id="new-org"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Acme Trading"
                    className="h-9"
                    autoFocus
                  />
                </div>
                {create.error && (
                  <p className="text-xs text-destructive" role="alert">
                    Could not create organization.
                  </p>
                )}
                <div className="mt-auto flex flex-wrap gap-2">
                  <Button type="submit" size="sm" disabled={create.isPending}>
                    {create.isPending ? "Creating…" : "Create"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setCreating(false);
                      setName("");
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="group flex aspect-square flex-col items-center justify-center gap-3 rounded-2xl border border-dashed bg-card/50 p-5 text-center transition hover:border-foreground/30 hover:bg-card focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <span className="flex size-12 items-center justify-center rounded-xl border border-dashed bg-muted/50 transition group-hover:bg-muted">
                <Plus className="size-6 text-muted-foreground" />
              </span>
              <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground">
                Create new
              </span>
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
