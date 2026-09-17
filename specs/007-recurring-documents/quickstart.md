# Quickstart

Create a monthly invoice schedule, POST `/recurring/run` with `as_of`, confirm one draft per date.

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest apps\finance\tests\test_recurring.py -q
```
