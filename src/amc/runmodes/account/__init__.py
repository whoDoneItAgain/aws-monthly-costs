import calendar
import logging
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, account_list, daily_average=False):
    account_costs: dict = {}
    account_name_list: list = []

    if daily_average:
        this_year = (date.today()).year

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        cost_month_name = cost_month.strftime("%b")

        if daily_average:
            day_count = calendar.monthrange(this_year, cost_month.month)[1]

        for account in period["Groups"]:
            for org_account in account_list:
                if account["Keys"][0] == org_account["Id"]:
                    if daily_average:
                        month_costs[org_account["Name"]] = (
                            float(account["Metrics"]["UnblendedCost"]["Amount"])
                            / day_count
                        )
                    else:
                        month_costs[org_account["Name"]] = account["Metrics"][
                            "UnblendedCost"
                        ]["Amount"]
                    if account not in account_name_list:
                        account_name_list.append(org_account["Name"])

        account_costs[cost_month_name] = month_costs

    return account_costs, account_name_list


def _build_cost_matrix(account_costs, account_name_list):
    cost_matrix: dict = {}

    for cost_month, costs_for_month in account_costs.items():
        account_month_costs: dict = {}

        for account_name in account_name_list:
            if account_name in costs_for_month:
                account_month_costs[account_name] = float(costs_for_month[account_name])
        for k in account_month_costs:
            account_month_costs[k] = round(account_month_costs[k], 2)
        account_month_costs["total"] = sum(account_month_costs.values())

        cost_matrix[cost_month] = account_month_costs

    return cost_matrix


def accountcosts(
    ce_client,
    o_client,
    start_date,
    end_date,
    top_cost_count,
    daily_average=False,
):
    account_list: list = []
    list_accounts_response = o_client.list_accounts()
    account_list.extend(list_accounts_response["Accounts"])

    while "NextToken" in list_accounts_response:
        list_accounts_response = o_client.list_accounts(
            NextToken=list_accounts_response["NextToken"]
        )
        account_list.extend(list_accounts_response["Accounts"])

    account_get_cost_and_usage = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )

    LOGGER.debug(account_get_cost_and_usage["ResultsByTime"])

    account_costs, account_name_list = _build_costs(
        account_get_cost_and_usage,
        account_list,
        daily_average,
    )

    LOGGER.debug(account_costs)

    account_cost_matrix = _build_cost_matrix(account_costs, account_name_list)

    recent_month = (list(account_cost_matrix.items())[-1])[0]

    recent_month_costs = account_cost_matrix[recent_month]

    recent_month_costs_sorted = dict(
        sorted(recent_month_costs.items(), key=lambda item: item[1], reverse=True)
    )

    sorted_account_cost_matrix = {}

    sorted_accounts = list(recent_month_costs_sorted.keys())

    top_sorted_accounts = sorted_accounts[0:top_cost_count]

    for cost_month in account_cost_matrix.keys():
        top_services_month_total: float = 0
        month_cost: dict = {}
        for service in top_sorted_accounts:
            if service != "total":
                month_cost[service] = account_cost_matrix[cost_month][service]
                top_services_month_total += account_cost_matrix[cost_month][service]
        month_cost["total"] = round(top_services_month_total, 2)

        sorted_account_cost_matrix[cost_month] = month_cost

    return sorted_account_cost_matrix


def accountnames(cost_matrix):
    account_names: list = []

    months = list(cost_matrix.keys())

    current_month = months[-1]

    account_names.extend(cost_matrix[current_month])
    months.pop()

    for month in months:
        for account_name in cost_matrix[month].keys():
            if account_name not in account_names:
                account_names.append(account_name)

    return account_names
