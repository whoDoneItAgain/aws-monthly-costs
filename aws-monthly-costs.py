import argparse
import configparser
import itertools
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import boto3
import yaml

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
        "--config-file",
        action="store",
        type=str,
        default="./account-groups.yaml",
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
        "--export-file",
        action="store",
        type=str,
        default="./aws-spend.txt",
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
    config_file = Path(config_args.config_file).absolute()
    export_file = Path(config_args.export_file).absolute()
    time_period: str = config_args.time_period

    aws_config = configparser.RawConfigParser()
    aws_config.read(aws_config_file)

    with open(config_file, "r") as cf:
        account_list: dict = yaml.safe_load(cf)

    LOGGER.debug(aws_config_file)
    LOGGER.debug(account_list)
    LOGGER.debug(aws_config.sections())

    if not (aws_config.has_section(f"profile {aws_profile}")):
        raise Exception(
            f"AWS profile does not exist in aws config file: {aws_config_file}"
        )

    if time_period == "previous":
        end_date = date.today().replace(day=1)
        start_date = (end_date - timedelta(days=1)).replace(day=1)
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
        GroupBy=[{"Type": "DIMENSION", "Key": "LINKED_ACCOUNT"}],
    )

    LOGGER.info(response["ResultsByTime"])

    account_costs: dict = {}

    for account in response["ResultsByTime"][0]["Groups"]:
        account_costs[account["Keys"][0]] = account["Metrics"]["UnblendedCost"][
            "Amount"
        ]

    LOGGER.debug(account_costs)

    bu_costs: dict = {}

    for b, a in account_list.items():  # k = bu name #v = account(s) for bu
        for i, j in itertools.product(a, account_costs.keys()):
            if i == j:
                if b in bu_costs:
                    bu_costs[b] += float(account_costs[j])
                else:
                    bu_costs[b] = float(account_costs[j])
                account_costs.pop(j)

    for k in bu_costs:
        bu_costs[k] = round(bu_costs[k], 2)

    LOGGER.debug(bu_costs)

    with open(export_file, "w") as ef:
        for k in bu_costs:
            ef.write(str(bu_costs[k]))
            ef.write("\n")


if __name__ == "__main__":
    main()
