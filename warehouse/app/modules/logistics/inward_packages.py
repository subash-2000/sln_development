"""Serialize / parse inward invoice package lines stored on stock_transactions.remarks."""

import json
from typing import Any

PACKAGES_TAG = "[INWARD_PACKAGES]"


def encode_packages_json(package_lines: list[dict[str, Any]], total_packages: int | None) -> str:
    data = {"lines": package_lines, "total_packages": total_packages}
    return f"{PACKAGES_TAG}{json.dumps(data, separators=(',', ':'))}"


def parse_packages_from_remarks(remarks: str | None) -> dict[str, Any] | None:
    if not remarks or PACKAGES_TAG not in remarks:
        return None
    try:
        raw = remarks.split(PACKAGES_TAG, 1)[1].strip()
        json_part = raw.split(" | ", 1)[0].strip()
        return json.loads(json_part)
    except (json.JSONDecodeError, IndexError):
        return None
