# Research

## Cash flow

- Decision: indirect statement from account `cashflow_kind` plus P&L net income.
- Rationale: one classification field; ties to cash accounts without a second engine.
- Alternatives: direct method by document source (fragile); FAS 95 worksheets.

## Tags

- Decision: optional FK on `JournalLine`, unique name per org.
- Rationale: FIN-08 flat labels; SavedFilter already stores list queries.
- Alternatives: tag groups, line splits across tags (deferred).

## Comparatives

- Decision: extra query params; nest `prior` beside unchanged current keys.
- Rationale: existing banking tests read `expense_total` at the top level.
- Alternatives: new `/reports/comparative-*` routes (more surface).
