from fees import service_fee


def charge(amount: int) -> int:
    return amount + service_fee(amount)


def quote(amount: int) -> int:
    return amount + service_fee(amount)
