from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import JournalEntry, JournalLine
from apps.finance.services.money import quantize_amount


def _posted_lines(*, org, start=None, end=None, as_of=None, tag_id=None):
    qs = JournalLine.objects.filter(organization=org, journal__status=JournalEntry.Status.POSTED)
    if start:
        qs = qs.filter(journal__entry_date__gte=start)
    if end:
        qs = qs.filter(journal__entry_date__lte=end)
    if as_of:
        qs = qs.filter(journal__entry_date__lte=as_of)
    if tag_id:
        qs = qs.filter(tag_id=tag_id)
    return qs


def trial_balance(*, org, start, end, exponent: int, tag_id=None):
    qs = _posted_lines(org=org, start=start, end=end, tag_id=tag_id)
    rows = (
        qs.values("account_id", "account__code", "account__name")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )
    out = []
    for row in rows:
        debit = quantize_amount(row["debit"] or 0, exponent)
        credit = quantize_amount(row["credit"] or 0, exponent)
        out.append(
            {
                "account_id": row["account_id"],
                "code": row["account__code"],
                "name": row["account__name"],
                "debit": str(debit),
                "credit": str(credit),
            }
        )
    return out


def general_ledger(*, org, start, end, account_id=None, tag_id=None):
    qs = _posted_lines(org=org, start=start, end=end, tag_id=tag_id).select_related("journal", "account")
    if account_id:
        qs = qs.filter(account_id=account_id)
    qs = qs.order_by("journal__entry_date", "journal__number", "id")
    return [
        {
            "journal_id": line.journal_id,
            "number": line.journal.number,
            "entry_date": line.journal.entry_date.isoformat(),
            "account_id": line.account_id,
            "code": line.account.code,
            "description": line.description,
            "debit": str(line.debit),
            "credit": str(line.credit),
            "tag_id": line.tag_id,
        }
        for line in qs
    ]


def _period_rows(*, org, start, end, exponent: int, tag_id=None):
    qs = _posted_lines(org=org, start=start, end=end, tag_id=tag_id)
    return (
        qs.values("account_id", "account__code", "account__name", "account__classification")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )


def profit_loss(*, org, start, end, exponent: int, tag_id=None):
    income, expense = [], []
    income_total = Decimal("0")
    expense_total = Decimal("0")
    for row in _period_rows(org=org, start=start, end=end, exponent=exponent, tag_id=tag_id):
        debit = quantize_amount(row["debit"] or 0, exponent)
        credit = quantize_amount(row["credit"] or 0, exponent)
        item = {
            "account_id": row["account_id"],
            "code": row["account__code"],
            "name": row["account__name"],
            "amount": "0",
        }
        if row["account__classification"] == "income":
            net = credit - debit
            item["amount"] = str(net)
            income.append(item)
            income_total += net
        elif row["account__classification"] == "expense":
            net = debit - credit
            item["amount"] = str(net)
            expense.append(item)
            expense_total += net
    return {
        "income": income,
        "expense": expense,
        "income_total": str(quantize_amount(income_total, exponent)),
        "expense_total": str(quantize_amount(expense_total, exponent)),
        "net_income": str(quantize_amount(income_total - expense_total, exponent)),
    }


