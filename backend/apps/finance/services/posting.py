import hashlib
import json
from decimal import Decimal

from django.db import IntegrityError
from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Account,
    FinanceAuditEvent,
    FinanceIdempotency,
    FinanceSettings,
    FiscalPeriodLock,
    JournalEntry,
    JournalLine,
    ReportingTag,
)
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.sequence import next_journal_number


def _hash_body(body) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def _begin_idempotency(org, operation, key, body):
    if not key:
        raise AuthAPIError("validation_error", "Idempotency-Key required")
    request_hash = _hash_body(body)
    existing = FinanceIdempotency.objects.filter(
        organization=org, operation=operation, key=key
    ).select_related("journal").first()
    if existing:
        if existing.request_hash != request_hash:
            raise AuthAPIError("idempotency_conflict", "Idempotency key reused with different payload")
        return existing, True
    try:
        rec = FinanceIdempotency.objects.create(
            organization=org, operation=operation, key=key, request_hash=request_hash
        )
        return rec, False
    except IntegrityError:
        existing = FinanceIdempotency.objects.get(organization=org, operation=operation, key=key)
        if existing.request_hash != request_hash:
            raise AuthAPIError("idempotency_conflict", "Idempotency key reused with different payload")
        return existing, True


def _lock_period(org, entry_date):
    locked = (
        FiscalPeriodLock.objects.select_for_update()
        .filter(organization=org, start_on__lte=entry_date, end_on__gte=entry_date, status=FiscalPeriodLock.Status.LOCKED)
        .first()
    )
    if locked:
        raise AuthAPIError("period_closed", "Period is locked")


def _settings(org) -> FinanceSettings:
    settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
    if not settings:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return settings


CONTROL_SOURCES = {
    JournalEntry.Source.OPENING,
    JournalEntry.Source.INVOICE,
    JournalEntry.Source.PAYMENT,
    JournalEntry.Source.CREDIT,
    JournalEntry.Source.REFUND,
    JournalEntry.Source.BILL,
    JournalEntry.Source.EXPENSE,
    JournalEntry.Source.VENDOR_PAYMENT,
    JournalEntry.Source.VENDOR_CREDIT,
    JournalEntry.Source.VENDOR_REFUND,
    JournalEntry.Source.ASSET,
}


def _prepare_line(org, source_type, line, exponent):
    account = line.account
    if account.organization_id != org.id:
        raise AuthAPIError("cross_organization", "Account does not belong to organization")
    if account.status != Account.Status.ACTIVE:
        raise AuthAPIError("account_inactive", "Account is inactive")
    if account.is_control and source_type not in CONTROL_SOURCES:
        raise AuthAPIError("control_account_restricted", "Control accounts require opening workflow")
    debit = quantize_amount(line.debit, exponent)
    credit = quantize_amount(line.credit, exponent)
    if (debit > 0 and credit > 0) or (debit == 0 and credit == 0) or debit < 0 or credit < 0:
        raise AuthAPIError("journal_imbalanced", "Each line needs a nonnegative debit or credit, not both")
    return account, line.description, debit, credit


def _validate_lines(org, source_type, lines, exponent):
    if not lines:
        raise AuthAPIError("journal_imbalanced", "Journal has no lines")
    debit_total = Decimal("0")
    credit_total = Decimal("0")
    prepared = []
    for line in lines:
        account, desc, debit, credit = _prepare_line(org, source_type, line, exponent)
        debit_total += debit
        credit_total += credit
        prepared.append((account, desc, debit, credit))
    if debit_total != credit_total:
        raise AuthAPIError("journal_imbalanced", "Debits must equal credits")
    return prepared, debit_total


def replace_draft_lines(journal, lines_payload):
    org = journal.organization
    exponent = _settings(org).base_currency.exponent
    journal.lines.all().delete()
    stubs = []
    for raw in lines_payload:
        account = Account.objects.filter(id=raw.get("account_id"), organization=org).first()
        if not account:
            raise AuthAPIError("cross_organization", "Account does not belong to organization")
        line = JournalLine(
            journal=journal,
            organization=org,
            account=account,
            description=raw.get("description") or "",
            debit=Decimal(str(raw.get("debit") or 0)),
            credit=Decimal(str(raw.get("credit") or 0)),
        )
        tag_id = raw.get("tag_id")
        if tag_id:
            if not ReportingTag.objects.filter(id=tag_id, organization=org).exists():
                raise AuthAPIError("cross_organization", "Tag not found")
            line.tag_id = tag_id
        _prepare_line(org, journal.source_type, line, exponent)
        stubs.append(line)
    JournalLine.objects.bulk_create(stubs)


def post_journal(*, user_id, org, journal_id, version, idempotency_key, body):
    with finance_tx(user_id=user_id, organization_id=org.id):
        return _post_journal(
            user_id=user_id,
            org=org,
            journal_id=journal_id,
            version=version,
            idempotency_key=idempotency_key,
            body=body,
        )


