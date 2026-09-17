import csv
import hashlib
import io
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from django.db import IntegrityError, transaction
from django.db.models import Sum

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Account,
    BankLine,
    BankReconciliation,
    BankRule,
    BankStatement,
    CustomerPayment,
    FinanceAuditEvent,
    FinanceSettings,
    JournalEntry,
    VendorPayment,
)
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.posting import post_generated


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _settings(org) -> FinanceSettings:
    settings = FinanceSettings.objects.select_related("base_currency").filter(organization=org).first()
    if not settings:
        raise AuthAPIError("validation_error", "Finance setup is incomplete")
    return settings


def _bank_account(org, account_id):
    account = Account.objects.filter(id=account_id, organization=org).first()
    if not account:
        raise AuthAPIError("cross_organization", "Account not found")
    if account.status != Account.Status.ACTIVE:
        raise AuthAPIError("account_inactive", "Account is inactive")
    if account.classification != Account.Classification.ASSET:
        raise AuthAPIError("validation_error", "Bank account must be an asset")
    return account


def _fingerprint(org_id, account_id, entry_date, amount, description) -> str:
    raw = f"{org_id}|{account_id}|{entry_date.isoformat()}|{amount}|{(description or '').strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _parse_date(value) -> date:
    s = str(value).strip()
    if not s:
        raise ValueError("empty date")
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    try:
        n = float(s)
        if n > 2000:
            return (datetime(1899, 12, 30) + timedelta(days=n)).date()
    except ValueError:
        pass
    raise ValueError("bad date")


def _coerce_rows(dicts, exponent: int):
    rows = []
    for row in dicts:
        if not any(str(v).strip() for v in row.values() if v is not None):
            continue
        try:
            entry_date = _parse_date(row["date"])
            amount = quantize_amount(Decimal(str(row["amount"]).strip()), exponent)
        except (InvalidOperation, ValueError, KeyError):
            raise AuthAPIError("validation_error", "Invalid statement date or amount")
        rows.append((entry_date, amount, str(row.get("description") or "").strip()[:255]))
    return rows


def _header_map(names):
    fields = {str(name).strip().lower(): name for name in names if name}
    if not {"date", "amount", "description"} <= fields.keys():
        raise AuthAPIError("validation_error", "Columns must be date,amount,description")
    return fields


def _parse_csv_bytes(raw, exponent: int):
    text = raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise AuthAPIError("validation_error", "Statement has no header")
    fields = _header_map(reader.fieldnames)
    dicts = []
    for row in reader:
        dicts.append({k: (row.get(fields[k]) or "") for k in ("date", "amount", "description")})
    return _coerce_rows(dicts, exponent)


def _col_index(ref: str) -> int:
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + ord(ch.upper()) - 64
    return n - 1


