from shopkit.catalog.pricing import unit_price


def line_total(sku: str, quantity: int) -> int:
    return unit_price(sku) * quantity
