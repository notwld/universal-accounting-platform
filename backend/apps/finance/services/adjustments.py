from decimal import Decimal

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import Account, FinanceAdjustment, JournalEntry
from apps.finance.services.context import finance_tx
from apps.finance.services.posting import post_generated, reverse_journal
from apps.finance.services.resolve import org_get


def post_adjustment(*, user_id, org, payload, idempotency_key):
    kind = payload.get("kind") or "accrual"
    if kind not in ("accrual", "deferral"):
        raise AuthAPIError("validation_error", "kind must be accrual or deferral")
    amount = Decimal(str(payload.get("amount") or 0))
    if amount <= 0:
        raise AuthAPIError("validation_error", "amount must be positive")
    debit = org_get(Account, org, payload.get("debit_account_id"))
    credit = org_get(Account, org, payload.get("credit_account_id"))
    entry_date = payload.get("entry_date")
    reverse_on = payload.get("reverse_on")
    if not entry_date or not reverse_on:
        raise AuthAPIError("validation_error", "entry_date and reverse_on are required")
    if str(reverse_on)[:10] <= str(entry_date)[:10]:
        raise AuthAPIError("validation_error", "reverse_on must be after entry_date")
    memo = (payload.get("memo") or kind)[:255]
    with finance_tx(user_id=user_id, organization_id=org.id):
        journal = post_generated(
            user_id=user_id,
            org=org,
            entry_date=entry_date,
            source_type=JournalEntry.Source.ADJUST,
            memo=memo,
            gl_lines=[
                {"account_id": debit.id, "debit": str(amount), "credit": "0", "description": memo},
                {"account_id": credit.id, "debit": "0", "credit": str(amount), "description": memo},
            ],
            idempotency_key=idempotency_key,
            body={"kind": kind, "amount": str(amount), "entry_date": str(entry_date)},
        )
        adj = FinanceAdjustment.objects.create(
            organization=org,
            kind=kind,
            debit_account=debit,
            credit_account=credit,
            amount=amount,
            entry_date=entry_date,
            reverse_on=reverse_on,
            memo=memo,
            journal=journal,
        )
        return adj


def reverse_due(*, user_id, org, as_of, idempotency_key):
    created = []
    with finance_tx(user_id=user_id, organization_id=org.id):
        qs = FinanceAdjustment.objects.filter(
            organization=org, reverse_journal__isnull=True, reverse_on__lte=as_of
        ).select_related("journal")
        for i, adj in enumerate(qs):
            if not adj.journal_id:
                continue
            rev = reverse_journal(
                user_id=user_id,
                org=org,
                journal_id=adj.journal_id,
                reason=f"reverse {adj.kind}",
                entry_date=as_of,
                idempotency_key=f"{idempotency_key}:{i}",
                body={"adjustment_id": adj.id, "as_of": str(as_of)},
            )
            adj.reverse_journal = rev
            adj.save(update_fields=["reverse_journal"])
            created.append(adj.id)
    return created
