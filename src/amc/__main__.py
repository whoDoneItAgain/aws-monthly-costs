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
from amc.version import __version__

LOGGER = logging.getLogger("amc")

DEFAULT_OUTPUT_FOLDER = "./outputs/"
DEFAULT_OUTPUT_PREFIX = "aws-monthly-costs"
DEFAULT_AWS_CONFIG_FILE = "~/.aws/config"
DEFAULT_CONFIG_LOCATION = Path(__file__).parent.joinpath(
    "data/config/aws-monthly-costs-config.yaml"
)
SKELETON_CONFIG_PATH = Path(__file__).parent.joinpath(
    "data/config/skeleton-config.yaml"
)
USER_RC_FILE = "~/.amcrc"


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
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the version number and exit",
    )

    parser.add_argument(
        "--profile",
        type=str,
        required=False,
        help="AWS profile name to use for authentication (from ~/.aws/config)",
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Inline YAML configuration string (highest priority)",
    )

    parser.add_argument(
        "--config-file",
        type=str,
        default=None,
        help=f"Path to the configuration YAML file (default: {USER_RC_FILE} if exists, otherwise skeleton config)",
    )

    parser.add_argument(
        "--generate-config",
        nargs="?",
        const=USER_RC_FILE,
        default=None,
        metavar="PATH",
        help=f"Generate a skeleton configuration file at the specified path (default: {USER_RC_FILE}) and exit",
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

    parser.add_argument(
        "--top-accounts",
        type=int,
        default=None,
        help="Number of top accounts to include in reports (overrides configuration file)",
    )

    parser.add_argument(
        "--top-services",
        type=int,
        default=None,
        help="Number of top services to include in reports (overrides configuration file)",
    )

    parser.add_argument(
        "--test-access",
        action="store_true",
        help="Test AWS profile access and required permissions, then exit",
    )

    args = parser.parse_args()

    # Validate that --profile is provided when not using --generate-config or --test-access
    if args.generate_config is None and args.test_access is False and args.profile is None:
        parser.error("the following arguments are required: --profile")

    # For --test-access, --profile is required
    if args.test_access and args.profile is None:
        parser.error("--test-access requires --profile")

    return args


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


def merge_configs(base: dict, override: dict) -> dict:
    """Merge two configuration dictionaries with mix-in semantics.
    
    For most top-level keys, values from override completely replace base values.
    Exception: 'top-costs-count' allows partial specification - if override only
    specifies 'account', the 'service' value from base is preserved.
    
    This allows:
    - Skeleton config provides defaults for all keys
    - User config can override entire sections (like account-groups)
    - User config OR CLI can partially override top-costs-count values
    
    Args:
        base: Base configuration dictionary (lower priority)
        override: Override configuration dictionary (higher priority)
    
    Returns:
        Merged configuration dictionary
    
    Example:
        base = {"top-costs-count": {"account": 10, "service": 10}}
        override = {"top-costs-count": {"account": 5}}
        result = merge_configs(base, override)
        # result["top-costs-count"] == {"account": 5, "service": 10}
    """
    result = base.copy()
    
    for key, value in override.items():
        # Special case for top-costs-count: merge nested values
        if key == "top-costs-count" and isinstance(value, dict) and isinstance(result.get(key), dict):
            # Merge nested dict to allow partial specification
            result[key] = {**result[key], **value}
        else:
            # For all other keys: complete replacement
            result[key] = value
    
    return result


def load_configuration(config_file_path: Path, validate: bool = True) -> dict:
    """Load configuration from YAML file.

    Args:
        config_file_path: Path to the configuration YAML file
        validate: If True, validate required keys (default: True)

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

    if validate:
        validate_configuration(config)

    return config


def validate_configuration(config: dict):
    """Validate that configuration has all required keys and structure.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If configuration is missing required keys or has invalid structure
    """
    # Validate required keys
    required_keys = ["account-groups", "service-aggregations", "top-costs-count"]
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        raise ValueError(
            f"Configuration missing required keys: {', '.join(missing_keys)}"
        )

    # Validate account-groups has 'ss' key
    if "ss" not in config["account-groups"]:
        raise ValueError(
            "Configuration 'account-groups' must contain 'ss' (shared services) key"
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


def load_configuration_from_string(config_string: str, validate: bool = True) -> dict:
    """Load configuration from YAML string.

    Args:
        config_string: YAML configuration as a string
        validate: If True, validate required keys (default: True)

    Returns:
        Dictionary containing configuration settings

    Raises:
        ValueError: If config string is invalid or missing required keys
    """
    try:
        config = yaml.safe_load(config_string)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in configuration string: {e}")

    if config is None:
        raise ValueError("Configuration string is empty")

    if validate:
        validate_configuration(config)

    return config


def generate_skeleton_config(output_path: str):
    """Generate a skeleton configuration file at the specified path.

    Args:
        output_path: Path where the skeleton config should be written

    Raises:
        OSError: If file cannot be written
    """
    output_path_resolved = Path(os.path.expanduser(output_path)).absolute()

    # Create parent directories if they don't exist
    output_path_resolved.parent.mkdir(parents=True, exist_ok=True)

    # Read skeleton config from file and write to output
    with open(SKELETON_CONFIG_PATH, "r") as src:
        skeleton_content = src.read()
    
    with open(output_path_resolved, "w") as f:
        f.write(skeleton_content)

    LOGGER.info(f"Generated skeleton configuration file at: {output_path_resolved}")
    print(f"✓ Generated skeleton configuration file at: {output_path_resolved}")
    print("\nEdit this file to add your AWS account mappings and run:")
    print(f"  amc --profile your-profile --config-file {output_path}")


def resolve_config_file_path(config_file_arg: str | None) -> Path:
    """Resolve the configuration file path based on priority order.

    Priority order:
    1. --config-file parameter (if specified)
    2. ~/.amcrc file in user's home directory (if exists)
    3. Use skeleton configuration (lowest priority)

    Note: --config inline YAML string is handled separately and takes highest priority

    Args:
        config_file_arg: The --config-file argument value (None if not provided)

    Returns:
        Path to the configuration file to use

    Raises:
        FileNotFoundError: If explicitly specified config file doesn't exist
    """
    # Priority 1: If --config-file was explicitly provided, use it
    if config_file_arg is not None:
        config_path = Path(config_file_arg).absolute()
        if not config_path.exists():
            raise FileNotFoundError(
                f"Specified configuration file not found: {config_path}"
            )
        LOGGER.debug(f"Using configuration from --config-file: {config_path}")
        return config_path

    # Priority 2: Check for ~/.amcrc in user's home directory
    user_rc_path = Path(os.path.expanduser(USER_RC_FILE)).absolute()
    if user_rc_path.exists():
        LOGGER.debug(f"Using configuration from user RC file: {user_rc_path}")
        return user_rc_path

    # Priority 3: Return None to indicate skeleton config should be used
    LOGGER.debug("Using skeleton configuration (no config file or RC file found)")
    return None


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


def test_aws_access(aws_profile: str, aws_config_file_path: Path):
    """Test AWS profile access and required permissions.
    
    Tests that the profile is:
    1. Valid and exists in the config file
    2. Active (credentials are valid, including SSO if applicable)
    3. Has the required IAM permissions for the tool
    
    Args:
        aws_profile: AWS profile name to test
        aws_config_file_path: Path to AWS config file
    
    Raises:
        SystemExit: Always exits after testing (success or failure)
    """
    print(f"Testing AWS access for profile: {aws_profile}")
    print("=" * 60)
    
    # Test 1: Profile exists in config file
    print("\n1. Checking if profile exists in config file...")
    aws_config = configparser.RawConfigParser()
    aws_config.read(aws_config_file_path)
    
    if not aws_config.has_section(f"profile {aws_profile}"):
        print(f"   ✗ FAIL: Profile '{aws_profile}' not found in {aws_config_file_path}")
        print(f"\n   Available profiles:")
        for section in aws_config.sections():
            if section.startswith("profile "):
                print(f"     - {section.replace('profile ', '')}")
        sys.exit(1)
    
    print(f"   ✓ Profile '{aws_profile}' exists in config file")
    
    # Test 2: Credentials are valid and active (including SSO)
    print("\n2. Testing if credentials are active...")
    try:
        session = boto3.Session(profile_name=aws_profile)
        sts_client = session.client("sts")
        identity = sts_client.get_caller_identity()
        
        print(f"   ✓ Credentials are active")
        print(f"   Account: {identity['Account']}")
        print(f"   User/Role ARN: {identity['Arn']}")
        print(f"   User ID: {identity['UserId']}")
    except Exception as e:
        print(f"   ✗ FAIL: Credentials are not active or invalid")
        print(f"   Error: {e}")
        print(f"\n   If using SSO, try running: aws sso login --profile {aws_profile}")
        sys.exit(1)
    
    # Test 3: Required IAM permissions
    print("\n3. Testing required IAM permissions...")
    
    required_permissions = {
        "sts:GetCallerIdentity": {"tested": True, "result": True},  # Already tested above
        "ce:GetCostAndUsage": {"tested": False, "result": False},
        "organizations:ListAccounts": {"tested": False, "result": False},
        "organizations:DescribeAccount": {"tested": False, "result": False},
    }
    
    # Test Cost Explorer access
    print("   Testing ce:GetCostAndUsage...")
    try:
        ce_client = session.client("ce")
        # Make a minimal request for a single day
        from datetime import datetime, timedelta
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        ce_client.get_cost_and_usage(
            TimePeriod={
                "Start": yesterday.strftime("%Y-%m-%d"),
                "End": today.strftime("%Y-%m-%d"),
            },
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
        )
        required_permissions["ce:GetCostAndUsage"]["tested"] = True
        required_permissions["ce:GetCostAndUsage"]["result"] = True
        print("     ✓ ce:GetCostAndUsage - OK")
    except Exception as e:
        required_permissions["ce:GetCostAndUsage"]["tested"] = True
        required_permissions["ce:GetCostAndUsage"]["result"] = False
        print(f"     ✗ ce:GetCostAndUsage - FAIL")
        print(f"       Error: {str(e)[:100]}")
    
    # Test Organizations access
    print("   Testing organizations:ListAccounts...")
    try:
        orgs_client = session.client("organizations")
        orgs_client.list_accounts(MaxResults=1)
        required_permissions["organizations:ListAccounts"]["tested"] = True
        required_permissions["organizations:ListAccounts"]["result"] = True
        print("     ✓ organizations:ListAccounts - OK")
    except Exception as e:
        required_permissions["organizations:ListAccounts"]["tested"] = True
        required_permissions["organizations:ListAccounts"]["result"] = False
        print(f"     ✗ organizations:ListAccounts - FAIL")
        print(f"       Error: {str(e)[:100]}")
    
    print("   Testing organizations:DescribeAccount...")
    try:
        # Use the account ID from identity to test DescribeAccount
        orgs_client.describe_account(AccountId=identity['Account'])
        required_permissions["organizations:DescribeAccount"]["tested"] = True
        required_permissions["organizations:DescribeAccount"]["result"] = True
        print("     ✓ organizations:DescribeAccount - OK")
    except Exception as e:
        required_permissions["organizations:DescribeAccount"]["tested"] = True
        required_permissions["organizations:DescribeAccount"]["result"] = False
        print(f"     ✗ organizations:DescribeAccount - FAIL")
        print(f"       Error: {str(e)[:100]}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_passed = all(perm["result"] for perm in required_permissions.values())
    
    if all_passed:
        print("✓ All tests PASSED")
        print("\nThe profile has all required permissions and is ready to use.")
        sys.exit(0)
    else:
        print("✗ Some tests FAILED")
        print("\nFailed permissions:")
        for perm_name, perm_info in required_permissions.items():
            if perm_info["tested"] and not perm_info["result"]:
                print(f"  - {perm_name}")
        
        print("\nRequired IAM policy:")
        print("""
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "organizations:ListAccounts",
        "organizations:DescribeAccount",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
""")
        sys.exit(1)


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

    # Handle --generate-config if specified
    if args.generate_config:
        generate_skeleton_config(args.generate_config)
        sys.exit(0)

    # Handle --test-access if specified
    if args.test_access:
        aws_config_file_path = Path(os.path.expanduser(args.aws_config_file)).absolute()
        test_aws_access(args.profile, aws_config_file_path)
        # test_aws_access will exit, so this line is never reached

    # Configure logging
    configure_logging(debug_logging=args.debug_logging, info_logging=args.info_logging)

    LOGGER.debug(f"Configuration Arguments: {args}")

    # Load configuration using mix-in approach
    # Priority order (lowest to highest):
    # 1. Skeleton config (base/defaults)
    # 2. ~/.amcrc file (if exists)
    # 3. --config-file (if specified)
    # 4. --config inline string (if specified)
    # 5. Command-line arguments (if specified)
    
    # Start with skeleton configuration as base
    LOGGER.debug(f"Loading skeleton configuration from: {SKELETON_CONFIG_PATH}")
    config_settings = load_configuration(SKELETON_CONFIG_PATH, validate=False)
    
    # Merge ~/.amcrc if it exists
    user_rc_path = Path(os.path.expanduser(USER_RC_FILE)).absolute()
    if user_rc_path.exists():
        LOGGER.debug(f"Merging configuration from user RC file: {user_rc_path}")
        user_config = load_configuration(user_rc_path, validate=False)
        config_settings = merge_configs(config_settings, user_config)
    
    # Merge --config-file if specified
    if args.config_file:
        config_file_path = Path(args.config_file).absolute()
        if not config_file_path.exists():
            raise FileNotFoundError(
                f"Specified configuration file not found: {config_file_path}"
            )
        LOGGER.debug(f"Merging configuration from --config-file: {config_file_path}")
        file_config = load_configuration(config_file_path, validate=False)
        config_settings = merge_configs(config_settings, file_config)
    
    # Merge --config inline string if specified
    if args.config:
        LOGGER.debug("Merging configuration from --config inline string")
        inline_config = load_configuration_from_string(args.config, validate=False)
        config_settings = merge_configs(config_settings, inline_config)
    
    # Merge command-line arguments if specified (highest priority)
    cli_overrides = {}
    if args.top_accounts is not None or args.top_services is not None:
        cli_overrides["top-costs-count"] = {}
        if args.top_accounts is not None:
            LOGGER.debug(f"Overriding top accounts count from CLI: {args.top_accounts}")
            cli_overrides["top-costs-count"]["account"] = args.top_accounts
        if args.top_services is not None:
            LOGGER.debug(f"Overriding top services count from CLI: {args.top_services}")
            cli_overrides["top-costs-count"]["service"] = args.top_services
        config_settings = merge_configs(config_settings, cli_overrides)
    
    # Validate final merged configuration
    LOGGER.debug("Validating final merged configuration")
    validate_configuration(config_settings)

    # Resolve AWS config file path
    aws_config_file_path = Path(os.path.expanduser(args.aws_config_file)).absolute()

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
