from billing import charge, quote


def test_charge_includes_ten_percent_fee():
    assert charge(100) == 110


def test_quote_includes_ten_percent_fee():
    assert quote(40) == 44
