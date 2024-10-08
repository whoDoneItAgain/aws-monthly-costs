import argparse
import configparser
import csv
import logging
import os
import sys
from datetime import date
from pathlib import Path

import boto3
import yaml

from amc.runmodes.account import accountcosts, accountnames
from amc.runmodes.bu import bucosts
from amc.runmodes.service import servicecosts, servicecostsagg

LOGGER = logging.getLogger("amc")

DEFAULT_OUTPUT_FOLDER = "./outputs/"
DEFAULT_OUTPUT_PREFIX = "aws-monthly-costs"

VALID_RUN_MODES = [
    "account",
    "account-daily",
    "bu",
    "bu-daily",
    "service",
    "service-daily",
]


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
        default="./src/amc/data/config/aws-monthy-costs-config.yaml",
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


def export_report(export_file, cost_matrix, group_list, group_by_type):
    (export_file.parent).mkdir(parents=True, exist_ok=True)

    with open(export_file, "w", newline="") as ef:
        writer = csv.writer(ef)
        csv_header = list(cost_matrix.keys())
        csv_header.insert(0, "Month")

        writer.writerow(csv_header)

        months = list(cost_matrix.keys())

        if group_by_type == "account":
            for account in group_list:
                csv_row: list = []
                csv_row.append(account)
                for month in months:
                    csv_row.append(cost_matrix[month][account])
                writer.writerow(csv_row)
        elif group_by_type == "bu":
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
    if any(x in ["account", "account-daily"] for x in run_modes):
        o_client = aws_session.client("organizations")

    for run_mode in run_modes:
        export_file = Path(
            f"{DEFAULT_OUTPUT_FOLDER}{DEFAULT_OUTPUT_PREFIX}-{run_mode}.csv"
        ).absolute()
        match run_mode:
            # by Account
            case "account":
                cost_matrix = accountcosts(
                    ce_client,
                    o_client,
                    start_date,
                    end_date,
                    top_costs_counts["account"] + 1,
                )

                account_names = accountnames(cost_matrix)

                export_report(
                    export_file, cost_matrix, account_names, group_by_type="account"
                )
            case "account-daily":
                cost_matrix = accountcosts(
                    ce_client,
                    o_client,
                    start_date,
                    end_date,
                    top_costs_counts["account"] + 1,
                    daily_average=True,
                )

                account_names = accountnames(cost_matrix)

                export_report(
                    export_file,
                    cost_matrix,
                    account_names,
                    group_by_type="account",
                )
            # by Bu
            case "bu":
                cost_matrix = bucosts(
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
                cost_matrix = bucosts(
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
            # by Service
            case "service":
                cost_matrix = servicecosts(
                    ce_client,
                    start_date,
                    end_date,
                    service_aggregation,
                    top_cost_count=top_costs_counts["service"] + 1,
                )

                service_list_agg = servicecostsagg(cost_matrix, service_aggregation)

                export_report(
                    export_file, cost_matrix, service_list_agg, group_by_type="service"
                )
            case "service-daily":
                cost_matrix = servicecosts(
                    ce_client,
                    start_date,
                    end_date,
                    service_aggregation,
                    top_cost_count=top_costs_counts["service"] + 1,
                    daily_average=True,
                )

                service_list_agg = servicecostsagg(cost_matrix, service_aggregation)

                export_report(
                    export_file, cost_matrix, service_list_agg, group_by_type="service"
                )


if __name__ == "__main__":
    main()
