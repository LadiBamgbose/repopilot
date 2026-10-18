from mailbox import normalize_email


def test_lowercases():
    assert normalize_email("Ada@Example.COM") == "ada@example.com"


def test_strips_spaces():
    assert normalize_email("  bob@ex.com  ") == "bob@ex.com"
