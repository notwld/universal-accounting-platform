# Research

- Decision: Accrual/deferral = one reversing journal pair. No prepaid amortization table.
- Decision: Unrealized FX = reverse prior reval, then restate remaining AR/AP `remain/total * base_total` vs `remain * rate(as_of)`. Realized stays on payment.
- Decision: Cutover XOR stored on `FinanceSettings.cutover_mode`; stages are sequential.
- Decision: Webhooks = HMAC-SHA256 outbox + deliver command. No Svix hosted outbound (Svix is inbound Clerk only).
- Decision: PDF = minimal PDF 1.4 text page. Golden = JSON TB expected amounts.
- Decision: CI = migrate as `uap`, pytest as `uap_app`. Load = query-count ceiling. SLO = YAML rules. Backup = runbook + exercise script.
