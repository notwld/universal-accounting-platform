from decimal import Decimal, ROUND_HALF_UP


def quantize_amount(amount, exponent: int) -> Decimal:
    q = Decimal("1") if exponent == 0 else Decimal("1").scaleb(-exponent)
    return Decimal(amount).quantize(q, rounding=ROUND_HALF_UP)
