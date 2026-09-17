# Data Model

## FixedAsset

organization, number, name, cost, residual, life_months, in_service_date, accum, status active|disposed, disposed_on (nullable).
cost_account, accum_account, expense_account FKs.
Unique (org, number). Table `finance_fixed_asset`.

## AssetCharge

organization, asset, kind depreciate|write_down, period (first of month; write-down uses entry month), amount, journal FK.
Unique (asset, kind, period) for depreciate uniqueness; write-down uses distinct kind so same month is allowed.
Table `finance_asset_charge`.

JournalEntry.Source.ASSET = `asset`.

RLS ENABLE without FORCE.
