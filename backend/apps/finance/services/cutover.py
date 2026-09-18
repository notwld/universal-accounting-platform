from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import Account, Contact, FinanceSettings, Item, JournalEntry
from apps.finance.services.context import finance_tx
from apps.finance.services.posting import post_generated, post_journal, replace_draft_lines
from apps.finance.services.resolve import org_get

STAGES = ["settings_chart", "masters", "balances", "documents", "bank", "transactions"]


def _settings(org):
    s = FinanceSettings.objects.filter(organization=org).first()
    if not s:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return s


def _next_stage(current):
    if not current:
        return STAGES[0]
    idx = STAGES.index(current)
    if idx + 1 >= len(STAGES):
        return None
    return STAGES[idx + 1]


def run_cutover(*, user_id, org, mode, stage, dry_run, rows):
    if mode not in ("openings", "history"):
        raise AuthAPIError("validation_error", "mode must be openings or history")
    if stage not in STAGES:
        raise AuthAPIError("validation_error", "Unknown cutover stage")
    settings = _settings(org)
    if settings.cutover_mode and settings.cutover_mode != mode:
        raise AuthAPIError("validation_error", "Cutover mode already locked")
    expected = _next_stage(settings.cutover_stage)
    if expected is None:
        raise AuthAPIError("validation_error", "Cutover is complete")
    if stage != expected:
        raise AuthAPIError("validation_error", f"Next stage is {expected}")
    rows = list(rows or [])
    created = []
    if dry_run:
        _validate_stage(org, mode, stage, rows)
        return {"dry_run": True, "stage": stage, "mode": mode, "created": [], "count": len(rows)}
    with finance_tx(user_id=user_id, organization_id=org.id):
        created = _apply_stage(user_id=user_id, org=org, mode=mode, stage=stage, rows=rows)
        settings.cutover_mode = mode
        settings.cutover_stage = stage
        settings.save(update_fields=["cutover_mode", "cutover_stage"])
    return {"dry_run": False, "stage": stage, "mode": mode, "created": created, "count": len(created)}


def _validate_stage(org, mode, stage, rows):
    if stage == "balances":
        has_lines = any(isinstance(r, dict) and r.get("lines") for r in rows)
        if mode == "openings" and has_lines:
            raise AuthAPIError("validation_error", "History journals are not allowed in openings mode")
        if mode == "history" and rows and not has_lines:
            raise AuthAPIError("validation_error", "Opening balance rows are not allowed in history mode")


def _apply_stage(*, user_id, org, mode, stage, rows):
    _validate_stage(org, mode, stage, rows)
    created = []
    if stage == "settings_chart":
        for row in rows:
            acc, _ = Account.objects.get_or_create(
                organization=org,
                code=row.get("code"),
                defaults={"name": row.get("name") or row.get("code"), "classification": row.get("classification") or "asset"},
            )
            created.append(acc.id)
    elif stage == "masters":
        for row in rows:
            kind = row.get("kind") or ("item" if row.get("sku") else "contact")
            if kind == "item":
                if not row.get("income_account_id"):
                    raise AuthAPIError("validation_error", "income_account_id is required")
                item, _ = Item.objects.get_or_create(
                    organization=org,
                    sku=row.get("sku"),
                    defaults={
                        "name": row.get("name") or row.get("sku"),
                        "unit_price": row.get("unit_price") or 0,
                        "income_account_id": row.get("income_account_id"),
                        "expense_account_id": row.get("expense_account_id"),
                    },
                )
                created.append(item.id)
            else:
                c, _ = Contact.objects.get_or_create(
                    organization=org,
                    name=row.get("name"),
                    defaults={"is_customer": bool(row.get("is_customer", True)), "is_vendor": bool(row.get("is_vendor"))},
                )
                created.append(c.id)
    elif stage == "balances":
        if mode == "openings":
            if rows:
                journal = JournalEntry.objects.create(
                    organization=org, entry_date=rows[0].get("entry_date") or "2026-01-01",
                    source_type=JournalEntry.Source.OPENING, memo="cutover opening",
                )
                replace_draft_lines(journal, [{"account_id": _acct(org, r), "debit": r.get("debit") or 0, "credit": r.get("credit") or 0} for r in rows])
                posted = post_journal(
                    user_id=user_id, org=org, journal_id=journal.id, version=journal.version,
                    idempotency_key=f"cutover-open:{org.id}:{stage}",
                    body={"stage": stage, "mode": mode},
                )
                created.append(posted.id)
        else:
            for i, row in enumerate(rows):
                posted = post_generated(
                    user_id=user_id,
                    org=org,
                    entry_date=row.get("entry_date"),
                    source_type=row.get("source_type") or JournalEntry.Source.MANUAL,
                    memo=row.get("memo") or "cutover history",
                    gl_lines=row.get("lines") or [],
                    idempotency_key=f"cutover-hist:{org.id}:{i}",
                    body={"stage": stage, "i": i},
                )
                created.append(posted.id)
    elif stage in ("documents", "bank", "transactions"):
        if rows:
            raise AuthAPIError("validation_error", f"{stage} rows are not imported; send [] to skip")
        created = []
    return created


def _acct(org, row):
    if row.get("account_id"):
        return org_get(Account, org, row["account_id"]).id
    acc = Account.objects.filter(organization=org, code=row.get("account_code")).first()
    if not acc:
        raise AuthAPIError("validation_error", "Unknown account_code")
    return acc.id
