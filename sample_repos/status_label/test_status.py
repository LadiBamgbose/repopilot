from status import display


def test_active_user_label():
    assert display("Ada", "active") == "Active: Ada"
