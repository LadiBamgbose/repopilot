from shopkit.export.report import export_order_csv


def test_export_order_csv_line():
    assert export_order_csv("ord-1", "ada@example.com", 85) == "ord-1,ada@example.com,85"
