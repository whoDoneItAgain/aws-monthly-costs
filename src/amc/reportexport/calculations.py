"""Calculation utilities for report generation.

This module provides common calculation functions used across report exports
to eliminate code duplication.
"""


def calculate_percentage_difference(val1: float, val2: float) -> float:
    """Calculate percentage difference between two values.

    Handles edge cases:
    - If val1 is 0 and val2 is non-zero, returns 1.0 (100% increase) or -1.0 (100% decrease)
    - If both values are 0, returns 0.0
    - Otherwise calculates: (val2 - val1) / val1

    Args:
        val1: First value (baseline)
        val2: Second value (comparison)

    Returns:
        Percentage difference as a decimal (e.g., 0.25 for 25% increase)
    """
    if val1 > 0:
        return (val2 - val1) / val1
    elif val1 == 0 and val2 != 0:
        # If starting from 0, show as 100% increase/decrease
        return 1.0 if val2 > 0 else -1.0
    else:
        # Both are 0
        return 0.0


def calculate_difference(val1: float, val2: float) -> float:
    """Calculate absolute difference between two values.

    Args:
        val1: First value
        val2: Second value

    Returns:
        Absolute difference
    """
    return abs(val2 - val1)


def calculate_percentage_spend(value: float, total: float) -> float:
    """Calculate what percentage a value represents of a total.

    Args:
        value: The value to calculate percentage for
        total: The total to compare against (denominator)

    Returns:
        Percentage as a decimal (e.g., 0.15 for 15%)
    """
    if total > 0:
        return value / total
    return 0.0
