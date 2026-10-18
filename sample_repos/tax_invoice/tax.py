from rates import rate_for


def apply_tax(amount: int, region: str) -> int:
    return amount + int(amount * rate_for(region))
