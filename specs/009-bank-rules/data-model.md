# Data Model: Bank Rules

## BankRule

| Field | Rule |
|---|---|
| id | uuid string PK |
| organization | FK, required |
| pattern | non-empty string, max 255; matched case-insensitive against BankLine.description |
| account | FK Account in same org; active; not `is_control` |
| direction | any \| inflow \| outflow (default any) |
| priority | integer, default 0; lower applied first, then id |
| active | boolean, default true |

Table: `finance_bank_rule`. RLS ENABLE without FORCE.

Apply considers `BankLine.status=imported` only. First matching active rule wins.
