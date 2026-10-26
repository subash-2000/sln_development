"""Parse stock move remarks created from inward posting."""

from __future__ import annotations

import re
from typing import Any


def parse_inward_move_remarks(remarks: str | None) -> dict[str, Any]:
    """Split user remark from Part / Pkgs / HSN / Boxes metadata."""
    if not remarks or not remarks.strip():
        return {
            "line_remark": "",
            "part_number": None,
            "package_count": None,
            "hsn_code": None,
        }

    user_parts: list[str] = []
    part_number = None
    package_count = None
    hsn_code = None

    for segment in remarks.split("|"):
        seg = segment.strip()
        if not seg:
            continue
        if seg.startswith("Part:"):
            part_number = seg[5:].strip() or None
        elif seg.startswith("Pkgs:"):
            m = re.search(r"(\d+)", seg[5:])
            package_count = int(m.group(1)) if m else None
        elif seg.startswith("HSN:"):
            hsn_code = seg[4:].strip() or None
        elif seg.startswith("Boxes:"):
            continue
        else:
            user_parts.append(seg)

    return {
        "line_remark": " | ".join(user_parts).strip(),
        "part_number": part_number,
        "package_count": package_count,
        "hsn_code": hsn_code,
    }
