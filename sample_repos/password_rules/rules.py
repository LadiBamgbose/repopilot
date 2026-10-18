MIN_LENGTH = 8


def meets_length(password: str) -> bool:
    return len(password) > MIN_LENGTH


def has_required_digit(password: str) -> bool:
    return any(character.isupper() for character in password)