def _post_journal(*, user_id, org, journal_id, version, idempotency_key, body):
    rec, replay = _begin_idempotency(org, "journal.post", idempotency_key, body)
    if replay:
        if rec.journal_id:
            return rec.journal
        raise AuthAPIError("idempotency_conflict", "Idempotency key in progress")
    meta = JournalEntry.objects.filter(id=journal_id, organization=org).values("entry_date").first()
    if not meta:
        raise AuthAPIError("cross_organization", "Journal not found")
    _lock_period(org, meta["entry_date"])
    journal = JournalEntry.objects.select_for_update().filter(id=journal_id, organization=org).first()
    if not journal:
        raise AuthAPIError("cross_organization", "Journal not found")
    if journal.status == JournalEntry.Status.POSTED:
        rec.journal = journal
        rec.save(update_fields=["journal"])
        return journal
    if journal.version != version:
        raise AuthAPIError("stale_version", "Journal version mismatch")
    settings = _settings(org)
    lines = list(journal.lines.select_related("account").all())
    prepared, _ = _validate_lines(org, journal.source_type, lines, settings.base_currency.exponent)
    for line, (account, desc, debit, credit) in zip(lines, prepared, strict=True):
        line.debit = debit
        line.credit = credit
        line.account = account
        line.description = desc
        JournalLine.objects.filter(pk=line.pk).update(debit=debit, credit=credit, description=desc)
    journal.number = next_journal_number(org)
    journal.status = JournalEntry.Status.POSTED
    journal.posted_at = timezone.now()
    journal.posted_by = user_id
    JournalEntry.objects.filter(pk=journal.pk).update(
        number=journal.number,
        status=journal.status,
        posted_at=journal.posted_at,
        posted_by=journal.posted_by,
        updated_at=timezone.now(),
    )
    rec.journal = journal
    rec.save(update_fields=["journal"])
    FinanceAuditEvent.objects.create(
        organization=org,
        actor_user_id=user_id,
        action="journal.post",
        object_type="journal",
        object_id=journal.id,
        payload={"number": journal.number},
    )
    journal.refresh_from_db()
    return journal


def post_generated(*, user_id, org, entry_date, source_type, memo, gl_lines, idempotency_key, body):
    rec, replay = _begin_idempotency(org, f"{source_type}.post", idempotency_key, body)
    if replay:
        if rec.journal_id:
            return rec.journal
        raise AuthAPIError("idempotency_conflict", "Idempotency key in progress")
    journal = JournalEntry.objects.create(
        organization=org,
        status=JournalEntry.Status.DRAFT,
        entry_date=entry_date,
        memo=memo or "",
        source_type=source_type,
    )
    replace_draft_lines(journal, gl_lines)
    posted = _post_journal(
        user_id=user_id,
        org=org,
        journal_id=journal.id,
        version=journal.version,
        idempotency_key=f"{idempotency_key}:je",
        body=body,
    )
    rec.journal = posted
    rec.save(update_fields=["journal"])
    return posted


def reverse_journal(*, user_id, org, journal_id, reason, entry_date, idempotency_key, body):
    if not (reason or "").strip():
        raise AuthAPIError("validation_error", "Reversal reason is required")
    with finance_tx(user_id=user_id, organization_id=org.id):
        rec, replay = _begin_idempotency(org, "journal.reverse", idempotency_key, body)
        if replay:
            if rec.journal_id:
                return rec.journal
            raise AuthAPIError("idempotency_conflict", "Idempotency key in progress")
        original = JournalEntry.objects.select_for_update().filter(id=journal_id, organization=org).first()
        if not original:
            raise AuthAPIError("cross_organization", "Journal not found")
        if original.status != JournalEntry.Status.POSTED:
            raise AuthAPIError("validation_error", "Only posted journals can be reversed")
        if original.reversed_by_id:
            raise AuthAPIError("already_reversed", "Journal already reversed")
        date = entry_date or original.entry_date
        _lock_period(org, date)
        reversal = JournalEntry.objects.create(
            organization=org,
            status=JournalEntry.Status.DRAFT,
            entry_date=date,
            memo=reason.strip(),
            source_type=original.source_type,
            reverses=original,
        )
        for line in original.lines.all():
            JournalLine.objects.create(
                journal=reversal,
                organization=org,
                account=line.account,
                description=line.description,
                debit=line.credit,
                credit=line.debit,
            )
        posted = _post_journal(
            user_id=user_id,
            org=org,
            journal_id=reversal.id,
            version=reversal.version,
            idempotency_key=f"{idempotency_key}:inner",
            body={"reverse_of": original.id, "reason": reason},
        )
        JournalEntry.objects.filter(pk=original.pk).update(reversed_by=posted, updated_at=timezone.now())
        rec.journal = posted
        rec.save(update_fields=["journal"])
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="journal.reverse",
            object_type="journal",
            object_id=posted.id,
            payload={"original_id": original.id, "reason": reason.strip()},
        )
        return posted