def balance_sheet(*, org, as_of, exponent: int):
    qs = _posted_lines(org=org, as_of=as_of)
    rows = (
        qs.values("account_id", "account__code", "account__name", "account__classification")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )
    buckets = {"asset": [], "liability": [], "equity": []}
    totals = {k: Decimal("0") for k in buckets}
    retained = Decimal("0")
    for row in rows:
        debit = quantize_amount(row["debit"] or 0, exponent)
        credit = quantize_amount(row["credit"] or 0, exponent)
        klass = row["account__classification"]
        if klass == "asset":
            net = debit - credit
            buckets["asset"].append(
                {"account_id": row["account_id"], "code": row["account__code"], "name": row["account__name"], "amount": str(net)}
            )
            totals["asset"] += net
        elif klass == "liability":
            net = credit - debit
            buckets["liability"].append(
                {"account_id": row["account_id"], "code": row["account__code"], "name": row["account__name"], "amount": str(net)}
            )
            totals["liability"] += net
        elif klass == "equity":
            net = credit - debit
            buckets["equity"].append(
                {"account_id": row["account_id"], "code": row["account__code"], "name": row["account__name"], "amount": str(net)}
            )
            totals["equity"] += net
        elif klass == "income":
            retained += credit - debit
        elif klass == "expense":
            retained -= debit - credit
    retained = quantize_amount(retained, exponent)
    equity_total = quantize_amount(totals["equity"] + retained, exponent)
    return {
        "assets": buckets["asset"],
        "liabilities": buckets["liability"],
        "equity": buckets["equity"],
        "asset_total": str(quantize_amount(totals["asset"], exponent)),
        "liability_total": str(quantize_amount(totals["liability"], exponent)),
        "retained_earnings": str(retained),
        "equity_total": str(equity_total),
        "liability_and_equity_total": str(quantize_amount(totals["liability"] + equity_total, exponent)),
    }


def _as_of_rows(*, org, as_of):
    qs = _posted_lines(org=org, as_of=as_of)
    return qs.values(
        "account_id",
        "account__code",
        "account__name",
        "account__classification",
        "account__cashflow_kind",
    ).annotate(debit=Sum("debit"), credit=Sum("credit"))


def _signed_net(klass, debit, credit):
    if klass == "asset":
        return debit - credit
    return credit - debit


def _day(value) -> date:
    return date.fromisoformat(str(value)[:10])


def cash_flow(*, org, start, end, exponent: int):
    pnl = profit_loss(org=org, start=start, end=end, exponent=exponent)
    ni = Decimal(pnl["net_income"])
    before = (_day(start) - timedelta(days=1)).isoformat()
    opening = {
        r["account_id"]: r
        for r in _as_of_rows(org=org, as_of=before)
    }
    closing = {
        r["account_id"]: r
        for r in _as_of_rows(org=org, as_of=end)
    }
    buckets = {"operating": ni, "investing": Decimal("0"), "financing": Decimal("0")}
    cash_open = Decimal("0")
    cash_close = Decimal("0")
    items = []
    for aid in set(opening) | set(closing):
        o = opening.get(aid) or {}
        c = closing.get(aid) or {}
        klass = c.get("account__classification") or o.get("account__classification")
        kind = (c.get("account__cashflow_kind") or o.get("account__cashflow_kind") or "").strip()
        o_net = _signed_net(klass, quantize_amount(o.get("debit") or 0, exponent), quantize_amount(o.get("credit") or 0, exponent)) if o else Decimal("0")
        c_net = _signed_net(klass, quantize_amount(c.get("debit") or 0, exponent), quantize_amount(c.get("credit") or 0, exponent)) if c else Decimal("0")
        if not o:
            o_net = Decimal("0")
        if not c:
            c_net = Decimal("0")
        delta = c_net - o_net
        if kind == "cash":
            cash_open += o_net
            cash_close += c_net
            continue
        if klass in ("income", "expense") or kind not in ("operating", "investing", "financing"):
            continue
        effect = -delta if klass == "asset" else delta
        buckets[kind] += effect
        items.append(
            {
                "account_id": aid,
                "code": c.get("account__code") or o.get("account__code"),
                "name": c.get("account__name") or o.get("account__name"),
                "section": kind,
                "amount": str(quantize_amount(effect, exponent)),
            }
        )
    net = buckets["operating"] + buckets["investing"] + buckets["financing"]
    return {
        "net_income": pnl["net_income"],
        "operating": str(quantize_amount(buckets["operating"], exponent)),
        "investing": str(quantize_amount(buckets["investing"], exponent)),
        "financing": str(quantize_amount(buckets["financing"], exponent)),
        "net_change": str(quantize_amount(net, exponent)),
        "cash_change": str(quantize_amount(cash_close - cash_open, exponent)),
        "items": items,
    }
