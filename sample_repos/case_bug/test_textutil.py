from textutil import normalize


def test_normalize_lowercases():
    assert normalize("AbC") == "abc"
