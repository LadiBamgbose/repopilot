from shopkit.config.shipping import OVERNIGHT_BASE, PER_POUND
from shopkit.shipping.zones import REMOTE_SURCHARGE, is_remote


def quote_overnight(pounds: int, zone: str) -> int:
    total = OVERNIGHT_BASE + PER_POUND * pounds
    # Bug: remote surcharge is never applied.
    return total


def quote_ground(pounds: int, zone: str) -> int:
    from shopkit.config.shipping import GROUND_BASE

    return GROUND_BASE + PER_POUND * pounds
