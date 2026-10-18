RATES = {
    "CA": 0.05,
    "NY": 0.04,
}


def rate_for(region: str) -> float:
    return RATES[region]
