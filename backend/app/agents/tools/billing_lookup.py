from __future__ import annotations

import random

from langchain_core.tools import tool


@tool
def billing_lookup(customer_id: str) -> str:
    """Look up billing information for a customer.

    Args:
        customer_id: The customer's account ID or email.

    Returns:
        Billing summary including plan, next invoice date, and outstanding balance.
    """
    # Mock implementation — replace with real billing DB query in production
    plans = ["Basic ($9/mo)", "Pro ($29/mo)", "Enterprise ($99/mo)"]
    statuses = ["Current", "Current", "Current", "Overdue"]
    plan = random.choice(plans)
    balance = round(random.uniform(0, 150), 2)
    status = random.choice(statuses)

    return (
        f"Customer: {customer_id}\n"
        f"Plan: {plan}\n"
        f"Balance: ${balance}\n"
        f"Payment Status: {status}\n"
        f"Next Invoice: 2024-02-01\n"
        f"Billing Email: {customer_id}@example.com"
    )
