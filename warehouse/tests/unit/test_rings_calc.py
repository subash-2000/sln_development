from decimal import Decimal

from app.modules.rings.calc import basic_value, gross_weight, packing_detail_text, received_quantity


def test_received_quantity_pallets_and_boxes():
    assert received_quantity(11, Decimal("300"), 2, Decimal("100")) == Decimal("3500.000")


def test_gross_weight_uses_quantity_not_basic_value():
    qty = Decimal("3500")
    ring_wt = Decimal("0.063")
    packing = Decimal("12")
    assert gross_weight(qty, ring_wt, packing) == Decimal("232.500")
    assert basic_value(qty, Decimal("2.5")) == Decimal("8750.00")
    # Excel wrongly did basic_value * ring_wt; that must not be the gross weight.
    assert gross_weight(qty, ring_wt, packing) != (
        basic_value(qty, Decimal("2.5")) * ring_wt + packing
    ).quantize(Decimal("0.001"))


def test_packing_detail_from_pallets():
    assert packing_detail_text(None, 3, Decimal("5000"), 0, Decimal("0")) == "3*5000"


def test_amount_in_words():
    from app.modules.rings.pdf_common import amount_in_words

    assert amount_in_words(Decimal("8750")).startswith("Rupees")
