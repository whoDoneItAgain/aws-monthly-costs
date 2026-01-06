import calendar
import logging
from datetime import datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, daily_average=False, include_year=False):
    account_costs: dict = {}

    for period in cost_and_usage["ResultsByTime"]:
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        # Include year in key for multi-year analysis
        if include_year:
            cost_month_name = cost_month.strftime("%Y-%b")
        else:
            cost_month_name = cost_month.strftime("%b")

        if daily_average:
            # Use the actual year from the cost data, not today's year
            day_count = calendar.monthrange(cost_month.year, cost_month.month)[1]
            month_costs = {
                account["Keys"][0]: float(account["Metrics"]["UnblendedCost"]["Amount"])
                / day_count
                for account in period["Groups"]
            }
        else:
            month_costs = {
                account["Keys"][0]: float(account["Metrics"]["UnblendedCost"]["Amount"])
                for account in period["Groups"]
            }

        account_costs[cost_month_name] = month_costs

    return account_costs


def _build_cost_matrix(account_list, account_costs, ss_percentages=None, ss_costs=None):
    cost_matrix: dict = {}

    for cost_month, costs_for_month in account_costs.items():
        bu_month_costs: dict = {}

        # Aggregate costs by BU
        for bu, bu_accounts in account_list.items():
            # Sum costs for all accounts in this BU
            bu_cost = sum(
                costs_for_month.get(account_id, 0.0)
                for account_id in bu_accounts.keys()
            )

            # Add shared services allocation if applicable
            if ss_percentages and ss_costs and bu in ss_percentages:
                bu_cost += ss_costs[cost_month]["ss"] * ss_percentages[bu] / 100

            bu_month_costs[bu] = bu_cost

        # Add shared services as separate line item if not allocated
        if ss_percentages is None and ss_costs is not None:
            bu_month_costs["ss"] = ss_costs[cost_month]["ss"]

        # Round all values
        bu_month_costs = {k: round(v, 2) for k, v in bu_month_costs.items()}
        bu_month_costs["total"] = round(sum(bu_month_costs.values()), 2)

        cost_matrix[cost_month] = bu_month_costs

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
        Dictionary of cost data organized by month and business unit
    """
    # Determine if we need to include year in month keys (for multi-year queries)
    months_span = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    include_year = months_span > 12
    
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

    # Build all costs at once
    all_account_costs = _build_costs(
        all_costs_response,
        daily_average,
        include_year=include_year,
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

    return bu_cost_matrix
