import calendar
import logging
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, daily_average=False):
    account_costs: dict = {}

    if daily_average:
        this_year = date.today().year

    for period in cost_and_usage["ResultsByTime"]:
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        cost_month_name = cost_month.strftime("%b")

        if daily_average:
            day_count = calendar.monthrange(this_year, cost_month.month)[1]
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


def bucosts(
    ce_client,
    start_date,
    end_date,
    account_list,
    ss_allocation_percentages,
    daily_average=False,
):
    ss_get_cost_and_usage = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Filter={
            "Dimensions": {
                "Key": "LINKED_ACCOUNT",
                "Values": list((account_list["ss"]).keys()),
                "MatchOptions": ["EQUALS"],
            }
        },
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )

    account_get_cost_and_usage = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Filter={
            "Not": {
                "Dimensions": {
                    "Key": "LINKED_ACCOUNT",
                    "Values": list((account_list["ss"]).keys()),
                    "MatchOptions": ["EQUALS"],
                }
            }
        },
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )

    LOGGER.debug(ss_get_cost_and_usage["ResultsByTime"])
    LOGGER.debug(account_get_cost_and_usage["ResultsByTime"])

    ss_account_costs = _build_costs(
        ss_get_cost_and_usage,
        daily_average,
    )
    bu_account_costs = _build_costs(
        account_get_cost_and_usage,
        daily_average,
    )

    LOGGER.debug(ss_account_costs)
    LOGGER.debug(bu_account_costs)

    ss_cost_matrix = _build_cost_matrix(account_list, ss_account_costs)
    bu_cost_matrix = _build_cost_matrix(
        account_list,
        bu_account_costs,
        ss_allocation_percentages,
        ss_cost_matrix,
    )

    LOGGER.debug(ss_cost_matrix)
    LOGGER.debug(bu_cost_matrix)

    return bu_cost_matrix
