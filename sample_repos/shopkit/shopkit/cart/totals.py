def merchandise_subtotal(lines: list[tuple[str, int]]) -> int:
    from shopkit.cart.lines import line_total

    return sum(line_total(sku, quantity) for sku, quantity in lines)


def final_merchandise(
    subtotal: int,
    *,
    tier: str = "none",
    coupon_rate: float = 0.0,
) -> int:
    """Apply loyalty and optional coupon.

    Correct behavior: loyalty first, then coupon on the reduced amount.
    This path keeps its own loyalty math so the checkout loyalty-rate bug
    remains a separate task.
    """
    loyalty_off = 0
    if tier == "gold":
        loyalty_off = int(subtotal * 0.15)
    coupon_off = int(subtotal * coupon_rate) if coupon_rate else 0
    # Bug: both discounts are taken from the original subtotal.
    return subtotal - loyalty_off - coupon_off
