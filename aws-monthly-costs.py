import argparse
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

VALID_RUN_MODES = ["bu"]


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


def build_account_month_costs(cost_and_usage):
    account_costs: dict = {}

    for period in cost_and_usage["ResultsByTime"]:
        month_costs: dict = {}
        cost_month = (
            datetime.strptime(period["TimePeriod"]["Start"], "%Y-%m-%d")
        ).strftime("%b")
        for account in period["Groups"]:
            month_costs[account["Keys"][0]] = account["Metrics"]["UnblendedCost"][
                "Amount"
            ]
        account_costs[cost_month] = month_costs

    return account_costs


def build_cost_matrix(account_list, account_costs, ss_percentages=None, ss_costs=None):
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


def monthly_costs_by_bu(
    ce_client, start_date, end_date, account_list, ss_allocation_percentages
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

    ss_month_costs = build_account_month_costs(ss_get_cost_and_usage)
    account_month_costs = build_account_month_costs(account_get_cost_and_usage)

    LOGGER.debug(ss_month_costs)
    LOGGER.debug(account_month_costs)

    ss_cost_matrix = build_cost_matrix(account_list, ss_month_costs)
    bu_cost_matrix = build_cost_matrix(
        account_list, account_month_costs, ss_allocation_percentages, ss_cost_matrix
    )

    LOGGER.debug(ss_cost_matrix)
    LOGGER.debug(bu_cost_matrix)

    return bu_cost_matrix


def export_report(export_file, bu_cost_matrix, account_list):
    (export_file.parent).mkdir(parents=True, exist_ok=True)

    with open(export_file, "w", newline="") as ef:
        writer = csv.writer(ef)
        csv_header = list(bu_cost_matrix.keys())
        csv_header.insert(0, "Month")

        writer.writerow(csv_header)

        months = list(bu_cost_matrix.keys())
        bus = list(account_list.keys())
        bus.remove("ss")
        bus.extend(["total"])
        for bu in bus:
            csv_row: list = []
            csv_row.append(bu)
            for month in months:
                csv_row.append(bu_cost_matrix[month][bu])

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
        match run_mode:
            case "bu":
                export_file = Path(
                    f"{DEFAULT_OUTPUT_FOLDER}{DEFAULT_OUTPUT_PREFIX}-{run_mode}.csv"
                ).absolute()
                bu_cost_matrix = monthly_costs_by_bu(
                    ce_client,
                    start_date,
                    end_date,
                    account_list,
                    ss_allocation_percentages,
                )
            case _:
                raise Exception(f"Run Mode ({run_mode}) Not Recognized")

        export_report(export_file, bu_cost_matrix, account_list)


if __name__ == "__main__":
    main()
