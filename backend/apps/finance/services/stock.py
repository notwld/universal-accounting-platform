from decimal import Decimal

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    FinanceSettings,
    Item,
    JournalEntry,
    StockBalance,
    StockMove,
    Warehouse,
)
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.posting import post_generated


def _settings(org) -> FinanceSettings:
    s = FinanceSettings.objects.select_related("base_currency", "inventory_account", "cogs_account").filter(
        organization=org
    ).first()
    if not s:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return s


def require_stock_accounts(settings: FinanceSettings):
    if not settings.inventory_account_id or not settings.cogs_account_id:
        raise AuthAPIError("validation_error", "Inventory and COGS accounts are required")


def default_warehouse(org) -> Warehouse:
    wh, _ = Warehouse.objects.get_or_create(organization=org, name="Main")
    return wh


def _balance(*, org, warehouse, item):
    bal, _ = StockBalance.objects.get_or_create(
        organization=org, warehouse=warehouse, item=item, defaults={"qty": 0, "value": 0}
    )
    return StockBalance.objects.select_for_update().get(pk=bal.pk)


def _avg(bal: StockBalance, exponent: int) -> Decimal:
    if bal.qty <= 0:
        return Decimal("0")
    return quantize_amount(bal.value / bal.qty, exponent)


def _move(*, org, warehouse, item, kind, qty, unit_cost, source_type, source_id, entry_date, exponent):
    qty = Decimal(str(qty))
    bal = _balance(org=org, warehouse=warehouse, item=item)
    if qty > 0:
        unit_cost = quantize_amount(Decimal(str(unit_cost)), exponent)
        value = quantize_amount(qty * unit_cost, exponent)
        bal.qty = quantize_amount(bal.qty + qty, exponent)
        bal.value = quantize_amount(bal.value + value, exponent)
    else:
        need = -qty
        avg = _avg(bal, exponent)
        given = Decimal(str(unit_cost or 0))
        unit_cost = quantize_amount(given if given else avg, exponent)
        if bal.qty < need:
            raise AuthAPIError("negative_stock", "Insufficient stock")
        value = quantize_amount(need * unit_cost, exponent)
        bal.qty = quantize_amount(bal.qty - need, exponent)
        bal.value = quantize_amount(bal.value - value, exponent)
        if bal.qty == 0:
            bal.value = Decimal("0")
    bal.save(update_fields=["qty", "value"])
    StockMove.objects.create(
        organization=org,
        warehouse=warehouse,
        item=item,
        kind=kind,
        qty=qty,
        unit_cost=unit_cost,
        value=value,
        source_type=source_type,
        source_id=source_id or "",
        entry_date=entry_date,
    )
    return unit_cost, value


def receive_line(*, org, item, qty, cost, source_type, source_id, entry_date, warehouse=None):
    if not item.tracked:
        return Decimal("0")
    settings = _settings(org)
    require_stock_accounts(settings)
    wh = warehouse or default_warehouse(org)
    _move(
        org=org,
        warehouse=wh,
        item=item,
        kind=StockMove.Kind.RECEIVE,
        qty=qty,
        unit_cost=Decimal(str(cost)) / Decimal(str(qty)) if Decimal(str(qty)) else 0,
        source_type=source_type,
        source_id=source_id,
        entry_date=entry_date,
        exponent=settings.base_currency.exponent,
    )
    return Decimal(str(cost))


def issue_line(*, org, item, qty, source_type, source_id, entry_date, warehouse=None):
    if not item.tracked:
        return Decimal("0")
    settings = _settings(org)
    require_stock_accounts(settings)
    wh = warehouse or default_warehouse(org)
    _cost, value = _move(
        org=org,
        warehouse=wh,
        item=item,
        kind=StockMove.Kind.ISSUE,
        qty=-Decimal(str(qty)),
        unit_cost=0,
        source_type=source_type,
        source_id=source_id,
        entry_date=entry_date,
        exponent=settings.base_currency.exponent,
    )
    return value


def reverse_moves(*, org, source_type, source_id, entry_date, new_source_type, new_source_id):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    gl_value = Decimal("0")
    moves = list(StockMove.objects.filter(organization=org, source_type=source_type, source_id=source_id))
    for move in moves:
        item = move.item
        if move.kind == StockMove.Kind.RECEIVE:
            _move(
                org=org,
                warehouse=move.warehouse,
                item=item,
                kind=StockMove.Kind.ISSUE,
                qty=-move.qty,
                unit_cost=move.unit_cost,
                source_type=new_source_type,
                source_id=new_source_id,
                entry_date=entry_date,
                exponent=exponent,
            )
            gl_value += move.value
        elif move.kind == StockMove.Kind.ISSUE:
            _move(
                org=org,
                warehouse=move.warehouse,
                item=item,
                kind=StockMove.Kind.RECEIVE,
                qty=-move.qty if move.qty < 0 else move.qty,
                unit_cost=move.unit_cost,
                source_type=new_source_type,
                source_id=new_source_id,
                entry_date=entry_date,
                exponent=exponent,
            )
            gl_value += move.value
    return gl_value


