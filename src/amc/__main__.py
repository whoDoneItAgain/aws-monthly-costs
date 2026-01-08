import argparse
import configparser
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

import boto3
import yaml

from amc.constants import (
    DEFAULT_RUN_MODES,
    MIN_MONTHS_FOR_YEAR_ANALYSIS,
    OUTPUT_FORMAT_BOTH,
    OUTPUT_FORMAT_CSV,
    OUTPUT_FORMAT_EXCEL,
    RUN_MODE_ACCOUNT,
    RUN_MODE_ACCOUNT_DAILY,
    RUN_MODE_BUSINESS_UNIT,
    RUN_MODE_BUSINESS_UNIT_DAILY,
    RUN_MODE_SERVICE,
    RUN_MODE_SERVICE_DAILY,
    TIME_PERIOD_MONTH,
    TIME_PERIOD_YEAR,
    VALID_OUTPUT_FORMATS,
    VALID_RUN_MODES,
)
from amc.reportexport import (
    export_analysis_excel,
    export_report,
    export_year_analysis_excel,
)
from amc.runmodes.account import calculate_account_costs, get_account_names
from amc.runmodes.bu import calculate_business_unit_costs
from amc.runmodes.service import calculate_service_costs, get_service_list

LOGGER = logging.getLogger("amc")

DEFAULT_OUTPUT_FOLDER = "./outputs/"
DEFAULT_OUTPUT_PREFIX = "aws-monthly-costs"
DEFAULT_AWS_CONFIG_FILE = "~/.aws/config"
DEFAULT_CONFIG_LOCATION = Path(__file__).parent.joinpath(
    "data/config/aws-monthly-costs-config.yaml"
)


