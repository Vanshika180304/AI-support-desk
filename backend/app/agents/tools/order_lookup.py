from __future__ import annotations

import random

from langchain_core.tools import tool


@tool
def order_lookup(order_id: str) -> str:
    """Look up the status of an order or subscription change.

    Args:
        order_id: The order ID, subscription ID, or reference number.

    Returns:
        Order status, estimated delivery or completion date.
    """
    # Mock implementation — replace with real order DB query in production
    statuses = [
        "Processing",
        "Confirmed",
        "Shipped",
        "Delivered",
        "Pending cancellation",
    ]
    status = random.choice(statuses)
    eta = "2024-01-28" if status not in ("Delivered",) else "N/A (completed)"

    return (
        f"Order ID: {order_id}\n"
        f"Status: {status}\n"
        f"ETA: {eta}\n"
        f"Last Updated: 2024-01-20 14:32 UTC"
    )
