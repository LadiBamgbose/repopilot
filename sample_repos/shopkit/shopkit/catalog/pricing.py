from shopkit.catalog.products import get_product


def unit_price(sku: str) -> int:
    return get_product(sku)["price"]
