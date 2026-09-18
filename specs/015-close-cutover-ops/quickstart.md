# Quickstart

1. Accrual 50, reverse on date, P&L nets to 0.
2. EUR invoice 100 @ 1.00, revalue @ 1.10, AR +10.
3. Lock period, post in range → `period_closed`.
4. Cutover openings, then history → `validation_error`.
5. Webhook deliver with mocked 500 until `dead`.
6. `pytest apps/finance/tests` ; Postgres job uses `uap` then `uap_app`.
