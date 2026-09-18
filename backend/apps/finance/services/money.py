from decimal import Decimal, ROUND_HALF_UP

QUANTITY_EXPONENT = 8
UNIT_COST_EXPONENT = 8


def _quantum(exponent: int) -> Decimal:
    return Decimal("1") if exponent == 0 else Decimal("1").scaleb(-exponent)


def quantize_amount(amount, exponent: int) -> Decimal:
    return Decimal(amount).quantize(_quantum(exponent), rounding=ROUND_HALF_UP)


def quantize_quantity(amount) -> Decimal:
    return quantize_amount(amount, QUANTITY_EXPONENT)


def quantize_unit_cost(amount) -> Decimal:
    return quantize_amount(amount, UNIT_COST_EXPONENT)
