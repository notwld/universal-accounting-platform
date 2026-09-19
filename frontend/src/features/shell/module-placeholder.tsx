export function ModulePlaceholder({
  title,
  group,
}: {
  title: string;
  group: string;
}) {
  return (
    <div className="mx-auto flex h-full w-full max-w-[1600px] flex-col gap-4 overflow-auto p-4 sm:gap-6 sm:p-6">
      <div className="min-w-0">
        <p className="text-sm text-muted-foreground">{group}</p>
        <h1 className="text-balance text-xl font-semibold tracking-tight sm:text-2xl">
          {title}
        </h1>
      </div>

      <section className="rounded-xl border bg-card p-4 sm:p-5">
        <p className="text-sm text-muted-foreground text-pretty">
          This screen is a placeholder. List views, forms, and full CRUD will be added here
          next. Navigation and actions will also be gated by org RBAC — the UI will hide or
          disable what you cannot do; the API remains the security boundary.
        </p>
      </section>
    </div>
  );
}
