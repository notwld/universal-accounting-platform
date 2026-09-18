# Finance STRIDE (B12) — tenant isolation, posting, files, exports

| Threat | Control in this repo |
|---|---|
| Spoofing | Clerk JWT; org header only after membership |
| Tampering | Posted journals immutable; recon complete locks the bank account dates |
| Repudiation | FinanceAuditEvent on post, lock, recon, grants |
| Information disclosure | RLS + org_get; attachments sniffed; export requires step-up |
| Denial of service | Export throttle 30/min; attachment size cap |
| Elevation | Separate list vs command permissions; step-up on reopen, roles, base-currency change, export |

Country packs, live bank, and outbound webhooks are out of scope until named.
