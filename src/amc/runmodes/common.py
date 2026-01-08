"""Common utilities for cost calculation across all runmodes.

This module provides shared functionality used by account, business unit, and service calculators
to eliminate code duplication and ensure consistency.
"""

import calendar
from datetime import datetime


def parse_cost_month(period_start_date: str) -> tuple[datetime, str]:
    """Parse period start date and return datetime object and formatted month name.

    Args:
        period_start_date: Start date string in format YYYY-MM-DD

    Returns:
        Tuple of (datetime object, formatted month name as YYYY-Mon)
    """
    cost_month = datetime.strptime(period_start_date, "%Y-%m-%d")
    cost_month_name = cost_month.strftime("%Y-%b")
    return cost_month, cost_month_name


def calculate_days_in_month(year: int, month: int) -> int:
    """Calculate the number of days in a given month, accounting for leap years.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        Number of days in the month
    """
    return calendar.monthrange(year, month)[1]


def extract_cost_amount(group_item: dict) -> float:
    """Extract and convert cost amount from AWS Cost Explorer group item.

    Args:
        group_item: Group item from AWS Cost Explorer response

    Returns:
        Cost amount as float
    """
    return float(group_item["Metrics"]["UnblendedCost"]["Amount"])


def calculate_daily_average(cost_amount: float, days_in_month: int) -> float:
    """Calculate daily average cost for a given month.

    Args:
        cost_amount: Total cost for the month
        days_in_month: Number of days in the month

    Returns:
        Daily average cost
    """
    return cost_amount / days_in_month


def add_total_to_cost_dict(cost_dict: dict) -> dict:
    """Add a 'total' key with sum of all values to a cost dictionary.

    Args:
        cost_dict: Dictionary of costs

    Returns:
        Dictionary with 'total' key added
    """
    cost_dict["total"] = round(sum(cost_dict.values()), 2)
    return cost_dict


def round_cost_values(cost_dict: dict) -> dict:
    """Round all cost values in dictionary to 2 decimal places.

    Args:
        cost_dict: Dictionary of costs

    Returns:
        Dictionary with rounded values
    """
    return {k: round(v, 2) for k, v in cost_dict.items()}


def get_most_recent_month(cost_matrix: dict) -> str:
    """Get the most recent month key from cost matrix.

    Args:
        cost_matrix: Dictionary of costs organized by month

    Returns:
        Most recent month key (YYYY-Mon format)
    """
    return next(reversed(cost_matrix))


def sort_by_cost_descending(items: dict, exclude_keys: list = None) -> list:
    """Sort items by cost in descending order.

    Args:
        items: Dictionary of items with cost values
        exclude_keys: List of keys to exclude from sorting (e.g., ['total'])

    Returns:
        List of tuples (item_name, cost) sorted by cost descending
    """
    exclude_keys = exclude_keys or []
    return sorted(
        ((item, cost) for item, cost in items.items() if item not in exclude_keys),
        key=lambda x: x[1],
        reverse=True,
    )


def build_top_n_matrix(cost_matrix: dict, top_items: list) -> dict:
    """Build a cost matrix containing only the top N items.

    Args:
        cost_matrix: Full cost matrix organized by month
        top_items: List of top item names to include

    Returns:
        Cost matrix with only top items, including recalculated totals
    """
    result_matrix = {}
    for cost_month, month_data in cost_matrix.items():
        month_costs = {item: month_data.get(item, 0) for item in top_items}
        month_costs["total"] = round(sum(month_costs.values()), 2)
        result_matrix[cost_month] = month_costs
    return result_matrix
