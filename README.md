# aws-monthly-costs

A tool to retrieve and report AWS monthly costs across accounts, business units, and services.

## Features

- Generate cost reports by account, business unit, or service
- Support for daily average cost calculations
- **Automatic analysis Excel file with charts and formatted tables** (default output)
- Optional export of individual reports in **CSV** or **Excel** format (XLSX)
- Customizable cost aggregations and groupings
- Shared services cost allocation

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

Generate analysis Excel file only (default):

```bash
amc --profile your-aws-profile
```

This will automatically run the three modes needed for the analysis file (`account`, `bu`, `service`) and create the analysis Excel file (`aws-monthly-costs-analysis.xlsx`) with formatted tables and charts. Individual report files are NOT generated unless explicitly requested with `--output-format`.

### Output Format Options

The `--output-format` option allows you to generate individual report files:
- **Not specified (default)**: Only generates the analysis Excel file
- `csv`: Generates individual CSV files for each run mode
- `excel`: Generates individual Excel (XLSX) files with formatted headers and auto-adjusted columns
- `both`: Generates both CSV and Excel files for each run mode

### Generate Individual Reports

Generate individual CSV reports:

```bash
amc --profile your-aws-profile --output-format csv
```

Generate individual Excel reports:

```bash
amc --profile your-aws-profile --output-format excel
```

Generate both CSV and Excel individual reports:

```bash
amc --profile your-aws-profile --output-format both
```

### Other Options

```bash
# Run with custom options
amc --profile your-aws-profile \
    --config-file path/to/config.yaml \
    --time-period previous \
    --output-format both

# Run specific modes (e.g., include daily modes)
amc --profile your-aws-profile \
    --run-modes account bu service account-daily bu-daily service-daily
```

Run `amc --help` for all available options.

**Note**: By default, the tool runs `account`, `bu`, and `service` modes, which are the three modes required to generate the analysis Excel file.

## Output

### Analysis Excel File (Default Output)

By default, when running all three main modes (`account`, `bu`, and `service` - not the daily versions), an analysis file is automatically generated:
- **File**: `aws-monthly-costs-analysis.xlsx`
- **Content**: Interactive Excel workbook with 6 sheets containing formatted analysis tables and pie charts:
  - **BU Costs**: Monthly totals comparison table (last 2 months) with pie chart showing business unit distribution
  - **BU Costs - Daily Avg**: Daily average comparison for business units
  - **Top Services**: Monthly totals for top 10 services + "Other" with pie chart
  - **Top Services - Daily Avg**: Daily average comparison for top services
  - **Top Accounts**: Monthly totals for top 10 accounts + "Other" with pie chart
  - **Top Accounts - Daily Avg**: Daily average comparison for top accounts
  
**Table Features:**
- Comparison of last 2 months with Difference and % Difference columns
- Conditional formatting: Green for cost decreases (savings), Red for cost increases
- Formatted headers with bold text on light blue background (#D9E1F2)
- Proper number formatting for currency and percentages
- Auto-adjusted column widths for immediate readability
- Business units with zero costs in both months are omitted

**Pie Charts:**
- Large, easy-to-read charts showing cost distribution
- Data labels on pie slices (category name and percentage only)
- No legends (all information shown on slices)
- Top 10 items + "Other" category for services and accounts

### Individual Report Files (Optional)

When `--output-format` is specified, individual reports are generated in the `./outputs/` directory with filenames like:
- CSV format: `aws-monthly-costs-{run_mode}.csv`
- Excel format: `aws-monthly-costs-{run_mode}.xlsx`

**Example**: Generate only the analysis file (default):
```bash
amc --profile your-aws-profile --run-modes account bu service
```

**Example**: Generate analysis file AND individual CSV reports:
```bash
amc --profile your-aws-profile --output-format csv
```

Note: The analysis file is only generated when all three required modes (`account`, `bu`, `service`) are run, which is the default behavior.
