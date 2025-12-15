import calendar
import logging
from datetime import date, datetime

LOGGER = logging.getLogger(__name__)


def _build_costs(cost_and_usage, daily_average=False):
    service_costs: dict = {}
    service_set = set()  # Use set to avoid duplicates from the start

    if daily_average:
        this_year = date.today().year

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        cost_month_name = cost_month.strftime("%b")

        if daily_average:
            day_count = calendar.monthrange(this_year, cost_month.month)[1]

        for service in period["Groups"]:
            service_name = service["Keys"][0]
            cost_amount = float(service["Metrics"]["UnblendedCost"]["Amount"])

            month_costs[service_name] = (
                cost_amount / day_count if daily_average else cost_amount
            )
            service_set.add(service_name)

        service_costs[cost_month_name] = month_costs

    return service_costs, list(service_set)


def _build_cost_matrix(service_list, service_costs, service_aggregation):
    cost_matrix: dict = {}

    # Build reverse mapping for faster lookups: service -> aggregation name
    service_to_agg = {}
    for agg_name, agg_services in service_aggregation.items():
        for service in agg_services:
            service_to_agg[service] = agg_name

    for cost_month, costs_for_month in service_costs.items():
        service_month_costs: dict = {}

        for service in service_list:
            cost = costs_for_month.get(service, 0.0)

            # Check if service belongs to an aggregation
            if service in service_to_agg:
                agg_name = service_to_agg[service]
                service_month_costs[agg_name] = (
                    service_month_costs.get(agg_name, 0.0) + cost
                )
            else:
                service_month_costs[service] = cost

        # Round all values
        service_month_costs = {k: round(v, 2) for k, v in service_month_costs.items()}
        service_month_costs["total"] = round(sum(service_month_costs.values()), 2)

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

    # Get top services excluding 'total'
    top_sorted_services = [
        svc
        for svc in list(recent_month_costs_sorted.keys())[0:top_cost_count]
        if svc != "total"
    ]

    for cost_month, month_data in service_cost_matrix.items():
        month_cost = {
            service: month_data.get(service, 0) for service in top_sorted_services
        }
        month_cost["total"] = round(sum(month_cost.values()), 2)
        sorted_service_cost_matrix[cost_month] = month_cost

    return sorted_service_cost_matrix


def servicecostsagg(cost_matrix, service_aggregation):
    # Collect all unique services across all months using set
    service_set = set()
    for month_data in cost_matrix.values():
        service_set.update(month_data.keys())

    # Convert to list, keeping most recent month's services first
    months = list(cost_matrix.keys())
    recent_services = list(cost_matrix[months[-1]].keys())

    # Add remaining services not in recent month
    for service in service_set:
        if service not in recent_services:
            recent_services.append(service)

    return recent_services
