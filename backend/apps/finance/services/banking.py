import csv
import hashlib
import io
import ipaddress
import re
import socket
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

import httpx
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.authentication.exceptions import AuthAPIError
from apps.finance.models import (
    Account,
    BankFeed,
    BankLine,
    BankReconciliation,
    BankRule,
    BankStatement,
    CustomerPayment,
    FinanceAuditEvent,
    FinanceSettings,
    JournalEntry,
    JournalLine,
    VendorPayment,
)
from apps.finance.services.context import finance_tx
from apps.finance.services.money import quantize_amount
from apps.finance.services.posting import post_generated
from apps.finance.services.workflow import parse_optional_decimal, record_exception


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


def _parse_qif_date(value) -> date:
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%m/%d/%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except ValueError:
            continue
    return _parse_date(s)


def _parse_ofx(raw, exponent: int):
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else raw
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", text, flags=re.I | re.S)
    if not blocks:
        parts = re.split(r"<STMTTRN>", text, flags=re.I)[1:]
        blocks = [re.split(r"<STMTTRN>", p, flags=re.I)[0] for p in parts]
    dicts = []
    for block in blocks:
        amt = re.search(r"<TRNAMT>\s*([^<\s]+)", block, flags=re.I)
        posted = re.search(r"<DTPOSTED>\s*([^<\s]+)", block, flags=re.I)
        memo = re.search(r"<(?:MEMO|NAME)>\s*([^<\r\n]+)", block, flags=re.I)
        if not amt or not posted:
            continue
        digits = re.sub(r"[^0-9]", "", posted.group(1))[:8]
        dicts.append(
            {
                "date": f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}",
                "amount": amt.group(1).strip(),
                "description": (memo.group(1).strip() if memo else "")[:255],
            }
        )
    if not dicts:
        raise AuthAPIError("validation_error", "OFX has no transactions")
    return _coerce_rows(dicts, exponent)


def _parse_qif(raw, exponent: int):
    text = raw.decode("utf-8", errors="replace") if isinstance(raw, (bytes, bytearray)) else raw
    dicts = []
    cur = {}
    for line in text.splitlines():
        if not line:
            continue
        code, rest = line[0], line[1:].strip()
        if code == "D":
            cur["date"] = _parse_qif_date(rest).isoformat()
        elif code == "T" or code == "U":
            cur["amount"] = rest.replace("(", "-").replace(")", "")
        elif code in ("P", "M"):
            cur["description"] = rest[:255]
        elif code == "^":
            if "date" in cur and "amount" in cur:
                cur.setdefault("description", "")
                dicts.append(cur)
            cur = {}
    if "date" in cur and "amount" in cur:
        cur.setdefault("description", "")
        dicts.append(cur)
    if not dicts:
        raise AuthAPIError("validation_error", "QIF has no transactions")
    return _coerce_rows(dicts, exponent)


def _rows_from_table(table, exponent: int):
    header_idx = next((i for i, row in enumerate(table) if any(str(c).strip() for c in row)), None)
    if header_idx is None:
        raise AuthAPIError("validation_error", "Statement has no header")
    fields = _header_map(table[header_idx])
    key_to_col = {k: table[header_idx].index(fields[k]) for k in ("date", "amount", "description")}
    dicts = []
    for row in table[header_idx + 1 :]:
        dicts.append({k: row[idx] if idx < len(row) else "" for k, idx in key_to_col.items()})
    return _coerce_rows(dicts, exponent)


def _parse_xls(raw, exponent: int):
    if not isinstance(raw, (bytes, bytearray)):
        raw = raw.encode()
    try:
        import xlrd
        wb = xlrd.open_workbook(file_contents=bytes(raw))
        sheet = wb.sheet_by_index(0)
        table = []
        for r in range(sheet.nrows):
            row = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate_as_datetime(cell.value, wb.datemode).date().isoformat())
                else:
                    row.append(cell.value)
            table.append(row)
        return _rows_from_table(table, exponent)
    except Exception as exc:
        raise AuthAPIError("validation_error", "Invalid spreadsheet") from exc


