# Research

## Cadence
- **Decision**: Monthly only; clamp day-of-month to last day of month.
- **Rationale**: Phase 5 names month-end explicitly. Weekly/yearly later.

## Draft vs post
- **Decision**: Invoice/bill stay draft. Expense posts with idempotency `recurring:{schedule}:{date}`.
- **Rationale**: Auto-posting AR/AP without approval is unsafe; paid expenses are already immediate in the product.

## Jobs
- **Decision**: Shared `run_due` called from HTTP and a daily Celery task.
- **Rationale**: Tests need an explicit as-of; production needs a clock.
