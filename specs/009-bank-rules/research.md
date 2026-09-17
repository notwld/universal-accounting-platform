# Research: Bank Rules

## Match text

- Decision: case-insensitive substring (`contains`).
- Rationale: covers bank-fee memos without a regex engine.
- Alternatives: regex (too sharp for clerks), exact match (too brittle).

## Apply timing

- Decision: explicit `POST .../bank-rules/apply` after the accountant matches payments. Do not auto-apply on import.
- Rationale: auto-apply on import would categorize a payment that should be matched (no second cash journal).
- Alternatives: apply-on-import with match-first heuristics (ambiguous duplicates).

## Posting

- Decision: call existing `categorize_line`; stable idempotency key `bank-rule:{line_id}`.
- Rationale: one posting path; replay is `already_matched`.
- Alternatives: a second generated journal type (duplicate engine).