def adjust_stock(*, user_id, org, warehouse_id, item_id, quantity, unit_cost, entry_date, idempotency_key):
    settings = _settings(org)
    require_stock_accounts(settings)
    exponent = settings.base_currency.exponent
    qty = Decimal(str(quantity))
    if qty == 0:
        raise AuthAPIError("validation_error", "quantity cannot be zero")
    with finance_tx(user_id=user_id, organization_id=org.id):
        item = Item.objects.filter(id=item_id, organization=org, tracked=True).first()
        if not item:
            raise AuthAPIError("cross_organization", "Tracked item not found")
        wh = Warehouse.objects.filter(id=warehouse_id, organization=org).first()
        if not wh:
            raise AuthAPIError("cross_organization", "Warehouse not found")
        if qty > 0:
            cost = Decimal(str(unit_cost or 0))
            if cost <= 0:
                cost = _avg(_balance(org=org, warehouse=wh, item=item), exponent)
            unit, value = _move(
                org=org, warehouse=wh, item=item, kind=StockMove.Kind.ADJUST, qty=qty,
                unit_cost=cost, source_type="adjust", source_id="", entry_date=entry_date, exponent=exponent,
            )
            gl = [
                {"account_id": settings.inventory_account_id, "debit": str(value), "credit": "0", "description": "adjust"},
                {"account_id": settings.cogs_account_id, "debit": "0", "credit": str(value), "description": "adjust"},
            ]
        else:
            unit, value = _move(
                org=org, warehouse=wh, item=item, kind=StockMove.Kind.ADJUST, qty=qty,
                unit_cost=0, source_type="adjust", source_id="", entry_date=entry_date, exponent=exponent,
            )
            gl = [
                {"account_id": settings.cogs_account_id, "debit": str(value), "credit": "0", "description": "adjust"},
                {"account_id": settings.inventory_account_id, "debit": "0", "credit": str(value), "description": "adjust"},
            ]
        journal = post_generated(
            user_id=user_id, org=org, entry_date=entry_date, source_type=JournalEntry.Source.STOCK,
            memo="stock adjust", gl_lines=gl, idempotency_key=idempotency_key,
            body={"item_id": item_id, "warehouse_id": warehouse_id, "qty": str(qty)},
        )
        return journal, item, wh


def transfer_stock(*, user_id, org, from_warehouse_id, to_warehouse_id, item_id, quantity, entry_date):
    if from_warehouse_id == to_warehouse_id:
        raise AuthAPIError("validation_error", "Warehouses must differ")
    qty = Decimal(str(quantity))
    if qty <= 0:
        raise AuthAPIError("validation_error", "quantity must be positive")
    with finance_tx(user_id=user_id, organization_id=org.id):
        settings = _settings(org)
        exponent = settings.base_currency.exponent
        item = Item.objects.filter(id=item_id, organization=org, tracked=True).first()
        if not item:
            raise AuthAPIError("cross_organization", "Tracked item not found")
        src = Warehouse.objects.filter(id=from_warehouse_id, organization=org).first()
        dst = Warehouse.objects.filter(id=to_warehouse_id, organization=org).first()
        if not src or not dst:
            raise AuthAPIError("cross_organization", "Warehouse not found")
        unit, value = _move(
            org=org, warehouse=src, item=item, kind=StockMove.Kind.TRANSFER, qty=-qty,
            unit_cost=0, source_type="transfer", source_id="", entry_date=entry_date, exponent=exponent,
        )
        _move(
            org=org, warehouse=dst, item=item, kind=StockMove.Kind.TRANSFER, qty=qty,
            unit_cost=unit, source_type="transfer", source_id="", entry_date=entry_date, exponent=exponent,
        )
        return src, dst, item


def valuation(*, org):
    settings = _settings(org)
    exponent = settings.base_currency.exponent
    rows = []
    total = Decimal("0")
    for bal in StockBalance.objects.filter(organization=org).select_related("item", "warehouse"):
        total += bal.value
        rows.append(
            {
                "item_id": bal.item_id,
                "sku": bal.item.sku,
                "warehouse_id": bal.warehouse_id,
                "warehouse": bal.warehouse.name,
                "qty": str(quantize_amount(bal.qty, exponent)),
                "value": str(quantize_amount(bal.value, exponent)),
            }
        )
    gl = Decimal("0")
    if settings.inventory_account_id:
        from django.db.models import Sum
        from apps.finance.models import JournalLine

        agg = JournalLine.objects.filter(
            organization=org,
            account_id=settings.inventory_account_id,
            journal__status=JournalEntry.Status.POSTED,
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        gl = quantize_amount((agg["d"] or 0) - (agg["c"] or 0), exponent)
    return {"items": rows, "stock_total": str(quantize_amount(total, exponent)), "gl_inventory": str(gl)}
