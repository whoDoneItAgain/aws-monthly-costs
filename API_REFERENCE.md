# API Reference

This document provides a reference for the main modules, functions, and classes in the aws-monthly-costs codebase.

## Main Module (`amc.__main__`)

### `parse_arguments() -> argparse.Namespace`
Parse command-line arguments for the AWS Monthly Costs tool.

**Returns**: Parsed command-line arguments

### `configure_logging(debug_logging: bool = False, info_logging: bool = False) -> None`
Configure logging for the application.

**Args**:
- `debug_logging`: Enable debug-level logging
- `info_logging`: Enable info-level logging

### `load_configuration(config_file_path: Path) -> dict`
Load and validate configuration from YAML file.

**Args**:
- `config_file_path`: Path to YAML configuration file

**Returns**: Configuration dictionary

**Raises**: 
- `FileNotFoundError`: If config file doesn't exist
- `ValueError`: If config is invalid or missing required keys

### `parse_time_period(time_period_str: str) -> tuple[date, date]`
Parse time period string into start and end dates.

**Args**:
- `time_period_str`: Period string ('month', 'year', or 'YYYY-MM-DD_YYYY-MM-DD')

**Returns**: Tuple of (start_date, end_date)

**Raises**:
- `ValueError`: If time period format is invalid

### `create_aws_session(aws_profile: str, aws_config_file_path: Path) -> boto3.Session`
Create and validate AWS session.

**Args**:
- `aws_profile`: AWS profile name
- `aws_config_file_path`: Path to AWS config file

**Returns**: Validated boto3 Session object

**Raises**:
- `ValueError`: If profile doesn't exist or session is invalid

## Runmodes

### Account Mode (`amc.runmodes.account`)

#### `calculate_account_costs(...) -> dict`
Calculate costs grouped by AWS account.

**Args**:
- `cost_explorer_client`: Boto3 Cost Explorer client
- `organizations_client`: Boto3 Organizations client
- `start_date`: Start date for cost query
- `end_date`: End date for cost query
- `top_count`: Number of top accounts to return
- `daily_average`: Calculate daily averages if True

**Returns**: Dictionary with cost matrix and account list

#### `get_account_names(organizations_client) -> list[dict]`
Get list of AWS accounts with names from Organizations API.

**Args**:
- `organizations_client`: Boto3 Organizations client

**Returns**: List of account dictionaries with 'Id' and 'Name' keys

### Business Unit Mode (`amc.runmodes.bu`)

#### `calculate_business_unit_costs(...) -> dict`
Calculate costs aggregated by business unit.

**Args**:
- `cost_explorer_client`: Boto3 Cost Explorer client
- `organizations_client`: Boto3 Organizations client
- `start_date`: Start date for cost query
- `end_date`: End date for cost query
- `business_unit_accounts`: Dict mapping BU names to account ID lists
- `shared_services_allocation`: Optional dict with 'accounts' and 'allocation' keys
- `include_shared_services`: Whether to allocate shared services costs
- `daily_average`: Calculate daily averages if True

**Returns**: Cost matrix dictionary organized by month and business unit

### Service Mode (`amc.runmodes.service`)

#### `calculate_service_costs(...) -> dict`
Calculate costs grouped by AWS service.

**Args**:
- `cost_explorer_client`: Boto3 Cost Explorer client
- `start_date`: Start date for cost query
- `end_date`: End date for cost query
- `service_aggregations`: Dict mapping aggregation names to service lists
- `top_count`: Number of top services to return
- `daily_average`: Calculate daily averages if True

**Returns**: Cost matrix dictionary organized by month and service

#### `get_service_list(cost_explorer_client, start_date, end_date) -> list[str]`
Get list of all services with costs in the time period.

**Args**:
- `cost_explorer_client`: Boto3 Cost Explorer client
- `start_date`: Start date for query
- `end_date`: End date for query

**Returns**: Sorted list of service names

## Common Utilities (`amc.runmodes.common`)

### `parse_cost_month(period_start_date: str) -> tuple[datetime, str]`
Parse period start date and return datetime object and formatted month name.

**Args**:
- `period_start_date`: Start date string in format YYYY-MM-DD

**Returns**: Tuple of (datetime object, formatted month name as YYYY-Mon)

### `calculate_days_in_month(year: int, month: int) -> int`
Calculate the number of days in a given month, accounting for leap years.

**Args**:
- `year`: Year (e.g., 2024)
- `month`: Month (1-12)

