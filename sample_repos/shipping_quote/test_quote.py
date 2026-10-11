from quote import quote_package


def test_overnight_two_pounds():
    assert quote_package(2, "overnight") == 25


def test_ground_two_pounds():
    assert quote_package(2, "ground") == 13
