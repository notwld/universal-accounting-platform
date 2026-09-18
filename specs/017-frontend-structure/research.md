# Research: Next.js production structure

Sources: Next.js project-structure docs; 2026 App Router scale write-ups (feature folders, thin pages, `app/` routing-only).

## Decision

Hybrid of Next’s “store files outside `app/`” and feature-sliced scale:

- `src/app` — routes only, plus `(app)` group so a later `(auth)` group can sit beside it without URL changes.
- `src/components/ui` — shadcn only.
- `src/lib` — env (zod), axios client, query keys.
- `src/stores` — client session (org id).
- `src/types` — Django envelope types used by the client.
- `src/features/*` — **not created empty**. First real screen owns the first feature folder.

Rejected: FSD layers (`widgets/entities/shared`), Vite-era `app/router.tsx`, pre-building `finance/sales|purchases|banking`. Those are empty trees.
