"""Business unit cost calculation module.

This module contains the business logic for calculating AWS costs grouped by business unit.
"""

import logging

from amc.runmodes.common import (
    add_total_to_cost_dict,
    calculate_daily_average,
    calculate_days_in_month,
    extract_cost_amount,
    parse_cost_month,
    round_cost_values,
)

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, daily_average=False):
    """Build cost dictionary from AWS Cost Explorer response.

    Args:
        cost_and_usage: Response from AWS Cost Explorer API
        daily_average: If True, calculate daily average costs

    Returns:
        Dictionary of costs organized by month and account ID
    """
    account_costs: dict = {}

    for period in cost_and_usage["ResultsByTime"]:
        cost_month, cost_month_name = parse_cost_month(period["TimePeriod"]["Start"])

        if daily_average:
            days_in_month = calculate_days_in_month(cost_month.year, cost_month.month)
            month_costs = {
                account["Keys"][0]: calculate_daily_average(
                    extract_cost_amount(account), days_in_month
                )
                for account in period["Groups"]
            }
        else:
            month_costs = {
                account["Keys"][0]: extract_cost_amount(account)
                for account in period["Groups"]
            }

        account_costs[cost_month_name] = month_costs

    return account_costs


def _build_cost_matrix(account_list, account_costs, ss_percentages=None, ss_costs=None):
    """Build final cost matrix aggregated by business unit.

    Args:
        account_list: Dictionary of business unit account groups
        account_costs: Dictionary of costs by account ID
        ss_percentages: Optional shared services allocation percentages
        ss_costs: Optional shared services cost matrix

    Returns:
        Dictionary of costs aggregated by business unit
    """
    cost_matrix: dict = {}

    for cost_month, costs_for_month in account_costs.items():
        bu_month_costs: dict = {}
        
        # Track which accounts have been assigned to a BU
        assigned_accounts = set()

        # Aggregate costs by BU
        for bu, bu_accounts in account_list.items():
            # Sum costs for all accounts in this BU
            bu_cost = sum(
                costs_for_month.get(account_id, 0.0)
                for account_id in bu_accounts.keys()
            )
            
            # Track assigned accounts
            assigned_accounts.update(bu_accounts.keys())

            # Add shared services allocation if applicable
            if ss_percentages and ss_costs and bu in ss_percentages:
                bu_cost += ss_costs[cost_month]["ss"] * ss_percentages[bu] / 100

            bu_month_costs[bu] = bu_cost

        # Add shared services as separate line item if not allocated
        if ss_percentages is None and ss_costs is not None:
            bu_month_costs["ss"] = ss_costs[cost_month]["ss"]
        
        # Include costs from unallocated accounts
        unallocated_accounts = {
            account_id: cost
            for account_id, cost in costs_for_month.items()
            if account_id not in assigned_accounts
        }
        
        if unallocated_accounts:
            unallocated_total = sum(unallocated_accounts.values())
            bu_month_costs["unallocated"] = unallocated_total
            
            # Log unallocated accounts for review
            LOGGER.warning(
                f"Unallocated accounts found for {cost_month}: "
                f"{list(unallocated_accounts.keys())} "
                f"(total: ${unallocated_total:.2f})"
            )

        # Round all values and add total
        bu_month_costs = round_cost_values(bu_month_costs)
        cost_matrix[cost_month] = add_total_to_cost_dict(bu_month_costs)

    return cost_matrix


def calculate_business_unit_costs(
    cost_explorer_client,
    start_date,
    end_date,
    account_groups,
    shared_services_allocations,
    daily_average=False,
):
    """Calculate AWS costs grouped by business unit.

    Args:
        cost_explorer_client: AWS Cost Explorer client
        start_date: Start date for cost data
        end_date: End date for cost data
        account_groups: Dictionary of business unit account groups
        shared_services_allocations: Optional shared services allocation percentages
        daily_average: If True, calculate daily average costs

    Returns:
        Tuple of (bu_cost_matrix, all_account_costs) where:
        - bu_cost_matrix: Dictionary of cost data organized by month and business unit
        - all_account_costs: Dictionary of all account costs by month
    """
    # Make single API call for all accounts (optimization: reduced from 2 calls to 1)
    all_costs_response = cost_explorer_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )

    LOGGER.debug(all_costs_response["ResultsByTime"])

    # Build all costs at once (always uses YYYY-Mon format)
    all_account_costs = _build_costs(
        all_costs_response,
        daily_average,
    )

    # Separate SS accounts from BU accounts using set for O(1) lookup
    ss_account_ids = set(account_groups["ss"].keys())

    # Split costs into shared services and business unit accounts
    ss_account_costs = {}
    bu_account_costs = {}

    for month, costs in all_account_costs.items():
        ss_account_costs[month] = {
            account_id: cost
            for account_id, cost in costs.items()
            if account_id in ss_account_ids
        }
        bu_account_costs[month] = {
            account_id: cost
            for account_id, cost in costs.items()
            if account_id not in ss_account_ids
        }

    LOGGER.debug(ss_account_costs)
    LOGGER.debug(bu_account_costs)

    ss_cost_matrix = _build_cost_matrix(account_groups, ss_account_costs)
    bu_cost_matrix = _build_cost_matrix(
        account_groups,
        bu_account_costs,
        shared_services_allocations,
        ss_cost_matrix,
    )

    LOGGER.debug(ss_cost_matrix)
    LOGGER.debug(bu_cost_matrix)

    return bu_cost_matrix, all_account_costs
