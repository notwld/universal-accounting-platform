# Research: Login / signup UX

Sources: Nielsen/Baymard auth forms; Clerk Next.js custom pages; Clerk shadcn theme.

## Decisions

- **Two routes**, not a tabbed combo: user asked for login and signup screens; switching intent with a footer link is clearer than one hybrid form.
- **Centered card (~24rem)** on a muted canvas: standard 2026 SaaS auth (Linear/Vercel). Full-page forms feel like settings, not a gate.
- **Labels above fields**, placeholders as examples only.
- **Show password instead of confirm-password** on signup (NNG).
- **Clerk for credentials**. Custom shadcn form so the card matches the app when keys are missing; `useSignIn` / `useSignUp` when `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` is set.
- **No `clerk init`** this slice (needs user approval / existing app). `proxy.ts` no-ops without `CLERK_SECRET_KEY`.

Rejected: Clerk prebuilt widget as the only UI (blank/error without keys); building MFA/OAuth by hand.
