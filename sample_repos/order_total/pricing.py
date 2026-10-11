from catalog import price

PRICES = {"widget": 5, "gadget": 7}


def _price(sku: str) -> int:
    return PRICES[sku]
