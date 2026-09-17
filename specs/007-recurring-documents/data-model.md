# Data Model

### RecurringSchedule
organization, kind invoice|bill|expense, status active|paused, contact, currency, day_of_month (1–31), start_on, next_on, end_on nullable, lines JSON, bank_account nullable (expense), created_by, fx_rate

### RecurringOccurrence
organization, schedule, occurs_on unique (schedule, occurs_on), invoice/bill/expense FKs nullable
