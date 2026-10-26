from decimal import Decimal

ZERO = Decimal("0")


def received_quantity(
    pallet_count: int | Decimal,
    qty_per_pallet: Decimal,
    box_count: int | Decimal,
    qty_per_box: Decimal,
) -> Decimal:
    """(P × Qp) + (B × Qb) as used on rings inward sheets."""
    pallets = Decimal(pallet_count or 0)
    boxes = Decimal(box_count or 0)
    per_pallet = Decimal(qty_per_pallet or 0)
    per_box = Decimal(qty_per_box or 0)
    qty = (pallets * per_pallet) + (boxes * per_box)
    return qty.quantize(Decimal("0.001"))


def basic_value(quantity: Decimal, unit_rate: Decimal) -> Decimal:
    return (Decimal(quantity or 0) * Decimal(unit_rate or 0)).quantize(Decimal("0.01"))


def ring_weight_total(quantity: Decimal, per_ring_weight: Decimal) -> Decimal:
    return (Decimal(quantity or 0) * Decimal(per_ring_weight or 0)).quantize(Decimal("0.001"))


def gross_weight(quantity: Decimal, per_ring_weight: Decimal, packing_weight: Decimal) -> Decimal:
    """Physical gross weight: (qty × ring kg) + total packing kg. Never uses basic value."""
    return (ring_weight_total(quantity, per_ring_weight) + Decimal(packing_weight or 0)).quantize(
        Decimal("0.001")
    )


def packing_detail_text(
    packing_detail: str | None,
    pallet_count: int | Decimal = 0,
    qty_per_pallet: Decimal = ZERO,
    box_count: int | Decimal = 0,
    qty_per_box: Decimal = ZERO,
) -> str:
    if packing_detail and str(packing_detail).strip():
        return str(packing_detail).strip()
    parts: list[str] = []
    if int(pallet_count or 0) and Decimal(qty_per_pallet or 0) > 0:
        parts.append(f"{int(pallet_count)}*{_compact_qty(qty_per_pallet)}")
    if int(box_count or 0) and Decimal(qty_per_box or 0) > 0:
        parts.append(f"{int(box_count)}*{_compact_qty(qty_per_box)}")
    return "+".join(parts)


def compact_qty(value: Decimal) -> str:
    d = Decimal(value or 0)
    if d == d.to_integral_value():
        return str(int(d))
    return format(d.normalize(), "f")


def box_star_qty(
    box_count: int | Decimal = 0,
    qty_per_box: Decimal = ZERO,
    pallet_count: int | Decimal = 0,
    qty_per_pallet: Decimal = ZERO,
) -> str | None:
    if int(box_count or 0) and Decimal(qty_per_box or 0) > 0:
        return f"{int(box_count)}*{compact_qty(qty_per_box)}"
    if int(pallet_count or 0) and Decimal(qty_per_pallet or 0) > 0:
        return f"{int(pallet_count)}*{compact_qty(qty_per_pallet)}"
    return None


def _compact_qty(value: Decimal) -> str:
    return compact_qty(value)
