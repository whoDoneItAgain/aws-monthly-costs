# aws-monthly-costs

A tool to retrieve and report AWS monthly costs across accounts, business units, and services.

## Features

- Generate cost reports by account, business unit, or service
- Support for daily average cost calculations
- Export reports in **CSV** and **Excel** format (XLSX) simultaneously (default)
- **Automatic analysis Excel file with charts** when all three data types are available
- Customizable cost aggregations and groupings
- Shared services cost allocation

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

Generate cost reports in both CSV and Excel formats (default):

```bash
amc --profile your-aws-profile
```

This will create both `.csv` and `.xlsx` files for each run mode.

### Output Format Options

The `--output-format` option allows you to choose the output format:
- `both` (default): Generates both CSV and Excel files
- `csv`: Generates only CSV files
- `excel`: Generates only Excel (XLSX) files with formatted headers and auto-adjusted columns

### Generate Only CSV

```bash
amc --profile your-aws-profile --output-format csv
```

### Generate Only Excel

```bash
amc --profile your-aws-profile --output-format excel
```

### Other Options

```bash
amc --profile your-aws-profile \
    --config-file path/to/config.yaml \
    --run-modes account bu service \
    --time-period previous \
    --output-format both
```

Run `amc --help` for all available options.

## Output

Reports are generated in the `./outputs/` directory with filenames like:
- CSV format: `aws-monthly-costs-{run_mode}.csv`
- Excel format: `aws-monthly-costs-{run_mode}.xlsx`

By default, both formats are generated for each run mode.

### Analysis Excel File with Charts

When you run all three main modes (`account`, `bu`, and `service` - not the daily versions), an additional analysis file is automatically generated:
- **File**: `aws-monthly-costs-analysis.xlsx`
- **Content**: Interactive Excel workbook with:
  - Data sheets: `aws-spend` (BU data), `aws-spend-top-services` (service data), `aws-spend-top-accounts` (account data)
  - Analysis sheets with charts:
    - **Analysis - BU Costs**: Area chart and line chart showing cost trends by business unit
    - **Analysis - Services**: Bar chart showing top services by cost
    - **Analysis - Accounts**: Pie chart showing cost distribution by account
  - All charts are generated programmatically and automatically populated with your cost data
  
This file provides visual insights into your AWS spending patterns without requiring any external templates.

**Example**: To generate the analysis file:
```bash
amc --profile your-aws-profile --run-modes account bu service
```
