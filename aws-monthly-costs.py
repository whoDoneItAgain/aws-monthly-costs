import argparse
import calendar
import configparser
import csv
import itertools
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import boto3
import yaml

LOGGER = logging.getLogger("amc")

DEFAULT_OUTPUT_FOLDER = "./outputs/"
DEFAULT_OUTPUT_PREFIX = "aws-monthly-costs"

VALID_RUN_MODES = ["bu", "bu-daily", "service", "service-daily"]


def get_config_args():
    # Define the parser
    parser = argparse.ArgumentParser(description="AWS Monthly Costs")
    parser.add_argument(
        "--profile",
        action="store",
        type=str,
        default="ab-root-use1-admin",
        help="Profile Name",
    )
    parser.add_argument(
        "--config-file",
        action="store",
        type=str,
        default="./aws-monthy-costs-config.yaml",
        help="Path to Configuration File",
    )
    parser.add_argument(
        "--aws-config-file",
        action="store",
        type=str,
        default="~/.aws/config",
        help="Path to Configuration File",
    )
    parser.add_argument(
        "--run-modes",
        action="store",
        type=str,
        default=VALID_RUN_MODES,
        nargs="*",
        help="Run Modes of Script.",
    )
    parser.add_argument(
        "--time-period",
        action="store",
        type=str,
        default="previous",
        help="Time Period. Enter in either previous (default) or syntax of YYYY-MM-DD_YYYY-MM-DD",
    )
    parser.add_argument(
        "--debug-logging",
        action="store_true",
        help="Enables Debug Level Logging",
    )
    parser.add_argument(
        "--info-logging",
        action="store_true",
        help="Enables Info Level Logging. Superseded by debug-logging",
    )

    args = parser.parse_args()

    return args


def configure_logging(debug_logging: bool = False, info_logging: bool = False):
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    if debug_logging:
        LOGGER.setLevel(logging.DEBUG)
    elif info_logging:
        LOGGER.setLevel(logging.INFO)
    else:
        LOGGER.setLevel(logging.NOTSET)
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(log_formatter)

    # make sure all other log handlers are removed before adding it back
    for handler in LOGGER.handlers:
        LOGGER.removeHandler(handler)
    LOGGER.addHandler(ch)


def build_account_costs_by_bu(cost_and_usage, daily_average=False):
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


def build_costs_by_service(cost_and_usage, daily_average=False):
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


def build_cost_matrix_by_bu(
    account_list, account_costs, ss_percentages=None, ss_costs=None
):
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


def build_cost_matrix_by_service(service_list, service_costs, service_aggregation):
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