**Returns**: Number of days in the month

### `calculate_daily_average(cost_amount: float, days_in_month: int) -> float`
Calculate daily average cost for a month.

**Args**:
- `cost_amount`: Total monthly cost
- `days_in_month`: Number of days in the month

**Returns**: Daily average cost (rounded to 2 decimal places)

### `round_cost_values(cost_dict: dict) -> dict`
Round all cost values in dictionary to 2 decimal places.

**Args**:
- `cost_dict`: Dictionary of cost values

**Returns**: New dictionary with rounded values

### `add_total_to_cost_dict(cost_dict: dict) -> dict`
Add 'total' key with sum of all values to cost dictionary.

**Args**:
- `cost_dict`: Dictionary of cost values

**Returns**: Dictionary with 'total' key added

### `sort_by_cost_descending(cost_dict: dict, exclude_keys: list = None) -> list[tuple]`
Sort cost dictionary by values in descending order.

**Args**:
- `cost_dict`: Dictionary of cost values
- `exclude_keys`: Optional list of keys to exclude from sorting

**Returns**: List of (key, value) tuples sorted by value descending

### `build_top_n_matrix(cost_matrix: dict, top_n: int) -> dict`
Build matrix with only top N items by most recent month cost.

**Args**:
- `cost_matrix`: Full cost matrix
- `top_n`: Number of top items to include

**Returns**: Matrix with top N items plus "Other" category

## Report Export (`amc.reportexport`)

### `export_report(cost_matrix: dict, file_path: Path, file_format: str) -> None`
Export cost matrix to CSV or Excel file.

**Args**:
- `cost_matrix`: Cost data to export
- `file_path`: Output file path
- `file_format`: 'csv' or 'excel'

### `export_analysis_excel(output_dir: Path, analysis_data: dict) -> None`
Generate comprehensive analysis Excel workbook.

**Args**:
- `output_dir`: Output directory path
- `analysis_data`: Dictionary containing cost matrices for account, bu, and service modes

### `export_year_analysis_excel(output_dir: Path, analysis_data: dict, year_labels: list) -> None`
Generate year-level analysis Excel workbook.

**Args**:
- `output_dir`: Output directory path
- `analysis_data`: Dictionary containing cost matrices for account, bu, and service modes
- `year_labels`: List of two year label strings (e.g., ["Year 1 (2023)", "Year 2 (2024)"])

## Report Export Utilities

### Calculations (`amc.reportexport.calculations`)

#### `calculate_percentage_difference(val1: float, val2: float) -> float`
Calculate percentage difference between two values with edge case handling.

**Returns**: Percentage difference as decimal (e.g., 0.25 for 25%)

#### `calculate_difference(val1: float, val2: float) -> float`
Calculate absolute difference between two values.

#### `calculate_percentage_spend(value: float, total: float) -> float`
Calculate what percentage a value represents of a total.

### Formatting (`amc.reportexport.formatting`)

#### `apply_header_style(cell, font=None, fill=None, alignment=None) -> None`
Apply formatting styles to a cell for header rows.

#### `apply_currency_format(worksheet, column: str, start_row: int, end_row: int) -> None`
Apply currency number format to a column range.

#### `apply_percentage_format(worksheet, column: str, start_row: int, end_row: int) -> None`
Apply percentage number format to a column range.

#### `auto_adjust_column_widths(worksheet, max_width: int = 50) -> None`
Auto-adjust all column widths based on content.

**Args**:
- `worksheet`: openpyxl worksheet object
- `max_width`: Maximum column width to set

### Charts (`amc.reportexport.charts`)

#### `create_pie_chart(**kwargs) -> PieChart`
Create a configured pie chart with sensible defaults.

**Args**: Various chart configuration options (title, height, width, etc.)

**Returns**: Configured openpyxl PieChart object

#### `add_data_to_pie_chart(chart, worksheet, data_col, label_col, start_row, end_row) -> None`
Add data and labels to a pie chart.

#### `add_chart_to_worksheet(worksheet, chart, anchor_cell: str) -> None`
Position and add chart to worksheet.

**Args**:
- `worksheet`: openpyxl worksheet
- `chart`: openpyxl chart object
- `anchor_cell`: Cell reference for chart position (e.g., "F2")

## Constants (`amc.constants`)

