"""Service cost calculation module.

This module contains the business logic for calculating AWS costs grouped by service.
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


def _build_costs(cost_and_usage, daily_average=False):
    """Build cost dictionary from AWS Cost Explorer response.

    Args:
        cost_and_usage: Response from AWS Cost Explorer API
        daily_average: If True, calculate daily average costs

    Returns:
        Tuple of (service_costs dict, service_list)
    """
    service_costs: dict = {}
    service_set = set()  # Use set to avoid duplicates from the start

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month, cost_month_name = parse_cost_month(period["TimePeriod"]["Start"])

        if daily_average:
            days_in_month = calculate_days_in_month(cost_month.year, cost_month.month)

        for service in period["Groups"]:
            service_name = service["Keys"][0]
            cost_amount = extract_cost_amount(service)

            month_costs[service_name] = (
                calculate_daily_average(cost_amount, days_in_month)
                if daily_average
                else cost_amount
            )
            service_set.add(service_name)

        service_costs[cost_month_name] = month_costs

    return service_costs, list(service_set)


def _build_cost_matrix(service_list, service_costs, service_aggregation, service_exclusions=None):
    """Build final cost matrix with service aggregations and exclusions applied.

    Args:
        service_list: List of all service names
        service_costs: Dictionary of costs by service
        service_aggregation: Dictionary of service aggregation rules
        service_exclusions: List of services to exclude from reports

    Returns:
        Dictionary of costs with aggregations applied
    """
    cost_matrix: dict = {}

    # Build reverse mapping for faster lookups: service -> aggregation name
    service_to_agg = {}
    for agg_name, agg_services in service_aggregation.items():
        for service in agg_services:
            service_to_agg[service] = agg_name

    # Normalize exclusions list (default to empty list if None)
    exclusions = service_exclusions if service_exclusions else []

    for cost_month, costs_for_month in service_costs.items():
        service_month_costs: dict = {}

        for service in service_list:
            # Skip excluded services
            if service in exclusions:
                continue

            cost = costs_for_month.get(service, 0.0)

            # Check if service belongs to an aggregation
            if service in service_to_agg:
                agg_name = service_to_agg[service]
                service_month_costs[agg_name] = (
                    service_month_costs.get(agg_name, 0.0) + cost
                )
            else:
                service_month_costs[service] = cost

        # Round all values and add total
        service_month_costs = round_cost_values(service_month_costs)
        cost_matrix[cost_month] = add_total_to_cost_dict(service_month_costs)

    return cost_matrix


def calculate_service_costs(
    cost_explorer_client,
    start_date,
    end_date,
    service_aggregations,
    top_cost_count,
    daily_average=False,
    service_exclusions=None,
):
    """Calculate AWS costs grouped by service.

    Args:
        cost_explorer_client: AWS Cost Explorer client
        start_date: Start date for cost data
        end_date: End date for cost data
        service_aggregations: Dictionary of service aggregation rules
        top_cost_count: Number of top services to include
        daily_average: If True, calculate daily average costs
        service_exclusions: List of services to exclude from reports

    Returns:
        Dictionary of cost data organized by month and service
    """
    get_cost_and_usage = cost_explorer_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    LOGGER.debug(get_cost_and_usage["ResultsByTime"])

    # Build costs (always uses YYYY-Mon format)
    service_costs, service_list = _build_costs(
        get_cost_and_usage,
        daily_average,
    )

    LOGGER.debug(service_costs)

    service_cost_matrix = _build_cost_matrix(
        service_list, service_costs, service_aggregations, service_exclusions
    )

    # Get the most recent month and sort services by cost
    recent_month = get_most_recent_month(service_cost_matrix)
    recent_month_costs = service_cost_matrix[recent_month]

    # Sort and get top services
    sorted_items = sort_by_cost_descending(recent_month_costs, exclude_keys=["total"])
    top_sorted_services = [svc for svc, _ in sorted_items[:top_cost_count]]

    # Build matrix with only top services
    return build_top_n_matrix(service_cost_matrix, top_sorted_services)


def get_service_list(cost_matrix, service_aggregations=None):
    """Extract unique service names from cost matrix.

    Args:
        cost_matrix: Dictionary of cost data organized by month
        service_aggregations: Dictionary of service aggregation rules (reserved for future use)

    Returns:
        List of service names
    """
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
