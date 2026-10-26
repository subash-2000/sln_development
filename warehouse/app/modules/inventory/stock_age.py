"""Age of stock since last movement (aligned with inventory master 'age of days' concept)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

AgeStatus = Literal["STOCK_OK", "AGING", "OVERDUE", "UNKNOWN"]

# ≤7 days: STOCK OK (e.g. "5 days" still OK); 8–30: Aging; 31+: Review
STOCK_OK_MAX_DAYS = 7
AGING_MAX_DAYS = 30


def compute_stock_age(last_movement_at: datetime | None) -> tuple[int | None, str | None, AgeStatus]:
    if last_movement_at is None:
        return None, None, "UNKNOWN"

    now = datetime.now(UTC)
    moved = last_movement_at
    if moved.tzinfo is None:
        moved = moved.replace(tzinfo=UTC)
    else:
        moved = moved.astimezone(UTC)

    days = max(0, (now - moved).days)
    if days == 0:
        label = "Today"
    elif days == 1:
        label = "1 day"
    else:
        label = f"{days} days"

    if days <= STOCK_OK_MAX_DAYS:
        status: AgeStatus = "STOCK_OK"
    elif days <= AGING_MAX_DAYS:
        status = "AGING"
    else:
        status = "OVERDUE"

    return days, label, status


def age_status_display(status: AgeStatus | str | None) -> str:
    mapping = {
        "STOCK_OK": "STOCK OK",
        "AGING": "Aging",
        "OVERDUE": "Review",
        "UNKNOWN": "—",
    }
    if not status:
        return "—"
    return mapping.get(str(status).upper(), str(status))
