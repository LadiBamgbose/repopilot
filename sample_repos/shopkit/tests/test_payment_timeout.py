from shopkit.payments.client import timeout_seconds


def test_payment_timeout_is_thirty_seconds():
    assert timeout_seconds() == 30
