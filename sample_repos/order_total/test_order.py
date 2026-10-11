from order import line_total


def test_two_widgets_cost_ten():
    assert line_total("widget", 2) == 10


def test_three_gadgets_cost_twenty_one():
    assert line_total("gadget", 3) == 21
