from shopkit.notifications.emailer import render_order_email


def test_order_email():
    assert render_order_email("Ada") == "Thanks for your order, Ada!"
