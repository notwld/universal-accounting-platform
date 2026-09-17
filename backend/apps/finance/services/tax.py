from decimal import Decimal

from apps.finance.services.money import quantize_amount


def line_tax(*, amount, rate, method: str, exponent: int):
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
