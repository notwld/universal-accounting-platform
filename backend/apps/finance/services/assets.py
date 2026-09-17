from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Account,
    AssetCharge,
    FinanceIdempotency,
    FinanceSettings,
    FixedAsset,
    JournalEntry,
    JournalLine,
)
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.posting import post_generated
from apps.finance.services.sequence import next_document_number


def _settings(org) -> FinanceSettings:
    s = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
    if not s:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return s


def _account(org, account_id):
    acc = Account.objects.filter(id=account_id, organization=org, status=Account.Status.ACTIVE).first()
    if not acc:
        raise AuthAPIError("cross_organization", "Account not found")
    return acc


def _date(value) -> date:
    if isinstance(value, date) and not isinstance(value, str):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise AuthAPIError("validation_error", "Invalid date") from exc


def _month_end(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _add_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _nbv(asset: FixedAsset, exponent: int) -> Decimal:
    return quantize_amount(asset.cost - asset.accum, exponent)


def _monthly(asset: FixedAsset, exponent: int) -> Decimal:
    if asset.life_months < 1:
        raise AuthAPIError("validation_error", "life_months must be at least 1")
    return quantize_amount((asset.cost - asset.residual) / asset.life_months, exponent)


def _room(asset: FixedAsset, exponent: int) -> Decimal:
    return quantize_amount(asset.cost - asset.residual - asset.accum, exponent)


def _months(asset: FixedAsset, through: date) -> list[date]:
    cur = date(asset.in_service_date.year, asset.in_service_date.month, 1)
    out = []
    for _ in range(asset.life_months):
        end = _month_end(cur)
        if end > through:
            break
        out.append(cur)
        cur = _add_month(cur)
    return out


def _post_charge(*, user_id, org, asset, kind, period, amount, entry_date, exponent, key):
    if amount <= 0:
        return
    journal = post_generated(
        user_id=user_id,
        org=org,
        entry_date=entry_date,
        source_type=JournalEntry.Source.ASSET,
        memo=f"{kind} {asset.number}",
        gl_lines=[
            {"account_id": asset.expense_account_id, "debit": str(amount), "credit": "0", "description": kind},
            {"account_id": asset.accum_account_id, "debit": "0", "credit": str(amount), "description": kind},
        ],
        idempotency_key=key,
        body={"asset_id": asset.id, "kind": kind, "period": str(period), "amount": str(amount)},
    )
    AssetCharge.objects.create(
        organization=org, asset=asset, kind=kind, period=period, amount=amount, journal=journal
    )
    asset.accum = quantize_amount(asset.accum + amount, exponent)
    asset.save(update_fields=["accum"])


def _require_active(asset: FixedAsset):
    if not asset or asset.status != FixedAsset.Status.ACTIVE:
        raise AuthAPIError("validation_error", "Asset is not active")


def capitalize(*, user_id, org, payload, idempotency_key):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    cost = quantize_amount(Decimal(str(payload.get("cost") or 0)), exponent)
    residual = quantize_amount(Decimal(str(payload.get("residual") or 0)), exponent)
    try:
        life = int(payload.get("life_months") or 0)
    except (TypeError, ValueError) as exc:
        raise AuthAPIError("validation_error", "Invalid life_months") from exc
    if cost <= 0 or residual < 0 or residual > cost or life < 1:
        raise AuthAPIError("validation_error", "Invalid cost, residual, or life")
    name = (payload.get("name") or "").strip()
    if not name:
        raise AuthAPIError("validation_error", "Name is required")
    in_service = _date(payload.get("in_service_date"))
    cost_acc = _account(org, payload.get("cost_account_id"))
    accum_acc = _account(org, payload.get("accum_account_id"))
    exp_acc = _account(org, payload.get("expense_account_id"))
    credit_acc = _account(org, payload.get("credit_account_id"))
    with finance_tx(user_id=user_id, organization_id=org.id):
        existing = FinanceIdempotency.objects.filter(
            organization=org, operation="asset.post", key=idempotency_key
        ).select_related("journal").first()
        if existing and existing.journal_id:
            asset = FixedAsset.objects.filter(organization=org, journal_id=existing.journal_id).first()
            if asset:
                return asset, existing.journal
        number = next_document_number(org, "asset", "FA-")
        journal = post_generated(
            user_id=user_id,
            org=org,
            entry_date=in_service,
            source_type=JournalEntry.Source.ASSET,
            memo=f"capitalize {number}",
            gl_lines=[
                {"account_id": cost_acc.id, "debit": str(cost), "credit": "0", "description": name},
                {"account_id": credit_acc.id, "debit": "0", "credit": str(cost), "description": name},
            ],
            idempotency_key=idempotency_key,
            body={"name": name, "cost": str(cost), "in_service": str(in_service)},
        )
        asset = FixedAsset.objects.create(
            organization=org,
            number=number,
            name=name[:255],
            cost=cost,
            residual=residual,
            life_months=life,
            in_service_date=in_service,
            cost_account=cost_acc,
            accum_account=accum_acc,
            expense_account=exp_acc,
            journal=journal,
        )
        return asset, journal


def _run_depreciation(*, user_id, org, through, idempotency_key, asset_id, exponent):
    qs = FixedAsset.objects.select_for_update().filter(organization=org, status=FixedAsset.Status.ACTIVE)
    if asset_id:
        qs = qs.filter(pk=asset_id)
        if not qs.exists():
            raise AuthAPIError("validation_error", "Asset is not active")
    charged = 0
    for asset in qs:
        for period in _months(asset, through):
            if AssetCharge.objects.filter(asset=asset, kind=AssetCharge.Kind.DEPRECIATE, period=period).exists():
                continue
            amount = min(_monthly(asset, exponent), _room(asset, exponent))
            if amount <= 0:
                continue
            _post_charge(
                user_id=user_id, org=org, asset=asset, kind=AssetCharge.Kind.DEPRECIATE,
                period=period, amount=amount, entry_date=_month_end(period), exponent=exponent,
                key=f"{idempotency_key}:{asset.id}:{period}",
            )
            charged += 1
    return charged


def depreciate(*, user_id, org, through_date, idempotency_key, asset_id=None):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    through = _date(through_date)
    with finance_tx(user_id=user_id, organization_id=org.id):
        return _run_depreciation(
            user_id=user_id, org=org, through=through, idempotency_key=idempotency_key,
            asset_id=asset_id, exponent=exponent,
        )


def write_down(*, user_id, org, asset_id, amount, entry_date, idempotency_key):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    amt = quantize_amount(Decimal(str(amount or 0)), exponent)
    when = _date(entry_date)
    if amt <= 0:
        raise AuthAPIError("validation_error", "amount must be positive")
    with finance_tx(user_id=user_id, organization_id=org.id):
        asset = FixedAsset.objects.select_for_update().filter(id=asset_id, organization=org).first()
        _require_active(asset)
        room = _room(asset, exponent)
        if amt > room:
            raise AuthAPIError("validation_error", "Write-down exceeds net book value")
        _post_charge(
            user_id=user_id, org=org, asset=asset, kind=AssetCharge.Kind.WRITE_DOWN,
            period=when, amount=amt, entry_date=when, exponent=exponent, key=idempotency_key,
        )
        return asset


def dispose(*, user_id, org, asset_id, entry_date, proceeds, proceeds_account_id, gain_loss_account_id, idempotency_key):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    when = _date(entry_date)
    proceeds = quantize_amount(Decimal(str(proceeds or 0)), exponent)
    if proceeds < 0:
        raise AuthAPIError("validation_error", "proceeds cannot be negative")
    if proceeds > 0 and not proceeds_account_id:
        raise AuthAPIError("validation_error", "proceeds_account_id is required")
    gain_acc = _account(org, gain_loss_account_id)
    proceeds_acc = _account(org, proceeds_account_id) if proceeds > 0 else None
    with finance_tx(user_id=user_id, organization_id=org.id):
        asset = FixedAsset.objects.select_for_update().filter(id=asset_id, organization=org).first()
        _require_active(asset)
        _run_depreciation(
            user_id=user_id, org=org, through=when - timedelta(days=1),
            idempotency_key=f"{idempotency_key}:catchup", asset_id=asset.id, exponent=exponent,
        )
        asset.refresh_from_db()
        nbv = _nbv(asset, exponent)
        delta = quantize_amount(proceeds - nbv, exponent)
        gl = []
        if asset.accum:
            gl.append({"account_id": asset.accum_account_id, "debit": str(asset.accum), "credit": "0", "description": "accum"})
        if proceeds:
            gl.append({"account_id": proceeds_acc.id, "debit": str(proceeds), "credit": "0", "description": "proceeds"})
        if delta < 0:
            gl.append({"account_id": gain_acc.id, "debit": str(-delta), "credit": "0", "description": "loss"})
        gl.append({"account_id": asset.cost_account_id, "debit": "0", "credit": str(asset.cost), "description": "cost"})
        if delta > 0:
            gl.append({"account_id": gain_acc.id, "debit": "0", "credit": str(delta), "description": "gain"})
        journal = post_generated(
            user_id=user_id, org=org, entry_date=when, source_type=JournalEntry.Source.ASSET,
            memo=f"dispose {asset.number}", gl_lines=gl, idempotency_key=idempotency_key,
            body={"asset_id": asset.id, "proceeds": str(proceeds)},
        )
        asset.status = FixedAsset.Status.DISPOSED
        asset.disposed_on = when
        asset.save(update_fields=["status", "disposed_on"])
        return asset, journal


def _net(org, account_ids, exponent):
    if not account_ids:
        return Decimal("0")
    agg = JournalLine.objects.filter(
        organization=org, account_id__in=account_ids, journal__status=JournalEntry.Status.POSTED
    ).aggregate(d=Sum("debit"), c=Sum("credit"))
    return quantize_amount((agg["d"] or 0) - (agg["c"] or 0), exponent)


def register(*, org):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    rows = []
    active_nbv = Decimal("0")
    cost_ids, accum_ids = set(), set()
    for a in FixedAsset.objects.filter(organization=org):
        nbv = _nbv(a, exponent)
        if a.status == FixedAsset.Status.ACTIVE:
            active_nbv += nbv
        cost_ids.add(a.cost_account_id)
        accum_ids.add(a.accum_account_id)
        rows.append(
            {
                "id": a.id,
                "number": a.number,
                "name": a.name,
                "cost": str(quantize_amount(a.cost, exponent)),
                "accum": str(quantize_amount(a.accum, exponent)),
                "nbv": str(nbv),
                "status": a.status,
            }
        )
    gl_nbv = _net(org, cost_ids, exponent) + _net(org, accum_ids, exponent)
    return {
        "items": rows,
        "register_nbv": str(quantize_amount(active_nbv, exponent)),
        "gl_nbv": str(gl_nbv),
    }
