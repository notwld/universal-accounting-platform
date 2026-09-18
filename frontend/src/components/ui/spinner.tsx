import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/** Centered indeterminate spinner — no visible copy (sr-only for a11y). */
export function Spinner({ className, size = "md" }: { className?: string; size?: "sm" | "md" }) {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={cn("flex items-center justify-center", className)}
    >
      <Loader2
        aria-hidden
        className={cn(
          "animate-spin text-muted-foreground motion-reduce:animate-none",
          size === "sm" ? "size-4" : "size-6"
        )}
      />
      <span className="sr-only">Loading</span>
    </div>
  );
}
