import calendar
import logging
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, daily_average=False):
    service_costs: dict = {}
    service_list: list = []

    if daily_average:
        this_year = (date.today()).year

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        cost_month_name = cost_month.strftime("%b")

        if daily_average:
            day_count = calendar.monthrange(this_year, cost_month.month)[1]

        for service in period["Groups"]:
            if daily_average:
                month_costs[service["Keys"][0]] = (
                    float(service["Metrics"]["UnblendedCost"]["Amount"]) / day_count
                )
            else:
                month_costs[service["Keys"][0]] = service["Metrics"]["UnblendedCost"][
                    "Amount"
                ]

            service_list.append(service["Keys"][0])

        service_costs[cost_month_name] = month_costs

    service_list = list(set(service_list))

    return service_costs, service_list


def _build_cost_matrix(service_list, service_costs, service_aggregation):
    cost_matrix: dict = {}

    for cost_month, costs_for_month in service_costs.items():
        service_month_costs: dict = {}
        for service in service_list:
            for agg_name, agg_services in service_aggregation.items():
                if service in agg_services:
                    if service in costs_for_month:
                        if agg_name in service_month_costs:
                            service_month_costs[agg_name] += float(
                                costs_for_month[service]
                            )
                        else:
                            service_month_costs[agg_name] = float(
                                costs_for_month[service]
                            )

                    else:
                        service_month_costs[agg_name] = float(0)
                    break

                elif service in costs_for_month:
                    service_month_costs[service] = float(costs_for_month[service])

                else:
                    service_month_costs[service] = float(0)

        for k in service_aggregation:
            for v in service_aggregation[k]:
                if v in service_month_costs:
                    service_month_costs.pop(v)

        for k in service_month_costs:
            service_month_costs[k] = round(service_month_costs[k], 2)

        service_month_costs["total"] = sum(service_month_costs.values())

        cost_matrix[cost_month] = service_month_costs

    return cost_matrix


def servicecosts(
    ce_client,
    start_date,
    end_date,
    service_aggregation,
    top_cost_count,
    daily_average=False,
):
    get_cost_and_usage = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    LOGGER.debug(get_cost_and_usage["ResultsByTime"])

    service_costs, service_list = _build_costs(
        get_cost_and_usage,
        daily_average,
    )

    LOGGER.debug(service_costs)

    service_cost_matrix = _build_cost_matrix(
        service_list, service_costs, service_aggregation
    )

    recent_month = (list(service_cost_matrix.items())[-1])[0]

    recent_month_costs = service_cost_matrix[recent_month]

    recent_month_costs_sorted = dict(
        sorted(recent_month_costs.items(), key=lambda item: item[1], reverse=True)
    )

    sorted_service_cost_matrix = {}

    sorted_services = list(recent_month_costs_sorted.keys())

    top_sorted_services = sorted_services[0:top_cost_count]

    for cost_month in service_cost_matrix.keys():
        top_services_month_total: float = 0
        month_cost: dict = {}
        for service in top_sorted_services:
            if service != "total":
                month_cost[service] = service_cost_matrix[cost_month][service]
                top_services_month_total += service_cost_matrix[cost_month][service]
        month_cost["total"] = round(top_services_month_total, 2)

        sorted_service_cost_matrix[cost_month] = month_cost

    return sorted_service_cost_matrix


def servicecostsagg(cost_matrix, service_aggregation):
    service_list: list = []
    agg_service_list: list = []

    for agg_name in service_aggregation:
        agg_service_list.extend(service_aggregation[agg_name])

    months = list(cost_matrix.keys())

    current_month = months[-1]

    service_list.extend(cost_matrix[current_month])
    months.pop()

    for month in months:
        for service in cost_matrix[month].keys():
            if service not in service_list:
                service_list.append(service)

    return service_list
