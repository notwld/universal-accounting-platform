from decimal import Decimal

from django.db.models import Sum

from apps.finance.models import JournalEntry, JournalLine
from apps.finance.services.money import quantize_amount


def trial_balance(*, org, start, end, exponent: int):
    qs = JournalLine.objects.filter(
        organization=org,
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__gte=start,
        journal__entry_date__lte=end,
    )
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


def general_ledger(*, org, start, end, account_id=None):
    qs = JournalLine.objects.filter(
        organization=org,
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__gte=start,
        journal__entry_date__lte=end,
    ).select_related("journal", "account")
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
        }
        for line in qs
    ]


def _period_rows(*, org, start, end, exponent: int):
    qs = JournalLine.objects.filter(
        organization=org,
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__gte=start,
        journal__entry_date__lte=end,
    )
    return (
        qs.values("account_id", "account__code", "account__name", "account__classification")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
        .order_by("account__code")
    )


def profit_loss(*, org, start, end, exponent: int):
    income, expense = [], []
    income_total = Decimal("0")
    expense_total = Decimal("0")
    for row in _period_rows(org=org, start=start, end=end, exponent=exponent):
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
    qs = JournalLine.objects.filter(
        organization=org,
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__lte=as_of,
    )
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