from shopkit.cart.totals import final_merchandise


def test_loyalty_only():
    assert final_merchandise(100, tier="gold") == 85


def test_coupon_only():
    assert final_merchandise(100, coupon_rate=0.10) == 90


def test_loyalty_then_coupon_on_reduced_amount():
    # 100 -> 85 after loyalty, then 10% off 85 -> 77
    assert final_merchandise(100, tier="gold", coupon_rate=0.10) == 77
