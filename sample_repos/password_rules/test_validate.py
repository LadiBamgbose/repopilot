from validate import is_valid


def test_rejects_short_password():
    assert is_valid("short1") is False


def test_rejects_password_without_digit():
    assert is_valid("longenough") is False


def test_accepts_valid_password():
    assert is_valid("goodpas1") is True
