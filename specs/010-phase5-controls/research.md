# Research: Phase 5 Controls

## Email

- Decision: `django.core.mail.send_mail` to contact.email when a reminder row is first created.
- Rationale: SMTP already configured; Clerk still owns OTP.
- Alternatives: SMS (out of scope), Celery-only send (HTTP run would hide failures from the test).

## Regex / amount / auto-apply

- Decision: `match_kind` contains|regex; signed `amount_min`/`amount_max`; call `apply_bank_rules` after import.
- Rationale: one matching engine; import is when unmatched fees appear.
- Alternatives: auto-apply only via cron (extra hop).

## XLS / OFX / QIF / feeds

- Decision: parse every format into `(date, amount, description)` then existing fingerprint/match/categorize. Feeds = stored HTTPS file URL + fetch. `xlrd` for BIFF `.xls`.
- Rationale: user asked for these file types; no named open-banking provider, so no Plaid client.
- Alternatives: live bank APIs (blocked until a named provider is chosen).

## Approvals

- Decision: threshold 0 = all docs; levels = distinct ApprovalAction rows.
- Rationale: extends current pending/approved without a workflow engine.
- Alternatives: per-role chains (not requested).
