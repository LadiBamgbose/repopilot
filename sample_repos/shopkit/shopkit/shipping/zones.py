REMOTE_ZONES = {"AK", "HI"}
REMOTE_SURCHARGE = 0


def is_remote(zone: str) -> bool:
    return zone in REMOTE_ZONES
