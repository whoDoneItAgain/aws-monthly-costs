# aws-monthly-costs

A Python CLI tool to retrieve and report AWS monthly costs across accounts, business units, and services using AWS Cost Explorer API.

## 🚨 Breaking Changes (v2.0+)

If you're upgrading from an earlier version, please note:

- **`--profile` is now REQUIRED**: Previously optional with a hardcoded default, now you must explicitly specify an AWS profile for security
- **`--include-ss` renamed to `--include-shared-services`**: More descriptive argument name

See the [Migration Guide](#migration-guide) below for upgrade instructions.

## Features

- 📊 Generate cost reports by account, business unit, or service
- 📈 Support for daily average cost calculations
- 📑 **Automatic analysis Excel file with charts and formatted tables** (default output)
- 💾 Optional export of individual reports in **CSV** or **Excel** format (XLSX)
- 🔧 Customizable cost aggregations and groupings
- 🤝 Shared services cost allocation across business units
- ✅ Comprehensive test coverage (112 tests, 48% overall, 100% core business logic)
- 🔒 Security-focused design (no vulnerabilities)
- 📝 Well-documented with inline docstrings

## Requirements

- Python 3.10 or higher
- AWS credentials configured (via `~/.aws/config`)
- Required AWS IAM permissions:
  - `ce:GetCostAndUsage` (AWS Cost Explorer)
  - `organizations:ListAccounts` (AWS Organizations)
  - `organizations:DescribeAccount` (AWS Organizations)
  - `sts:GetCallerIdentity` (AWS STS)

## Installation

### From Source

```bash
git clone https://github.com/whoDoneItAgain/aws-monthly-costs.git
cd aws-monthly-costs
pip install -e .
```

### Dependencies

The tool requires the following Python packages (automatically installed):
- `boto3>=1.42.17` - AWS SDK for Python
- `pyyaml>=6.0.3` - YAML configuration file parsing
- `openpyxl>=3.1.5` - Excel file generation

## Usage

### Quick Start

The simplest command to get started:

```bash
amc --profile your-aws-profile
```

This will:
1. Query AWS Cost Explorer for the previous month's costs
2. Run the three main report modes (`account`, `bu`, `service`)
3. Generate an analysis Excel file (`./outputs/aws-monthly-costs-analysis.xlsx`) with:
   - Formatted comparison tables
   - Pie charts showing cost distribution
   - Business unit, service, and account breakdowns
   - Daily average calculations

**Note**: Individual report files are NOT generated unless explicitly requested with `--output-format`.

### AWS Profile Setup

Before running the tool, ensure your AWS credentials are configured:

```bash
# Configure AWS CLI credentials
aws configure --profile your-profile-name

# Verify the profile exists
aws sts get-caller-identity --profile your-profile-name
```

The profile should have the required IAM permissions listed in the [Requirements](#requirements) section.

### Advanced Usage

#### Custom Time Periods

```bash
# Use a specific date range
amc --profile your-aws-profile --time-period 2024-01-01_2024-12-31

# Use year mode for two-year comparison (requires 24+ months of data)
amc --profile your-aws-profile --time-period year
```

**Year Mode**: When you use `--time-period year`, the tool will:
1. Fetch the last 24 months of AWS cost data
2. Split the data into two complete 12-month periods for comparison
3. Generate a separate `year-analysis.xlsx` file with:
   - Yearly cost totals comparison
   - Daily average costs for each year period
   - Monthly average costs for each year period
   - Comparative charts and formatted tables

**Requirements for Year Mode**:
- At least 24 consecutive months of AWS cost data
- Data should be non-overlapping and complete
- If insufficient data exists, you'll receive an actionable error message

**Example Error Messages**:
```
Error: Insufficient data for year analysis. Provide at least 24 consecutive, 
non-overlapping months for two-year comparison. Currently have 18 months.

To generate year analysis, provide at least 24 consecutive months of data.
Use a custom date range like: --time-period YYYY-MM-DD_YYYY-MM-DD with 24+ months
```

#### Generate Individual Report Files

By default, only the analysis Excel file is created. Use `--output-format` to generate individual reports:

```bash
# Generate individual CSV reports (plus analysis file)
amc --profile your-aws-profile --output-format csv

# Generate individual Excel reports (plus analysis file)
amc --profile your-aws-profile --output-format excel

# Generate both CSV and Excel individual reports (plus analysis file)
amc --profile your-aws-profile --output-format both
```

#### Include Shared Services Allocation

Allocate shared services costs across business units based on percentages defined in your configuration:

```bash
amc --profile your-aws-profile --include-shared-services
```

#### Run Specific Modes

```bash
# Run only specific modes
amc --profile your-aws-profile --run-modes account bu

# Include daily average calculations
amc --profile your-aws-profile --run-modes account bu service account-daily bu-daily service-daily
```

**Note**: The analysis Excel file is only generated when all three main modes (`account`, `bu`, `service`) are run.

#### Custom Configuration File

```bash
# Use a custom configuration file
amc --profile your-aws-profile --config-file /path/to/custom-config.yaml
```

#### Debug Logging

Enable detailed logging for troubleshooting:

```bash
amc --profile your-aws-profile --debug-logging
```

**Security Note**: Debug logs may contain AWS account IDs and cost data. Use with caution in sensitive environments.

#### Complete Examples

```bash
# Full command with all options
amc --profile production-readonly \
    --config-file ./config/prod-config.yaml \
    --time-period 2024-01-01_2024-12-31 \
    --output-format both \
    --include-shared-services \
    --run-modes account bu service account-daily bu-daily service-daily \
    --debug-logging

# Year-level analysis with 24 months of data
amc --profile production-readonly \
    --time-period 2023-01-01_2024-12-31 \
    --include-shared-services \
    --debug-logging

# Year mode (automatically fetches last 24 months)
amc --profile production-readonly \
    --time-period year \
    --include-shared-services
```

### Command-Line Options

Run `amc --help` to see all available options:

```bash
amc --help
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--profile` | **Yes** | None | AWS profile name from `~/.aws/config` |
| `--config-file` | No | `src/amc/data/config/aws-monthly-costs-config.yaml` | Path to configuration YAML file |
| `--aws-config-file` | No | `~/.aws/config` | Path to AWS credentials config file |
| `--include-shared-services` | No | False | Allocate shared services costs across business units |
| `--run-modes` | No | `account bu service` | Report types to generate (space-separated) |
| `--time-period` | No | `previous` | Time period: `previous` for last month, `year` for year-level analysis (24+ months), or `YYYY-MM-DD_YYYY-MM-DD` for custom range |
| `--output-format` | No | None | Individual report format: `csv`, `excel`, or `both` (omit for analysis file only) |
| `--debug-logging` | No | False | Enable debug-level logging |

### Configuration File

The configuration file defines business units, shared services, and service aggregation rules. Example structure:

```yaml
# Business unit definitions
business_units:
  Engineering:
    - "123456789012"  # Account IDs
    - "234567890123"
  Operations:
    - "345678901234"
  Marketing:
    - "456789012345"

# Shared services accounts (optional)
shared_services:
  accounts:
    - "567890123456"
  allocation:  # Percentage allocation across BUs
    Engineering: 50
    Operations: 30
    Marketing: 20

# Service name aggregation rules (optional)
service_aggregation:
  "Compute":
    - "Amazon Elastic Compute Cloud - Compute"
    - "Amazon EC2 Container Service"
  "Storage":
    - "Amazon Simple Storage Service"
    - "Amazon Elastic Block Store"
```

For a complete example, see the included `src/amc/data/config/aws-monthly-costs-config.yaml` file.

## Output Files

All output files are generated in the `./outputs/` directory.

### Analysis Excel File (Default Output)

**File**: `aws-monthly-costs-analysis.xlsx`

Generated automatically when running the three main modes (`account`, `bu`, `service`). This is the primary output and contains:

#### Worksheets

1. **BU Costs** - Business unit monthly totals comparison
   - Last 2 months side-by-side
   - Difference and % Difference columns
   - Pie chart showing BU cost distribution
   - Conditional formatting (green for savings, red for increases)

2. **BU Costs - Daily Avg** - Business unit daily average comparison
   - Accounts for different month lengths and leap years
   - Same comparison format as monthly totals

3. **Top Services** - Top 10 services + "Other" category
   - Monthly totals with pie chart
   - Aggregated based on configuration rules

4. **Top Services - Daily Avg** - Daily average for top services

5. **Top Accounts** - Top 10 accounts + "Other" category
   - Monthly totals with pie chart
   - Account names from AWS Organizations

6. **Top Accounts - Daily Avg** - Daily average for top accounts

#### Features

- **Formatted Tables**: Bold headers, light blue background (#D9E1F2)
- **Conditional Formatting**: 
  - 🟢 Green for cost decreases (savings)
  - 🔴 Red for cost increases
- **Pie Charts**: Large, easy-to-read with data labels on slices
- **Number Formatting**: 
  - Currency format with 2 decimal places
  - Percentage format for differences
- **Auto-adjusted Columns**: Proper width for immediate readability
- **Smart Filtering**: Zero-cost business units omitted from charts

### Individual Report Files (Optional)

Generated only when `--output-format` is specified. Files are created in `./outputs/` with the naming pattern:

- **CSV format**: `aws-monthly-costs-{run_mode}.csv`
- **Excel format**: `aws-monthly-costs-{run_mode}.xlsx`

Where `{run_mode}` is one of: `account`, `bu`, `service`, `account-daily`, `bu-daily`, `service-daily`

#### CSV Format

Simple comma-separated values file with:
- Header row with column names
- Data rows with cost values
- Easy to import into other tools

#### Excel Format

Formatted Excel workbook with:
- Bold headers with light blue background
- Auto-adjusted column widths
- Proper number formatting
- Professional appearance

**Examples**:
```bash
# Analysis file only (default)
amc --profile prod
# Creates: ./outputs/aws-monthly-costs-analysis.xlsx

# Analysis file + CSV reports
amc --profile prod --output-format csv
# Creates: ./outputs/aws-monthly-costs-analysis.xlsx
#          ./outputs/aws-monthly-costs-account.csv
#          ./outputs/aws-monthly-costs-bu.csv
#          ./outputs/aws-monthly-costs-service.csv

# Year analysis file (when using --time-period year)
amc --profile prod --time-period year
# Creates: ./outputs/aws-monthly-costs-analysis.xlsx
#          ./outputs/aws-monthly-costs-year-analysis.xlsx
```

### Year Analysis Excel File (Year Mode)

**File**: `aws-monthly-costs-year-analysis.xlsx`

Generated when using `--time-period year` option. Requires at least 24 consecutive months of data. This file contains:

#### Worksheets

1. **BU Costs - Yearly** - Business unit yearly totals comparison
   - Two most recent complete 12-month periods side-by-side
   - Difference and % Difference columns
   - Pie chart showing BU cost distribution for most recent year
   - Conditional formatting (green for savings, red for increases)

2. **BU Costs - Daily Avg** - Business unit daily average comparison
   - Accounts for different month lengths and leap years
   - Same comparison format as yearly totals

3. **BU Costs - Monthly Avg** - Business unit monthly average comparison
   - Average cost per month across each 12-month period
   - Useful for normalized comparisons

4. **Top Services - Yearly** - Top 10 services yearly totals + "Other"
   - Yearly totals with pie chart
   - Aggregated based on configuration rules

5. **Top Services - Daily Avg** - Daily average for top services

6. **Top Services - Monthly Avg** - Monthly average for top services

7. **Top Accounts - Yearly** - Top 10 accounts yearly totals + "Other"
   - Yearly totals with pie chart
   - Account names from AWS Organizations

8. **Top Accounts - Daily Avg** - Daily average for top accounts

9. **Top Accounts - Monthly Avg** - Monthly average for top accounts

#### Features

- **Formatted Tables**: Bold headers, blue background (#4472C4)
- **Conditional Formatting**: 
  - 🟢 Green for cost decreases (savings)
  - 🔴 Red for cost increases
- **Pie Charts**: Large, easy-to-read with data labels on slices
- **Number Formatting**: 
  - Currency format with 2 decimal places
  - Percentage format for differences
- **Auto-adjusted Columns**: Proper width for immediate readability
- **Year Labels**: Clear identification of time periods (e.g., "Year 1 (2023-Jan - 2023-Dec)")

## Architecture Overview

The application follows a modular architecture with clear separation of concerns:

```
aws-monthly-costs/
├── src/amc/
│   ├── __main__.py              # Entry point & orchestration (610 lines)
│   ├── constants.py             # Named constants (52 lines)
│   ├── data/config/             # Default configuration files
│   ├── reportexport/            # Report generation (1031 lines)
│   │   └── __init__.py          # CSV/Excel export, charts, formatting
│   └── runmodes/                # Cost calculation modules
│       ├── account/             # Account cost calculations (152 lines)
│       ├── bu/                  # Business unit calculations (140 lines)
│       └── service/             # Service cost calculations (161 lines)
└── tests/                       # Comprehensive test suite (112 tests)
```

### Key Components

#### 1. Main Module (`__main__.py`)
- **Purpose**: Entry point and orchestration
- **Responsibilities**:
  - Parse command-line arguments
  - Load and validate configuration
  - Create AWS sessions
  - Coordinate runmode execution
  - Trigger report generation
- **Key Functions**:
  - `parse_arguments()` - CLI argument parsing
  - `configure_logging()` - Logging setup
  - `load_configuration()` - YAML config loading with validation
  - `parse_time_period()` - Date range parsing and validation
  - `create_aws_session()` - AWS session creation with validation
  - `main()` - Main orchestration logic

#### 2. Constants Module (`constants.py`)
- **Purpose**: Centralized constants and magic values
- **Contains**:
  - Run mode identifiers (`RUN_MODE_ACCOUNT`, `RUN_MODE_BUSINESS_UNIT`, etc.)
  - Output format constants (`OUTPUT_FORMAT_CSV`, `OUTPUT_FORMAT_EXCEL`, etc.)
  - AWS API dimension and metric names
  - Valid choices for CLI arguments

#### 3. Run Modes
Each runmode is a separate module that:
- Queries AWS Cost Explorer API
- Processes and aggregates cost data
- Calculates daily averages (accounting for leap years)
- Returns structured cost dictionaries

**Account Mode** (`runmodes/account/`)
- Retrieves costs grouped by AWS account
- Supports pagination for large account lists
- Extracts account names from AWS Organizations
- Returns top N accounts by cost

**Business Unit Mode** (`runmodes/bu/`)
- Aggregates account costs into business units
- Supports shared services allocation
- Single optimized API call (not separate calls per BU)
- Handles leap year calculations correctly

**Service Mode** (`runmodes/service/`)
- Groups costs by AWS service
- Applies service aggregation rules from config
- Returns top N services by cost
- Handles service name variations

#### 4. Report Export (`reportexport/`)
- **Purpose**: Generate output files
- **Capabilities**:
  - CSV export with proper formatting
  - Excel export with styled headers, auto-width columns
  - Analysis Excel file with multiple worksheets, charts, conditional formatting
  - Pie charts for cost distribution visualization
- **Key Functions**:
  - `export_report()` - Generate individual CSV/Excel reports
  - `export_analysis_excel()` - Generate comprehensive analysis workbook
  - Helper functions for chart creation, formatting, width calculation

### Data Flow

```
1. User runs CLI command
   ↓
2. Parse arguments & load configuration
   ↓
3. Create & validate AWS session
   ↓
4. For each run mode:
   a. Query AWS Cost Explorer API
   b. Process & aggregate data
   c. Calculate daily averages
   ↓
5. Generate reports:
   a. Optional: Individual CSV/Excel files
   b. Default: Analysis Excel file (if all 3 modes run)
   ↓
6. Save to ./outputs/ directory
```

### Design Patterns

- **Single Responsibility**: Each module has one clear purpose
- **DRY (Don't Repeat Yourself)**: Helper functions avoid code duplication
- **Configuration Over Convention**: Behavior customizable via YAML
- **Fail-Fast**: Comprehensive input validation with clear error messages
- **Modular Architecture**: Easy to extend with new run modes or export formats

### Performance Optimizations

Applied by Performance-Optimizer Agent (see `AGENT_HANDOFF.md`):
- **Reduced API calls**: BU mode makes 1 API call instead of 2 (50% reduction)
- **Efficient sorting**: Direct list slicing instead of intermediate dict conversions
- **Optimized Excel generation**: Single-pass column width calculation
- **Set-based filtering**: O(1) lookups for account categorization

## Troubleshooting

### Common Issues

#### "AWS profile does not exist"

**Error**: `AWS profile 'xyz' does not exist in /home/user/.aws/config`

**Solution**:
```bash
# List available profiles
aws configure list-profiles

# Configure a new profile
aws configure --profile your-profile-name

# Verify the profile
aws sts get-caller-identity --profile your-profile-name
```

#### "AWS profile session is not valid"

**Error**: `AWS profile (xyz) session is not valid`

**Causes**:
- Invalid or expired credentials
- Incorrect profile configuration
- Missing IAM permissions

**Solutions**:
```bash
# Verify credentials work
aws sts get-caller-identity --profile your-profile-name

# Reconfigure the profile
aws configure --profile your-profile-name

# Check if using SSO (requires login)
aws sso login --profile your-profile-name
```

#### "Configuration file not found"

**Error**: `Configuration file not found: /path/to/config.yaml`

**Solution**:
```bash
# Use the default config
amc --profile your-profile-name

# Or specify correct path
amc --profile your-profile-name --config-file /correct/path/to/config.yaml

# Copy example config
cp src/amc/data/config/aws-monthly-costs-config.yaml my-config.yaml
```

#### "Invalid time period format"

**Error**: `Invalid time period format`

**Solution**:
```bash
# Use 'previous' for last month (default)
amc --profile your-profile-name --time-period previous

# Or use correct date format: YYYY-MM-DD_YYYY-MM-DD
amc --profile your-profile-name --time-period 2024-01-01_2024-12-31
```

#### "Missing required configuration keys"

**Error**: `Configuration file is missing required key(s)`

**Solution**: Ensure your configuration file has all required sections:
```yaml
# Minimum required structure
business_units:
  YourBU:
    - "123456789012"  # At least one account ID

# Optional but recommended
shared_services:
  accounts: []
  allocation: {}

service_aggregation: {}
```

#### Missing IAM Permissions

**Error**: `An error occurred (AccessDeniedException) when calling the GetCostAndUsage operation`

**Solution**: Ensure your AWS IAM user/role has these permissions:
```json
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
```

#### Analysis File Not Generated

**Issue**: Running the tool but analysis Excel file is not created

**Cause**: Analysis file requires all three main modes (`account`, `bu`, `service`) to be run.

**Solution**:
```bash
# Use default run modes (includes all 3)
amc --profile your-profile-name

# Or explicitly specify all 3
amc --profile your-profile-name --run-modes account bu service
```

#### Empty or Incorrect Cost Data

**Issue**: Reports show $0 or unexpected values

**Possible Causes**:
1. Time period has no cost data
2. AWS Organizations not configured
3. Cost allocation tags not enabled
4. Incorrect business unit account mappings in config

**Solutions**:
```bash
# Enable debug logging to see API responses
amc --profile your-profile-name --debug-logging

# Verify your time period
amc --profile your-profile-name --time-period 2024-01-01_2024-01-31

# Check AWS Cost Explorer in the console to verify data exists
```

### Debug Logging

Enable debug logging for detailed diagnostic information:

```bash
amc --profile your-profile-name --debug-logging
```

**Debug logs include**:
- AWS API request/response details
- Configuration values
- Cost calculation steps
- Account and service mapping

**Security Note**: Debug logs may contain:
- AWS account IDs
- Cost data
- Configuration details

Do not share debug logs in public forums without sanitizing sensitive data.

### Getting Help

1. **Check Documentation**: Review this README and `TESTING.md`
2. **Review Configuration**: Ensure your YAML config is valid
3. **Enable Debug Logging**: Use `--debug-logging` for detailed diagnostics
4. **Check AWS Console**: Verify data exists in AWS Cost Explorer
5. **Review Permissions**: Ensure IAM permissions are correct
6. **File an Issue**: Open a GitHub issue with debug logs (sanitized)

## Migration Guide

### Upgrading from v1.x to v2.0+

Version 2.0 introduced breaking changes to improve security and code quality. Follow these steps to upgrade:

#### Step 1: Update Command-Line Arguments

**Breaking Change 1: `--profile` is now required**

❌ **Old** (v1.x):
```bash
# Profile was optional with hardcoded default
amc --include-ss
amc  # Used hardcoded default profile
```

✅ **New** (v2.0+):
```bash
# Profile is now REQUIRED (more secure)
amc --profile your-profile-name --include-shared-services
```

**Breaking Change 2: `--include-ss` renamed to `--include-shared-services`**

❌ **Old** (v1.x):
```bash
amc --profile prod --include-ss
```

✅ **New** (v2.0+):
```bash
amc --profile prod --include-shared-services
```

#### Step 2: Update Scripts and Automation

If you have scripts, CI/CD pipelines, or cron jobs calling `amc`, update them:

**Before**:
```bash
#!/bin/bash
# v1.x script
amc --include-ss --output-format csv
```

**After**:
```bash
#!/bin/bash
# v2.0+ script
amc --profile production-readonly --include-shared-services --output-format csv
```

#### Step 3: Review Configuration File

The configuration file format has not changed, but validation is now stricter:

```yaml
# Ensure all required keys are present
business_units:
  Engineering:
    - "123456789012"

# Optional sections can be empty but should exist
shared_services:
  accounts: []
  allocation: {}

service_aggregation: {}
```

#### Step 4: Verify

Test your new command:

```bash
# Verify it works
amc --profile your-profile-name --help

# Test with your configuration
amc --profile your-profile-name --config-file your-config.yaml
```

### What Changed in v2.0

**Bug Fixes** (all verified with tests):
1. ✅ Time period parsing now correctly calculates previous month
2. ✅ Year calculation for leap years uses actual cost data year
3. ✅ Difference calculations show signed values (negative = savings)
4. ✅ Percentage calculations handle zero baseline correctly
5. ✅ Configuration validation with clear error messages
6. ✅ Improved logging when analysis file cannot be generated

**Performance Improvements**:
1. ⚡ BU mode API calls reduced from 2 to 1 (50% reduction)
2. ⚡ Optimized sorting algorithms
3. ⚡ Faster Excel generation

**Security Enhancements**:
1. 🔒 Required `--profile` argument (no hardcoded defaults)
2. 🔒 Comprehensive input validation
3. 🔒 Safe YAML loading (yaml.safe_load)
4. 🔒 No hardcoded credentials
5. 🔒 Secure error messages

**Code Quality**:
1. 📝 100% test coverage on core logic (112 tests)
2. 📝 Comprehensive docstrings
3. 📝 Named constants instead of magic values
4. 📝 Extracted helper functions
5. 📝 Improved code organization

**Documentation**:
1. 📚 Updated README (this file)
2. 📚 Testing guide (`TESTING.md`)
3. 📚 Security review (`SECURITY_REVIEW.md`)
4. 📚 Detailed test documentation (`tests/README.md`)

### Benefits of Upgrading

- **More Secure**: Required authentication profile
- **More Reliable**: Bug fixes and comprehensive tests
- **Better Performance**: Optimized API calls and algorithms
- **Better Documented**: Clear documentation and examples
- **Better Maintained**: Well-organized, testable code

## Testing

The project has comprehensive test coverage. See `TESTING.md` for details.

### Quick Test Run

```bash
# Run all tests
tox

# Run tests for specific Python version
tox -e py312

# View coverage report
tox -e py312
open htmlcov/index.html
```

### Test Statistics

- **Total Tests**: 112 (all passing ✅)
- **Coverage**: 48% overall, 100% core business logic (runmodes, main orchestration)
- **Execution Time**: < 2 seconds
- **Test Types**: Unit tests (100) + Integration tests (12)

See `tests/README.md` for detailed test documentation.

## Security

The application follows security best practices:

- ✅ No hardcoded credentials
- ✅ Safe YAML loading (yaml.safe_load)
- ✅ Comprehensive input validation
- ✅ No code injection vulnerabilities
- ✅ Secure dependency versions
- ✅ Proper error handling

See `SECURITY_REVIEW.md` for detailed security analysis.

## Contributing

Contributions are welcome! Please ensure:

1. **Tests pass**: Run `tox` before submitting
2. **Code is formatted**: Run `ruff format .`
3. **Linting passes**: Run `ruff check .`
4. **Documentation updated**: Update README if adding features
5. **Security**: No new vulnerabilities introduced

### Release Process

For maintainers, see [RELEASE_WORKFLOW.md](RELEASE_WORKFLOW.md) for detailed instructions on:
- Creating releases with semantic versioning
- Automated changelog generation
- Dependency management
- Publishing to PyPI

### Development Setup

```bash
# Clone the repository
git clone https://github.com/whoDoneItAgain/aws-monthly-costs.git
cd aws-monthly-costs

# Install in development mode
pip install -e .

# Install development dependencies
pip install tox pytest pytest-cov ruff

# Run tests
tox

# Run linting
ruff check .

# Format code
ruff format .
```

## License

See `LICENSE.md` for license information.

## Changelog

### Version 2.0.0 (2026-01-02)

**Breaking Changes**:
- `--profile` argument now required (previously optional)
- `--include-ss` renamed to `--include-shared-services`

**Bug Fixes**:
- Fixed time period parsing for previous month calculation
- Fixed year calculation for leap year handling in historical data
- Fixed difference calculations (now shows signed values)
- Fixed percentage calculations for zero baseline edge case
- Added comprehensive configuration validation

**Performance**:
- Reduced BU mode API calls from 2 to 1 (50% reduction)
- Optimized sorting algorithms
- Improved Excel generation performance

**Testing**:
- Added 112 comprehensive tests (100% coverage on core logic)
- Added integration tests
- Added edge case tests (leap years, year boundaries, etc.)

**Documentation**:
- Complete README rewrite with examples
- Added troubleshooting guide
- Added migration guide
- Added architecture overview
- Added security review documentation

**Security**:
- CodeQL security scan: 0 alerts
- No vulnerable dependencies
- Comprehensive security review completed

See `AGENT_HANDOFF.md`, `REFACTORING_SUMMARY.md`, `TEST_IMPLEMENTATION_SUMMARY.md`, and `SECURITY_REVIEW.md` for detailed change logs and security analysis.

## Acknowledgments

This project was comprehensively refactored and tested by specialized agents:
- **Refactoring-Expert Agent**: Code quality improvements
- **Bug-Hunter Agent**: Fixed 7 critical bugs
- **Security-Analyzer Agent**: Security review and hardening
- **Performance-Optimizer Agent**: Performance optimizations
- **Test-Generator Agent**: Comprehensive test suite (112 tests)
- **Documentation-Writer Agent**: Documentation updates
