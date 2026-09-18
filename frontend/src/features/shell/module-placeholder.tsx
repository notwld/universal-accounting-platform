export function ModulePlaceholder({
  title,
  group,
  api,
}: {
  title: string;
  group: string;
  api: string;
}) {
  return (
    <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-4 p-4 sm:gap-6 sm:p-6">
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">{group}</p>
        <h1 className="text-balance text-xl font-semibold tracking-tight sm:text-2xl">
          {title}
        </h1>
      </div>

      <section className="rounded-xl border bg-card p-4 sm:p-5">
        <p className="text-sm text-muted-foreground text-pretty">
          This screen is a placeholder. List views, forms, and full CRUD against the finance API
          will be added here next. Navigation and actions will also be gated by org RBAC
          (backend finance grants / permission actions) — the UI will hide or disable what you
          cannot do; the API remains the security boundary.
        </p>
        <p className="mt-3 font-mono text-xs text-muted-foreground break-all">
          Planned API: <span className="text-foreground">{api}</span>
        </p>
      </section>
    </div>
  );
}
