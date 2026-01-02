import calendar
import logging
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, account_list, daily_average=False):
    account_costs: dict = {}
    # Build account ID to name mapping once for O(1) lookups
    account_map = {acc["Id"]: acc["Name"] for acc in account_list}

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        cost_month_name = cost_month.strftime("%b")

        if daily_average:
            # Use the actual year from the cost data, not today's year
            day_count = calendar.monthrange(cost_month.year, cost_month.month)[1]

        for account in period["Groups"]:
            account_id = account["Keys"][0]
            if account_id in account_map:
                cost_amount = float(account["Metrics"]["UnblendedCost"]["Amount"])
                if daily_average:
                    month_costs[account_map[account_id]] = cost_amount / day_count
                else:
                    month_costs[account_map[account_id]] = cost_amount

        account_costs[cost_month_name] = month_costs

    return account_costs


def _build_cost_matrix(account_costs):
    cost_matrix: dict = {}

    for cost_month, costs_for_month in account_costs.items():
        # Round values and convert to float in one pass
        account_month_costs = {
            k: round(float(v), 2) for k, v in costs_for_month.items()
        }
        account_month_costs["total"] = round(sum(account_month_costs.values()), 2)

        cost_matrix[cost_month] = account_month_costs

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
        Dictionary of cost data organized by month and account
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

    account_costs = _build_costs(
        account_get_cost_and_usage,
        account_list,
        daily_average,
    )

    LOGGER.debug(account_costs)

    account_cost_matrix = _build_cost_matrix(account_costs)

    recent_month = (list(account_cost_matrix.items())[-1])[0]

    recent_month_costs = account_cost_matrix[recent_month]

    recent_month_costs_sorted = dict(
        sorted(recent_month_costs.items(), key=lambda item: item[1], reverse=True)
    )

    sorted_account_cost_matrix = {}

    # Get top accounts excluding 'total'
    top_sorted_accounts = [
        acc
        for acc in list(recent_month_costs_sorted.keys())[0:top_cost_count]
        if acc != "total"
    ]

    for cost_month, month_data in account_cost_matrix.items():
        month_cost = {
            service: month_data.get(service, 0) for service in top_sorted_accounts
        }
        month_cost["total"] = round(sum(month_cost.values()), 2)
        sorted_account_cost_matrix[cost_month] = month_cost

    return sorted_account_cost_matrix


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
