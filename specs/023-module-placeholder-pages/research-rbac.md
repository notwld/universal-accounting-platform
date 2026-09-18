# Research: Frontend RBAC for UAP Books (production)

**Date**: 2026-09-18  
**Scope**: Future frontend authz UX layered on existing backend `FinanceRole` / `FinanceGrant` / `ACTIONS`  
**Not in scope now**: Implementing gates — placeholders only note that RBAC is planned.

## Backend already owns the security boundary

UAP finance permissions live in `backend/apps/finance/permissions.py` as action strings (`finance.invoice.create`, `finance.document.approve`, …) with role presets (`owner`, `accountant`, `sales_clerk`, `viewer`, …) and APIs `roles` / `grants`. Org context is `X-Organization-ID`. That remains the **only** enforcement layer (OWASP ASVS 8.3.1: never rely on client-side JS for authorization).

## Production frontend practices (consensus)

Sources synthesized: [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [OWASP ASVS V8](https://github.com/OWASP/ASVS/blob/master/5.0/en/0x17-V8-Authorization.md), [DEV: same policy both sides](https://dev.to/kensaadi/rbac-in-react-and-node-enforce-the-same-policy-on-both-sides-2ial), [Frontend security architecture](https://blog.ranveerkumar.com/articles/frontend-security-architecture-auth-tokens-rbac-csp-browser-risks-secure-defaults), [Authorization patterns](https://devsofus.com/security/authorization), [Next.js RBAC / zero-trust](https://www.averagedevs.com/blog/rbac-zero-trust-architecture-nextjs), [SaaS RBAC 2026](https://viprasol.com/blog/saas-role-based-access/), plus accounting SoD concerns from ERP practice.

### 1. UI is affordance, API is the gate

- Hide/disable nav, buttons, and fields from effective permissions for UX.
- Every mutating and sensitive read still returns **403** from Django if unauthorized.
- Deleting every frontend check must leave the app secure; deleting one server check must not.

### 2. Prefer **permissions** in the UI, not role name strings

- Gate on `finance.invoice.create`, not `role === "accountant"`.
- Roles are bundles that change; action strings are stable and match the backend `ACTIONS` list.
- Share one catalog of permission codes (generated or mirrored from backend) to avoid drift.

### 3. Load effective grants once per org context

- On bootstrap / org switch: fetch grants (or me/context payload that includes them), cache in org-scoped client state.
- Invalidate on org switch, sign-out, and permission-version / grant change (parity plan already requires this).
- Never accept role/permission lists from the client request body as truth.

### 4. Hide vs disable

| Situation | UI pattern |
|-----------|------------|
| Role should never use the feature (viewer → Settings → Grants) | **Hide** nav item and route affordance |
| Action exists but blocked by plan / missing grant / SoD | **Disable** with short reason, or empty state “Ask an admin for `finance.document.approve`” |
| Soft upsell (not UAP’s model today) | Fallback CTA — N/A for finance RBAC |

For accounting apps, prefer **hide** for whole modules the grant set cannot reach; use **disable + reason** on in-page actions the user can see but not execute (e.g. Approve on an invoice they can read).

### 5. Route and data layers

- Client route guards: redirect/forbidden page if `can(viewModule)` is false — still UX only.
- List/detail queries: handle 403 without leaking existence of forbidden resources where the API supports it.
- Do not render columns or export actions the user cannot access (field-level when backend supports it later).

### 6. Workflow + segregation of duties (finance-specific)

- Permission alone is not enough: re-check **document state** (draft → submit → approve → post) on every action.
- SoD: UI should not offer “create + approve + pay” as one persona when grants forbid combinations; backend must still reject conflicts.
- Approvals (`finance.document.approve`) and posting (`finance.document.post`) are separate affordances.

### 7. Recommended UAP frontend shape (when implementing)

```text
useFinancePermissions()     // effective action set for current org
can("finance.invoice.create")
<Can action="…">…</Can>    // hide children if false
nav.ts                      // each child declares requiredPermission?: ACTION
module pages                // list/create/approve buttons gated per action
```

Map modules roughly:

| Nav area | Example permissions |
|----------|---------------------|
| Sales invoices | `finance.invoice.create`, `finance.document.post`, `finance.document.approve` |
| Purchases bills | `finance.bill.create`, same post/approve |
| Payments | `finance.payment.record` |
| Accountant journals | `finance.journal.*` |
| Reports | `finance.report.view` |
| Settings / roles / grants | `finance.access.manage`, `finance.settings.configure` |

### 8. Anti-patterns to avoid

- Checking only `isOwner` / Clerk public metadata for finance actions.
- Trusting Zustand/localStorage permission caches across org switches.
- Showing disabled Admin everywhere (leaks surface area; prefer hide).
- Duplicating a second incompatible permission vocabulary on the frontend.

## Decision for placeholders (now)

Module placeholder copy must state that **RBAC (permission-gated nav and actions)** will apply when lists/forms/CRUD land, driven by backend grants — not role strings hardcoded in React.
