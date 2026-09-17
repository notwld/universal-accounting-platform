# Data Model

## Item

`tracked` boolean default false. Tracked requires `kind=good`.

## FinanceSettings

`inventory_account`, `cogs_account` optional FKs.

## Warehouse

organization, name. Unique (org, name). Table `finance_warehouse`.

## StockBalance

organization, warehouse, item, qty, value. Unique (warehouse, item). Table `finance_stock_balance`.

## StockMove

organization, warehouse, item, kind receive|issue|adjust|transfer, qty (signed), unit_cost, value, source_type, source_id, entry_date. Table `finance_stock_move`.

RLS ENABLE without FORCE.
