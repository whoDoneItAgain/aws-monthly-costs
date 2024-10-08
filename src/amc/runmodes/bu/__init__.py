import calendar
import itertools
import logging
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, daily_average=False):
    account_costs: dict = {}

    if daily_average:
        this_year = (date.today()).year

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        cost_month_name = cost_month.strftime("%b")

        if daily_average:
            day_count = calendar.monthrange(this_year, cost_month.month)[1]

        for account in period["Groups"]:
            if daily_average:
                month_costs[account["Keys"][0]] = (
                    float(account["Metrics"]["UnblendedCost"]["Amount"]) / day_count
                )
            else:
                month_costs[account["Keys"][0]] = account["Metrics"]["UnblendedCost"][
                    "Amount"
                ]
        account_costs[cost_month_name] = month_costs

    return account_costs


def _build_cost_matrix(account_list, account_costs, ss_percentages=None, ss_costs=None):
    cost_matrix: dict = {}

    for cost_month, costs_for_month in account_costs.items():
        bu_month_costs: dict = {}
        for bu, bu_accounts in account_list.items():
            for i, j in itertools.product(bu_accounts, costs_for_month.keys()):
                if i == j:
                    if bu in bu_month_costs:
                        bu_month_costs[bu] += float(costs_for_month[j])
                    else:
                        bu_month_costs[bu] = float(costs_for_month[j])

            if ss_percentages is None or ss_costs is None:
                pass
            else:
                if bu in ss_percentages:
                    bu_month_costs[bu] += float(
                        ss_costs[cost_month]["ss"] * ss_percentages[bu] / 100
                    )
        for k in bu_month_costs:
            bu_month_costs[k] = round(bu_month_costs[k], 2)
        if ss_percentages is None or ss_costs is None:
            pass
        else:
            bu_month_costs["total"] = sum(bu_month_costs.values())

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
                "Values": account_list["ss"],
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
                    "Values": account_list["ss"],
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