def monthly_costs_by_bu(
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

    ss_account_costs = build_account_costs_by_bu(
        ss_get_cost_and_usage,
        daily_average,
    )
    bu_account_costs = build_account_costs_by_bu(
        account_get_cost_and_usage,
        daily_average,
    )

    LOGGER.debug(ss_account_costs)
    LOGGER.debug(bu_account_costs)

    ss_cost_matrix = build_cost_matrix_by_bu(account_list, ss_account_costs)
    bu_cost_matrix = build_cost_matrix_by_bu(
        account_list,
        bu_account_costs,
        ss_allocation_percentages,
        ss_cost_matrix,
    )

    LOGGER.debug(ss_cost_matrix)
    LOGGER.debug(bu_cost_matrix)

    return bu_cost_matrix


def monthly_costs_by_service(
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

    service_costs, service_list = build_costs_by_service(
        get_cost_and_usage,
        daily_average,
    )

    LOGGER.debug(service_costs)

    service_cost_matrix = build_cost_matrix_by_service(
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


def export_report(export_file, cost_matrix, group_list, group_by_type):
    (export_file.parent).mkdir(parents=True, exist_ok=True)

    with open(export_file, "w", newline="") as ef:
        writer = csv.writer(ef)
        csv_header = list(cost_matrix.keys())
        csv_header.insert(0, "Month")

        writer.writerow(csv_header)

        months = list(cost_matrix.keys())

        if group_by_type == "bu":
            bus = list(group_list.keys())
            bus.remove("ss")
            bus.extend(["total"])
            for bu in bus:
                csv_row: list = []
                csv_row.append(bu)
                for month in months:
                    csv_row.append(cost_matrix[month][bu])
                writer.writerow(csv_row)
        elif group_by_type == "service":
            for service in group_list:
                csv_row: list = []
                csv_row.append(service)
                for month in months:
                    if service in cost_matrix[month]:
                        csv_row.append(cost_matrix[month][service])
                writer.writerow(csv_row)


def build_service_list_with_aggregation(cost_matrix, service_aggregation):
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


def main():
    assert sys.version_info >= (3, 12)

    config_args = get_config_args()

    configure_logging(
        debug_logging=config_args.debug_logging, info_logging=config_args.info_logging
    )

    LOGGER.debug(f"Configuration Arguments - {config_args}")

    aws_config_file = Path(os.path.expanduser(config_args.aws_config_file)).absolute()
    aws_profile: str = config_args.profile
    config_file = Path(config_args.config_file).absolute()
    run_modes = config_args.run_modes

    if not (set(run_modes).issubset(set(VALID_RUN_MODES))):
        raise Exception(
            f"Run Mode list ({run_modes}) is not Valid. Valid Run Modes are {VALID_RUN_MODES}"
        )

    time_period: str = config_args.time_period

    aws_config = configparser.RawConfigParser()
    aws_config.read(aws_config_file)

    with open(config_file, "r") as cf:
        config_settings: dict = yaml.safe_load(cf)

    account_list: dict = config_settings["account-groups"]
    ss_allocation_percentages: dict = config_settings["ss-allocations"]
    service_aggregation: dict = config_settings["service-aggregations"]
    top_costs_counts: dict = config_settings["top-costs-count"]

    LOGGER.debug(aws_config_file)
    LOGGER.debug(account_list)
    LOGGER.debug(ss_allocation_percentages)
    LOGGER.debug(aws_config.sections())

    if not (aws_config.has_section(f"profile {aws_profile}")):
        raise Exception(
            f"AWS profile does not exist in aws config file: {aws_config_file}"
        )

    if time_period == "previous":
        end_date = date.today().replace(day=1)
        start_date = end_date.replace(month=1)
    else:
        end_date = (time_period.split("_"))[1]
        start_date = (time_period.split("_"))[0]

    LOGGER.debug(start_date)
    LOGGER.debug(end_date)

    aws_session = boto3.Session(profile_name=aws_profile)
    ce_client = aws_session.client("ce")

    for run_mode in run_modes:
        export_file = Path(
            f"{DEFAULT_OUTPUT_FOLDER}{DEFAULT_OUTPUT_PREFIX}-{run_mode}.csv"
        ).absolute()
        match run_mode:
            case "bu":
                cost_matrix = monthly_costs_by_bu(
                    ce_client,
                    start_date,
                    end_date,
                    account_list,
                    ss_allocation_percentages,
                )
                export_report(
                    export_file, cost_matrix, account_list, group_by_type="bu"
                )
            case "bu-daily":
                cost_matrix = monthly_costs_by_bu(
                    ce_client,
                    start_date,
                    end_date,
                    account_list,
                    ss_allocation_percentages,
                    daily_average=True,
                )
                export_report(
                    export_file, cost_matrix, account_list, group_by_type="bu"
                )
            case "service":
                cost_matrix = monthly_costs_by_service(
                    ce_client,
                    start_date,
                    end_date,
                    service_aggregation,
                    top_cost_count=top_costs_counts["service"] + 1,
                )

                service_list_agg = build_service_list_with_aggregation(
                    cost_matrix, service_aggregation
                )

                export_report(
                    export_file, cost_matrix, service_list_agg, group_by_type="service"
                )

            case "service-daily":
                cost_matrix = monthly_costs_by_service(
                    ce_client,
                    start_date,
                    end_date,
                    service_aggregation,
                    top_cost_count=top_costs_counts["service"] + 1,
                    daily_average=True,
                )

                service_list_agg = build_service_list_with_aggregation(
                    cost_matrix, service_aggregation
                )

                export_report(
                    export_file, cost_matrix, service_list_agg, group_by_type="service"
                )


if __name__ == "__main__":
    main()
