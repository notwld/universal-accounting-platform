"""Line tax: exclusive/inclusive, compound (ERPNext previous-row total vs parallel on net),
reverse-charge self-accounting (HMRC/EU buyer output+input), withholding (AP/AR reduced),
recoverable purchase tax. Country rates are not implied.
"""

from decimal import Decimal

from apps.authentication.exceptions import AuthAPIError
from apps.finance.services.money import quantize_amount

KIND_STANDARD = "standard"
KIND_REVERSE = "reverse_charge"
KIND_WITHHOLDING = "withholding"
KIND_EXEMPT = "exempt"
BASE_NET = "net"
BASE_RUNNING = "running"


def line_tax(*, amount, rate, method: str, exponent: int):
    return apply_simple(amount=amount, rate=rate, method=method, exponent=exponent)[:3]


def apply_simple(*, amount, rate, method: str, exponent: int):
    amount = Decimal(str(amount))
    rate = Decimal(str(rate or 0))
    if method == "inclusive":
        net = amount / (1 + rate) if rate else amount
        tax = amount - net
        total = amount
    else:
        net = amount
        tax = net * rate
        total = net + tax
    return quantize_amount(net, exponent), quantize_amount(tax, exponent), quantize_amount(total, exponent)


def _chain(tax):
    rows = []
    seen = set()
    cur = tax
    while cur is not None:
        if cur.id in seen:
            raise AuthAPIError("validation_error", "Tax compound chain is cyclic")
        seen.add(cur.id)
        rows.append(cur)
        cur = cur.compound_on
        if len(rows) > 8:
            raise AuthAPIError("validation_error", "Tax compound chain is too long")
    rows.reverse()
    return rows


def _exclusive_parts(tax, net, exponent):
    parts = []
    running = Decimal("0")
    for row in _chain(tax):
        rate = Decimal("0") if row.kind == KIND_EXEMPT else Decimal(str(row.rate or 0))
        base = net + running if (row.compound_on_id and (row.compound_base or BASE_RUNNING) == BASE_RUNNING) else net
        amt = quantize_amount(base * rate, exponent)
        recover = Decimal(str(row.recoverable_rate if row.recoverable_rate is not None else 1))
        if recover < 0 or recover > 1:
            raise AuthAPIError("validation_error", "recoverable_rate must be between 0 and 1")
        rec_amt = quantize_amount(amt * recover, exponent)
        parts.append(
            {
                "id": row.id,
                "name": row.name,
                "kind": row.kind,
                "rate": str(rate),
                "method": row.method,
                "amount": amt,
                "recoverable": rec_amt,
                "payable_account_id": row.payable_account_id,
                "recoverable_account_id": row.recoverable_account_id or row.payable_account_id,
            }
        )
        running += amt
    return parts, running


def apply_rate(*, tax, amount, exponent: int, entry_date=None):
    amount = Decimal(str(amount))
    if tax is None:
        q = quantize_amount(amount, exponent)
        return {"net": q, "tax": Decimal("0"), "total": q, "kind": KIND_STANDARD, "components": []}
    if entry_date:
        on = str(entry_date)[:10]
        if str(tax.valid_from)[:10] > on:
            raise AuthAPIError("validation_error", "Tax rate is not yet valid")
        if getattr(tax, "valid_to", None) and str(tax.valid_to)[:10] < on:
            raise AuthAPIError("validation_error", "Tax rate is no longer valid")
    kind = tax.kind or KIND_STANDARD
    method = tax.method or "exclusive"
    chain = _chain(tax)
    if method == "inclusive" and kind == KIND_STANDARD:
        running = any(r.compound_on_id and (r.compound_base or BASE_RUNNING) == BASE_RUNNING for r in chain)
        if running:
            factor = Decimal("1")
            for row in chain:
                factor *= 1 + (Decimal("0") if row.kind == KIND_EXEMPT else Decimal(str(row.rate or 0)))
        else:
            factor = Decimal("1") + sum(
                (Decimal("0") if row.kind == KIND_EXEMPT else Decimal(str(row.rate or 0))) for row in chain
            )
        net = amount / factor if factor else amount
        parts, tax_total = _exclusive_parts(tax, quantize_amount(net, exponent), exponent)
        net = quantize_amount(net, exponent)
        return {
            "net": net,
            "tax": tax_total,
            "total": quantize_amount(amount, exponent),
            "kind": kind,
            "components": parts,
        }
    net = quantize_amount(amount, exponent)
    parts, tax_total = _exclusive_parts(tax, net, exponent)
    if kind == KIND_REVERSE or kind == KIND_EXEMPT:
        total = net
    elif kind == KIND_WITHHOLDING:
        total = quantize_amount(net - tax_total, exponent)
    else:
        total = quantize_amount(net + tax_total, exponent)
    return {"net": net, "tax": tax_total, "total": total, "kind": kind, "components": parts}