### Run Mode Constants
- `RUN_MODE_ACCOUNT = "account"`
- `RUN_MODE_BUSINESS_UNIT = "bu"`
- `RUN_MODE_SERVICE = "service"`
- `RUN_MODE_ACCOUNT_DAILY = "account-daily"`
- `RUN_MODE_BUSINESS_UNIT_DAILY = "bu-daily"`
- `RUN_MODE_SERVICE_DAILY = "service-daily"`

### Output Format Constants
- `OUTPUT_FORMAT_CSV = "csv"`
- `OUTPUT_FORMAT_EXCEL = "excel"`
- `OUTPUT_FORMAT_BOTH = "both"`

### Time Period Constants
- `TIME_PERIOD_MONTH = "month"`
- `TIME_PERIOD_YEAR = "year"`

### Other Constants
- `MIN_MONTHS_FOR_YEAR_ANALYSIS = 24`
- `DEFAULT_RUN_MODES = [RUN_MODE_ACCOUNT, RUN_MODE_BUSINESS_UNIT, RUN_MODE_SERVICE]`
- `VALID_RUN_MODES`: List of all valid run mode values
- `VALID_OUTPUT_FORMATS`: List of all valid output format values

## AWS API Dimensions and Metrics

### Cost Explorer Dimensions
- `DIMENSION_LINKED_ACCOUNT = "LINKED_ACCOUNT"`
- `DIMENSION_SERVICE = "SERVICE"`

### Cost Explorer Metrics
- `METRIC_UNBLENDED_COST = "UnblendedCost"`

### Cost Explorer Granularity
- `GRANULARITY_MONTHLY = "MONTHLY"`

## Version Information (`amc.version`)

### `VERSION`
Current version string (e.g., "0.1.2")

## Usage Examples

### Using the Account Runmode Programmatically

```python
import boto3
from datetime import date
from amc.runmodes.account import calculate_account_costs

# Create AWS clients
session = boto3.Session(profile_name='my-profile')
ce_client = session.client('ce')
org_client = session.client('organizations')

# Calculate costs
result = calculate_account_costs(
    cost_explorer_client=ce_client,
    organizations_client=org_client,
    start_date=date(2024, 1, 1),
    end_date=date(2024, 2, 1),
    top_count=10,
    daily_average=False
)

# Access results
cost_matrix = result['cost_matrix']
account_list = result['account_list']
```

### Using Export Functions Programmatically

```python
from pathlib import Path
from amc.reportexport import export_report

# Export to CSV
export_report(
    cost_matrix={'2024-Jan': {'Account A': 1234.56, 'total': 1234.56}},
    file_path=Path('./outputs/costs.csv'),
    file_format='csv'
)

# Export to Excel
export_report(
    cost_matrix={'2024-Jan': {'Account A': 1234.56, 'total': 1234.56}},
    file_path=Path('./outputs/costs.xlsx'),
    file_format='excel'
)
```

### Using Common Utilities

```python
from amc.runmodes.common import (
    calculate_days_in_month,
    calculate_daily_average,
    round_cost_values
)

# Calculate days accounting for leap years
days = calculate_days_in_month(2024, 2)  # Returns 29 for Feb 2024

# Calculate daily average
monthly_cost = 3000.00
daily_avg = calculate_daily_average(monthly_cost, days)  # 103.45

# Round all values in a dictionary
costs = {'Account A': 1234.567, 'Account B': 5678.901}
rounded = round_cost_values(costs)  # {'Account A': 1234.57, 'Account B': 5678.90}
```

## Type Hints

The codebase uses Python type hints extensively. Common types used:

- `dict`: Generic dictionary
- `list[dict]`: List of dictionaries
- `tuple[date, date]`: Tuple containing two date objects
- `Path`: pathlib.Path object
- `boto3.Session`: Boto3 session object
- `str | None`: String or None (union type)

## Error Handling

All functions use specific exception types:

- `ValueError`: For invalid input or configuration
- `FileNotFoundError`: For missing files
- `KeyError`: For missing dictionary keys (typically in AWS responses)
- `ClientError`: From boto3 for AWS API errors

Example error handling pattern:

```python
try:
    result = calculate_account_costs(...)
except ValueError as e:
    print(f"Configuration error: {e}")
except ClientError as e:
    print(f"AWS API error: {e}")
```

## See Also

- [README.md](README.md) - User-facing documentation
- [TESTING.md](TESTING.md) - Testing guide
- [AGENT_HANDOFF.md](AGENT_HANDOFF.md) - Detailed implementation notes
- [SECURITY_REVIEW.md](SECURITY_REVIEW.md) - Security analysis
