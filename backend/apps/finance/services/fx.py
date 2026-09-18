from decimal import Decimal

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import Bill, FinanceFxReval, FinanceSettings, Invoice, JournalEntry
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.posting import post_generated, reverse_journal
from apps.finance.services.purchases import outstanding as bill_outstanding
from apps.finance.services.sales import outstanding as invoice_outstanding
from apps.finance.services.sales import resolve_rate, to_base


def _open_base(doc, remain, exponent):
    if not remain or not doc.total:
        return Decimal("0")
    return quantize_amount(remain / doc.total * doc.base_total, exponent)


def revalue(*, user_id, org, as_of, idempotency_key):
    settings = FinanceSettings.objects.select_related("base_currency", "ar_account", "ap_account").filter(
        organization=org
    ).first()
    if not settings or not settings.fx_gain_account_id or not settings.fx_loss_account_id:
        raise AuthAPIError("validation_error", "FX gain and loss accounts are required")
    exponent = settings.base_currency.exponent
    existing = FinanceFxReval.objects.filter(organization=org, as_of=as_of).first()
    if existing:
        return existing
    with finance_tx(user_id=user_id, organization_id=org.id):
        prev = (
            FinanceFxReval.objects.filter(organization=org, reverse_journal__isnull=True)
            .exclude(as_of=as_of)
            .order_by("-as_of")
            .first()
        )
        if prev and prev.journal_id:
            rev = reverse_journal(
                user_id=user_id,
                org=org,
                journal_id=prev.journal_id,
                reason="unrealized fx reverse",
                entry_date=as_of,
                idempotency_key=f"{idempotency_key}:rev",
                body={"reverse_reval": prev.id},
            )
            prev.reverse_journal = rev
            prev.save(update_fields=["reverse_journal"])
        ar_diff = Decimal("0")
        ap_diff = Decimal("0")
        base_id = settings.base_currency_id
        for inv in Invoice.objects.filter(organization=org, status=Invoice.Status.POSTED).exclude(currency_id=base_id):
            remain = invoice_outstanding(inv, as_of=as_of)
            book = _open_base(inv, remain, exponent)
            rate = resolve_rate(org, inv.currency_id, as_of, base_id, None)
            current = to_base(remain, rate, exponent)
            ar_diff += current - book
        for bill in Bill.objects.filter(organization=org, status=Bill.Status.POSTED).exclude(currency_id=base_id):
            remain = bill_outstanding(bill, as_of=as_of)
            book = _open_base(bill, remain, exponent)
            rate = resolve_rate(org, bill.currency_id, as_of, base_id, None)
            current = to_base(remain, rate, exponent)
            ap_diff += current - book
        gl = []
        if ar_diff and settings.ar_account_id:
            if ar_diff > 0:
                gl.append({"account_id": settings.ar_account_id, "debit": str(ar_diff), "credit": "0", "description": "unrealized"})
                gl.append({"account_id": settings.fx_gain_account_id, "debit": "0", "credit": str(ar_diff), "description": "unrealized"})
            else:
                amt = -ar_diff
                gl.append({"account_id": settings.fx_loss_account_id, "debit": str(amt), "credit": "0", "description": "unrealized"})
                gl.append({"account_id": settings.ar_account_id, "debit": "0", "credit": str(amt), "description": "unrealized"})
        if ap_diff and settings.ap_account_id:
            if ap_diff > 0:
                gl.append({"account_id": settings.fx_loss_account_id, "debit": str(ap_diff), "credit": "0", "description": "unrealized"})
                gl.append({"account_id": settings.ap_account_id, "debit": "0", "credit": str(ap_diff), "description": "unrealized"})
            else:
                amt = -ap_diff
                gl.append({"account_id": settings.ap_account_id, "debit": str(amt), "credit": "0", "description": "unrealized"})
                gl.append({"account_id": settings.fx_gain_account_id, "debit": "0", "credit": str(amt), "description": "unrealized"})
        journal = None
        total = abs(ar_diff) + abs(ap_diff)
        if gl:
            journal = post_generated(
                user_id=user_id,
                org=org,
                entry_date=as_of,
                source_type=JournalEntry.Source.FX_REVAL,
                memo="unrealized fx",
                gl_lines=gl,
                idempotency_key=idempotency_key,
                body={"as_of": str(as_of)},
            )
        return FinanceFxReval.objects.create(
            organization=org, as_of=as_of, amount=total, journal=journal
        )
