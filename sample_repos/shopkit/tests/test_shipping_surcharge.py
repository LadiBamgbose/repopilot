from shopkit.shipping.quotes import quote_overnight


def test_overnight_remote_includes_surcharge():
    # overnight base 20 + 2lb*2 + remote surcharge 7 = 31
    assert quote_overnight(2, "HI") == 31


def test_overnight_local_has_no_surcharge():
    assert quote_overnight(2, "CA") == 24
