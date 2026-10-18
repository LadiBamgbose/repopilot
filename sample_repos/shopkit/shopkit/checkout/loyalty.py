from shopkit.util.money import percent_off

GOLD_RATE = 0.10


def apply_loyalty(subtotal: int, tier: str) -> int:
    if tier == "gold":
        return percent_off(subtotal, GOLD_RATE)
    return subtotal
