from totals import compute_total


def create_invoice(amount: int, region: str) -> int:
    return compute_total(amount, region)
