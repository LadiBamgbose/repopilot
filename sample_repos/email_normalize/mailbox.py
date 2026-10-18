from cleaners import clean_email


def normalize_email(value: str) -> str:
    return clean_email(value)
