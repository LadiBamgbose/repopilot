from shopkit.checkout.order import merchandise_total


def test_gold_member_pays_fifteen_percent_less():
    assert merchandise_total(100, tier="gold") == 85
