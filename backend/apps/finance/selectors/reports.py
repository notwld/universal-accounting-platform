from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Sum

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
    start_d = date.fromisoformat(str(start)[:10])
    end_d = date.fromisoformat(str(end)[:10])
    opening_end = start_d - timedelta(days=1)
    opening_rows = (
        _posted_lines(org=org, end=opening_end.isoformat(), tag_id=tag_id)
        .values("account_id", "account__code", "account__name")
        .annotate(debit=Sum("debit"), credit=Sum("credit"))
    )
    period_rows = (
        _posted_lines(org=org, start=start, end=end, tag_id=tag_id)
        .values("account_id", "account__code", "account__name")
        .annotate(debit=Sum("debit"), credit=Sum("credit"), line_count=Count("id"))
    )
    opening = {row["account_id"]: row for row in opening_rows}
    period = {row["account_id"]: row for row in period_rows}
    out = []
    for aid in sorted(set(opening) | set(period), key=lambda i: (opening.get(i) or period[i])["account__code"]):
        o = opening.get(aid) or {}
        p = period.get(aid) or {}
        od = quantize_amount(o.get("debit") or 0, exponent)
        oc = quantize_amount(o.get("credit") or 0, exponent)
        pd = quantize_amount(p.get("debit") or 0, exponent)
        pc = quantize_amount(p.get("credit") or 0, exponent)
        onet = od - oc
        cnet = onet + pd - pc
        meta = p or o
        out.append(
            {
                "account_id": aid,
                "code": meta["account__code"],
                "name": meta["account__name"],
                "opening_debit": str(quantize_amount(onet if onet > 0 else 0, exponent)),
                "opening_credit": str(quantize_amount(-onet if onet < 0 else 0, exponent)),
                "debit": str(pd),
                "credit": str(pc),
                "closing_debit": str(quantize_amount(cnet if cnet > 0 else 0, exponent)),
                "closing_credit": str(quantize_amount(-cnet if cnet < 0 else 0, exponent)),
                "line_count": int(p.get("line_count") or 0),
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


def tax_summary(*, org, start, end, exponent: int):
    from apps.finance.models import TaxRate

    ids = {
        aid
        for pair in TaxRate.objects.filter(organization=org).values_list("payable_account_id", "recoverable_account_id")
        for aid in pair
        if aid
    }
    qs = _posted_lines(org=org, start=start, end=end)
    if ids:
        qs = qs.filter(account_id__in=ids)
    else:
        qs = qs.none()
    items = []
    total = Decimal("0")
    for row in qs.values("account_id", "account__code", "account__name").annotate(debit=Sum("debit"), credit=Sum("credit")):
        net = quantize_amount((row["credit"] or 0) - (row["debit"] or 0), exponent)
        total += net
        items.append(
            {
                "account_id": row["account_id"],
                "code": row["account__code"],
                "name": row["account__name"],
                "amount": str(net),
            }
        )
    return {"items": items, "total": str(quantize_amount(total, exponent))}


def equity_movement(*, org, start, end, exponent: int):
    start_d = date.fromisoformat(str(start)[:10])
    opening = balance_sheet(org=org, as_of=(start_d - timedelta(days=1)).isoformat(), exponent=exponent)
    closing = balance_sheet(org=org, as_of=end, exponent=exponent)
    pnl = profit_loss(org=org, start=start, end=end, exponent=exponent)
    return {
        "opening_equity": opening["equity_total"],
        "net_income": pnl["net_income"],
        "closing_equity": closing["equity_total"],
        "retained_earnings": closing["retained_earnings"],
        "equity": closing["equity"],
    }


def as_csv(rows, fieldnames=None) -> str:
    import csv
    from io import StringIO

    buf = StringIO()
    if not fieldnames:
        fieldnames = list(rows[0].keys()) if rows else []
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buf.getvalue()


def as_xlsx(rows) -> bytes:
    from io import BytesIO
    from xml.sax.saxutils import escape
    import zipfile

    fields = list(rows[0].keys()) if rows else []
    shared = list(fields)
    body = ["<row r=\"1\">" + "".join(
        f'<c r="{chr(65 + i)}1" t="s"><v>{i}</v></c>' for i in range(len(fields))
    ) + "</row>"]
    for r, row in enumerate(rows, 2):
        cells = []
        for i, key in enumerate(fields):
            text = str(row.get(key, ""))
            if text not in shared:
                shared.append(text)
            cells.append(f'<c r="{chr(65 + i)}{r}" t="s"><v>{shared.index(text)}</v></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    sst = f'<sst xmlns="{ns}">' + "".join(f"<si><t>{escape(s)}</t></si>" for s in shared) + "</sst>"
    sheet = f'<worksheet xmlns="{ns}"><sheetData>{"".join(body)}</sheetData></worksheet>'
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/sharedStrings.xml", sst)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


def as_pdf(title, rows) -> bytes:
    keys = list(rows[0].keys()) if rows else []
    lines = [str(title or "report")]
    if keys:
        lines.append(" | ".join(keys))
        for row in rows[:60]:
            lines.append(" | ".join(str(row.get(k, ""))[:32] for k in keys))
    body = " ".join(lines)[:800].replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 40 750 Td ({body}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
    for off in offsets[1:]:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer << /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