def _parse_statement(file_obj, exponent: int):
    raw = file_obj.read()
    name = (getattr(file_obj, "name", "") or "").lower()
    sample = raw[:64] if isinstance(raw, (bytes, bytearray)) else str(raw)[:64].encode()
    text_head = sample.decode("utf-8", errors="ignore").lstrip()
    if name.endswith(".ofx") or name.endswith(".qfx") or b"OFXHEADER" in sample.upper() or "<OFX" in text_head.upper():
        return _parse_ofx(raw, exponent)
    if name.endswith(".qif") or text_head.startswith("!Type"):
        return _parse_qif(raw, exponent)
    xlsx = name.endswith(".xlsx") or sample[:2] == b"PK"
    if xlsx:
        if isinstance(raw, str):
            raw = raw.encode()
        return _parse_xlsx(raw, exponent)
    if name.endswith(".xls") or sample[:4] == b"\xd0\xcf\x11\xe0":
        return _parse_xls(raw, exponent)
    return _parse_csv_bytes(raw, exponent)


def import_statement(*, user_id, org, account_id, uploaded, dry_run=False):
    with finance_tx(user_id=user_id, organization_id=org.id):
        account = _bank_account(org, account_id)
        exponent = _settings(org).base_currency.exponent
        raw = uploaded.read()
        if isinstance(raw, str):
            raw = raw.encode()
        file_hash = hashlib.sha256(raw).hexdigest()
        prior = BankStatement.objects.filter(
            organization=org, account=account, file_hash=file_hash
        ).first()
        if prior:
            duplicates = [
                {"entry_date": line.entry_date.isoformat(), "amount": str(line.amount), "description": line.description}
                for line in prior.lines.all()
            ]
            return prior, [], duplicates, []
        wrapped = SimpleUploadedFile(getattr(uploaded, "name", "") or "statement.csv", raw)
        rows = _parse_statement(wrapped, exponent)
        existing_fps = set(
            BankLine.objects.filter(organization=org, account=account).values_list("fingerprint", flat=True)
        )
        if dry_run:
            created, duplicates = [], []
            seen = set(existing_fps)
            for entry_date, amount, description in rows:
                fp = _fingerprint(org.id, account.id, entry_date, amount, description)
                row = {"entry_date": entry_date.isoformat(), "amount": str(amount), "description": description}
                if fp in seen:
                    duplicates.append(row)
                else:
                    created.append(row)
                    seen.add(fp)
            return None, created, duplicates, []
        statement = BankStatement.objects.create(
            organization=org,
            account=account,
            original_name=(getattr(uploaded, "name", "") or "")[:255],
            file_hash=file_hash,
        )
        created, duplicates = [], []
        for source_row, (entry_date, amount, description) in enumerate(rows, start=1):
            fp = _fingerprint(org.id, account.id, entry_date, amount, description)
            review = fp in existing_fps
            line = BankLine.objects.create(
                organization=org,
                statement=statement,
                account=account,
                entry_date=entry_date,
                amount=amount,
                description=description,
                fingerprint=fp,
                parser_version="1",
                source_row=source_row,
                raw={"date": entry_date.isoformat(), "amount": str(amount), "description": description},
                review_reason="fingerprint_match" if review else "",
                status=BankLine.Status.REVIEW if review else BankLine.Status.IMPORTED,
            )
            if review:
                duplicates.append({"entry_date": entry_date.isoformat(), "amount": str(amount), "description": description})
            else:
                created.append(line)
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.import",
            object_type="bank_statement",
            object_id=statement.id,
            payload={"created": len(created), "duplicates": len(duplicates)},
        )
    categorized = apply_bank_rules(user_id=user_id, org=org, account_id=account.id) if created else []
    return statement, created, duplicates, categorized