def _parse_xlsx(raw: bytes, exponent: int):
    # ponytail: first sheet only; named tabs if a bank splits pages
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise AuthAPIError("validation_error", "Invalid spreadsheet") from exc
    strings = []
    names = zf.namelist()
    if "xl/sharedStrings.xml" in names:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in root.iter():
            if _local(si.tag) != "si":
                continue
            strings.append("".join(node.text or "" for node in si.iter() if _local(node.tag) == "t"))
    sheet_path = next((n for n in sorted(names) if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")), None)
    if not sheet_path:
        raise AuthAPIError("validation_error", "Spreadsheet has no worksheet")
    grid = {}
    max_row = 0
    max_col = 0
    for cell in ET.fromstring(zf.read(sheet_path)).iter():
        if _local(cell.tag) != "c" or not cell.attrib.get("r"):
            continue
        ref = cell.attrib["r"]
        col = _col_index(ref)
        row = int("".join(ch for ch in ref if ch.isdigit()))
        max_row = max(max_row, row)
        max_col = max(max_col, col)
        kind = cell.attrib.get("t")
        if kind == "inlineStr":
            value = "".join(node.text or "" for node in cell.iter() if _local(node.tag) == "t")
        else:
            vnode = next((node for node in cell if _local(node.tag) == "v"), None)
            if vnode is None or vnode.text is None:
                continue
            value = strings[int(vnode.text)] if kind == "s" else vnode.text
        grid[(row, col)] = value
    table = []
    for r in range(1, max_row + 1):
        table.append([grid.get((r, c), "") for c in range(max_col + 1)])
    header_idx = next((i for i, row in enumerate(table) if any(str(c).strip() for c in row)), None)
    if header_idx is None:
        raise AuthAPIError("validation_error", "Statement has no header")
    fields = _header_map(table[header_idx])
    key_to_col = {k: table[header_idx].index(fields[k]) for k in ("date", "amount", "description")}
    dicts = []
    for row in table[header_idx + 1 :]:
        dicts.append({k: row[idx] if idx < len(row) else "" for k, idx in key_to_col.items()})
    return _coerce_rows(dicts, exponent)


def _parse_statement(file_obj, exponent: int):
    raw = file_obj.read()
    name = (getattr(file_obj, "name", "") or "").lower()
    xlsx = name.endswith(".xlsx") or (isinstance(raw, bytes) and raw[:2] == b"PK")
    if xlsx:
        if isinstance(raw, str):
            raw = raw.encode()
        return _parse_xlsx(raw, exponent)
    return _parse_csv_bytes(raw, exponent)


def import_statement(*, user_id, org, account_id, uploaded):
    with finance_tx(user_id=user_id, organization_id=org.id):
        account = _bank_account(org, account_id)
        exponent = _settings(org).base_currency.exponent
        rows = _parse_statement(uploaded, exponent)
        statement = BankStatement.objects.create(
            organization=org, account=account, original_name=(getattr(uploaded, "name", "") or "")[:255]
        )
        created, duplicates = [], []
        for entry_date, amount, description in rows:
            fp = _fingerprint(org.id, account.id, entry_date, amount, description)
            try:
                with transaction.atomic():
                    line = BankLine.objects.create(
                        organization=org,
                        statement=statement,
                        account=account,
                        entry_date=entry_date,
                        amount=amount,
                        description=description,
                        fingerprint=fp,
                    )
                created.append(line)
            except IntegrityError:
                duplicates.append({"entry_date": entry_date.isoformat(), "amount": str(amount), "description": description})
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.import",
            object_type="bank_statement",
            object_id=statement.id,
            payload={"created": len(created), "duplicates": len(duplicates)},
        )
        return statement, created, duplicates


def match_line(*, user_id, org, line_id, customer_payment_id=None, vendor_payment_id=None):
    if bool(customer_payment_id) == bool(vendor_payment_id):
        raise AuthAPIError("validation_error", "Provide exactly one payment id")
    with finance_tx(user_id=user_id, organization_id=org.id):
        line = BankLine.objects.select_for_update().filter(id=line_id, organization=org).first()
        if not line:
            raise AuthAPIError("cross_organization", "Bank line not found")
        if line.status != BankLine.Status.IMPORTED:
            raise AuthAPIError("already_matched", "Bank line already matched or categorized")
        if customer_payment_id:
            pay = CustomerPayment.objects.filter(
                id=customer_payment_id, organization=org, status=CustomerPayment.Status.POSTED
            ).first()
            if not pay or pay.bank_account_id != line.account_id:
                raise AuthAPIError("cross_organization", "Payment not found")
            if line.amount <= 0 or abs(line.amount) != pay.amount:
                raise AuthAPIError("validation_error", "Amount or direction does not match payment")
            line.customer_payment = pay
        else:
            pay = VendorPayment.objects.filter(
                id=vendor_payment_id, organization=org, status=VendorPayment.Status.POSTED
            ).first()
            if not pay or pay.bank_account_id != line.account_id:
                raise AuthAPIError("cross_organization", "Payment not found")
            if line.amount >= 0 or abs(line.amount) != pay.amount:
                raise AuthAPIError("validation_error", "Amount or direction does not match payment")
            line.vendor_payment = pay
        line.status = BankLine.Status.MATCHED
        try:
            line.save(update_fields=["status", "customer_payment", "vendor_payment"])
        except IntegrityError:
            raise AuthAPIError("already_matched", "Payment already matched")
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.match",
            object_type="bank_line",
            object_id=line.id,
            payload={"payment_id": pay.id},
        )
        return line


