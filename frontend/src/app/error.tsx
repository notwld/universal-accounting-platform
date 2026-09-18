"use client";

import { Button } from "@/components/ui/button";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-3">
      <p>Something went wrong.</p>
      <Button onClick={reset}>Retry</Button>
    </main>
  );
}
