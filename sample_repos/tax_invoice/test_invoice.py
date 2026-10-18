from invoice import create_invoice


def test_california_invoice():
    assert create_invoice(100, "CA") == 108


def test_new_york_invoice():
    assert create_invoice(100, "NY") == 104
