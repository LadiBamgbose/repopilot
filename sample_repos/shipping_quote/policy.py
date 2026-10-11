from rates import RATES

PER_POUND = 2.5


def price_for(method: str, pounds: int) -> float:
    return RATES[method] + PER_POUND * pounds