def categorize_line(*, user_id, org, line_id, account_id, idempotency_key):
    with finance_tx(user_id=user_id, organization_id=org.id):
        line = BankLine.objects.select_for_update().filter(id=line_id, organization=org).first()
        if not line:
            raise AuthAPIError("cross_organization", "Bank line not found")
        if line.status != BankLine.Status.IMPORTED:
            raise AuthAPIError("already_matched", "Bank line already matched or categorized")
        contra = Account.objects.filter(id=account_id, organization=org).first()
        if not contra:
            raise AuthAPIError("cross_organization", "Account not found")
        if contra.id == line.account_id:
            raise AuthAPIError("validation_error", "Cannot categorize to the bank account")
        amount = abs(line.amount)
        if line.amount > 0:
            gl_lines = [
                {"account_id": line.account_id, "debit": str(amount), "credit": "0", "description": line.description},
                {"account_id": contra.id, "debit": "0", "credit": str(amount), "description": line.description},
            ]
        elif line.amount < 0:
            gl_lines = [
                {"account_id": contra.id, "debit": str(amount), "credit": "0", "description": line.description},
                {"account_id": line.account_id, "debit": "0", "credit": str(amount), "description": line.description},
            ]
        else:
            raise AuthAPIError("validation_error", "Zero amount cannot be categorized")
        journal = post_generated(
            user_id=user_id,
            org=org,
            entry_date=line.entry_date,
            source_type=JournalEntry.Source.BANK,
            memo=line.description,
            gl_lines=gl_lines,
            idempotency_key=idempotency_key,
            body={"line_id": line.id, "account_id": contra.id},
        )
        line.status = BankLine.Status.CATEGORIZED
        line.journal = journal
        line.save(update_fields=["status", "journal"])
        return line


def create_reconciliation(*, user_id, org, account_id, start_on, end_on, opening, closing):
    with finance_tx(user_id=user_id, organization_id=org.id):
        account = _bank_account(org, account_id)
        exponent = _settings(org).base_currency.exponent
        rec = BankReconciliation.objects.create(
            organization=org,
            account=account,
            start_on=_as_date(start_on),
            end_on=_as_date(end_on),
            opening=quantize_amount(opening, exponent),
            closing=quantize_amount(closing, exponent),
        )
        return rec


def complete_reconciliation(*, user_id, org, recon_id):
    with finance_tx(user_id=user_id, organization_id=org.id):
        rec = BankReconciliation.objects.select_for_update().filter(id=recon_id, organization=org).first()
        if not rec:
            raise AuthAPIError("cross_organization", "Reconciliation not found")
        if rec.status == BankReconciliation.Status.COMPLETE:
            return rec
        exponent = _settings(org).base_currency.exponent
        net = BankLine.objects.filter(
            organization=org, account=rec.account, entry_date__gte=rec.start_on, entry_date__lte=rec.end_on
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        net = quantize_amount(net, exponent)
        if rec.opening + net != rec.closing:
            raise AuthAPIError("recon_imbalanced", "Opening plus statement lines must equal closing")
        rec.status = BankReconciliation.Status.COMPLETE
        rec.save(update_fields=["status"])
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.reconcile",
            object_type="bank_reconciliation",
            object_id=rec.id,
            payload={"opening": str(rec.opening), "closing": str(rec.closing)},
        )
        return rec


def reopen_reconciliation(*, user_id, org, recon_id, reason):
    if not (reason or "").strip():
        raise AuthAPIError("validation_error", "Reopen reason is required")
    with finance_tx(user_id=user_id, organization_id=org.id):
        rec = BankReconciliation.objects.select_for_update().filter(id=recon_id, organization=org).first()
        if not rec:
            raise AuthAPIError("cross_organization", "Reconciliation not found")
        rec.status = BankReconciliation.Status.OPEN
        rec.reopen_reason = reason.strip()
        rec.save(update_fields=["status", "reopen_reason"])
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.reopen",
            object_type="bank_reconciliation",
            object_id=rec.id,
            payload={"reason": rec.reopen_reason},
        )
        return rec


