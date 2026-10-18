from shopkit.catalog.pricing import unit_price
from shopkit.catalog.products import list_skus


def test_widget_price():
    assert unit_price("widget") == 25


def test_list_skus():
    assert "gadget" in list_skus()
