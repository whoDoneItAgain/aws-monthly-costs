import argparse
import configparser
import csv
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import boto3

LOGGER = logging.getLogger("amc")


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
        "--aws-config-file",
        action="store",
        type=str,
        default="~/.aws/config",
        help="Path to Configuration File",
    )
    parser.add_argument(
        "--export-file",
        action="store",
        type=str,
        default="./outputs/aws-spend-top-services.csv",
        help="Path to Export File",
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


def main():
    assert sys.version_info >= (3, 12)

    config_args = get_config_args()

    configure_logging(
        debug_logging=config_args.debug_logging, info_logging=config_args.info_logging
    )

    LOGGER.debug(f"Configuration Arguments - {config_args}")

    aws_config_file = Path(os.path.expanduser(config_args.aws_config_file)).absolute()
    aws_profile: str = config_args.profile
    export_file = Path(config_args.export_file).absolute()
    time_period: str = config_args.time_period

    aws_config = configparser.RawConfigParser()
    aws_config.read(aws_config_file)

    LOGGER.debug(aws_config_file)

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

    response = ce_client.get_cost_and_usage(
        TimePeriod={
            "Start": start_date.strftime("%Y-%m-%d"),
            "End": end_date.strftime("%Y-%m-%d"),
        },
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )

    LOGGER.debug(response["ResultsByTime"][0]["Groups"][0])

    service_costs: dict = {}
    service_list: list = []

    for period in response["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = (
            datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        ).strftime("%b")
        for service in period["Groups"]:
            month_costs[service["Keys"][0]] = service["Metrics"]["UnblendedCost"][
                "Amount"
            ]
            if service not in service_list:
                service_list.append(service["Keys"][0])

        service_costs[cost_month] = month_costs

    LOGGER.debug(service_costs)

    cost_matrix: dict = {}

    for cost_month, costs_for_month in service_costs.items():
        service_month_costs: dict = {}
        for service in service_list:
            if service in costs_for_month:
                service_month_costs[service] = float(costs_for_month[service])
        for k in service_month_costs:
            service_month_costs[k] = round(service_month_costs[k], 2)
        service_month_costs["total"] = sum(service_month_costs.values())

        cost_matrix[cost_month] = service_month_costs

    LOGGER.debug((list(cost_matrix.items())[-1])[0])

    recent_month = (list(cost_matrix.items())[-1])[0]

    recent_month_costs = cost_matrix[recent_month]

    recent_month_costs_sorted = dict(
        sorted(recent_month_costs.items(), key=lambda item: item[1], reverse=True)
    )

    LOGGER.debug(recent_month_costs_sorted)

    top_costs: list = list(recent_month_costs_sorted.items())[1:11]

    top_cost_services: list = []
    for tc in top_costs:
        top_cost_services.append(tc[0])

    LOGGER.info(top_cost_services)

    (export_file.parent).mkdir(parents=True, exist_ok=True)

    with open(export_file, "w", newline="") as ef:
        writer = csv.writer(ef)
        csv_header = list(cost_matrix.keys())
        csv_header.insert(0, "Month")

        writer.writerow(csv_header)

        months = list(cost_matrix.keys())

        service_list.extend(["total"])
        for service in top_cost_services:
            csv_row: list = []
            csv_row.append(service)
            for month in months:
                if service in cost_matrix[month]:
                    csv_row.append(cost_matrix[month][service])

            writer.writerow(csv_row)


if __name__ == "__main__":
    main()