def match_line(*, user_id, org, line_id, customer_payment_id=None, vendor_payment_id=None):
    if bool(customer_payment_id) == bool(vendor_payment_id):
        raise AuthAPIError("validation_error", "Provide exactly one payment id")
    with finance_tx(user_id=user_id, organization_id=org.id):
        line = BankLine.objects.select_for_update().filter(id=line_id, organization=org).first()
        if not line:
            raise AuthAPIError("cross_organization", "Bank line not found")
        if line.status not in (BankLine.Status.IMPORTED, BankLine.Status.REVIEW):
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
        if line.status not in (BankLine.Status.IMPORTED, BankLine.Status.REVIEW):
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
        if BankReconciliation.objects.filter(
            organization=org,
            account=rec.account,
            status=BankReconciliation.Status.COMPLETE,
            start_on__lte=rec.end_on,
            end_on__gte=rec.start_on,
        ).exclude(pk=rec.pk).exists():
            raise AuthAPIError("recon_overlap", "Overlapping completed reconciliation exists")
        exponent = _settings(org).base_currency.exponent
        period = BankLine.objects.filter(
            organization=org, account=rec.account, entry_date__gte=rec.start_on, entry_date__lte=rec.end_on
        )
        if period.exclude(status__in=[BankLine.Status.MATCHED, BankLine.Status.CATEGORIZED]).exists():
            raise AuthAPIError("recon_unresolved", "Unresolved statement lines remain")
        net = period.aggregate(total=Sum("amount"))["total"] or Decimal("0")
        net = quantize_amount(net, exponent)
        if rec.opening + net != rec.closing:
            raise AuthAPIError("recon_imbalanced", "Opening plus statement lines must equal closing")
        from apps.finance.models import JournalLine

        agg = JournalLine.objects.filter(
            organization=org,
            account=rec.account,
            journal__status=JournalEntry.Status.POSTED,
            journal__entry_date__lte=rec.end_on,
        ).aggregate(d=Sum("debit"), c=Sum("credit"))
        rec.book_balance = quantize_amount((agg["d"] or 0) - (agg["c"] or 0), exponent)
        rec.status = BankReconciliation.Status.COMPLETE
        rec.save(update_fields=["status", "book_balance"])
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.reconcile",
            object_type="bank_reconciliation",
            object_id=rec.id,
            payload={"opening": str(rec.opening), "closing": str(rec.closing)},
        )
        return rec


def recon_evidence(org, rec: BankReconciliation):
    period = BankLine.objects.filter(
        organization=org, account=rec.account, entry_date__gte=rec.start_on, entry_date__lte=rec.end_on
    )
    cleared = period.filter(status__in=[BankLine.Status.MATCHED, BankLine.Status.CATEGORIZED])
    outstanding_statement = [
        {"id": x.id, "entry_date": x.entry_date.isoformat(), "amount": str(x.amount), "description": x.description, "status": x.status}
        for x in period.exclude(status__in=[BankLine.Status.MATCHED, BankLine.Status.CATEGORIZED])
    ]
    linked = set(period.exclude(journal_id=None).values_list("journal_id", flat=True))
    uncleared_book = []
    for line in JournalLine.objects.filter(
        organization=org,
        account=rec.account,
        journal__status=JournalEntry.Status.POSTED,
        journal__entry_date__gte=rec.start_on,
        journal__entry_date__lte=rec.end_on,
    ).select_related("journal"):
        if line.journal_id in linked:
            continue
        uncleared_book.append(
            {
                "journal_id": line.journal_id,
                "entry_date": line.journal.entry_date.isoformat(),
                "debit": str(line.debit),
                "credit": str(line.credit),
                "description": line.description,
            }
        )
    difference = rec.book_balance - rec.closing
    return {
        "opening": str(rec.opening),
        "closing": str(rec.closing),
        "book_balance": str(rec.book_balance),
        "cleared_count": cleared.count(),
        "outstanding_statement": outstanding_statement,
        "uncleared_book": uncleared_book,
        "difference": str(difference),
    }


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
    text = line.description or ""
    if rule.match_kind == BankRule.MatchKind.REGEX:
        try:
            if not re.search(rule.pattern, text, flags=re.I):
                return False
        except re.error:
            return False
    elif rule.pattern.casefold() not in text.casefold():
        return False
    if rule.direction == BankRule.Direction.INFLOW and line.amount <= 0:
        return False
    if rule.direction == BankRule.Direction.OUTFLOW and line.amount >= 0:
        return False
    if rule.amount_min is not None and line.amount < rule.amount_min:
        return False
    if rule.amount_max is not None and line.amount > rule.amount_max:
        return False
    return True


def _rule_match_fields(payload, rule=None):
    match_kind = str(payload.get("match_kind") or (rule.match_kind if rule else BankRule.MatchKind.CONTAINS))
    if match_kind not in BankRule.MatchKind.values:
        raise AuthAPIError("validation_error", "Invalid match_kind")
    raw = payload.get("pattern") if "pattern" in payload else (rule.pattern if rule else "")
    pattern = str(raw or "").strip()
    if not pattern:
        raise AuthAPIError("validation_error", "pattern is required")
    if match_kind == BankRule.MatchKind.REGEX:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise AuthAPIError("validation_error", "Invalid regex") from exc
    amount_min = parse_optional_decimal(payload["amount_min"]) if "amount_min" in payload else (rule.amount_min if rule else None)
    amount_max = parse_optional_decimal(payload["amount_max"]) if "amount_max" in payload else (rule.amount_max if rule else None)
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise AuthAPIError("validation_error", "amount_min cannot exceed amount_max")
    return pattern[:255], match_kind, amount_min, amount_max


