# Quickstart — purchases payables (API only)

Reuse 002 org setup and 003 tax/FX. Add AP control account (`control_kind=ap`), expense account, tax account, vendor-advance asset, cash, FX loss expense.

1. Contact vendor, item (expense account), tax 10% exclusive.
2. Bill lines net 100 + tax → draft → preview → post. Journal Dr expense 100 Dr tax 10 Cr AP 110.
3. Vendor payment 60 allocated to bill. Outstanding 50.
4. Payment 80 → AP 0, vendor advance 30.
5. Replay post idempotency key → same bill.
6. Paid expense 50 + tax 5 from bank → no AP movement.
7. EUR bill: store rate 1.10, post EUR 100, pay at 1.15 → realized loss 5.
8. `GET ap-aging?as_of=` before payment still lists the bill.
9. Purchasing Clerk cannot post. Sales Clerk cannot create bills.

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\finance\tests -q
```
