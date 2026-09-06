from decimal import Decimal

from app.services.profit import FORMULA, compute_line, q


def test_gross_profit_happy_path():
    r = compute_line(
        selling_price=Decimal("189.00"),
        cogs=Decimal("72.00"),
        marketplace_fees=Decimal("28.35"),
        shipping_cost=Decimal("6.40"),
        returns_refunds=Decimal("0"),
        ads=Decimal("12.00"),
    )
    assert r["gross_profit"] == Decimal("70.2500")
    assert r["margin_pct"] == Decimal("37.1693")
    assert FORMULA == "selling_price - cogs - marketplace_fees - shipping_cost - returns_refunds - ads"


def test_zero_selling_price_margin():
    r = compute_line(0, 10, 1)
    assert r["gross_profit"] == Decimal("-11.0000")
    assert r["margin_pct"] == Decimal("0.0000")


def test_quantization_is_stable():
    assert q("1.23456") == Decimal("1.2346")
    assert q(1) == Decimal("1.0000")