def create_bank_rule(*, user_id, org, payload):
    pattern, match_kind, amount_min, amount_max = _rule_match_fields(payload)
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
            pattern=pattern,
            match_kind=match_kind,
            amount_min=amount_min,
            amount_max=amount_max,
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
        if "pattern" in payload or "match_kind" in payload or "amount_min" in payload or "amount_max" in payload:
            merged = {
                "pattern": payload.get("pattern", rule.pattern),
                "match_kind": payload.get("match_kind", rule.match_kind),
                "amount_min": payload["amount_min"] if "amount_min" in payload else rule.amount_min,
                "amount_max": payload["amount_max"] if "amount_max" in payload else rule.amount_max,
            }
            rule.pattern, rule.match_kind, rule.amount_min, rule.amount_max = _rule_match_fields(merged, rule)
            fields.extend(["pattern", "match_kind", "amount_min", "amount_max"])
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
        if not rules:
            return []
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
                record_exception(
                    org=org,
                    kind="bank_rule_apply",
                    reason=exc.message,
                    object_type="bank_line",
                    object_id=line.id,
                )
        FinanceAuditEvent.objects.create(
            organization=org,
            actor_user_id=user_id,
            action="bank.rule.apply",
            object_type="bank_rule",
            object_id=account_id or org.id,
            payload={"categorized": len(categorized)},
        )
        return categorized


def _host_blocked(host: str) -> bool:
    host = (host or "").strip().rstrip(".").lower()
    if not host or host == "localhost" or host.endswith(".localhost") or host.endswith(".internal"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _safe_feed_url(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme != "https" or not parsed.hostname:
        raise AuthAPIError("validation_error", "Feed URL must be https")
    if _host_blocked(parsed.hostname):
        raise AuthAPIError("validation_error", "Feed URL is not allowed")
    return parsed.geturl()


def _http_get_safe(url: str) -> bytes:
    parsed = urlparse(_safe_feed_url(url))
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise AuthAPIError("validation_error", "Feed host could not be resolved") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            raise AuthAPIError("validation_error", "Feed URL is not allowed")
    try:
        response = httpx.get(parsed.geturl(), timeout=15.0, follow_redirects=False)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise AuthAPIError("validation_error", "Feed fetch failed") from exc
    if len(response.content) > 2_000_000:
        raise AuthAPIError("validation_error", "Feed file is too large")
    return response.content


def create_bank_feed(*, user_id, org, payload):
    url = _safe_feed_url(payload.get("url"))
    with finance_tx(user_id=user_id, organization_id=org.id):
        account = _bank_account(org, payload.get("account_id"))
        return BankFeed.objects.create(organization=org, account=account, url=url)


def fetch_bank_feed(*, user_id, org, feed_id):
    with finance_tx(user_id=user_id, organization_id=org.id):
        feed = BankFeed.objects.select_for_update().filter(id=feed_id, organization=org).first()
        if not feed or not feed.active:
            raise AuthAPIError("cross_organization", "Bank feed not found")
        account_id = feed.account_id
        url = feed.url
        name = url.rsplit("/", 1)[-1] or "feed.ofx"
    try:
        raw = _http_get_safe(url)
        uploaded = SimpleUploadedFile(name, raw)
        statement, created, duplicates, categorized = import_statement(
            user_id=user_id, org=org, account_id=account_id, uploaded=uploaded
        )
        with finance_tx(user_id=user_id, organization_id=org.id):
            BankFeed.objects.filter(pk=feed_id).update(last_fetched_at=timezone.now(), last_error="")
        return statement, created, duplicates, categorized
    except AuthAPIError as exc:
        with finance_tx(user_id=user_id, organization_id=org.id):
            BankFeed.objects.filter(pk=feed_id).update(last_error=exc.message[:500])
            record_exception(org=org, kind="bank_feed_fetch", reason=exc.message, object_type="bank_feed", object_id=feed_id)
        raise
