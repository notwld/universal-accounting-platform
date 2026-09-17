# Quickstart — sales collection (API only)

Reuse 002 org setup. Add AR control account (`control_kind=ar`), income account, tax payable, advance liability, cash, FX gain income.

1. Contact customer, item (income account), tax 10% exclusive, term net 0.
2. Quote lines net 100 + tax → convert → invoice draft → preview → post. Journal Dr AR 110 Cr income 100 Cr tax 10.
3. Payment 60 to cash allocated to invoice. Outstanding 50.
4. Payment 80 → AR 0, advance 30.
5. Replay post idempotency key → same invoice.
6. EUR invoice: store rate 1.10, post EUR 100, pay at 1.15 → realized gain 5.
7. `GET ar-aging?as_of=` before payment still lists the invoice.
8. Sales Clerk token cannot post. Org B cannot see A's invoices.

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\finance\tests -q
```
