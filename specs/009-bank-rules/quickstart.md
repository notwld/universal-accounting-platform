# Quickstart: Bank Rules

1. Import a statement with an unmatched fee and a payment already matched.
2. `POST /bank-rules` with `pattern: "bank fee"`, expense `account_id`.
3. `POST /bank-rules/apply` — fee categorized, payment untouched.
4. Apply again — `categorized` empty.

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\finance\tests\test_bank_rules.py -q
```
