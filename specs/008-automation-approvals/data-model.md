# Data Model

RecurringSchedule: frequency monthly|weekly|yearly, weekday, month_of_year, auto_post; day_of_month nullable.

Invoice/Bill: pending|approved statuses; created_by; approved_by.

FinanceSettings: require_document_approval, allow_self_approve.

ReminderRule: document_kind, days_before_due, active.
Reminder: rule, object_type, object_id, due_date unique with rule.
