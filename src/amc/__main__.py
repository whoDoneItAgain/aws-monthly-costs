import argparse
import configparser
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import boto3
import yaml

from amc.reportexport import exportreport, export_analysis_excel
from amc.runmodes.account import accountcosts, accountnames
from amc.runmodes.bu import bucosts
from amc.runmodes.service import servicecosts, servicecostsagg

LOGGER = logging.getLogger("amc")

DEFAULT_OUTPUT_FOLDER = "./outputs/"
DEFAULT_OUTPUT_PREFIX = "aws-monthly-costs"
DEFAULT_CONFIG_LOCATION = Path(__file__).parent.joinpath(
    "data/config/aws-monthly-costs-config.yaml"
)

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
        default=DEFAULT_CONFIG_LOCATION,
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
        "--include-ss",
        action="store_true",
        help="Include Shared Services Percentages in Costs",
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
    parser.add_argument(
        "--output-format",
        action="store",
        type=str,
        default=None,
        choices=["csv", "excel", "both"],
        help="Output format for individual reports. Choose 'csv', 'excel', or 'both'. If not specified, only the analysis Excel file is generated (when account, bu, and service modes are run).",
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
    run_modes = config_args.run_modes
    include_ss: bool = config_args.include_ss
    output_format: str = config_args.output_format

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

    ss_allocation_percentages: dict | None = (
        config_settings["ss-allocations"] if include_ss else None
    )

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
        time_parts = time_period.split("_")
        start_date = datetime.strptime(time_parts[0], "%Y-%m-%d").date()
        end_date = datetime.strptime(time_parts[1], "%Y-%m-%d").date()

    LOGGER.debug(start_date)
    LOGGER.debug(end_date)

    aws_session = boto3.Session(profile_name=aws_profile)

    sts_client = aws_session.client("sts")

    try:
        sts_client.get_caller_identity()
    except Exception as e:
        LOGGER.error(f"AWS profile ({aws_profile}) session is not valid: {e}")
        print(
            f"AWS profile ({aws_profile}) session is not valid. Reauthenticate first."
        )
        sys.exit(1)

    ce_client = aws_session.client("ce")
    # Only create organizations client if needed
    o_client = None
    if any(mode in ["account", "account-daily"] for mode in run_modes):
        o_client = aws_session.client("organizations")

    # Pre-create output directory once
    output_dir = Path(DEFAULT_OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine which formats to generate for individual reports
    # If output_format is None, don't generate individual reports (only analysis Excel)
    if output_format is None:
        formats_to_generate = []
    elif output_format == "both":
        formats_to_generate = ["csv", "excel"]
    else:
        formats_to_generate = [output_format]

    # Store data for analysis Excel file
    analysis_data = {"bu": None, "service": None, "account": None}

    for run_mode in run_modes:
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
                # Store for analysis file
                analysis_data["account"] = (cost_matrix, account_names)

                for fmt in formats_to_generate:
                    file_extension = ".xlsx" if fmt == "excel" else ".csv"
                    export_file = (
                        output_dir
                        / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"
                    )
                    exportreport(
                        export_file,
                        cost_matrix,
                        account_names,
                        group_by_type="account",
                        output_format=fmt,
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

                for fmt in formats_to_generate:
                    file_extension = ".xlsx" if fmt == "excel" else ".csv"
                    export_file = (
                        output_dir
                        / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"
                    )
                    exportreport(
                        export_file,
                        cost_matrix,
                        account_names,
                        group_by_type="account",
                        output_format=fmt,
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
                # Store for analysis file
                analysis_data["bu"] = (cost_matrix, account_list)

                for fmt in formats_to_generate:
                    file_extension = ".xlsx" if fmt == "excel" else ".csv"
                    export_file = (
                        output_dir
                        / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"
                    )
                    exportreport(
                        export_file,
                        cost_matrix,
                        account_list,
                        group_by_type="bu",
                        output_format=fmt,
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
                for fmt in formats_to_generate:
                    file_extension = ".xlsx" if fmt == "excel" else ".csv"
                    export_file = (
                        output_dir
                        / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"
                    )
                    exportreport(
                        export_file,
                        cost_matrix,
                        account_list,
                        group_by_type="bu",
                        output_format=fmt,
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
                # Store for analysis file
                analysis_data["service"] = (cost_matrix, service_list_agg)

                for fmt in formats_to_generate:
                    file_extension = ".xlsx" if fmt == "excel" else ".csv"
                    export_file = (
                        output_dir
                        / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"
                    )
                    exportreport(
                        export_file,
                        cost_matrix,
                        service_list_agg,
                        group_by_type="service",
                        output_format=fmt,
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

                for fmt in formats_to_generate:
                    file_extension = ".xlsx" if fmt == "excel" else ".csv"
                    export_file = (
                        output_dir
                        / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"
                    )
                    exportreport(
                        export_file,
                        cost_matrix,
                        service_list_agg,
                        group_by_type="service",
                        output_format=fmt,
                    )

    # Generate analysis Excel file if we have all three data types
    if all(analysis_data.values()):
        LOGGER.info("Generating analysis Excel file with charts")

        analysis_file = output_dir / f"{DEFAULT_OUTPUT_PREFIX}-analysis.xlsx"

        bu_matrix, bu_list = analysis_data["bu"]
        service_matrix, service_list = analysis_data["service"]
        account_matrix, account_list = analysis_data["account"]

        export_analysis_excel(
            analysis_file,
            bu_matrix,
            bu_list,
            service_matrix,
            service_list,
            account_matrix,
            account_list,
        )
        LOGGER.info(f"Analysis file created: {analysis_file}")


if __name__ == "__main__":
    main()