def parse_arguments():
    """Parse command-line arguments for the AWS Monthly Costs tool.

    Returns:
        argparse.Namespace: Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate AWS monthly cost reports by account, business unit, or service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--profile",
        type=str,
        required=True,
        help="AWS profile name to use for authentication (from ~/.aws/config)",
    )

    parser.add_argument(
        "--config-file",
        type=str,
        default=DEFAULT_CONFIG_LOCATION,
        help=f"Path to the configuration YAML file (default: {DEFAULT_CONFIG_LOCATION})",
    )

    parser.add_argument(
        "--aws-config-file",
        type=str,
        default=DEFAULT_AWS_CONFIG_FILE,
        help=f"Path to AWS credentials config file (default: {DEFAULT_AWS_CONFIG_FILE})",
    )

    parser.add_argument(
        "--include-shared-services",
        action="store_true",
        help="Allocate shared services costs across business units based on configured percentages",
    )

    parser.add_argument(
        "--run-modes",
        type=str,
        nargs="*",
        default=DEFAULT_RUN_MODES,
        choices=VALID_RUN_MODES,
        help=f"Report types to generate. Default: {', '.join(DEFAULT_RUN_MODES)} (required for analysis file)",
    )

    parser.add_argument(
        "--time-period",
        type=str,
        default=TIME_PERIOD_MONTH,
        help=f"Time period for cost analysis. Use '{TIME_PERIOD_MONTH}' for last 2 months, '{TIME_PERIOD_YEAR}' for year-level analysis (requires 24+ months), or 'YYYY-MM-DD_YYYY-MM-DD' for custom range (default: {TIME_PERIOD_MONTH})",
    )

    parser.add_argument(
        "--debug-logging",
        action="store_true",
        help="Enable debug-level logging for detailed diagnostic information",
    )

    parser.add_argument(
        "--info-logging",
        action="store_true",
        help="Enable info-level logging (overridden by --debug-logging if both are specified)",
    )

    parser.add_argument(
        "--output-format",
        type=str,
        default=None,
        choices=VALID_OUTPUT_FORMATS,
        help="Format for individual report files: 'csv', 'excel', or 'both'. If not specified, only generates the analysis Excel file",
    )

    return parser.parse_args()


def configure_logging(debug_logging: bool = False, info_logging: bool = False):
    """Configure logging for the application.

    Args:
        debug_logging: If True, enables DEBUG level logging
        info_logging: If True, enables INFO level logging (superseded by debug_logging)
    """
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    if debug_logging:
        LOGGER.setLevel(logging.DEBUG)
    elif info_logging:
        LOGGER.setLevel(logging.INFO)
    else:
        LOGGER.setLevel(logging.NOTSET)

    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(log_formatter)

    # Remove existing handlers before adding new one
    for handler in LOGGER.handlers:
        LOGGER.removeHandler(handler)
    LOGGER.addHandler(console_handler)


def load_configuration(config_file_path: Path) -> dict:
    """Load configuration from YAML file.

    Args:
        config_file_path: Path to the configuration YAML file

    Returns:
        Dictionary containing configuration settings

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file is missing required keys or is invalid
    """
    try:
        with open(config_file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration file: {e}")

    if config is None:
        raise ValueError(f"Configuration file is empty: {config_file_path}")

    # Validate required keys
    required_keys = ["account-groups", "service-aggregations", "top-costs-count"]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(
            f"Configuration file missing required keys: {', '.join(missing_keys)}"
        )

    # Validate account-groups has 'ss' key
    if "ss" not in config["account-groups"]:
        raise ValueError(
            "Configuration file 'account-groups' must contain 'ss' (shared services) key"
        )

    # Validate top-costs-count has required subkeys
    if not isinstance(config["top-costs-count"], dict):
        raise ValueError("Configuration 'top-costs-count' must be a dictionary")

    required_top_costs_keys = ["account", "service"]
    missing_top_costs_keys = [
        key for key in required_top_costs_keys if key not in config["top-costs-count"]
    ]
    if missing_top_costs_keys:
        raise ValueError(
            f"Configuration 'top-costs-count' missing required keys: {', '.join(missing_top_costs_keys)}"
        )

    return config


def parse_time_period(time_period_str: str) -> tuple[date, date]:
    """Parse time period string into start and end dates.

    Args:
        time_period_str: Either 'month' for last 2 months, 'year' for year analysis,
                        or 'YYYY-MM-DD_YYYY-MM-DD' format

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        ValueError: If time_period_str is not in valid format
    """
    if time_period_str == TIME_PERIOD_MONTH:
        # Get the first day of current month, which is the end_date for the query
        end_date = date.today().replace(day=1)
        # Go back 2 months for start date to get 2 full months of data
        start_month = end_date.month - 2
        if start_month <= 0:
            # Need to go back to previous year
            start_date = end_date.replace(
                year=end_date.year - 1, month=start_month + 12
            )
        else:
            start_date = end_date.replace(month=start_month)
    elif time_period_str == TIME_PERIOD_YEAR:
        # For year mode, calculate 24 months back from first day of current month
        end_date = date.today().replace(day=1)
        # Go back 24 months for start date
        start_month = end_date.month - 24
        if start_month <= 0:
            # Need to go back years
            years_back = (-start_month // 12) + 1
            new_month = start_month + (years_back * 12)
            start_date = end_date.replace(
                year=end_date.year - years_back, month=new_month
            )
        else:
            start_date = end_date.replace(month=start_month)
    else:
        try:
            time_parts = time_period_str.split("_")
            if len(time_parts) != 2:
                raise ValueError(
                    f"Time period must be in format 'YYYY-MM-DD_YYYY-MM-DD', got: {time_period_str}"
                )
            start_date = datetime.strptime(time_parts[0], "%Y-%m-%d").date()
            end_date = datetime.strptime(time_parts[1], "%Y-%m-%d").date()
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time period format '{time_period_str}': {e}")

    return start_date, end_date


def validate_year_data(cost_matrix: dict) -> tuple[list[str], list[str]]:
    """Validate that cost data is sufficient for year-level analysis.

    Performs the following validation:
    1. Checks for at least 24 months of data
    2. Verifies months are consecutive (no gaps)
    3. Identifies the two most recent complete 12-month periods

    Args:
        cost_matrix: Dictionary of monthly cost data with month names as keys (e.g., '2023-Jan', '2023-Feb')

    Returns:
        Tuple of (year1_months, year2_months) - Lists of month names for each year period

    Raises:
        ValueError: If data is insufficient, has gaps, or doesn't meet requirements
    """
    if not cost_matrix:
        raise ValueError(
            "No cost data available. Please provide cost data for year analysis."
        )

    # Get list of months from data (in order)
    available_months = list(cost_matrix.keys())

    # Check minimum data requirement
    if len(available_months) < MIN_MONTHS_FOR_YEAR_ANALYSIS:
        raise ValueError(
            f"Insufficient data for year analysis. "
            f"Provide at least {MIN_MONTHS_FOR_YEAR_ANALYSIS} consecutive, non-overlapping months "
            f"for two-year comparison. Currently have {len(available_months)} months."
        )

    # Take the last 24 months as our data set for year analysis
    last_24_months = available_months[-MIN_MONTHS_FOR_YEAR_ANALYSIS:]

    # Split into two 12-month periods (most recent complete years)
    year1_months = last_24_months[:12]  # First 12 months
    year2_months = last_24_months[12:]  # Last 12 months (most recent)

    LOGGER.debug(f"Year 1 months: {year1_months}")
    LOGGER.debug(f"Year 2 months: {year2_months}")

    return year1_months, year2_months


def create_aws_session(aws_profile: str, aws_config_file_path: Path) -> boto3.Session:
    """Create and validate AWS session.

    Args:
        aws_profile: AWS profile name to use
        aws_config_file_path: Path to AWS config file

    Returns:
        Validated boto3 Session object

    Raises:
        SystemExit: If profile doesn't exist or session is invalid
    """
    # Validate AWS config file has the profile
    aws_config = configparser.RawConfigParser()
    aws_config.read(aws_config_file_path)

    if not aws_config.has_section(f"profile {aws_profile}"):
        raise ValueError(
            f"AWS profile '{aws_profile}' does not exist in config file: {aws_config_file_path}"
        )

    # Create session and validate credentials
    session = boto3.Session(profile_name=aws_profile)
    sts_client = session.client("sts")

    try:
        sts_client.get_caller_identity()
    except Exception as e:
        LOGGER.error(f"AWS profile ({aws_profile}) session is not valid: {e}")
        print(
            f"AWS profile ({aws_profile}) session is not valid. Please reauthenticate first."
        )
        sys.exit(1)

    LOGGER.debug(f"Successfully authenticated with AWS profile: {aws_profile}")
    return session


def determine_output_formats(output_format: str | None) -> list[str]:
    """Determine which output formats to generate.

    Args:
        output_format: User-specified output format (csv, excel, both, or None)

    Returns:
        List of formats to generate (empty list if None)
    """
    if output_format is None:
        return []
    elif output_format == OUTPUT_FORMAT_BOTH:
        return [OUTPUT_FORMAT_CSV, OUTPUT_FORMAT_EXCEL]
    else:
        return [output_format]


def generate_output_file_path(
    output_dir: Path, run_mode: str, file_format: str
) -> Path:
    """Generate output file path for a given run mode and format.

    Args:
        output_dir: Directory to save the file
        run_mode: Run mode name (e.g., 'account', 'bu', 'service')
        file_format: File format ('csv' or 'excel')

    Returns:
        Path object for the output file
    """
    file_extension = ".xlsx" if file_format == OUTPUT_FORMAT_EXCEL else ".csv"
    return output_dir / f"{DEFAULT_OUTPUT_PREFIX}-{run_mode}{file_extension}"


def _process_account_mode(
    run_mode: str,
    cost_explorer_client,
    organizations_client,
    start_date: date,
    end_date: date,
    top_cost_count: int,
    output_dir: Path,
    output_formats: list[str],
    analysis_data: dict,
):
    """Process account-based cost reporting.

    Args:
        run_mode: The run mode (account or account-daily)
        cost_explorer_client: AWS Cost Explorer client
        organizations_client: AWS Organizations client
        start_date: Start date for cost data
        end_date: End date for cost data
        top_cost_count: Number of top accounts to include
        output_dir: Directory for output files
        output_formats: List of formats to generate
        analysis_data: Dictionary to store data for analysis file
    """
    is_daily = run_mode == RUN_MODE_ACCOUNT_DAILY

    cost_matrix, account_list = calculate_account_costs(
        cost_explorer_client,
        organizations_client,
        start_date,
        end_date,
        top_cost_count,
        daily_average=is_daily,
    )

    account_names = get_account_names(cost_matrix)

    # Store for analysis file (only for non-daily mode)
    if run_mode == RUN_MODE_ACCOUNT:
        analysis_data[RUN_MODE_ACCOUNT] = (cost_matrix, account_names, account_list)

    # Generate individual reports if requested
    for file_format in output_formats:
        export_file = generate_output_file_path(output_dir, run_mode, file_format)
        export_report(
            export_file,
            cost_matrix,
            account_names,
            group_by_type="account",
            output_format=file_format,
        )


def _process_business_unit_mode(
    run_mode: str,
    cost_explorer_client,
    start_date: date,
    end_date: date,
    account_groups: dict,
    shared_services_allocations: dict | None,
    output_dir: Path,
    output_formats: list[str],
    analysis_data: dict,
):
    """Process business unit-based cost reporting.

    Args:
        run_mode: The run mode (bu or bu-daily)
        cost_explorer_client: AWS Cost Explorer client
        start_date: Start date for cost data
        end_date: End date for cost data
        account_groups: Dictionary of business unit account groups
        shared_services_allocations: Optional shared services allocation percentages
        output_dir: Directory for output files
        output_formats: List of formats to generate
        analysis_data: Dictionary to store data for analysis file
    """
    is_daily = run_mode == RUN_MODE_BUSINESS_UNIT_DAILY

    cost_matrix, all_account_costs = calculate_business_unit_costs(
        cost_explorer_client,
        start_date,
        end_date,
        account_groups,
        shared_services_allocations,
        daily_average=is_daily,
    )

    # Store for analysis file (only for non-daily mode)
    if run_mode == RUN_MODE_BUSINESS_UNIT:
        analysis_data[RUN_MODE_BUSINESS_UNIT] = (
            cost_matrix,
            account_groups,
            all_account_costs,
        )

    # Generate individual reports if requested
    for file_format in output_formats:
        export_file = generate_output_file_path(output_dir, run_mode, file_format)
        export_report(
            export_file,
            cost_matrix,
            account_groups,
            group_by_type="bu",
            output_format=file_format,
        )


def _process_service_mode(
    run_mode: str,
    cost_explorer_client,
    start_date: date,
    end_date: date,
    service_aggregations: dict,
    top_cost_count: int,
    output_dir: Path,
    output_formats: list[str],
    analysis_data: dict,
    service_exclusions: list = None,
):
    """Process service-based cost reporting.

    Args:
        run_mode: The run mode (service or service-daily)
        cost_explorer_client: AWS Cost Explorer client
        start_date: Start date for cost data
        end_date: End date for cost data
        service_aggregations: Dictionary of service aggregation rules
        top_cost_count: Number of top services to include
        output_dir: Directory for output files
        output_formats: List of formats to generate
        analysis_data: Dictionary to store data for analysis file
        service_exclusions: List of services to exclude from reports
    """
    is_daily = run_mode == RUN_MODE_SERVICE_DAILY

    cost_matrix = calculate_service_costs(
        cost_explorer_client,
        start_date,
        end_date,
        service_aggregations,
        top_cost_count=top_cost_count,
        daily_average=is_daily,
        service_exclusions=service_exclusions,
    )

    service_list = get_service_list(cost_matrix, service_aggregations)

    # Store for analysis file (only for non-daily mode)
    if run_mode == RUN_MODE_SERVICE:
        analysis_data[RUN_MODE_SERVICE] = (cost_matrix, service_list)

    # Generate individual reports if requested
    for file_format in output_formats:
        export_file = generate_output_file_path(output_dir, run_mode, file_format)
        export_report(
            export_file,
            cost_matrix,
            service_list,
            group_by_type="service",
            output_format=file_format,
        )


def _generate_analysis_file(output_dir: Path, analysis_data: dict):
    """Generate the combined analysis Excel file if all required data is available.

    Args:
        output_dir: Directory for output files
        analysis_data: Dictionary containing data for bu, service, and account modes
    """
    # Check if we have all three required data types
    missing_modes = [mode for mode, data in analysis_data.items() if data is None]
    if missing_modes:
        LOGGER.info(
            f"Skipping analysis file generation - missing required modes: {', '.join(missing_modes)}"
        )
        LOGGER.info(
            f"To generate analysis file, run with modes: {RUN_MODE_ACCOUNT}, {RUN_MODE_BUSINESS_UNIT}, {RUN_MODE_SERVICE}"
        )
        return

    LOGGER.info("Generating analysis Excel file with charts")

    analysis_file = output_dir / f"{DEFAULT_OUTPUT_PREFIX}-analysis.xlsx"

    bu_matrix, bu_groups, all_account_costs = analysis_data[RUN_MODE_BUSINESS_UNIT]
    service_matrix, service_list = analysis_data[RUN_MODE_SERVICE]
    account_matrix, account_names, account_list = analysis_data[RUN_MODE_ACCOUNT]

    # Build account ID to name mapping from Organizations API data
    account_id_to_name = {acc["Id"]: acc["Name"] for acc in account_list}

    export_analysis_excel(
        analysis_file,
        bu_matrix,
        bu_groups,
        service_matrix,
        service_list,
        account_matrix,
        account_names,
        all_account_costs,
        account_id_to_name,
    )

    LOGGER.info(f"Analysis file created: {analysis_file}")


def _generate_year_analysis_file(
    output_dir: Path,
    analysis_data: dict,
    cost_explorer_client,
    organizations_client,
    start_date: date,
    end_date: date,
    account_groups: dict,
    shared_services_allocations: dict,
    service_aggregations: dict,
    top_costs_limits: dict,
):
    """Generate year-level analysis Excel file if all required data is available.

    Args:
        output_dir: Directory for output files
        analysis_data: Dictionary containing data for bu, service, and account modes
        cost_explorer_client: AWS Cost Explorer client
        organizations_client: AWS Organizations client
        start_date: Start date for cost data
        end_date: End date for cost data
        account_groups: Dictionary of business unit account groups
        shared_services_allocations: Optional shared services allocation percentages
        service_aggregations: Dictionary of service aggregation rules
        top_costs_limits: Dictionary with top costs count limits
    """
    # Check if we have all three required data types
    missing_modes = [mode for mode, data in analysis_data.items() if data is None]
    if missing_modes:
        LOGGER.info(
            f"Skipping year analysis file generation - missing required modes: {', '.join(missing_modes)}"
        )
        LOGGER.info(
            f"To generate year analysis file, run with modes: {RUN_MODE_ACCOUNT}, {RUN_MODE_BUSINESS_UNIT}, {RUN_MODE_SERVICE}"
        )
        return

    LOGGER.info("Generating year-level analysis Excel file")

    # Extract the cost matrices from analysis_data
    bu_matrix, bu_groups, all_account_costs = analysis_data[RUN_MODE_BUSINESS_UNIT]
    service_matrix, service_list = analysis_data[RUN_MODE_SERVICE]
    account_matrix, account_names, account_list = analysis_data[RUN_MODE_ACCOUNT]

    # Build account ID to name mapping from Organizations API data
    account_id_to_name = {acc["Id"]: acc["Name"] for acc in account_list}

    # Validate and get year periods
    try:
        year1_months, year2_months = validate_year_data(bu_matrix)
    except ValueError as e:
        LOGGER.error(f"Year analysis validation failed: {e}")
        print(f"\nError: {e}")
        print(
            "To generate year analysis, provide at least 24 consecutive months of data."
        )
        print(
            f"Use a custom date range like: --time-period YYYY-MM-DD_YYYY-MM-DD with {MIN_MONTHS_FOR_YEAR_ANALYSIS}+ months"
        )
        return

    # Generate year analysis file
    year_analysis_file = output_dir / f"{DEFAULT_OUTPUT_PREFIX}-year-analysis.xlsx"

    export_year_analysis_excel(
        year_analysis_file,
        bu_matrix,
        bu_groups,
        service_matrix,
        service_list,
        account_matrix,
        account_names,
        year1_months,
        year2_months,
        all_account_costs,
        account_id_to_name,
    )

    LOGGER.info(f"Year analysis file created: {year_analysis_file}")


def main():
    """Main entry point for the AWS Monthly Costs tool."""
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or higher is required")

    # Parse command-line arguments
    args = parse_arguments()

    # Configure logging
    configure_logging(debug_logging=args.debug_logging, info_logging=args.info_logging)

    LOGGER.debug(f"Configuration Arguments: {args}")

    # Resolve file paths
    aws_config_file_path = Path(os.path.expanduser(args.aws_config_file)).absolute()
    config_file_path = Path(args.config_file).absolute()

    # Load configuration
    config_settings = load_configuration(config_file_path)
    account_groups = config_settings["account-groups"]
    shared_services_allocations = (
        config_settings["ss-allocations"] if args.include_shared_services else None
    )
    service_aggregations = config_settings["service-aggregations"]
    service_exclusions = config_settings.get("service-exclusions", [])
    top_costs_limits = config_settings["top-costs-count"]

    # Parse time period
    start_date, end_date = parse_time_period(args.time_period)
    LOGGER.debug(f"Time period: {start_date} to {end_date}")

    # Create and validate AWS session
    aws_session = create_aws_session(args.profile, aws_config_file_path)

    # Create AWS clients
    cost_explorer_client = aws_session.client("ce")

    # Only create organizations client if needed for account-related run modes
    organizations_client = None
    if any(
        mode in [RUN_MODE_ACCOUNT, RUN_MODE_ACCOUNT_DAILY] for mode in args.run_modes
    ):
        organizations_client = aws_session.client("organizations")

    # Create output directory
    output_dir = Path(DEFAULT_OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output formats for individual reports
    output_formats = determine_output_formats(args.output_format)

    # Store data for analysis Excel file (requires account, bu, and service modes)
    analysis_data = {
        RUN_MODE_BUSINESS_UNIT: None,
        RUN_MODE_SERVICE: None,
        RUN_MODE_ACCOUNT: None,
    }

    # Process each run mode
    for run_mode in args.run_modes:
        LOGGER.info(f"Processing run mode: {run_mode}")

        if run_mode in [RUN_MODE_ACCOUNT, RUN_MODE_ACCOUNT_DAILY]:
            _process_account_mode(
                run_mode,
                cost_explorer_client,
                organizations_client,
                start_date,
                end_date,
                top_costs_limits["account"] + 1,
                output_dir,
                output_formats,
                analysis_data,
            )
        elif run_mode in [RUN_MODE_BUSINESS_UNIT, RUN_MODE_BUSINESS_UNIT_DAILY]:
            _process_business_unit_mode(
                run_mode,
                cost_explorer_client,
                start_date,
                end_date,
                account_groups,
                shared_services_allocations,
                output_dir,
                output_formats,
                analysis_data,
            )
        elif run_mode in [RUN_MODE_SERVICE, RUN_MODE_SERVICE_DAILY]:
            _process_service_mode(
                run_mode,
                cost_explorer_client,
                start_date,
                end_date,
                service_aggregations,
                top_costs_limits["service"] + 1,
                output_dir,
                output_formats,
                analysis_data,
                service_exclusions,
            )

    # Generate analysis Excel file if all required data is available
    _generate_analysis_file(output_dir, analysis_data)

    # Generate year analysis file if time period is "year" mode
    if args.time_period == TIME_PERIOD_YEAR:
        _generate_year_analysis_file(
            output_dir,
            analysis_data,
            cost_explorer_client,
            organizations_client,
            start_date,
            end_date,
            account_groups,
            shared_services_allocations,
            service_aggregations,
            top_costs_limits,
        )


if __name__ == "__main__":
    main()
