"""Account cost calculation module.

This module contains the business logic for calculating AWS costs grouped by account.
"""

import logging

from amc.runmodes.common import (
    add_total_to_cost_dict,
    build_top_n_matrix,
    calculate_daily_average,
    calculate_days_in_month,
    extract_cost_amount,
    get_most_recent_month,
    parse_cost_month,
    round_cost_values,
    sort_by_cost_descending,
)

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, account_list, daily_average=False):
    """Build cost dictionary from AWS Cost Explorer response.

    Args:
        cost_and_usage: Response from AWS Cost Explorer API
        account_list: List of AWS account information
        daily_average: If True, calculate daily average costs

    Returns:
        Dictionary of costs organized by month and account name
    """
    account_costs: dict = {}
    # Build account ID to name mapping once for O(1) lookups
    account_map = {acc["Id"]: acc["Name"] for acc in account_list}

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month, cost_month_name = parse_cost_month(period["TimePeriod"]["Start"])

        if daily_average:
            days_in_month = calculate_days_in_month(cost_month.year, cost_month.month)

        for account in period["Groups"]:
            account_id = account["Keys"][0]
            if account_id in account_map:
                cost_amount = extract_cost_amount(account)
                if daily_average:
                    month_costs[account_map[account_id]] = calculate_daily_average(
                        cost_amount, days_in_month
                    )
                else:
                    month_costs[account_map[account_id]] = cost_amount

        account_costs[cost_month_name] = month_costs

    return account_costs


def _build_cost_matrix(account_costs):
    """Build final cost matrix with rounded values and totals.

    Args:
        account_costs: Dictionary of costs organized by month and account

    Returns:
        Dictionary of costs with rounded values and monthly totals
    """
    cost_matrix: dict = {}

    for cost_month, costs_for_month in account_costs.items():
        account_month_costs = round_cost_values(costs_for_month)
        cost_matrix[cost_month] = add_total_to_cost_dict(account_month_costs)

    return cost_matrix


def calculate_account_costs(
    cost_explorer_client,
    organizations_client,
    start_date,
    end_date,
    top_cost_count,
    daily_average=False,
):
    """Calculate AWS costs grouped by account.

    Args:
        cost_explorer_client: AWS Cost Explorer client
        organizations_client: AWS Organizations client
        start_date: Start date for cost data
        end_date: End date for cost data
        top_cost_count: Number of top accounts to include
        daily_average: If True, calculate daily average costs

    Returns:
        Tuple of (cost_matrix, account_list) where:
        - cost_matrix: Dictionary of cost data organized by month and account
        - account_list: List of account information from Organizations API
    """
    account_list: list = []
    list_accounts_response = organizations_client.list_accounts()
    account_list.extend(list_accounts_response["Accounts"])

    while "NextToken" in list_accounts_response:
        list_accounts_response = organizations_client.list_accounts(
            NextToken=list_accounts_response["NextToken"]
        )
        account_list.extend(list_accounts_response["Accounts"])

    account_get_cost_and_usage = cost_explorer_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )

    LOGGER.debug(account_get_cost_and_usage["ResultsByTime"])

    # Build costs (always uses YYYY-Mon format)
    account_costs = _build_costs(
        account_get_cost_and_usage,
        account_list,
        daily_average,
    )

    LOGGER.debug(account_costs)

    account_cost_matrix = _build_cost_matrix(account_costs)

    # Get the most recent month and sort accounts by cost
    recent_month = get_most_recent_month(account_cost_matrix)
    recent_month_costs = account_cost_matrix[recent_month]

    # Sort and get top accounts
    sorted_items = sort_by_cost_descending(recent_month_costs, exclude_keys=["total"])
    top_sorted_accounts = [acc for acc, _ in sorted_items[:top_cost_count]]

    # Build matrix with only top accounts
    top_matrix = build_top_n_matrix(account_cost_matrix, top_sorted_accounts)

    return top_matrix, account_list


def get_account_names(cost_matrix):
    """Extract unique account names from cost matrix.

    Args:
        cost_matrix: Dictionary of cost data organized by month

    Returns:
        List of account names
    """
    # Collect all unique account names across all months using set
    account_names_set = set()
    for month_data in cost_matrix.values():
        account_names_set.update(month_data.keys())

    # Convert to list, keeping most recent month's accounts first
    months = list(cost_matrix.keys())
    recent_accounts = list(cost_matrix[months[-1]].keys())

    # Add remaining accounts not in recent month
    for account in account_names_set:
        if account not in recent_accounts:
            recent_accounts.append(account)

    return recent_accounts
