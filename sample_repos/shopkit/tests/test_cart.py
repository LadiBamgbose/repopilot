from shopkit.cart.lines import line_total


def test_line_total():
    assert line_total("widget", 2) == 50
