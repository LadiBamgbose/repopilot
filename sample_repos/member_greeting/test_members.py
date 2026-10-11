from members import message


def test_new_member_greeting():
    assert message("Ada", "new") == "Welcome, Ada."
