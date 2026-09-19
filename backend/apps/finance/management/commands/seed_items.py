"""Seed demo warehouses, items, and stock for local UI work."""

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.finance.models import (
    Account,
    Currency,
    FinanceSettings,
    Item,
    StockBalance,
    Warehouse,
)
from apps.finance.services.setup import seed_preset_roles
from apps.tenancy.models import Organization

# sku, name, kind, tracked, unit_price, stock_qty (Main / West)
ITEMS = [
    ("SKU-1001", "Ceramic Mug 12oz", "good", True, "12.50", ("48", "24")),
    ("SKU-1002", "Stainless Water Bottle 750ml", "good", True, "28.00", ("36", "12")),
    ("SKU-1003", "Notebook A5 Ruled", "good", True, "6.75", ("120", "80")),
    ("SKU-1004", "Wireless Mouse", "good", True, "32.00", ("22", "8")),
    ("SKU-1005", "USB-C Hub 7-in-1", "good", True, "54.90", ("15", "5")),
    ("SKU-1006", "Desk Mat Large", "good", True, "24.00", ("18", "0")),
    ("SKU-2001", "Branded Tote Bag", "good", False, "9.50", None),
    ("SKU-2002", "Sticker Pack", "good", False, "4.00", None),
    ("SVC-3001", "Onboarding Setup", "service", False, "250.00", None),
    ("SVC-3002", "Monthly Support Retainer", "service", False, "499.00", None),
    ("SVC-3003", "Training Workshop (half day)", "service", False, "750.00", None),
    ("SKU-1007", "Monitor Arm Dual", "good", True, "89.00", ("7", "3")),
]

WAREHOUSES = ("Main", "West Coast", "East Depot")

ACCOUNTS = (
    ("1000", "Cash", "asset", False, ""),
    ("1100", "Accounts Receivable", "asset", True, "ar"),
    ("1400", "Inventory", "asset", False, ""),
    ("2100", "Accounts Payable", "liability", True, "ap"),
    ("3000", "Opening Equity", "equity", False, ""),
    ("4000", "Product Revenue", "income", False, ""),
    ("4100", "Service Revenue", "income", False, ""),
    ("5000", "Cost of Goods Sold", "expense", False, ""),
    ("5100", "Purchases", "expense", False, ""),
)


class Command(BaseCommand):
    help = "Seed realistic items, warehouses, and stock balances for an organization"

    def add_arguments(self, parser):
        parser.add_argument("--org", default="", help="Organization id or name (default: first org)")

    def handle(self, *args, **options):
        org = self._org(options["org"])
        income, expense, inv, cogs, ar, ap = self._ensure_books(org)
        wh_main, wh_west, _wh_east = self._warehouses(org)

        created = updated = 0
        for sku, name, kind, tracked, price, stock in ITEMS:
            item, was_created = Item.objects.update_or_create(
                organization=org,
                sku=sku,
                defaults={
                    "name": name,
                    "kind": kind,
                    "tracked": tracked,
                    "unit_price": Decimal(price),
                    "income_account": income if kind == "good" else Account.objects.get(
                        organization=org, code="4100"
                    ),
                    "expense_account": expense if tracked else None,
                    "status": "active",
                },
            )
            created += int(was_created)
            updated += int(not was_created)
            if tracked and stock:
                self._balance(org, wh_main, item, qty=stock[0], unit=price)
                self._balance(org, wh_west, item, qty=stock[1], unit=price)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {org.name}: {created} items created, {updated} updated; "
                f"warehouses={Warehouse.objects.filter(organization=org).count()}"
            )
        )

    def _org(self, key: str) -> Organization:
        qs = Organization.objects.all().order_by("created_at")
        if key:
            org = qs.filter(id=key).first() or qs.filter(name__iexact=key).first()
            if not org:
                raise CommandError(f"Organization not found: {key}")
            return org
        org = qs.first()
        if not org:
            raise CommandError("No organizations in the database")
        return org

    def _ensure_books(self, org: Organization):
        currency = Currency.objects.filter(pk="USD").first() or Currency.objects.first()
        if not currency:
            raise CommandError("No currencies seeded — run migrations first")

        for code, name, classification, is_control, control_kind in ACCOUNTS:
            Account.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "classification": classification,
                    "is_control": is_control,
                    "control_kind": control_kind,
                },
            )

        by_code = {a.code: a for a in Account.objects.filter(organization=org)}
        income, expense = by_code["4000"], by_code["5100"]
        inv, cogs, ar, ap = by_code["1400"], by_code["5000"], by_code["1100"], by_code["2100"]

        settings, _ = FinanceSettings.objects.get_or_create(
            organization=org,
            defaults={
                "country_code": "US",
                "base_currency": currency,
                "fiscal_year_start_month": 1,
                "timezone": "UTC",
                "locale": "en",
                "tax_registration_applies": False,
                "setup_completed_at": timezone.now(),
                "ar_account": ar,
                "ap_account": ap,
                "inventory_account": inv,
                "cogs_account": cogs,
            },
        )
        dirty = []
        if not settings.ar_account_id:
            settings.ar_account = ar
            dirty.append("ar_account")
        if not settings.ap_account_id:
            settings.ap_account = ap
            dirty.append("ap_account")
        if not settings.inventory_account_id:
            settings.inventory_account = inv
            dirty.append("inventory_account")
        if not settings.cogs_account_id:
            settings.cogs_account = cogs
            dirty.append("cogs_account")
        if dirty:
            settings.save(update_fields=dirty)
        seed_preset_roles(org)
        return income, expense, inv, cogs, ar, ap

    def _warehouses(self, org: Organization):
        return tuple(Warehouse.objects.get_or_create(organization=org, name=n)[0] for n in WAREHOUSES)

    def _balance(self, org, warehouse, item, *, qty: str, unit: str):
        q = Decimal(qty)
        if q <= 0:
            StockBalance.objects.filter(organization=org, warehouse=warehouse, item=item).delete()
            return
        value = (q * Decimal(unit)).quantize(Decimal("0.01"))
        StockBalance.objects.update_or_create(
            organization=org,
            warehouse=warehouse,
            item=item,
            defaults={"qty": q, "value": value},
        )
