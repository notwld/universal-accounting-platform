# Data Model

## ReportingTag

organization, name. Unique (org, name). Table `finance_reporting_tag`.

## Account

`cashflow_kind` char: `cash` | `operating` | `investing` | `financing` | empty.

## JournalLine

`tag` optional FK to ReportingTag.

RLS ENABLE without FORCE on `finance_reporting_tag`.
