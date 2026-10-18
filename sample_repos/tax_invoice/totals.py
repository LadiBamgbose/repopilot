from tax import apply_tax


def compute_total(amount: int, region: str) -> int:
    return apply_tax(amount, region)
