from pricing import price


def line_total(sku: str, quantity: int) -> int:
    return price(sku) * quantity
