from rules import has_required_digit, meets_length


def is_valid(password: str) -> bool:
    return meets_length(password) and has_required_digit(password)