def _rule_account(org, account_id):
    account = Account.objects.filter(id=account_id, organization=org).first()
    if not account:
        raise AuthAPIError("cross_organization", "Account not found")
    if account.status != Account.Status.ACTIVE:
        raise AuthAPIError("account_inactive", "Account is inactive")
    if account.is_control:
        raise AuthAPIError("control_account_restricted", "Control accounts require opening workflow")
    return account


def _matches(rule: BankRule, line: BankLine) -> bool:
    if rule.pattern.casefold() not in (line.description or "").casefold():
        return False
    if rule.direction == BankRule.Direction.INFLOW and line.amount <= 0:
        return False
    if rule.direction == BankRule.Direction.OUTFLOW and line.amount >= 0:
        return False
    return True


def create_bank_rule(*, user_id, org, payload):
    pattern = str(payload.get("pattern") or "").strip()
    if not pattern:
        raise AuthAPIError("validation_error", "pattern is required")
    direction = str(payload.get("direction") or BankRule.Direction.ANY)
    if direction not in BankRule.Direction.values:
        raise AuthAPIError("validation_error", "Invalid direction")
    try:
        priority = int(payload.get("priority") or 0)
    except (TypeError, ValueError):
        raise AuthAPIError("validation_error", "Invalid priority")
    with finance_tx(user_id=user_id, organization_id=org.id):
        account = _rule_account(org, payload.get("account_id"))
        rule = BankRule.objects.create(
            organization=org,
            pattern=pattern[:255],
            account=account,
            direction=direction,
            priority=priority,
        )
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.rule.create",
            object_type="bank_rule",
            object_id=rule.id,
            payload={"pattern": rule.pattern, "account_id": account.id},
        )
        return rule


def update_bank_rule(*, user_id, org, rule_id, payload):
    with finance_tx(user_id=user_id, organization_id=org.id):
        rule = BankRule.objects.select_for_update().filter(id=rule_id, organization=org).first()
        if not rule:
            raise AuthAPIError("cross_organization", "Bank rule not found")
        fields = []
        if "pattern" in payload:
            pattern = str(payload.get("pattern") or "").strip()
            if not pattern:
                raise AuthAPIError("validation_error", "pattern is required")
            rule.pattern = pattern[:255]
            fields.append("pattern")
        if "account_id" in payload:
            rule.account = _rule_account(org, payload.get("account_id"))
            fields.append("account")
        if "direction" in payload:
            direction = str(payload.get("direction") or "")
            if direction not in BankRule.Direction.values:
                raise AuthAPIError("validation_error", "Invalid direction")
            rule.direction = direction
            fields.append("direction")
        if "priority" in payload:
            try:
                rule.priority = int(payload.get("priority"))
            except (TypeError, ValueError):
                raise AuthAPIError("validation_error", "Invalid priority")
            fields.append("priority")
        if "active" in payload:
            rule.active = bool(payload.get("active"))
            fields.append("active")
        if fields:
            rule.save(update_fields=fields)
        return rule


def apply_bank_rules(*, user_id, org, account_id=None):
    categorized = []
    with finance_tx(user_id=user_id, organization_id=org.id):
        rules = list(BankRule.objects.filter(organization=org, active=True).order_by("priority", "id"))
        qs = BankLine.objects.select_for_update().filter(organization=org, status=BankLine.Status.IMPORTED)
        if account_id:
            qs = qs.filter(account_id=account_id)
        for line in qs.order_by("entry_date", "id"):
            rule = next((r for r in rules if _matches(r, line)), None)
            if not rule:
                continue
            try:
                categorized.append(
                    categorize_line(
                        user_id=user_id,
                        org=org,
                        line_id=line.id,
                        account_id=rule.account_id,
                        idempotency_key=f"bank-rule:{line.id}",
                    )
                )
            except AuthAPIError as exc:
                if exc.code == "already_matched":
                    continue
                raise
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.rule.apply",
            object_type="bank_rule",
            object_id=account_id or org.id,
            payload={"categorized": len(categorized)},
        )
        return categorized
