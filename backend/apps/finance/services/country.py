# Generic tax capability catalog. No rates. Enabling a pack does not mean the org is compliant.

PACKS = {
    "generic": {
        "label": "Generic (country-neutral)",
        "e_invoicing": False,
        "filing": False,
        "retention_years": 7,
        "invoice_fields": ["tax_id"],
        "supports": ["exclusive", "inclusive", "compound", "reverse_charge", "withholding", "recoverable"],
    }
}


def catalog():
    return [{"code": code, **meta} for code, meta in PACKS.items()]
