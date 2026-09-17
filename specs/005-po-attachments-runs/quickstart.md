# Quickstart

1. PO lines → convert → bill draft → TB still empty until bill post.
2. Attach `receipt.pdf` to the bill; download; second org 404.
3. Post two bills; payment-run both; AP 0.
4. Vendor statement lists those bills/payments.
5. Credit an open invoice; vendor-credit an open bill.

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\finance\tests -q
```
