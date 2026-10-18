PRODUCTS = {
    "widget": {"name": "Widget", "price": 25},
    "gadget": {"name": "Gadget", "price": 40},
}


def get_product(sku: str) -> dict:
    return PRODUCTS[sku]


def list_skus() -> list[str]:
    return sorted(PRODUCTS)
