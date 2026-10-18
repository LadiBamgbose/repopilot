from shopkit.checkout.loyalty import apply_loyalty


def merchandise_total(subtotal: int, tier: str = "none") -> int:
    return apply_loyalty(subtotal, tier)
