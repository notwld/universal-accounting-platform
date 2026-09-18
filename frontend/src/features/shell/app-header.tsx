"use client";

import { UserButton } from "@clerk/nextjs";
import { Bell, Menu, Plus, Search, Settings, X } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useOrg } from "@/stores/org";

export function AppHeader({
  navOpen,
  onNavToggle,
}: {
  navOpen: boolean;
  onNavToggle: () => void;
}) {
  const orgName = useOrg((s) => s.orgName);

  return (
    <header className="flex h-12 shrink-0 items-center gap-2 bg-[oklch(0.28_0.04_255)] px-2 text-white sm:gap-3 sm:px-3">
      <Button
        type="button"
        size="icon-sm"
        variant="ghost"
        className="shrink-0 text-white hover:bg-white/10 hover:text-white lg:hidden"
        aria-label={navOpen ? "Close menu" : "Open menu"}
        aria-expanded={navOpen}
        onClick={onNavToggle}
      >
        {navOpen ? <X /> : <Menu />}
      </Button>

      <Link
        href="/dashboard"
        className="flex min-w-0 items-center gap-2 px-1 font-semibold tracking-tight transition-opacity hover:opacity-90"
      >
        <span className="flex size-7 shrink-0 items-center justify-center rounded bg-white/15 text-xs">
          U
        </span>
        <span className="hidden truncate sm:inline">UAP Books</span>
      </Link>

      <div className="mx-auto hidden w-full max-w-md md:block">
        <label className="relative block">
          <span className="sr-only">Search</span>
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-white/55" />
          <Input
            placeholder="Search ( / )"
            className="h-8 border-0 bg-white/10 pl-8 text-white placeholder:text-white/55 focus-visible:ring-white/30"
          />
        </label>
      </div>

      <div className="ml-auto flex items-center gap-1 sm:gap-1.5">
        <Link
          href="/"
          className="hidden max-w-36 truncate rounded-md px-2 py-1.5 text-sm text-white/90 transition-colors hover:bg-white/10 sm:block md:max-w-44"
          title="Switch organization"
        >
          {orgName ?? "Organization"}
        </Link>
        <Button
          type="button"
          size="icon-sm"
          className="bg-[oklch(0.55_0.14_250)] text-white transition-colors hover:bg-[oklch(0.5_0.14_250)]"
          aria-label="Quick create"
        >
          <Plus />
        </Button>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          className="hidden text-white hover:bg-white/10 hover:text-white sm:inline-flex"
          aria-label="Notifications"
        >
          <Bell />
        </Button>
        <Button
          type="button"
          size="icon-sm"
          variant="ghost"
          className="hidden text-white hover:bg-white/10 hover:text-white sm:inline-flex"
          aria-label="Settings"
        >
          <Settings />
        </Button>
        <UserButton />
      </div>
    </header>
  );
}
